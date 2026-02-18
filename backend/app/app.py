# app.py
# This work is licensed under the terms of the MIT license

import datetime
import sys
import time
import uuid
from datetime import timedelta, timezone

import bcrypt
import jwt
import redis
from bleach import Linker, clean, linkifier, linkify
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from flask_socketio import (
    SocketIO,
    emit,
)
from flask_socketio import (
    join_room as socket_join_room,
)
from flask_socketio import (
    leave_room as socket_leave_room,
)
from loguru import logger
from markdown import markdown
from sqlalchemy.exc import NoResultFound, SQLAlchemyError

import models
from config import (
    ALLOWED_ATTRIBUTES,
    ALLOWED_PROTOCOLS,
    ALLOWED_TAGS,
    JWT_ACCESS_EXPIRATION,
    JWT_ACCESS_SECRET_KEY,
    JWT_ALGORITHM,
    JWT_REFRESH_EXPIRATION,
    JWT_REFRESH_SECRET_KEY,
    MAX_MESSAGE_LENGTH,
    REDIS_HOST,
    REDIS_PORT,
    user,
)
from db import init_db, session_local
from models import MemberRole, Room_members

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
    origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:6767"],
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
)

linker = Linker(
    callbacks=[
        lambda attrs, new=False: {
            **attrs,
            (None, "target"): "_blank",
            (None, "rel"): "noopener noreferrer nofollow",
        }
    ]
)

# -------------------------
# Redis
# -------------------------
for i in range(50):
    try:
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        redis_client.ping()
        break
    except redis.ConnectionError:
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
            "iat": datetime.datetime.now(timezone.utc),
            "exp": datetime.datetime.now(timezone.utc)
            + timedelta(seconds=JWT_ACCESS_EXPIRATION),
            "iss": "vally_chat_app",
        },
        JWT_ACCESS_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def create_refresh_token(user_id: str) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "typ": "refresh",
            "iat": datetime.datetime.now(timezone.utc),
            "exp": datetime.datetime.now(timezone.utc)
            + timedelta(seconds=JWT_REFRESH_EXPIRATION),
            "iss": "vally_chat_app",
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
# Helper functions
# -------------------------


def get_token_from_header():
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth.split(" ", 1)[1]
    return None


def get_username(db, user_id: str) -> str:
    return (
        db.query(models.User.username).filter(models.User.user_id == user_id).scalar()
    )


def sanitize_message(message: str) -> str:
    sanitized_message = clean(
        message,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    sanitized_message = linkify(
        sanitized_message,
        callbacks=linkifier.DEFAULT_CALLBACKS
        + [
            lambda attrs, new=False: {
                **attrs,
                (None, "target"): "_blank",
                (None, "rel"): "noopener noreferrer nofollow",
            }
        ],
        skip_tags=["pre", "code"],
    )
    return sanitized_message


def render_message(message: str) -> str:
    html = markdown(message, extensions=["extra"])
    sanitized_html = sanitize_message(html)
    return sanitized_html


# -------------------------
# HTTP lifecycle
# -------------------------
@app.before_request
def start_request():
    g.request_id = str(uuid.uuid4())
    g.db = session_local()
    g.log = logger.bind(request_id=g.request_id)

    token = get_token_from_header()
    g.user_id = None
    if token:
        try:
            payload = verify_access_token(token)
            g.user_id = payload["sub"]
        except jwt.ExpiredSignatureError:
            g.log.warning("Token expired for request")
        except jwt.InvalidTokenError:
            g.log.warning("Invalid token for request")

    g.log.bind(user_id=g.user_id)
    g.log.trace(f"{request.method} {request.path} started")


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
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    if not username:
        g.log.error("Username not provided")
        return jsonify({"error": "Username not provided"}), 400
    password = data.get("password")
    if not password:
        g.log.error("Password not provided")
        return jsonify({"error": "Password not provided"}), 400

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
def get_rooms_for_user(user_id: str, db) -> list[dict]:
    rooms = (
        db.query(
            models.Room.room_id, models.Room.room_name, models.Room.room_description
        )
        .join(models.Room_members, models.Room.room_id == models.Room_members.room_id)
        .filter(models.Room_members.user_id == user_id)
        .all()
    )
    return [{"room_id": r, "room_name": n, "room_description": d} for r, n, d in rooms]


@app.route("/room", methods=["POST"])
def create_room():
    token = get_token_from_header()
    data = request.get_json(silent=True) or {}
    room_name = data.get("room_name")
    if not room_name:
        g.log.error("Room name not provided")
        return jsonify({"error": "Room name not provided"}), 400

    room_description = data.get("room_description", "")

    if not token:
        g.log.error("Token not provided")
        return jsonify({"error": "Token not provided"}), 400

    if not room_name:
        g.log.error("Room name not provided")
        return jsonify({"error": "Room name not provided"}), 400

    try:
        payload = verify_access_token(str(token))
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    try:
        room = models.Room(room_name=room_name, room_description=room_description)
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
    token = get_token_from_header()

    if not token:
        g.log.error("Token not provided")
        return jsonify({"error": "Token not provided"}), 400

    try:
        payload = verify_access_token(token)
    except jwt.ExpiredSignatureError:
        g.log.error("Token expired", token=token)
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        g.log.error("Invalid token", token=token)
        return jsonify({"error": "Invalid token"}), 401

    try:
        user_id = payload["sub"]
        member = (
            g.db.query(models.Room_members)
            .filter_by(room_id=room_id, user_id=user_id)
            .first()
        )
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


@app.route("/room/<string:room_id>", methods=["PATCH"])
def update_room(room_id):
    token = get_token_from_header()
    data = request.get_json()
    if not token:
        g.log.error("token is missing")
        return jsonify({"error": "missing token"}), 400

    if request.method != "PATCH":
        g.log.error("Wrong method")
        return jsonify({"error": "Wrong method"}), 400

    try:
        payload = verify_access_token(token)
    except jwt.ExpiredSignatureError:
        g.log.error("Token expired", token=token)
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        g.log.error("Invalid token", token=token)
        return jsonify({"error": "Invalid token"}), 401
    try:
        result = (
            g.db.query(models.User, models.Room_members)
            .join(
                models.Room_members, models.User.user_id == models.Room_members.user_id
            )
            .filter(
                models.User.user_id == payload["sub"],
                models.Room_members.room_id == room_id,
            )
            .first()
        )
        if not result:
            g.log.warning("unauthorized room update", token=token, room_id=room_id)
            return jsonify({"error": "unauthorized room update"}), 403

        user_obj, membership = result

        if membership.member_role not in [MemberRole.ADMIN, MemberRole.OWNER]:
            g.log.warning("unauthorized room update", token=token, room_id=room_id)
            return jsonify({"error": "unauthorized room update"}), 403

        room = g.db.query(models.Room).filter(models.Room.room_id == room_id).first()
        if not room:
            g.log.warning("room not found", token=token, room_id=room_id)
            return jsonify({"error": "room not found"}), 404
        room_name = data.get("room_name")
        room_description = data.get("room_description", "A room")
        if room_name:
            room.room_name = room_name
        if room_description:
            room.room_description = room_description
        g.db.commit()
        return jsonify({"message": "room updated"}), 200
    except SQLAlchemyError as e:
        g.db.rollback()
        g.log.error("Integrity error", token=token, room_id=room_id, error=str(e))
        return jsonify({"error": "Integrity error"}), 400


# return all rooms a user is join
@app.route("/my-rooms", methods=["GET"])
def my_rooms():
    token = get_token_from_header()
    if not token:
        g.log.error("token is missing")
        return jsonify({"error": "missing token"}), 400

    try:
        payload = verify_access_token(token)
    except jwt.ExpiredSignatureError:
        g.log.error("Token expired", token=token)
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        g.log.error("Invalid token", token=token)
        return jsonify({"error": "Invalid token"}), 401

    user_id = payload["sub"]
    try:
        rooms = (
            g.db.query(
                models.Room.room_id, models.Room.room_name, models.Room.room_description
            )
            .join(
                models.Room_members, models.Room.room_id == models.Room_members.room_id
            )
            .filter(
                models.Room_members.user_id == user_id,
                models.Room_members.member_role != MemberRole.BANNED,
            )
            .all()
        )
        rooms_list = [{"id": r, "name": n, "description": d} for r, n, d in rooms]
        g.log.info("Fetched user rooms", user_id=user_id, count=len(rooms_list))
    except Exception as e:
        g.log.error("Failed to fetch rooms", error=str(e))
        return jsonify({"error": "Failed to fetch rooms"}), 500

    return jsonify({"rooms": rooms_list}), 200


# -------------------------
# members management
# -------------------------
@app.route(
    "/room/<string:room_id>/members/<string:user_id>",
    methods=["POST", "DELETE", "PATCH"],
)
def manage_member(room_id, user_id):
    token = get_token_from_header()
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
    try:
        requester = (
            g.db.query(models.Room_members)
            .filter_by(user_id=requesting_user_id, room_id=room_id)
            .first()
        )
    except Exception as e:
        g.log.error("Error querying requester", error=str(e))
        return jsonify({"error": "Internal server error"}), 500

    if request.method != "POST" and not requester:
        g.log.error(
            "Requesting user not found", user_id=requesting_user_id, room_id=room_id
        )
        return jsonify({"error": "Unauthorized"}), 403

    # DELETE: remove member
    # Self-leave (allowed for everyone except owner)
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
            if user_id == requester.user_id:
                if member.member_role == MemberRole.OWNER:
                    return jsonify(
                        {"error": "Owner must transfer ownership or delete room"}
                    ), 403
                try:
                    g.db.delete(member)
                    g.db.commit()
                    return jsonify({"message": "Member deleted"}), 200
                except Exception as e:
                    g.log.error("Failed to delete member", error=str(e))
                    return jsonify({"error": "Failed to delete member"}), 500
            # member couldnt remove admin
            if requester.member_role not in [MemberRole.ADMIN, MemberRole.OWNER]:
                return jsonify(
                    {"error": "Only admins or owners can remove members"}
                ), 403

            if (
                member.member_role == MemberRole.OWNER
                and requester.member_role != MemberRole.OWNER
            ):
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
        data = request.get_json(silent=True) or {}
        new_role = data.get("role")
        if not new_role:
            g.log.error("Missing role", user_id=user_id, room_id=room_id)
            return jsonify({"error": "Missing role"}), 400
        try:
            new_role_enum = MemberRole(new_role)
        except ValueError:
            g.log.error("Invalid role", user_id=user_id, room_id=room_id, role=new_role)
            return jsonify({"error": "Invalid role"}), 400

        if (
            new_role_enum == MemberRole.OWNER
            and requester.member_role != MemberRole.OWNER
        ):
            g.log.error("Cannot change role to OWNER", user_id=user_id, room_id=room_id)
            return jsonify({"error": "Cannot change role to OWNER"}), 400

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
    token = get_token_from_header()

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
            .filter(
                Room_members.room_id == room_id,
                Room_members.user_id == current_owner_id,
            )
            .one()
        )
        if current_owner.member_role != MemberRole.OWNER:
            g.log.warning("current owner not owner", id=current_owner_id)
            return jsonify({"error": "current owner not owner"}), 403

    except NoResultFound:
        g.log.warning("current owner not found")
        return jsonify({"error": "current owner not found"}), 404

    try:
        new_owner = (
            g.db.query(Room_members)
            .filter(
                Room_members.room_id == room_id,
                Room_members.user_id == new_owner_id,
            )
            .one()
        )
        new_owner.member_role = MemberRole.OWNER
        current_owner.member_role = MemberRole.MEMBER
        g.db.commit()
        g.log.info("Ownership transferred", room_id=room_id, new_owner_id=new_owner_id)
        return jsonify({"message": "Ownership transferred"}), 200
    except NoResultFound:
        g.log.warning("new owner not found")
        return jsonify({"error": "new owner not found"}), 404


@app.route("/join_room/<string:room_id>", methods=["POST"])
def join_room_rest(room_id):
    token = get_token_from_header()
    try:
        payload = verify_access_token(str(token))
    except jwt.ExpiredSignatureError:
        g.log.error("Token expired", token=token)
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        g.log.error("Invalid token", token=token)
        return jsonify({"error": "Invalid token"}), 401
    user_id = payload["sub"]
    try:
        room = g.db.query(models.Room).filter_by(room_id=room_id).first()
        if not room:
            return jsonify({"error": "Room not found"}), 404
    except SQLAlchemyError as e:
        g.log.error("Failed to fetch room", error=str(e))
        return jsonify({"error": "Failed to fetch room"}), 500

    try:
        exists = (
            g.db.query(models.Room_members)
            .filter_by(user_id=user_id, room_id=room_id)
            .first()
        )
        if exists:
            if exists.member_role == MemberRole.BANNED:
                return jsonify({"error": "Already banned"}), 409
            return jsonify({"error": "Already a member"}), 409
        new_member = models.Room_members(
            user_id=user_id, room_id=room_id, member_role=MemberRole.MEMBER
        )

    except SQLAlchemyError as e:
        g.log.error("Failed to create member", error=str(e))
        return jsonify({"error": "Failed to create member"}), 500

    try:
        g.db.add(new_member)
        g.db.commit()
        g.log.info("Member added", user_id=user_id, room_id=room_id)
        return jsonify({"message": "Member added"}), 201
    except SQLAlchemyError as e:
        g.log.error("Failed to add member", error=str(e))
        g.db.rollback()
        return jsonify({"error": "Failed to add member"}), 500


@app.route("/leave_room/<string:room_id>", methods=["DELETE"])
def leave_room(room_id):
    token = get_token_from_header()
    try:
        payload = verify_access_token(str(token))
    except jwt.ExpiredSignatureError:
        g.log.error("Token expired", token=token)
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        g.log.error("Invalid token", token=token)
        return jsonify({"error": "Invalid token"}), 401

    user_id = payload["sub"]
    try:
        requester = (
            g.db.query(models.Room_members)
            .filter_by(user_id=user_id, room_id=room_id)
            .first()
        )

        if not requester:
            g.log.error("User not in room", user_id=user_id, room_id=room_id)
            return jsonify({"error": "You are not in this room"}), 404

        if requester.member_role == MemberRole.OWNER:
            g.log.error("User is owner", user_id=user_id, room_id=room_id)
            return jsonify({"error": "You are the owner"}), 403
        g.db.delete(requester)
        g.db.commit()
        g.log.info("User removed from room", user_id=user_id, room_id=room_id)
        return jsonify({"message": "User removed from room"}), 200
    except SQLAlchemyError as e:
        g.log.error("Database error", error=str(e))
        return jsonify({"error": "Database error"}), 500


@app.route("/room/<string:room_id>/members", methods=["GET"])
def list_members(room_id):
    token = get_token_from_header()
    try:
        verify_access_token(str(token))
    except jwt.ExpiredSignatureError:
        g.log.error("Token expired", token=token)
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        g.log.error("Invalid token", token=token)
        return jsonify({"error": "Invalid token"}), 401
    try:
        members = (
            g.db.query(models.Room_members, models.User.username)
            .join(models.User, models.Room_members.user_id == models.User.user_id)
            .filter(models.Room_members.room_id == room_id)
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


@app.route("/room/<string:room_id>/ban/<string:user_id>", methods=["POST"])
def ban_member(room_id, user_id):
    token = get_token_from_header()
    try:
        payload = verify_access_token(str(token))
        requester_user_id = payload["sub"]
    except jwt.ExpiredSignatureError:
        g.log.error("Token expired", token=token)
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        g.log.error("Invalid token", token=token)
        return jsonify({"error": "Invalid token"}), 401

    try:
        is_admin_or_owner = (
            g.db.query(models.Room_members)
            .filter_by(user_id=requester_user_id, room_id=room_id)
            .first()
        )
        if not is_admin_or_owner:
            g.log.error(
                "User is not an admin or owner",
                user_id=requester_user_id,
                room_id=room_id,
            )
            return jsonify({"error": "User is not an admin or owner"}), 403

        if is_admin_or_owner.member_role not in [
            models.MemberRole.ADMIN,
            models.MemberRole.OWNER,
        ]:
            g.log.error(
                "User is not an admin or owner",
                user_id=requester_user_id,
                room_id=room_id,
                member_role=is_admin_or_owner.member_role,
            )
            return jsonify({"error": "User is not an admin or owner"}), 403
    except SQLAlchemyError as e:
        g.log.error(
            "Error checking admin or owner status",
            error=str(e),
            user_id=requester_user_id,
            room_id=room_id,
        )
        return jsonify({"error": "Internal server error"}), 500
    try:
        banned_member = (
            g.db.query(models.Room_members)
            .filter_by(room_id=room_id, user_id=user_id)
            .first()
        )

        if user_id == requester_user_id:
            g.log.error(
                "User cannot ban themselves",
                user_id=user_id,
                room_id=room_id,
            )
            return jsonify({"error": "User cannot ban themselves"}), 403

        if not banned_member:
            g.log.error(
                "User is not a member of the room",
                user_id=user_id,
                room_id=room_id,
            )
            return jsonify({"error": "User is not a member of the room"}), 404

        if banned_member.member_role == MemberRole.OWNER:
            g.log.error("Cannot ban owner", user_id=user_id, room_id=room_id)
            return jsonify({"error": "Cannot ban owner"}), 403

        if banned_member.member_role == MemberRole.BANNED:
            g.log.error(
                "User is already banned",
                user_id=requester_user_id,
                room_id=room_id,
            )
            return jsonify({"error": "User is already banned"}), 403

        banned_member.member_role = MemberRole.BANNED
        g.db.commit()
        return jsonify({"message": "User banned successfully"}), 200

    except SQLAlchemyError as e:
        g.log.error(
            "Error banning user",
            error=str(e),
            user_id=requester_user_id,
            room_id=room_id,
        )
        return jsonify({"error": "Internal server error"}), 500


# -------------------------
# Socket.IO (JWT)
# -------------------------

socket_state: dict[str, dict] = {}


@socketio.on("connect")
def socket_connect(auth):
    request_id = request.sid
    token = None
    log = logger.bind(request_id=request_id)
    log.info("Socket connected")
    if not auth or "token" not in auth:
        log.error("Missing token on connect")
        return False

    if auth:
        token = auth.get("token")

    if not token:
        log.error("Missing token")
        return False

    try:
        payload = verify_access_token(token)
    except jwt.ExpiredSignatureError:
        log.warning("Token expired")
        return False
    except jwt.InvalidTokenError:
        log.error("Invalid token")
        return False

    user_id = payload["sub"]
    db = session_local()

    try:
        username = get_username(db, user_id)
    except Exception as e:
        db.rollback()
        log.error("Failed to get username", error=str(e))
        return False
    finally:
        db.close()

    socket_state[request.sid] = {
        "user_id": user_id,
        "username": username,
        "rooms": set(),
    }

    log.info("Socket connected", user_id=user_id)


@socketio.on("join_rooms")
def socket_join_rooms(data):
    log = logger.bind(request_id=request.sid)
    state = socket_state.get(request.sid)
    if not state:
        log.error("Unauthorized attempt to join rooms")
        emit("error", {"error": "Unauthorized"})
        return

    if not isinstance(data, dict):
        emit("error", {"error": "Invalid join payload"})
        return

    room_ids = data.get("room_ids", [])
    if not isinstance(room_ids, list):
        emit("error", {"error": "Invalid room list"})
        return

    room_ids = [str(room_id) for room_id in room_ids if room_id is not None]
    db = session_local()
    try:
        allowed_rooms = (
            db.query(models.Room_members.room_id)
            .filter(
                models.Room_members.user_id == state["user_id"],
                models.Room_members.room_id.in_(room_ids),
                models.Room_members.member_role != MemberRole.BANNED,
            )
            .all()
        )
        for (room_id,) in allowed_rooms:
            socket_join_room(room_id)
            state["rooms"].add(room_id)

        emit("joined_rooms", {"rooms": list(state["rooms"])})
    except Exception as e:
        log.error("Failed to join rooms", error=str(e))
        emit("error", {"error": "Failed to join rooms"})
    finally:
        db.close()


@socketio.on("fetch_history")
def fetch_history(data):
    print("Fetching history", data)
    state = socket_state.get(request.sid)
    room_id = data.get("room")
    log = logger.bind(room_id=room_id, request_id=request.sid)

    if not state or room_id not in state["rooms"]:
        emit("error", {"error": "Not in room"})
        return

    db = session_local()

    try:
        msgs_query = (
            db.query(models.Message, models.User.username)
            .join(models.User, models.Message.sender == models.User.user_id)
            .filter(models.Message.room_id == room_id)
            .order_by(models.Message.id.desc())
            .limit(100)
            .all()
        )

        msgs = [
            {
                "sender": sender,
                "sender_id": msg.sender,
                "message_id": msg.id,
                "message": msg.message,
                "timestamp": msg.date_created.astimezone(timezone.utc).isoformat(),
            }
            for msg, sender in reversed(msgs_query)
        ]

        emit("old_messages", {"room": room_id, "messages": msgs})
    except Exception as e:
        db.rollback()
        log.error("Failed to fetch history", error=str(e))
        emit("error", {"error": "Failed to fetch history"})
    finally:
        db.close()


@socketio.on("send_message")
def send_message(data):
    state = socket_state.get(request.sid)
    room_id = data.get("room")
    message = data.get("message")

    if not state or room_id not in state["rooms"]:
        emit("error", {"error": "Not in room"})
        return

    if not message:
        emit("error", {"error": "Empty message"})
        return

    if len(message) > MAX_MESSAGE_LENGTH:
        emit("error", {"error": "Message too long"})
        return
    message = render_message(message)
    db = session_local()

    try:
        msg = models.Message(
            sender=state["user_id"],
            room_id=room_id,
            message=message,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        payload = {
            "room": room_id,
            "sender": state["username"],
            "sender_id": state["user_id"],
            "message_id": msg.id,
            "message": message,
            "timestamp": msg.date_created.astimezone(timezone.utc).isoformat(),
        }

        emit("new_message", payload, room=room_id)

    except SQLAlchemyError:
        db.rollback()
        emit("error", {"error": "DB error"})
    finally:
        db.close()


@socketio.on("leave_room")
def leave_room_handler(data):
    state = socket_state.get(request.sid)
    if not state:
        return

    if not isinstance(data, dict):
        emit("error", {"error": "Invalid leave payload"})
        return

    room_id = data.get("room")
    if room_id is None:
        emit("error", {"error": "Missing room"})
        return

    room_id = str(room_id)
    if room_id not in state["rooms"]:
        return

    try:
        socket_leave_room(room_id)
    except Exception as e:
        logger.warning(
            "Socket leave_room failed",
            request_id=request.sid,
            room_id=room_id,
            error=str(e),
        )

    state["rooms"].discard(room_id)


@socketio.on("disconnect")
def socket_disconnect(reason):
    state = socket_state.pop(request.sid, None)
    if not state:
        return

    logger.info("Socket disconnected", user_id=state["user_id"], reason=reason)


@socketio.on_error_default
def socket_error_handler(error):
    logger.error("Socket error", sid=request.sid, error=str(error))


# -------------------------
# Run
# -------------------------
init_db()
if __name__ == "__main__":
    logger.info("Server started")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
