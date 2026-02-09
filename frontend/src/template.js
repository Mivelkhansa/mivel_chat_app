// Top bar template
export const SettingstopBarTemplate = () => `
<div id="top-bar">
    <div id="left-bar">
        <img
            id="back-button"
            src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAAACXBIWXMAAAsTAAALEwEAmpwYAAACBElEQVR4nO3dv2oUYRiF8dWoRYiFhVUabQyIuQM7a+1s0+QC0llb2uYWLJNGsFUbvQMrKyPERsRCiRBEH9EsBoL/9mOy5/1mn1+5yzLz7jA758wOM5OJJEmSJEmSpF+A68D541c0F8AycB84BO7NZ6n6CbgN7HHsALh69K5ODbAK7PJ7j05vyQsOOAdsAZ/4uzvpdR0d4Cbwkv/zBlhJr/MoAJeAbeArs3mQXveuAWeATeA9bZ4BS+k5ugSsAU8bv/gP0+PE2fQcvWf6WX0DHgKX03OMJdPP4hVwKz3DGDP9vxxM95gL6TnGnOn/5DFwJT3HImT6k/aBjfQMi5bpf/gy/ezF9By9ZvoN4B1tXgDr6Tm6hJk+AzN9Dmb6DMz0GZjpczDTZ2Cm7zbTPwdupOfoErA+LUUtzPStMNPnYKbPMNOHmOn7zvR3k+vfLTN9iJk+yEwfYqYPMtOHmOnD3ABF+BNUgAfhIrxcpAAvmCrCUxFF+Ad7AZ6OLsLuUAR2hzzsDjVgd8jD7lADdocasDvkYXcYRXf4bHcYtju8btwQdochYHeoAbgGPGncG+wOQ7A7FIHdYRTd4a3dYdju8LFxQ9gdBuwOO40bwe4wFLtDAdgdasDukIc3bq0Bb11cgzfv7qs7ePv6YHfwAQ7B7uAjTObNh/gU4WOsJEmSJEmSNBnAd4xhNAtPQ6i2AAAAAElFTkSuQmCC"
            alt="less-than"
        />
        <span id="Settings">Settings</span>
    </div>
</div>
`;

// Settings container template
export const settingsContainerTemplate = () => `
<div id="settings-container">
    <h2>Settings</h2>
    <ul class="settings-list">
        <li>
            <div id="room-id-container">
                <span>room-id:</span>
                <span id="room-id-display">123456789012345678901234</span>
            </div>
            <button id="copy-room-id">Copy</button>
        </li>
        <li>
            <div>
                <span>Room name:</span>
                <span id="room-name-display">programming</span>
            </div>
            <button>Edit</button>
        </li>
        <li>
            <span>Notifications</span>
            <label class="switch">
                <input type="checkbox" checked />
                <span class="slider"></span>
            </label>
        </li>
        <li id="members-container">
            <span>Members</span>
            <ul id="members-list"></ul> <!-- members will be rendered dynamically -->
        </li>
    </ul>
</div>
`;

// Member item template
export const memberItemTemplate = (name, role) => `
<li class="member-item">
    <div>
        <span class="member-name">${name}</span>
        <span class="member-role">${role}</span>
    </div>
    <button class="edit-member">Edit</button>
</li>
`;

// Popup template
export const popupTemplate = () => `
<div id="popup" class="popup hidden">
    <div class="popup-content">
        <p id="popup-message">This is a popup!</p>
        <div class="popup-buttons">
            <button id="popup-ok">OK</button>
            <button id="popup-cancel" class="hidden">Cancel</button>
        </div>
    </div>
</div>
`;
// Top bar template

export const roomListTopbarTemplate = () => `
  <div id="top-bar">
      <div id="left-bar"><span id="logo">Velly-chat</span></div>
      <div id="right-bar">
          <img
              id="settings-button"
              src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAAsTAAALEwEAmpwYAAABEElEQVR4nOWUz00CURDGV8+yBu0C79QBIe6VCoQqxAbgCjaANYBVcCPBmFgAcsOfmTAkZJmZgD4JiV/yLvu+P5v5difL/gWALvvopAx4NgJGqczvgLkRIM9qx5pdABNgDNwDA+ALH3LXV65opsBlFNDm92h75lfAe4KADyC3Ah4D0QJoARU9DWAW8HtWgIg+HfMbg1/VuzLEo+mNqQ6sSoJW0JmUuwvR1t2SVbQsiSoBNy9xl6H5DwKujwpwRtQI+MXBIwpKnkmhBv8WeHNK3n8p+bTwsdBCcz2FY77F0+l/tD9fFTvLThbWi46hD6wDs7VyCtW8hsvOAlBLtq6DkJERMExinm0COkbAQ7KAs8Y3aSD5YYFkBxMAAAAASUVORK5CYII="
              alt="settings"
          />
      </div>
  </div>
`;

// Room list template
export const roomListTemplate = (rooms = []) => `
<div id="room-list">
    ${rooms
      .map(
        (room) => `
    <div class="room" data-room="${room.name}" data-id="${room.id}">
        <div class="room-name">${room.name}</div>
        <div class="room-description">${room.description}</div>
    </div>
    `,
      )
      .join("")}
</div>
<div id="bottom-bar">
    <div id="add-room">
        <img src="icon/icons8-add-new-96.png" alt="Add Room" />
    </div>
</div>
`;

// Chat page template
export const chatPageTemplate = (roomName) => `
${topBarTemplate(false)}
<div id="chat-page">
    <h2>Room: ${roomName}</h2>
    <div id="messages"></div>
    <input type="text" id="chat-input" placeholder="Type a message..." />
    <button id="send-btn">Send</button>
</div>
`;

// Settings page template
export const settingsPageTemplate = () => `
${topBarTemplate(false)}
<div id="settings-container">
    <h2>Settings</h2>
    <ul class="settings-list">
        <li>
            <span>Profile:</span>
            <span>User123</span>
        </li>
        <li>
            <span>Notifications:</span>
            <label class="switch">
                <input type="checkbox" checked />
                <span class="slider"></span>
            </label>
        </li>
    </ul>
</div>
`;

// auth pop up
export function loginPopupTemplate() {
  return `
    <div id="login-overlay" class="overlay">
      <div class="popup">
        <h2>Login</h2>

        <input id="login-username" placeholder="Username" />
        <input id="login-password" type="password" placeholder="Password" />

        <div class="actions">
          <button id="login-submit">Login</button>
          <button id="login-close">Cancel</button>
        </div>

        <div class="switch">
          <span id="signup-open">Sign Up</span>
        </div>
      </div>
    </div>
  `;
}

export function signupPopupTemplate() {
  return `
    <div id="signup-overlay" class="overlay">
      <div class="popup">
        <h2>Sign Up</h2>

        <input id="signup-username" placeholder="Username" />
        <input id="signup-email" placeholder="Email" />
        <input id="signup-password" type="password" placeholder="Password" />
        <input id="signup-confirm-password" type="password" placeholder="Confirm Password" />

        <div class="actions">
          <button id="signup-submit">Sign Up</button>
          <button id="signup-close">Cancel</button>
        </div>

        <div class="switch">
          <span id="login-open">Login</span>
        </div>
      </div>
    </div>
  `;
}

export const createRoomPopupTemplate = () => `
<div id="create-room-popup-overlay" class="popup-overlay hidden">
  <div class="popup-content">
    <!-- Header with Close button -->
    <div class="popup-header">
      <h2>Create New Room</h2>
      <button id="create-room-popup-close" class="close-btn">✕</button>
    </div>

    <!-- Fields for creating room -->
    <div id="create-room-fields">
      <input id="room-name" placeholder="Room Name" />
    </div>

    <!-- Action buttons -->
    <div class="popup-buttons">
      <button id="create-room-submit">Create Room</button>
      <!-- Switch to Join Room -->
      <button id="switch-to-join" class="switch-btn">Switch to Join Room</button>
    </div>
  </div>
</div>
`;

export const joinRoomPopupTemplate = () => `
<div id="join-room-popup-overlay" class="popup-overlay hidden">
  <div class="popup-content">
    <!-- Header with Close button -->
    <div class="popup-header">
      <h2>Join Room</h2>
      <button id="join-room-popup-close" class="close-btn">✕</button>
    </div>

    <!-- Fields for joining room -->
    <div id="join-room-fields">
      <input id="room-id" placeholder="Room ID" />
      <input id="room-password" type="password" placeholder="Password (optional)" />
    </div>

    <!-- Action buttons -->
    <div class="popup-buttons">
      <button id="join-room-submit">Join Room</button>
      <!-- Switch to Create Room -->
      <button id="switch-to-create" class="switch-btn">Switch to Create Room</button>
    </div>
  </div>
</div>
`;
