import {
  aboutTemplate,
  authModalTemplate,
  chatPageTemplate,
  joinRoomPopupTemplate,
  createRoomPopupTemplate,
  roomListTemplate,
  roomListTopbarTemplate,
  roomSettingsTemplate,
  userSettingsTemplate,
} from "./template.js";

const API_BASE = "http://localhost:5000";

function decodeUserIdFromToken(token) {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.sub;
  } catch {
    return "";
  }
}

const state = {
  userId: "",
  accessToken: localStorage.getItem("access_token") || "",
  refreshToken: localStorage.getItem("refresh_token") || "",
  username: localStorage.getItem("username") || "",
  authMode: "login",
  rooms: [],
  activeRoom: null,
  socket: null,
};

function saveAuth({ access_token, refresh_token, username }) {
  if (access_token) {
    state.accessToken = access_token;
    state.userId = decodeUserIdFromToken(access_token);
    localStorage.setItem("access_token", access_token);
  }
  if (refresh_token) {
    state.refreshToken = refresh_token;
    localStorage.setItem("refresh_token", refresh_token);
  }
  if (username) {
    state.username = username;
    localStorage.setItem("username", username);
  }
}

function clearAuth() {
  state.accessToken = "";
  state.refreshToken = "";
  state.username = "";
  state.userId = "";
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("username");
}

async function api(path, options = {}, allowRetry = true) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (state.accessToken) {
    headers.Authorization = `Bearer ${state.accessToken}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && allowRetry && state.refreshToken) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return api(path, options, false);
    }
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || "Request failed");
  }

  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

async function refreshAccessToken() {
  try {
    const response = await fetch(`${API_BASE}/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: state.refreshToken }),
    });

    if (!response.ok) {
      clearAuth();
      return false;
    }

    const data = await response.json();
    saveAuth({ access_token: data.access_token });
    return true;
  } catch {
    clearAuth();
    return false;
  }
}

function showError(message) {
  alert(message);
}

function renderAuthModal() {
  document.body.insertAdjacentHTML(
    "beforeend",
    authModalTemplate(state.authMode),
  );

  document.getElementById("auth-switch").addEventListener("click", () => {
    document.getElementById("auth-overlay")?.remove();
    state.authMode = state.authMode === "login" ? "signup" : "login";
    renderAuthModal();
  });

  document.getElementById("auth-submit").addEventListener("click", async () => {
    const username = document.getElementById("auth-username").value.trim();
    const password = document.getElementById("auth-password").value;

    if (!username || !password) {
      return showError("Username and password are required.");
    }

    try {
      if (state.authMode === "signup") {
        await api("/signup", {
          method: "POST",
          body: JSON.stringify({ username, password }),
        });
      }

      const data = await api("/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });

      saveAuth({ ...data, username });
      document.getElementById("auth-overlay")?.remove();
      initSocket();
      await renderRooms();
    } catch (error) {
      showError(error.message);
    }
  });
}

function renderJoinRoomPopup() {
  document.body.insertAdjacentHTML("beforeend", joinRoomPopupTemplate());
  document.getElementById("join-room-cancel").addEventListener("click", () => {
    document.getElementById("join-room-popup-overlay")?.remove();
  });
  document
    .getElementById("join-room-submit")
    .addEventListener("click", async () => {
      const roomId = document.getElementById("join-room-id").value;
      if (!roomId) {
        showError("Room ID is required");
        return;
      }
      try {
        await api(`/join_room/${roomId}`, {
          method: "POST",
        });
        document.getElementById("join-room-popup")?.remove();
        await renderRooms();
      } catch (error) {
        showError(error.message);
      }
    });
  document.getElementById("open-create-room")?.addEventListener("click", () => {
    document.getElementById("join-room-popup-overlay")?.remove();
    renderCreateRoomPopup();
  });
}

function renderCreateRoomPopup() {
  document.body.insertAdjacentHTML("beforeend", createRoomPopupTemplate());

  document
    .getElementById("create-room-cancel")
    .addEventListener("click", () => {
      document.getElementById("create-room-popup-overlay")?.remove();
    });

  document
    .getElementById("create-room-submit")
    .addEventListener("click", async () => {
      const roomName = document.getElementById("room-name").value.trim();
      const roomDescription = document
        .getElementById("room-description")
        .value.trim();

      if (!roomName) {
        return showError("Room name is required.");
      }

      try {
        await api("/room", {
          method: "POST",
          body: JSON.stringify({
            room_name: roomName,
            room_description: roomDescription,
          }),
        });

        document.getElementById("create-room-popup-overlay")?.remove();
        await renderRooms();
      } catch (error) {
        showError(error.message);
      }
    });

  // 🔹 switch to join popup
  document.getElementById("open-join-room")?.addEventListener("click", () => {
    document.getElementById("create-room-popup-overlay")?.remove();
    renderJoinRoomPopup();
  });
}

async function renderRooms() {
  const app = document.getElementById("app");

  try {
    const data = await api("/my-rooms");
    state.rooms = data.rooms || [];
  } catch (error) {
    if (!state.accessToken) {
      app.innerHTML = "";
      renderAuthModal();
      return;
    }
    showError(error.message);
    state.rooms = [];
  }

  app.innerHTML =
    roomListTopbarTemplate(state.username) + roomListTemplate(state.rooms);

  document.getElementById("settings-button")?.addEventListener("click", () => {
    renderUserSettings();
  });

  document.querySelectorAll(".room").forEach((roomEl) => {
    roomEl.addEventListener("click", () => {
      const room = state.rooms.find((r) => String(r.id) === roomEl.dataset.id);
      if (room) {
        renderChat(room);
      }
    });
  });

  document.getElementById("add-room")?.addEventListener("click", () => {
    renderJoinRoomPopup();
  });
}

function renderMessage({ sender, message, timestamp, sender_id }) {
  const container = document.getElementById("chat-container");
  const mine = sender_id && state.userId === sender_id;
  const date = new Date(timestamp);

  container.insertAdjacentHTML(
    "beforeend",
    `<div class="message ${mine ? "my-message" : ""}">
      <div class="content">
        ${mine ? "" : `<span class="username">${sender}</span>`}
        <span class="timestamp">${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
        <p>${message}</p>
      </div>
    </div>`,
  );

  container.scrollTop = container.scrollHeight;
}

function renderChat(room) {
  state.activeRoom = room;
  const app = document.getElementById("app");
  app.innerHTML = chatPageTemplate(room.name);

  document.getElementById("back-button").addEventListener("click", () => {
    if (state.activeRoom) {
      state.socket?.emit("leave_room", { room: state.activeRoom.id });
    }
    state.activeRoom = null;
    renderRooms();
  });

  document.getElementById("settings-button").addEventListener("click", () => {
    renderRoomSettings();
  });

  document
    .getElementById("send-button")
    .addEventListener("click", sendActiveMessage);
  document
    .getElementById("message-input")
    .addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendActiveMessage();
      }
    });

  state.socket.emit("join_rooms", {
    room_ids: [String(room.id)],
  });

  state.socket.once("joined_rooms", (data) => {
    if (data.rooms.includes(String(room.id))) {
      state.socket.emit("fetch_history", {
        room: String(room.id),
      });
    } else {
      showError("Failed to join room");
    }
  });
}

function renderUserSettings() {
  const app = document.getElementById("app");
  app.innerHTML = userSettingsTemplate(state.username);

  document.getElementById("back-button").addEventListener("click", () => {
    renderRooms();
  });

  document.getElementById("open-about").addEventListener("click", () => {
    renderAbout();
  });

  document.getElementById("logout-button").addEventListener("click", () => {
    state.socket?.disconnect();
    clearAuth();
    app.innerHTML = "";
    renderAuthModal();
  });
}

async function renderRoomSettings() {
  const app = document.getElementById("app");
  const room = state.activeRoom;
  if (!room) return;

  try {
    const members = await api(`/room/${room.id}/members`);
    room.members = members.map((m) => ({
      id: m.id,
      name: m.username,
      role: m.role,
    }));
  } catch (err) {
    showError("Failed to fetch members: " + err.message);
    room.members = [];
  }

  app.innerHTML = roomSettingsTemplate(state.activeRoom);

  document.getElementById("back-button").addEventListener("click", () => {
    if (state.activeRoom) {
      renderChat(state.activeRoom);
    } else {
      renderRooms();
    }
  });

  document
    .getElementById("copy-room-id")
    ?.addEventListener("click", async () => {
      const roomId = String(state.activeRoom?.id || "");
      if (!roomId) {
        return;
      }

      try {
        await navigator.clipboard.writeText(roomId);
      } catch {
        showError("Unable to copy room id.");
      }
    });
  document
    .getElementById("leave-room-button")
    .addEventListener("click", async () => {
      if (!state.activeRoom) return;

      try {
        await api("/leave_room/" + state.activeRoom.id, { method: "DELETE" });
        state.activeRoom = null;
        renderRooms();
      } catch (err) {
        showError("Failed to leave room: " + err.message);
      }
    });
}

function renderAbout() {
  const app = document.getElementById("app");
  app.innerHTML = aboutTemplate();

  document.getElementById("back-button").addEventListener("click", () => {
    renderUserSettings();
  });
}

function sendActiveMessage() {
  const input = document.getElementById("message-input");
  const message = input.value.trim();

  if (!message || !state.activeRoom) {
    return;
  }

  state.socket?.emit("send_message", {
    room: state.activeRoom.id,
    message,
  });

  input.value = "";
}

function initSocket() {
  if (!window.io || !state.accessToken) return;

  if (state.socket) {
    state.socket.disconnect();
  }

  state.socket = io("http://localhost:5000", {
    auth: {
      token: state.accessToken,
    },
    transports: ["websocket"], // optional but clean
  });

  state.socket.on("connect", () => {
    console.log("Connected:", state.socket.id);
    if (state.rooms.length > 0) {
      state.socket.emit("join_rooms", {
        room_ids: state.rooms.map((r) => String(r.id)),
      });
    }
  });

  state.socket.on("disconnect", () => {
    console.log("Disconnected");
  });

  state.socket.on("error", (data) => {
    showError(data.error);
  });

  // 🔹 History (old messages)
  state.socket.on("old_messages", (data) => {
    const container = document.getElementById("chat-container");
    if (!container) return;

    container.innerHTML = "";
    data.messages.forEach(renderMessage);
  });

  // 🔹 Live messages
  state.socket.on("new_message", (data) => {
    renderMessage(data);
  });
}

async function bootstrap() {
  if (state.accessToken) {
    state.userId = decodeUserIdFromToken(state.accessToken);
  }

  if (!state.accessToken) {
    renderAuthModal();
    return;
  }

  initSocket();
  await renderRooms();
}

document.addEventListener("DOMContentLoaded", bootstrap);
