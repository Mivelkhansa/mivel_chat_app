# app.py
# MIT License

import sys
import uuid
from datetime import datetime, timedelta

import bcrypt
import jwt
import models
import redis
from config import (
    JWT_ACCESS_EXPIRATION,
    JWT_ACCESS_SECRET_KEY,
    JWT_ALGORITHM,
    JWT_REFRESH_EXPIRATION,
    JWT_REFRESH_SECRET_KEY,
    REDIS_HOST,
    REDIS_PORT,
)
from db import session_local
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from loguru import logger

# -------------------------
# App & Socket.IO
# -------------------------
app = Flask(__name__)

socketio = SocketIO(
    app,
    cors_allowed_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:6767",
    ],
    logger=True,
    engineio_logger=True,
)

CORS(
    app,
    origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
)

# -------------------------
# Redis
# -------------------------
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

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
# JWT helpers
# -------------------------
def create_access_token(user_id: str) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "typ": "access",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=JWT_ACCESS_EXPIRATION),
            "iss": "chat_app",
        },
        JWT_ACCESS_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def create_refresh_token(user_id: str) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "typ": "refresh",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=JWT_REFRESH_EXPIRATION),
            "iss": "chat_app",
        },
        JWT_REFRESH_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def verify_access_token(token: str):
    payload = jwt.decode(
        token,
        JWT_ACCESS_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
    )
    if payload.get("typ") != "access":
        raise jwt.InvalidTokenError("Not an access token")
    return payload


# -------------------------
# HTTP lifecycle
# -------------------------
@app.before_request
def start_request():
    g.request_id = str(uuid.uuid4())
    g.db = session_local()

    user_id = None
    auth = request.headers.get("Authorization")

    if auth and auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        try:
            payload = verify_access_token(token)
            user_id = payload["sub"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

    g.log = logger.bind(request_id=g.request_id, user_id=user_id)
    g.log.trace("HTTP request started")


@app.teardown_request
def end_request(exc):
    if hasattr(g, "log"):
        if exc:
            g.log.error("Request failed", error=str(exc))
        g.log.trace("HTTP request ended")

    db = g.pop("db", None)
    if db:
        db.close()


# -------------------------
# Health
# -------------------------
@app.route("/ping")
def ping():
    return "pong"


# -------------------------
# Auth routes
# -------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    g.log.trace("Login attempt", username=username)

    try:
        user = g.db.query(models.User).filter_by(username=username).first()
        if not user or not bcrypt.checkpw(
            password.encode(), user.password_hash.encode()
        ):
            g.log.warning("Login failed")
            return jsonify({"error": "Invalid credentials"}), 401

        return jsonify(
            {
                "access_token": create_access_token(user.user_id),
                "refresh_token": create_refresh_token(user.user_id),
            }
        ), 200

    except Exception:
        g.db.rollback()
        g.log.exception("Login error")
        return jsonify({"error": "Server error"}), 500


@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    try:
        g.db.add(models.User(username=username, password_hash=pw_hash))
        g.db.commit()
        g.log.info("User created", username=username)
        return jsonify({"message": "User created"}), 201
    except Exception:
        g.db.rollback()
        g.log.exception("Signup failed")
        return jsonify({"error": "Signup failed"}), 500


# -------------------------
# Socket.IO (JWT)
# -------------------------
socket_state: dict[str, dict] = {}


@socketio.on("connect")
def socket_connect(auth):
    request_id = str(uuid.uuid4())
    log = logger.bind(request_id=request_id)

    token = auth.get("token") if auth else None
    if not token:
        log.warning("Socket rejected: no token")
        return False

    try:
        payload = verify_access_token(token)
    except jwt.ExpiredSignatureError:
        log.warning("Socket rejected: token expired")
        return False
    except jwt.InvalidTokenError:
        log.warning("Socket rejected: invalid token")
        return False

    socket_state[request.sid] = {
        "user_id": payload["sub"],
        "request_id": request_id,
    }

    db = session_local()
    last_received_id = int(request.args.get("last_received_id", 0))
    try:
        msgs_query = (
            db.query(models.Message, models.User.username)
            .join(models.User, models.Message.sender == models.User.user_id)
            .filter(models.Message.id > last_received_id)
            .order_by(models.Message.date_created.asc())
            .all()
        )
        msgs = [
            {"id": msg.id, "sender": sender, "message": msg.message}
            for msg, sender in msgs_query
        ]
        emit("old_messages", msgs)
    except Exception:
        log.exception("Failed to fetch messages")
        return False
    finally:
        db.close()

    log.bind(user_id=payload["sub"]).info("Socket connected")


@socketio.on("message")
def socket_message(data):
    state = socket_state.get(request.sid)
    if not state:
        emit("error", {"error": "Unauthorized"})
        return

    user_id = state["user_id"]
    log = logger.bind(
        request_id=state["request_id"],
        user_id=user_id,
    )

    message = data.get("message")
    if not message:
        emit("error", {"error": "Message required"})
        return

    db = session_local()
    try:
        db.add(models.Message(sender=user_id, message=message))
        db.commit()
        sender = db.query(models.User).filter_by(user_id=user_id).first()
        emit(
            "new_message",
            {"sender": sender.username, "message": message},
            broadcast=True,
        )
    except Exception:
        db.rollback()
        log.exception("Message save failed")
        emit("error", {"error": "DB error"})
    finally:
        db.close()


@socketio.on("disconnect")
def socket_disconnect():
    socket_state.pop(request.sid, None)


# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
