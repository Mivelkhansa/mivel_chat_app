export const roomListTopbarTemplate = (username = "") => `
  <div id="top-bar">
      <div id="left-bar"><span id="logo">Velly-chat</span></div>
      <div id="right-bar">
          <span class="username-badge">${username}</span>
          <button id="logout-button" type="button">Logout</button>
      </div>
  </div>
`;

export const roomListTemplate = (rooms = []) => `
<div id="room-list">
    ${
      rooms.length
        ? rooms
            .map(
              (room) => `
    <div class="room" data-id="${room.id}">
        <div class="room-name">${room.name}</div>
        <div class="room-description">${room.description || "No description"}</div>
    </div>
    `,
            )
            .join("")
        : '<p class="empty-state">No rooms yet. Create one to get started.</p>'
    }
</div>
<div id="bottom-bar">
    <div id="add-room" title="Create room">
        <img src="icon/icons8-add-new-96.png" alt="Add Room" />
    </div>
</div>
`;

export const chatPageTemplate = (roomName) => `
<div id="top-bar">
  <div id="left-bar">
    <button id="back-button" type="button">←</button>
    <span id="room-name">${roomName}</span>
  </div>
</div>
<div id="chat-container"></div>
<div id="input-bar">
  <textarea id="message-input" placeholder="Type your message..."></textarea>
  <button id="send-button" type="button">
    <img src="icon/icons8-sent-24.png" alt="Send" />
  </button>
</div>
`;

export const authModalTemplate = (mode = "login") => {
  const isLogin = mode === "login";
  return `
  <div id="auth-overlay" class="overlay">
    <div class="auth-modal">
      <h2>${isLogin ? "Login" : "Sign up"}</h2>
      <input id="auth-username" placeholder="Username" />
      <input id="auth-password" type="password" placeholder="Password" />
      <div class="actions">
        <button id="auth-submit" type="button">${isLogin ? "Login" : "Sign up"}</button>
      </div>
      <button id="auth-switch" class="auth-switch" type="button">
        ${isLogin ? "Need an account? Sign up" : "Already have an account? Login"}
      </button>
    </div>
  </div>
`;
};

export const createRoomPopupTemplate = () => `
<div id="create-room-popup-overlay" class="overlay">
  <div class="auth-modal">
    <h2>Create room</h2>
    <input id="room-name" placeholder="Room name" />
    <input id="room-description" placeholder="Room description" />
    <div class="actions">
      <button id="create-room-submit" type="button">Create</button>
      <button id="create-room-cancel" type="button">Cancel</button>
    </div>
  </div>
</div>
`;
