from flask import Flask, render_template, request, session, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from flask_socketio import join_room, leave_room, send, SocketIO
from cryptography.fernet import Fernet
import os
import random
import time
import re
from collections import defaultdict
from string import ascii_uppercase
import emoji
import bcrypt  
from datetime import datetime, timedelta

app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
app.config["LOGS_FOLDER"] = "logs"
os.makedirs(app.config["LOGS_FOLDER"], exist_ok=True)

# In-memory user store (username: {password: hashed})
users = {}

# In-memory conversation storage:
# Key: dm room id (example: "dm-alice-bob")
# Value: list of messages (each a dict: {"name": sender, "message": message})
conversations = defaultdict(list)
# Track which conversation partners each user has
user_conversations = defaultdict(set)

# Rate limiting variables (if you need them for DMs as well)
user_message_times = defaultdict(list)
MESSAGE_LIMIT = 5
TIME_WINDOW = 10

# AES-256 Encryption Setup
ENCRYPTION_KEY = Fernet.generate_key()
cipher = Fernet(ENCRYPTION_KEY)

socketio = SocketIO(app)

def format_message(message):
    # Emoji Conversion
    message = emoji.emojize(message, language='alias')
    # Bold and Italics
    message = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", message)  # **Bold**
    message = re.sub(r"\*(?!\*)(.*?)\*", r"<i>\1</i>", message)  # *Italics*
    # Links
    message = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2" target="_blank">\1</a>', message)
    return message

def get_dm_room(user1, user2):
    """Returns a unique room id for a DM between two users (order independent)."""
    users_sorted = sorted([user1, user2])
    return f"dm-{users_sorted[0]}-{users_sorted[1]}"

def log_message(room, message):
    timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
    log_file = os.path.join(app.config["LOGS_FOLDER"], f"{room}_{timestamp}.txt")
    with open(log_file, "a", encoding='utf-8') as log:
        log.write(f"{message}\n")

# ----- Routes -----

# Login, logout, and registration remain mostly unchanged.
failed_attempts = {}  # Tracks failed attempts per username
LOCKOUT_TIME = 60    # Lockout duration in seconds 
MAX_ATTEMPTS = 3      # Maximum failed attempts before lockout

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            return render_template("register.html", error="Please fill out both fields.")
        if username in users:
            return render_template("register.html", error="Username already exists.")
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        users[username] = {"password": hashed_password}
        print(f"✅ Registered User: {username}")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # Check if the user is currently locked out
        if username in failed_attempts:
            lockout_info = failed_attempts[username]
            if lockout_info.get("lockout_until") and datetime.now() < lockout_info["lockout_until"]:
                remaining_time = (lockout_info["lockout_until"] - datetime.now()).seconds
                print(f"🚫 {username} is locked out. Remaining time: {remaining_time} seconds")
                return render_template("login.html", error=f"Too many failed attempts. Try again in {remaining_time} seconds.")
        if username not in users:
            print(f"❌ Attempted login with non-existent user: {username}")
            return render_template("login.html", error="User does not exist.")
        if not bcrypt.checkpw(password.encode('utf-8'), users[username]["password"]):
            print(f"❌ Incorrect password for user: {username}")
            if username not in failed_attempts:
                failed_attempts[username] = {"attempts": 1, "lockout_until": None}
            else:
                failed_attempts[username]["attempts"] += 1
            if failed_attempts[username]["attempts"] >= MAX_ATTEMPTS:
                failed_attempts[username]["lockout_until"] = datetime.now() + timedelta(seconds=LOCKOUT_TIME)
                print(f"🚨 {username} has been locked out for {LOCKOUT_TIME} seconds")
                return render_template("login.html", error=f"Too many failed attempts. Try again in {LOCKOUT_TIME // 60} minutes.")
            return render_template("login.html", error="Incorrect password.")
        session["username"] = username
        if username in failed_attempts:
            del failed_attempts[username]  # Reset failed attempts on successful login
        print(f"✅ Successful login for {username}")
        return redirect(url_for("home"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    print("✅ User logged out.")
    return redirect(url_for("login"))

# ----- DM Home/Dashboard -----
@app.route("/", methods=["GET", "POST"])
def home():
    if "username" not in session:
        return redirect(url_for("login"))
    current_user = session["username"]
    error = None
    if request.method == "POST":
        new_partner = request.form.get("new_partner")
        if not new_partner:
            error = "Please enter a username."
        elif new_partner == current_user:
            error = "You cannot DM yourself."
        elif new_partner not in users:
            error = "User does not exist."
        else:
            # Add conversation to both users' lists.
            user_conversations[current_user].add(new_partner)
            user_conversations[new_partner].add(current_user)
            # Redirect to the DM chat room with that user.
            return redirect(url_for("chat", partner=new_partner))
    # Get list of conversation partners for the current user.
    conversations_list = sorted(list(user_conversations[current_user]))
    return render_template("home.html", error=error, conversations=conversations_list, current_user=current_user)

# ----- DM Chat Room -----
@app.route("/chat/<partner>", methods=["GET"])
def chat(partner):
    if "username" not in session:
        return redirect(url_for("login"))
    current_user = session["username"]
    if partner not in users:
        return redirect(url_for("home"))
    if partner == current_user:
        return redirect(url_for("home"))
    # Ensure both users have the conversation listed.
    user_conversations[current_user].add(partner)
    user_conversations[partner].add(current_user)
    # Compute unique DM room id.
    room = get_dm_room(current_user, partner)
    # Retrieve conversation messages.
    messages = conversations[room]
    # Save the current chat partner in session (for use in socket events)
    session["current_partner"] = partner
    return render_template("chat.html", partner=partner, room=room, messages=messages, current_user=current_user)

# ----- SocketIO Events for DM -----
@socketio.on("connect")
def on_connect(auth):
    if "username" not in session or "current_partner" not in session:
        return
    current_user = session["username"]
    partner = session["current_partner"]
    room = get_dm_room(current_user, partner)
    join_room(room)
    send({"name": current_user, "message": "has entered the chat."}, to=room)
    print(f"{current_user} joined DM room {room}")

@socketio.on("message")
def handle_message(data):
    if "username" not in session or "current_partner" not in session:
        return
    current_user = session["username"]
    partner = session["current_partner"]
    room = get_dm_room(current_user, partner)
    formatted_message = format_message(data["data"])
    content = {"name": current_user, "message": formatted_message}
    send(content, to=room)
    conversations[room].append(content)
    log_entry = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {current_user}: {data['data']}"
    log_message(room, log_entry)
    print(f"{current_user} said: {data['data']} in DM with {partner}")

@socketio.on("disconnect")
def on_disconnect():
    if "username" not in session or "current_partner" not in session:
        return
    current_user = session["username"]
    partner = session["current_partner"]
    room = get_dm_room(current_user, partner)
    leave_room(room)
    send({"name": current_user, "message": "has left the chat."}, to=room)
    print(f"{current_user} left DM room {room}")

# ----- File Upload/Download remain the same -----
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part"})
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No selected file"})
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    encrypted_data = cipher.encrypt(file.read())
    with open(file_path, "wb") as f:
        f.write(encrypted_data)
    file_url = f"/download/{filename}"
    return jsonify({"success": True, "file_url": file_url, "file_name": filename})

@app.route("/download/<filename>")
def download_file(filename):
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    with open(file_path, "rb") as f:
        decrypted_data = cipher.decrypt(f.read())
    decrypted_file_path = os.path.join(app.config["UPLOAD_FOLDER"], f"decrypted_{filename}")
    with open(decrypted_file_path, "wb") as decrypted_file:
        decrypted_file.write(decrypted_data)
    return send_from_directory(app.config["UPLOAD_FOLDER"], f"decrypted_{filename}")

if __name__ == "__main__":
    print("🚀 Server is starting... Visit http://localhost:8080")
    socketio.run(app, host='0.0.0.0', port=8080, debug=True)