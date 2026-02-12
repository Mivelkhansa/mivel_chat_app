# Mivel Chat App
A fast, simple, and modern room-based chat application built with Flask + Socket.IO and a Vanilla JavaScript frontend.

## ✨ Features
- Real-time room messaging
- JWT-based authentication (access + refresh)
- Room management and member roles
- Simple dark-themed chat UI

## 🛠 Tech Stack
- **Frontend:** Vanilla JavaScript, HTML, CSS, Socket.IO client
- **Backend:** Python, Flask, Flask-SocketIO, SQLAlchemy
- **Database:** MySQL
- **Queue / PubSub:** Redis
- **Protocol:** HTTP + WebSocket (Socket.IO)

## 📚 Documentation
- Full project documentation: [`PROJECT_DOCUMENTATION.md`](./PROJECT_DOCUMENTATION.md)
- Coding conventions: [`STYLE_GUIDE.md`](./STYLE_GUIDE.md)

## 🚀 Quick start
### 1) Start backend services
```bash
cd backend
docker compose up --build
```

### 2) Serve frontend
In another terminal:
```bash
cd frontend
python -m http.server 6767
```

Open: `http://localhost:6767`

> Frontend API base URL is currently configured as `http://localhost:5000`.

## 📄 License
MIT (see `license.txt`).
