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



app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

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

# AES-256 Encryption Setup
ENCRYPTION_KEY = Fernet.generate_key()
cipher = Fernet(ENCRYPTION_KEY)

rooms = {}
user_message_times = defaultdict(list)

MESSAGE_LIMIT = 5
TIME_WINDOW = 10

@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join")
        create = request.form.get("create")

        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        if create == "CreateRoom":
            room = "".join(random.choices(ascii_uppercase, k=4))
            rooms[room] = {"members": 1, "messages": []}
            session["room"] = room
            session["name"] = name
            print(f"✅ Room created: {room}. Redirecting to /room")
            return redirect(url_for("room"))

        if code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)

        session["room"] = code
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("home.html")

@app.route("/room")
def room():
    room = session.get("room")
    if not room or not session.get("name") or room not in rooms:
        return redirect(url_for("home"))

    return render_template("room.html", code=room, messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):
    room = session.get("room")
    name = session.get("name")
    if room not in rooms:
        return

    formatted_message = format_message(data["data"])
    content = {"name": name, "message": formatted_message}

    send(content, to=room)
    rooms[room]["messages"].append(content)

    print(f"{name} said: {data['data']}")


@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]

    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")

# Secure File Upload Route
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part"})

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No selected file"})

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    # Encrypt file content
    encrypted_data = cipher.encrypt(file.read())
    with open(file_path, "wb") as f:
        f.write(encrypted_data)

    file_url = f"/download/{filename}"
    return jsonify({"success": True, "file_url": file_url, "file_name": filename})

# File Download Route (with Decryption)
@app.route("/download/<filename>")
def download_file(filename):
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    # Decrypt the file before sending
    with open(file_path, "rb") as f:
        decrypted_data = cipher.decrypt(f.read())

    decrypted_file_path = os.path.join(app.config["UPLOAD_FOLDER"], f"decrypted_{filename}")
    with open(decrypted_file_path, "wb") as decrypted_file:
        decrypted_file.write(decrypted_data)

    return send_from_directory(app.config["UPLOAD_FOLDER"], f"decrypted_{filename}")

if __name__ == "__main__":
    print("🚀 Server is starting... Visit http://localhost:8080")
    socketio.run(app, host='0.0.0.0', port=8080, debug=True)