# This work is licensed under the terms of the MIT license
# app.py
import os
import sys
from datetime import timedelta

import bcrypt
import models
from db import session_local
from flask import Flask, g, jsonify, request, session
from flask_socketio import SocketIO, disconnect, emit
from loguru import logger

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
)


logger.remove(0)
logger.add(
    sys.stderr,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="TRACE",
    colorize=True,
)

logger.add(
    "app.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="TRACE",
)

# Cookie/session settings
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = False  # requires HTTPS in production
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)


# -------------------------
# DB session handling
# -------------------------
@app.before_request
def start_session():
    logger.trace("Starting session")
    g.db = session_local()


@app.teardown_request
def teardown_session(exception):
    logger.trace("Teardown session")
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.route("/ping")
def ping():
    print("PING HIT")
    return "pong"


# -------------------------
# LOGIN ROUTE
# -------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    # match your model exactly
    user = g.db.query(models.User).filter(models.User.username == username).first()

    if user and bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        session.permanent = True
        session["user_id"] = user.id

        return jsonify({"message": "Login successful"}), 200

    return jsonify({"error": "Invalid credentials"}), 401


# -------------------------
# LOGOUT ROUTE
# -------------------------
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


# -------------------------
# SIGNUP ROUTE
# -------------------------
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get("username")
    raw_password = data.get("password")

    # hash password correctly
    password_hash = bcrypt.hashpw(
        raw_password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    # create new user
    new_user = models.User(username=username, password_hash=password_hash)
    g.db.add(new_user)
    g.db.commit()

    return jsonify({"message": "User created"}), 201


# -------------------------
# Get messages (example)
# -------------------------
# [2025-12-23]todo: change to websocket, keep it for legacy or fallback
@socketio.on("message")
def handle_message(data):
    if "user_id" not in session:
        # you can only see messages if logged in
        emit("error", {"error": "Unauthorized"})
        return

    data = request.get_json()
    message = data.get("message")
    if not message:
        emit("error", {"error": "Message is required"})
        return
    g.db.add(models.Message(sender=session["user_id"], message=message))
    g.db.commit()
    sender = g.db.query(models.User).filter_by(id=session["user_id"]).first()

    emit("new_message", {"sender": sender.username, "message": message}, broadcast=True)


@socketio.on("connect")
def handle_connect():
    if "user_id" not in session:
        disconnect()
        return
    msgs = (
        g.db.query(models.Message, models.User.username)
        .join(models.User, models.Message.sender == models.User.id)
        .order_by(models.Message.date_created.desc())
        .limit(50)
        .all()
    )

    messages = [
        {
            "id": m.Message.id,
            "sender": m.Message.sender,
            "sender_name": m.username,
            "message": m.Message.message,
            "date": m.Message.date_created.isoformat(),
        }
        for m in msgs
    ]
    emit("message_history", messages)


if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
