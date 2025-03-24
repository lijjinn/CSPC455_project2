### User Guide: Real-Time Chat Application

Overview: 

Welcome to the Real-Time DM Chat Application! This secure messaging platform allows you to connect directly with other users through private conversations. The app features secure message exchange, encrypted file uploads, and a user-friendly interface.

## Features
- **Instant messaging** – Messages are delivered in real time.
- **One-on-one conversations** – Users can initiate direct conversations for personal messaging.
- **User-friendly interface** – Simple and intuitive chat layout.
- **Connection notifications** – Get notified when a user joins or leaves a chat room.
- **WebSocket communication** – Real-time message updates by Flask-SocketIO.
- **Secure file sharing** – Encrypted file transfers using AES-256 encryption for enhanced security.
- **Encrypted Chat Logs** – All chat logs are securely encrypted to ensure privacy and prevent data leaks.
- **Rate limiting** – Users can send up to 5 messages within 10 seconds to prevent spam.
- **Brute Force Protection** – Account lockout occurs after 3 failed login attempts with a 60-second cooldown period to mitigate brute force attacks.

## Text Formatting
You can use the following syntax for text formatting in chat messages:
- **Bold:** Use `**your text**` for bold text.
- *Italics:* Use `*your text*` for italicized text.
- [Hyperlinks](https://example.com): Use `[Link Text](URL)` for clickable links.

## Technologies Used
- **Flask** (Python web framework)
- **Flask-SocketIO** (for WebSocket-based real-time communication)
- **HTML, CSS, JavaScript** (for the front-end UI)
- **Socket.IO JavaScript Client** (for message updates)
- **Cryptography Library** (for AES-256 encryption)
- **bcrypt** (for password hashing)

## Installation
### Prerequisites
Ensure you have Python installed on your system.

### Steps to Run Locally
1. Clone the repository:
   ```bash
   git clone <your-repository-url>
   cd <your-repository-folder>
   ```
2. Install dependencies:
   ```bash
   pip install flask flask-socketio cryptography bcrypt emoji
   ```
3. Run the server:
   ```bash
   python main.py
   ```

## Getting Started
- Open your browser
- Navigate to: [http://localhost:8080](http://localhost:8080)

## Using the Application
### Registering a New Account
- Visit `/register`.
- Enter a username and password to create an account.

### Logging In
- Visit `/login`.
- Enter your registered username and password.
- If you exceed 3 failed login attempts, your account will be locked for 60 seconds as a security measure.

### Starting a DM Conversation
- After logging in, visit the homepage.
- Enter the username of the person you wish to DM in the provided field.

### Sending Messages
- Type a message in the chat field and click 'Send'.
- Use the double click on your mouse to use emoji for enhanced expression.
- Use the provided formatting syntax for **bold**, *italics*, or [hyperlinks](https://example.com).

### Uploading Files
- Use the "Upload File" button to securely send files with encryption.

## Rate Limiting
To prevent spam, each user can send a maximum of 5 messages within 10 seconds. If the limit is exceeded, a message will appear stating:

> Rate limit exceeded. Please wait a moment.

This ensures smooth messaging while preventing excessive spam.

## Troubleshooting
### Messages Are Not Sending
- Ensure you have a stable internet connection.
- Try refreshing the page.
- Check if you've hit the rate limit and wait a few seconds.

### Locked Out After Failed Attempts
- Wait 60 seconds before trying to log in again.

### License
This project is licensed under the **MIT License**.

* *used AI for formatting user guide* *







