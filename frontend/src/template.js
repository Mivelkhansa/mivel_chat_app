export const roomListTopbarTemplate = () => `
  <div id="top-bar" class="page-header">
      <div id="left-bar"><span id="logo">Velly-chat</span></div>
      <div id="right-bar">
          <button id="settings-button" class="icon-button" type="button" aria-label="Open user settings">
          <img
              src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAAsTAAALEwEAmpwYAAABEElEQVR4nOWUz00CURDGV8+yBu0C79QBIe6VCoQqxAbgCjaANYBVcCPBmFgAcsOfmTAkZJmZgD4JiV/yLvu+P5v5difL/gWALvvopAx4NgJGqczvgLkRIM9qx5pdABNgDNwDA+ALH3LXV65opsBlFNDm92h75lfAe4KADyC3Ah4D0QJoARU9DWAW8HtWgIg+HfMbg1/VuzLEo+mNqQ6sSoJW0JmUuwvR1t2SVbQsiSoBNy9xl6H5DwKujwpwRtQI+MXBIwpKnkmhBv8WeHNK3n8p+bTwsdBCcz2FY77F0+l/tD9fFTvLThbWi46hD6wDs7VyCtW8hsvOAlBLtq6DkJERMExinm0COkbAQ7KAs8Y3aSD5YYFkBxMAAAAASUVORK5CYII="
              alt="settings"
          />
          </button>
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
<div class="chat-page">
  <div id="top-bar" class="page-header">
    <div id="left-bar">
      <button id="back-button" class="icon-button back-icon" type="button">‹</button>
      <span id="room-name">${roomName}</span>
    </div>
    <div id="right-bar">
      <button id="settings-button" class="icon-button" type="button">
        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAAsTAAALEwEAmpwYAAABEElEQVR4nOWUz00CURDGV8+yBu0C79QBIe6VCoQqxAbgCjaANYBVcCPBmFgAcsOfmTAkZJmZgD4JiV/yLvu+P5v5difL/gWALvvopAx4NgJGqczvgLkRIM9qx5pdABNgDNwDA+ALH3LXV65opsBlFNDm92h75lfAe4KADyC3Ah4D0QJoARU9DWAW8HtWgIg+HfMbg1/VuzLEo+mNqQ6sSoJW0JmUuwvR1t2SVbQsiSoBNy9xl6H5DwKujwpwRtQI+MXBIwpKnkmhBv8WeHNK3n8p+bTwsdBCcz2FY77F0+l/tD9fFTvLThbWi46hD6wDs7VyCtW8hsvOAlBLtq6DkJERMExinm0COkbAQ7KAs8Y3aSD5YYFkBxMAAAAASUVORK5CYII="
         alt="settings"/>
      </button>
    </div>
  </div>

  <div id="chat-container"></div>

  <div id="input-bar">
    <textarea id="message-input" placeholder="Type your message..."></textarea>
    <button id="send-button" type="button">
      <img src="icon/icons8-sent-24.png" alt="Send"/>
    </button>
  </div>
</div>
`;

export const userSettingsTemplate = (username = "") => `
<div class="settings-page">
  <div id="top-bar" class="page-header">
    <div id="left-bar">
      <button id="back-button" class="icon-button back-icon" type="button" aria-label="Go back">‹</button>
      <span id="room-name">Settings</span>
    </div>
  </div>

  <h2 class="settings-title">Settings</h2>

  <div class="setting-row">
    <span>Account ${username ? `<span class="muted-value">${username}</span>` : ""}</span>
    <button class="pill-button" type="button">Edit</button>
  </div>

  <div class="setting-row">
    <span>Notifications</span>
    <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
  </div>

  <div class="setting-row">
    <span>Appearance</span>
    <span class="option-value">Dark Mode ˅</span>
  </div>

  <div class="setting-row">
    <span>Language</span>
    <span class="option-value">English ˅</span>
  </div>

  <div class="setting-row">
    <span>About</span>
    <button id="open-about" class="pill-button" type="button">View</button>
  </div>

  <div class="settings-footer">
    <button id="logout-button" class="danger-link" type="button">Logout</button>
  </div>
</div>
`;

export const roomSettingsTemplate = (room) => {
  const roomId = room?.id ?? "123456789012345678901234";
  const roomName = room?.name ?? "programming";

  return `
<div class="settings-page">
  <div id="top-bar" class="page-header">
    <div id="left-bar">
      <button id="back-button" class="icon-button back-icon" type="button" aria-label="Go back">‹</button>
      <span id="room-name">Settings</span>
    </div>
  </div>

  <h2 class="settings-title">Settings</h2>

  <div class="setting-row">
    <span>room-id: <span class="muted-value">${roomId}</span></span>
    <button id="copy-room-id" class="pill-button" type="button">Copy</button>
  </div>

  <div class="setting-row">
    <span>Room name: <span class="muted-value">${roomName}</span></span>
    <button class="pill-button" type="button">Edit</button>
  </div>

  <div class="setting-row">
    <span>Notifications</span>
    <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
  </div>

  <div class="setting-box">
  ${room.members
    .map(
      (member) => `
      <div class="member-row">
        <span>${member.name} <span class="muted-value">${member.role}</span></span>
        <button
          class="pill-button edit-member-btn"
          data-id="${member.id}"
          type="button"
        >
          Edit
        </button>
      </div>
    `,
    )
    .join("")}
  </div>

  <div class="settings-footer">
    <button id="leave-room-button" class="danger-link" type="button">Leave Room</button>
  </div>
</div>
`;
};

export const aboutTemplate = () => `
<div class="about-page">
  <div id="top-bar" class="page-header">
    <div id="left-bar">
      <button id="back-button" class="icon-button back-icon" type="button" aria-label="Go back">‹</button>
      <span id="room-name">About</span>
    </div>
  </div>

  <div class="about-card">
    <h2>Velly-chat</h2>
    <p>A simple real-time chat app with room-based conversations and a clean dark UI.</p>
    <p>Made for fast messaging with focused user and room settings.</p>
    <ul>
    <li>Thanks <a href="https://icons8.com" target="_blank">icons8</a> for the icon</li>
    <li>The code source code for this project is available on <a href="https://github.com/Mivelkhansa/mivel_chat_app" target="_blank">GitHub</a></li>
    </ul>
  </div>
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
        <button id="auth-submit" class="button" type="button">${isLogin ? "Login" : "Sign up"}</button>
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
      <button id="create-room-submit" class="button" type="button">Create</button>
      <button id="create-room-cancel" class="button" type="button">Cancel</button>
    </div>
    <span id="open-join-room" class="create-room">Join room</span>
  </div>
</div>
`;

export const joinRoomPopupTemplate = () => `
<div id="join-room-popup-overlay" class="overlay">
  <div class="auth-modal">
    <h2>Join room</h2>
    <input id="join-room-id" placeholder="Room ID" />
    <div class="actions">
      <button id="join-room-submit" class="button" type="button">Join</button>
      <button id="join-room-cancel" class="button" type="button">Cancel</button>
    </div>
    <span id="open-create-room" class="join-room">Create room</span>
  </div>
</div>
`;

export const editMemberPopupTemplate = (member) => `
<div id="edit-member-popup-overlay" class="overlay">
  <div class="auth-modal">
    <h2>Edit member</h2>
    <p id="member-name">${member.name}</p>
    <p id="member-role" class="muted-value">${member.role}</p>

    <div class="actions">
      <button id="transfer-owner" class="button">Transfer ownership</button>
      <button id="promote-admin" class="button">Promote to admin</button>
      <button id="demote-member" class="button">Make member</button>
      <button id="ban-member" class="button danger">Ban</button>
      <button id="edit-member-cancel" class="button">Cancel</button>
    </div>
  </div>
</div>
`;
