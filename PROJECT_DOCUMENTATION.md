# Mivel Chat App Documentation

## 1. Project overview
Mivel Chat App is a room-based real-time chat application with:
- a **Flask + Socket.IO backend** for authentication, room management, and messaging.
- a **Vanilla JavaScript frontend** for UI rendering and Socket.IO communication.
- **MySQL** for persistent data.
- **Redis** for Socket.IO message queue / scaling support.

The app supports account signup/login, JWT-based auth, room creation and membership, and live messaging per room.

---

## 2. Repository structure

```text
mivel_chat_app/
├── backend/
│   ├── app/
│   │   ├── app.py              # Flask app + Socket.IO events + API endpoints
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── db.py               # SQLAlchemy engine/session setup
│   │   ├── config.py           # environment-based configuration
│   │   ├── requirements.txt    # Python dependencies
│   │   ├── test_ping.py        # basic health test
│   │   └── Dockerfile
│   ├── db/init/schema.sql      # DB bootstrap SQL
│   └── docker-compose.yml      # MySQL + Redis + Flask app services
├── frontend/
│   ├── src/
│   │   ├── index.js            # App state, API client, and UI orchestration
│   │   ├── template.js         # HTML templates as JS template literals
│   │   └── translation.js      # translation dictionary
│   ├── style/style.css         # shared styling
│   ├── index.html              # frontend entry page
│   └── package.json            # frontend package metadata
├── README.md
└── STYLE_GUIDE.md
```

---

## 3. Architecture

## 3.1 Backend
The backend is a Flask app with these responsibilities:
- Validates JWT tokens for protected HTTP routes.
- Handles auth (`/signup`, `/login`, `/refresh`).
- Manages rooms and memberships.
- Handles Socket.IO events (`connect`, `join_rooms`, `fetch_history`, `send_message`, etc.).
- Logs request-level details with Loguru.

### 3.2 Frontend
The frontend is intentionally framework-free:
- Uses a centralized `state` object in `frontend/src/index.js`.
- Builds the UI with template functions from `frontend/src/template.js`.
- Uses `fetch` for REST APIs.
- Uses Socket.IO for real-time message flow.

### 3.3 Data flow (high level)
1. User logs in (or signs up then logs in).
2. Frontend stores JWT tokens in localStorage.
3. Frontend loads `/my-rooms`.
4. Socket connection is initialized and joins room channels.
5. Messages are sent/received via Socket.IO and rendered in chat UI.

---

## 4. Setup and run

## 4.1 Prerequisites
- Docker + Docker Compose (recommended)
- OR local runtime:
  - Python 3.11+
  - MySQL
  - Redis

## 4.2 Run with Docker Compose
From `backend/`:

```bash
docker compose up --build
```

This starts:
- `db` (MySQL)
- `redis`
- `app` (Flask + Socket.IO)

Backend service runs on port `5000`.

## 4.3 Run frontend
From `frontend/`:
- Serve the static files with any simple HTTP server (example):

```bash
python -m http.server 6767
```

Then open `http://localhost:6767`.

> Note: `API_BASE` in `frontend/src/index.js` currently targets `http://localhost:5000`.

---

## 5. Environment configuration
Key backend variables (see `backend/app/config.py`):
- DB settings (host, port, username, password, db name)
- Redis host/port
- JWT secret keys and expiration
- JWT algorithm

Use environment variables for local/dev/prod so secrets are not hardcoded.

---

## 6. Database model summary
Defined in `backend/app/models.py`:
- `User`
  - `user_id`, `username`, `password_hash`, timestamps
- `Room`
  - `room_id`, `room_name`, `room_description`, timestamps
- `Room_members`
  - `user_id`, `room_id`, `member_role`, `join_date`
- `Message`
  - `sender`, `room_id`, `message`, timestamps

Role enum:
- `owner`
- `admin`
- `member`
- `banned`

---

## 7. HTTP API overview

## 7.1 Public endpoints
- `GET /ping` → health check (`pong`)
- `POST /signup` → create user account
- `POST /login` → returns access and refresh tokens
- `POST /refresh` → refreshes access token

## 7.2 Protected endpoints (Bearer access token)
- `POST /room` → create room (creator becomes OWNER)
- `DELETE /room/<room_id>` → delete room (OWNER only)
- `PATCH /room/<room_id>` → update room details
- `GET /my-rooms` → list rooms for current user
- Room member and owner-transfer routes under `/room/<room_id>/...`

### Token usage
Send access token in header:

```http
Authorization: Bearer <access_token>
```

---

## 8. Socket.IO event overview
Server handlers include:
- `connect`
- `join_rooms`
- `fetch_history`
- `send_message`
- `leave_room`
- `disconnect`

Typical real-time workflow:
1. Frontend connects with token context.
2. Frontend joins one or more rooms.
3. Frontend emits messages.
4. Server validates sender membership/permissions and broadcasts.

---

## 9. Frontend behavior summary
Main implementation file: `frontend/src/index.js`.

Highlights:
- Maintains auth/session in a single `state` object.
- Uses helper `api()` that auto-injects `Authorization` header.
- Automatically tries `/refresh` on `401` before failing request.
- Renders:
  - auth modal
  - room list
  - chat page
  - user settings
  - room settings

Templates are separated into `frontend/src/template.js` for readability and reuse.

---

## 10. Logging and observability
- Request lifecycle binds a generated `request_id`.
- Loguru outputs:
  - colored stderr logs
  - serialized JSON logs to `app.log`

This enables easier tracing across API calls and socket actions.

---

## 11. Security notes
- Passwords are hashed with `bcrypt`.
- JWT includes type (`access` vs `refresh`), issuer, iat, exp.
- Most room operations enforce role-based constraints.

Recommended hardening:
- move JWT secrets to secure secret manager in production.
- set stricter CORS origins for production domain only.
- add rate limiting for auth endpoints.

---

## 12. Known gaps and improvement ideas
- Add formal automated tests for auth, rooms, and sockets.
- Add OpenAPI/Swagger spec for HTTP endpoints.
- Add input schema validation (e.g., Pydantic/Marshmallow).
- Add structured frontend build/dev tooling and linting.
- Add deployment docs for production (Nginx + Gunicorn + TLS).

---

## 13. Related docs
- Style conventions: see `STYLE_GUIDE.md`
- Quick intro and project metadata: see `README.md`
