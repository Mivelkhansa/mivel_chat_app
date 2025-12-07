# app.py
import os
from datetime import timedelta

import bcrypt
import models
from db import session_local
from flask import Flask, g, jsonify, message_flashed, request, session

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

# Cookie/session settings
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = True  # requires HTTPS in production
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)


# -------------------------
# DB session handling
# -------------------------
@app.before_request
def start_session():
    g.db = session_local()


@app.teardown_request
def teardown_session(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


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
@app.route("/messages", methods=["GET", "POST"])
def messages():
    if "user_id" not in session:
        # you can only see messages if logged in
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "POST":
        data = request.get_json()
        message = data.get("message")
        if not message:
            return jsonify({"error": "Message is required"}), 400
        g.db.add(models.Message(sender=session["user_id"], message=message))
        g.db.commit()
        return jsonify({"message": "Message sent"}), 201

    elif request.method == "GET":
        msgs = (
            g.db.query(models.Message)
            .order_by(models.Message.date_created.desc())
            .all()
        )

        return jsonify(
            [
                {
                    "id": m.id,
                    "sender": m.sender,
                    "message": m.message,
                    "date": m.date_created.isoformat(),
                }
                for m in msgs
            ]
        )
    else:
        return jsonify({"error": "Method not allowed"}), 405


# -------------------------
# Contact
# -------------------------
@app.route("/contact")
def contact():
    return jsonify({"name": "mivel khavilla khansa", "email": "mivelkhansa6@gmail.com"})


if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0", port=5000)
