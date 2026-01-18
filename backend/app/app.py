# app.py
# This work is licensed under the terms of the MIT license

import datetime
import sys
import time
import uuid
from datetime import timedelta
from pyexpat import model

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
from db import init_db, session_local
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from flask_socketio import (
    SocketIO,
    close_room,
    disconnect,
    emit,
    join_room,
    leave_room,
    send,
)
from loguru import logger
from models import MemberRole, Room_members
from sqlalchemy.exc import NoResultFound, SQLAlchemyError

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
    logger=False,
    engineio_logger=False,
    message_queue="redis://redis:6379/0",
    async_mode="gevent",
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
for i in range(50):
    try:
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        redis_client.ping()
        break
    except redis.exceptions.ConnectionError:
        print("Waiting for Redis...")
        time.sleep(1)
else:
    raise RuntimeError("Cannot connect to Redis")

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
            "iat": datetime.datetime.now(datetime.UTC),
            "exp": datetime.datetime.now(datetime.UTC)
            + timedelta(seconds=JWT_ACCESS_EXPIRATION),
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
            "iat": datetime.datetime.now(datetime.UTC),
            "exp": datetime.datetime.now(datetime.UTC)
            + timedelta(seconds=JWT_REFRESH_EXPIRATION),
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


def verify_refresh_token(token: str):
    payload = jwt.decode(
        token,
        JWT_REFRESH_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
    )
    if payload.get("typ") != "refresh":
        raise jwt.InvalidTokenError("Not a refresh token")
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
    if data is None:
        g.log.error("Invalid request data")
        return jsonify({"error": "Invalid request data"}), 400
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

    except SQLAlchemyError as e:
        g.db.rollback()
        g.log.error("Login failed", error=str(e))
        return jsonify({"error": "Invalid credentials"}), 401


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
    except SQLAlchemyError as e:
        g.db.rollback()
        g.log.error("Signup failed", error=str(e))
        return jsonify({"error": "Signup failed"}), 500


@app.route("/refresh", methods=["POST"])
def refresh_token():
    json_data = request.get_json()
    if not json_data:
        g.log.error("Missing JSON data")
        return jsonify({"error": "Missing JSON data"}), 400

    token = json_data.get("refresh_token")
    if not token:
        g.log.error("Missing token")
        return jsonify({"error": "Missing token"}), 400
    g.log.info("Received refresh token", token=token)

    try:
        payload = verify_refresh_token(token)
    except jwt.ExpiredSignatureError:
        g.log.error("Token expired", token=token)
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        g.log.error("Invalid token")
        return jsonify({"error": "Invalid token"}), 401

    if payload["typ"] != "refresh":
        g.log.error("Invalid token type")
        return jsonify({"error": "Invalid token type"}), 401

    new_token = create_access_token(payload["sub"])
    return jsonify({"access_token": new_token}), 200


# -------------------------
# room management
# -------------------------
@app.route("/room", methods=["POST"])
def create_room():
    data = request.get_json()
    if data is None:
        g.log.error("Invalid request data")
        return jsonify({"error": "Invalid request data"}), 400
    token = data.get("token")
    room_name = data.get("room_name")

    if not token:
        g.log.error("Token not provided")
        return jsonify({"error": "Token not provided"}), 400

    try:
        payload = verify_access_token(token)
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    try:
        room = models.Room(room_name=room_name)
        g.db.add(room)
        g.db.flush()
        g.db.add(
            models.Room_members(
                room_id=room.room_id,
                user_id=payload["sub"],
                member_role=MemberRole.OWNER,
            )
        )
        g.db.commit()
        room_id = room.room_id
    except Exception as e:
        g.db.rollback()
        g.log.error("Room creation failed", error=str(e))
        return jsonify({"error": "Room creation failed"}), 500

    return jsonify({"message": "Room created", "room_id": room_id}), 201


@app.route("/room/<string:room_id>", methods=["DELETE"])
def delete_room(room_id):
    data = request.get_json()
    if data is None:
        g.log.error("Invalid request data")
        return jsonify({"error": "Invalid request data"}), 400
    token = data.get("token")

    if not token:
        g.log.error("Token not provided")
        return jsonify({"error": "Token not provided"}), 400

    try:
        verify_access_token(token)
    except jwt.ExpiredSignatureError:
        g.log.error("Token expired", token=token)
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        g.log.error("Invalid token", token=token)
        return jsonify({"error": "Invalid token"}), 401

    try:
        member = g.db.query(models.Room_members).filter_by(room_id=room_id).first()
        room = g.db.query(models.Room).filter_by(room_id=room_id).first()
        if not room:
            g.log.warning("room not found", token=token)
            return jsonify({"error": "room not found"}), 404
        if not member or member.member_role != MemberRole.OWNER:
            g.log.warning("unauthorized room deletion", token=token, room_id=room_id)
            return jsonify({"error": "unauthorized room deletion"}), 403

        g.db.delete(room)
        g.db.commit()
    except SQLAlchemyError as e:
        g.db.rollback()
        g.log.error("Room deletion failed", error=str(e))
        return jsonify({"error": "Room deletion failed"}), 500

    return jsonify({"message": "Room deleted"}), 200


# -------------------------
# members management
# -------------------------
@app.route(
    "/room/<string:room_id>/members/<string:user_id>",
    methods=["GET", "POST", "DELETE", "PATCH"],
)
def manage_member(room_id, user_id):
    data = request.get_json()
    if data is None:
        g.log.error("Invalid request data")
        return jsonify({"error": "Invalid request data"}), 400

    token = data.get("token")
    if not token:
        g.log.warning("Unauthorized member management")
        return jsonify({"error": "Unauthorized member management"}), 403

    try:
        payload = verify_access_token(token)
    except jwt.ExpiredSignatureError:
        g.log.error("Token expired", token=token)
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        g.log.error("Invalid token", token=token)
        return jsonify({"error": "Invalid token"}), 401

    requesting_user_id = payload["sub"]

    # Query the requester once
    requester = (
        g.db.query(models.Room_members)
        .filter_by(user_id=requesting_user_id, room_id=room_id)
        .first()
    )
    if not requester:
        g.log.error(
            "Requesting user not found", user_id=requesting_user_id, room_id=room_id
        )
        return jsonify({"error": "Unauthorized"}), 403

    # GET members (safe, no modification)
    if request.method == "GET":
        try:
            members = (
                g.db.query(models.Room_members, models.User.username)
                .join(models.User, models.Room_members.user_id == models.User.user_id)
                .filter_by(room_id=room_id)
                .all()
            )
            g.log.info("Members retrieved", room_id=room_id)
            return jsonify(
                [
                    {
                        "username": username,
                        "id": member.user_id,
                        "role": member.member_role.name,
                    }
                    for member, username in members
                ]
            ), 200
        except SQLAlchemyError as e:
            g.log.error("Failed to retrieve members", error=str(e))
            return jsonify({"error": "Failed to retrieve members"}), 500

    # POST: add member (must be self)
    elif request.method == "POST":
        if requesting_user_id != user_id:
            g.log.warning("Unauthorized member management")
            return jsonify({"error": "Unauthorized member management"}), 403
        try:
            g.db.add(models.Room_members(user_id=user_id, room_id=room_id))
            g.db.commit()
            g.log.info("Member added", user_id=user_id, room_id=room_id)
            return jsonify({"message": "Member added"}), 200
        except SQLAlchemyError as e:
            g.log.error("Failed to add member", error=str(e))
            g.db.rollback()
            return jsonify({"error": "Failed to add member"}), 500

    # DELETE: remove member
    elif request.method == "DELETE":
        try:
            member = (
                g.db.query(models.Room_members)
                .filter_by(user_id=user_id, room_id=room_id)
                .first()
            )
            if not member:
                g.log.error("Member not found", user_id=user_id, room_id=room_id)
                return jsonify({"error": "Member not found"}), 404

            # Only OWNER or ADMIN can remove members
            if requester.member_role not in [MemberRole.OWNER, MemberRole.ADMIN]:
                g.log.error("Not allowed to remove member", user_id=requesting_user_id)
                return jsonify({"error": "Not allowed"}), 403

            # Admins cannot remove owner
            if (
                member.member_role == MemberRole.OWNER
                and requester.member_role != MemberRole.OWNER
            ):
                g.log.warning("Cannot remove owner", user_id=user_id)
                return jsonify({"error": "Cannot remove owner"}), 403

            g.db.delete(member)
            g.db.commit()
            return jsonify({"message": "Member deleted"}), 200
        except Exception as e:
            g.log.error("Failed to delete member", error=str(e))
            g.db.rollback()
            return jsonify({"error": "Failed to delete member"}), 500

    # PATCH: update member role
    elif request.method == "PATCH":
        try:
            member = (
                g.db.query(models.Room_members)
                .filter_by(user_id=user_id, room_id=room_id)
                .first()
            )
            if not member:
                g.log.error("Member not found", user_id=user_id, room_id=room_id)
                return jsonify({"error": "Member not found"}), 404

            # Only OWNER or ADMIN can modify roles
            if requester.member_role not in [MemberRole.OWNER, MemberRole.ADMIN]:
                g.log.error("Not allowed to modify roles", user_id=requesting_user_id)
                return jsonify({"error": "Not allowed"}), 403

            # Admins cannot modify the owner
            if (
                member.member_role == MemberRole.OWNER
                and requester.member_role != MemberRole.OWNER
            ):
                g.log.warning("Cannot modify owner", user_id=user_id)
                return jsonify({"error": "Cannot modify owner"}), 403

            # Set new role
            try:
                member.member_role = MemberRole(data.get("role"))
            except ValueError:
                g.log.error("Invalid role", role=data.get("role"))
                return jsonify({"error": "Invalid role"}), 400

            # Admins cannot set member to OWNER
            if (
                member.member_role == MemberRole.OWNER
                and requester.member_role != MemberRole.OWNER
            ):
                g.log.warning("Admin cannot assign owner role", user_id=user_id)
                return jsonify({"error": "Cannot assign owner role"}), 403

            g.db.commit()
            return jsonify(
                {"message": "Member updated", "role": member.member_role.name}
            ), 200
        except Exception as e:
            g.log.error("Failed to update member", error=str(e))
            g.db.rollback()
            return jsonify({"error": "Failed to update member"}), 500

    else:
        g.log.error("Invalid method", method=request.method)
        return jsonify({"error": "Invalid method"}), 405


@app.route(
    "/room/<string:room_id>/transfer-owner/<string:new_owner_id>", methods=["PATCH"]
)
def transfer_owner(room_id, new_owner_id):
    data = request.get_json()
    if not data:
        g.log.warning("missing data")
        return jsonify({"error": "missing data"}), 400
    token = data.get("token")

    if not token:
        g.log.warning("missing token")
        return jsonify({"error": "missing token"}), 400

    if not new_owner_id:
        g.log.warning("missing new_owner")
        return jsonify({"error": "missing new_owner"}), 400

    try:
        payload = verify_access_token(token)
    except jwt.ExpiredSignatureError:
        g.log.error("Token expired", token=token)
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        g.log.error("Invalid token", token=token)
        return jsonify({"error": "Invalid token"}), 401
    current_owner_id = payload["sub"]

    try:
        current_owner = (
            g.db.query(Room_members)
            .filter(room_id=room_id, user_id=current_owner_id)
            .one()
        )
        if current_owner.member_role != MemberRole.OWNER:
            g.log.warning("current owner not owner", id=current_owner_id)
            return jsonify({"error": "current owner not owner"}), 403

    except g.db.NoResultFound:
        g.log.warning("current owner not found")
        return jsonify({"error": "current owner not found"}), 404

    try:
        new_owner = (
            g.db.query(Room_members).filter(room_id=room_id, user_id=new_owner_id).one()
        )
        new_owner.member_role = MemberRole.OWNER
        current_owner.member_role = MemberRole.MEMBER
        g.db.commit()
        g.log.info("Ownership transferred", room_id=room_id, new_owner_id=new_owner_id)
        return jsonify({"message": "Ownership transferred"}), 200
    except g.db.NoResultFound:
        g.log.warning("new owner not found")
        return jsonify({"error": "new owner not found"}), 404


# -------------------------
# Socket.IO (JWT)
# -------------------------
socket_state: dict[str, dict] = {}


@socketio.on("join_room")
def socket_connect(data):
    request_id = str(uuid.uuid4())
    log = logger.bind(request_id=request_id)
    room_id = data.get("room")
    token = data.get("token")
    if not token or not room_id:
        log.warning("Socket rejected: no token or room")
        emit("error", {"message": "Invalid token or room"})
        return False

    try:
        payload = verify_access_token(token)
    except jwt.ExpiredSignatureError:
        log.warning("Socket rejected: token expired")
        emit("error", {"message": "Token expired"})
        return False
    except jwt.InvalidTokenError:
        log.warning("Socket rejected: invalid token")
        emit("error", {"message": "Invalid token"})
        return False
    user_id = payload["sub"]
    db = session_local()

    try:
        user = (
            db.query(models.Room_members)
            .filter_by(user_id=user_id, room_id=room_id)
            .first()
        )
        if not user:
            log.warning("Socket rejected: user not found")
            emit("error", {"message": "User not found"})
            return False
        if user.member_role in [MemberRole.BANNED]:
            log.warning("Socket rejected: user is banned", user_id=user_id)
            emit("error", {"message": "User is banned"})
            return False
    except SQLAlchemyError as e:
        db.rollback()
        log.error("Socket rejected: error querying user", error=str(e))
        emit("error", {"message": "Error querying user"})
        return False

    try:
        username = (
            db.query(models.User.username)
            .filter(models.User.user_id == payload["sub"])
            .scalar()
        )
        msgs_query = (
            db.query(models.Message, models.User.username)
            .join(models.User, models.Message.sender == models.User.user_id)
            .filter(models.Message.room_id == room_id)
            .order_by(models.Message.id.asc())
            .limit(100)
            .all()
        )
        msgs = [
            {
                "sender": sender,
                "sender_id": msg.sender,
                "message_id": msg.id,
                "message": msg.message,
                "timestamp": msg.date_created.isoformat(),
            }
            for msg, sender in msgs_query
        ]
        emit("old_messages", msgs)
    except NoResultFound as e:
        log.error("message not found: %s", str(e))
        return False
    except SQLAlchemyError as e:
        log.error("Failed to fetch messages: %s", str(e))
        return False
    finally:
        db.close()
    join_room(room_id)
    socket_state[request.sid] = {
        "user_id": payload["sub"],
        "username": username,
        "request_id": request_id,
        "room_id": room_id,
    }
    log.bind(user_id=payload["sub"]).info("Socket connected")


@socketio.on("message")
def socket_message(data):
    state = socket_state.get(request.sid)
    if not state:
        emit("error", {"error": "Unauthorized"})
        return

    user_id = state["user_id"]
    username = state["username"]
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
        new_msg = models.Message(
            sender=user_id, message=message, room_id=state["room_id"]
        )
        db.add(new_msg)
        db.commit()
        db.refresh(new_msg)
        emit(
            "new_message",
            {
                "sender_id": new_msg.sender,
                "sender": username,
                "message_id": new_msg.id,
                "message": message,
                "timestamp": new_msg.date_updated.isoformat(),
            },
            room=state["room_id"],
            include_self=True,
        )
    except SQLAlchemyError as e:
        db.rollback()
        log.error("Message save failed", error=str(e))
        emit("error", {"error": "DB error"})
    finally:
        db.close()


@socketio.on("disconnect")
def socket_disconnect():
    state = socket_state.pop(request.sid, None)
    if state and "room_id" in state:
        leave_room(state["room_id"])


# -------------------------
# Run
# -------------------------
init_db()
if __name__ == "__main__":
    logger.info("Server started")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
