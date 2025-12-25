# This work is licensed under the terms of the MIT license
# app.py

import os
import sys
import uuid
from datetime import timedelta

import bcrypt
import models
from db import session_local
from flask import Flask, g, jsonify, request, session
from flask_socketio import SocketIO, disconnect, emit
from loguru import logger

# -------------------------
# App & Socket.IO
# -------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
)

# -------------------------
# Logging
# -------------------------
logger.remove(0)

logger.add(
    sys.stderr,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message} | {extra}",
    level="TRACE",
    colorize=True,
)

logger.add(
    "app.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message} | {extra}",
    level="TRACE",
    serialize=True,
)

# -------------------------
# Session / Cookie config
# -------------------------
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = False  # HTTPS only in production
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)


# -------------------------
# Request lifecycle
# -------------------------
@app.before_request
def start_request():
    g.request_id = str(uuid.uuid4())
    g.db = session_local()

    # bind only stable context
    g.log = logger.bind(request_id=g.request_id)
    g.log.trace("Request started")


@app.teardown_request
def end_request(exception):
    if hasattr(g, "log"):
        if exception:
            g.log.error("Request failed", error=str(exception))
        g.log.trace("Request ended")

    db = g.pop("db", None)
    if db is not None:
        db.close()


# -------------------------
# Health check
# -------------------------
@app.route("/ping")
def ping():
    return "pong"


# -------------------------
# LOGIN
# -------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    g.log.trace("Login attempt", username=username)

    try:
        user = g.db.query(models.User).filter(models.User.username == username).first()

        if not user or not bcrypt.checkpw(
            password.encode(),
            user.password_hash.encode(),
        ):
            g.log.warning("Login failed", username=username)
            return jsonify({"error": "Invalid credentials"}), 401

        session.permanent = True
        session["user_id"] = user.id

        # rebind volatile context
        g.log = g.log.bind(user_id=user.id)
        g.log.info("Login succeeded", username=username)

        return jsonify({"message": "Login successful"}), 200

    except Exception:
        g.db.rollback()
        g.log.exception("Login failed due to database error")
        return jsonify({"error": "Database error"}), 500


# -------------------------
# LOGOUT
# -------------------------
@app.route("/logout", methods=["POST"])
def logout():
    user_id = session.get("user_id")
    session.clear()

    g.log.info("Logout succeeded", user_id=user_id)
    return jsonify({"message": "Logged out"}), 200


# -------------------------
# SIGNUP
# -------------------------
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get("username")
    raw_password = data.get("password")

    g.log.trace("Signup attempt", username=username)

    password_hash = bcrypt.hashpw(
        raw_password.encode(),
        bcrypt.gensalt(),
    ).decode()

    try:
        new_user = models.User(
            username=username,
            password_hash=password_hash,
        )
        g.db.add(new_user)
        g.db.commit()

        g.log.info("Signup succeeded", username=username)
        return jsonify({"message": "User created"}), 201

    except Exception:
        g.db.rollback()
        g.log.exception("Signup failed")
        return jsonify({"error": "Failed to create user"}), 500


# -------------------------
# Socket.IO: messages
# -------------------------
@socketio.on("message")
def handle_message(data):
    if "user_id" not in session:
        g.log.warning("Socket message rejected: unauthenticated")
        emit("error", {"error": "Unauthorized"})
        return

    message = data.get("message")
    if not message:
        g.log.warning("Socket message rejected: empty message")
        emit("error", {"error": "Message is required"})
        return

    user_id = session["user_id"]

    try:
        g.db.add(models.Message(sender=user_id, message=message))
        g.db.commit()

        sender = g.db.query(models.User).filter_by(id=user_id).first()

        emit(
            "new_message",
            {"sender": sender.username, "message": message},
            broadcast=True,
        )

    except Exception:
        g.db.rollback()
        g.log.exception("Failed to save socket message")
        emit("db_error", {"error": "Failed to save message"})


# -------------------------
# Socket.IO: connect
# -------------------------
@socketio.on("connect")
def handle_connect():
    if "user_id" not in session:
        g.log.warning("Socket connect rejected: unauthenticated")
        disconnect()
        return

    user_id = session["user_id"]
    g.log = g.log.bind(user_id=user_id)
    g.log.info("Socket connected")

    try:
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

    except Exception:
        g.db.rollback()
        g.log.exception("Failed to fetch message history")
        emit("db_error", {"error": "Failed to fetch messages"})


# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
