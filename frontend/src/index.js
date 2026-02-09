import {
  roomListTemplate,
  roomListTopbarTemplate,
  loginPopupTemplate,
  signupPopupTemplate,
} from "./template.js";

let isLoggedIn = false;

// ====================
// ROUTES
// ====================
const route = {
  "/": renderRoomList,
};

// ====================
// RENDER ROOM LIST
// ====================
function renderRoomList() {
  const app = document.getElementById("app");
  app.innerHTML =
    roomListTopbarTemplate() +
    roomListTemplate([
      { id: 1, name: "Room 1", description: "General chat" },
      { id: 2, name: "Room 2", description: "Gaming" },
      { id: 3, name: "Room 3", description: "Programming" },
    ]);

  // Show login popup if not logged in
  if (!isLoggedIn) openSignupPopup();

  // Add-room button listener
  const addRoomButton = document.getElementById("add-room");
  if (addRoomButton) {
    addRoomButton.addEventListener("click", () => {
      console.log("Add Room clicked");
      app.insertAdjacentHTML("beforeend", createRoomPopupTemplate());
    });
  }
}

// ====================
// LOGIN POPUP FUNCTIONS
// ====================
function showLoginPopup() {
  // remove any existing auth popup
  const existingLogin = document.getElementById("login-overlay");
  if (existingLogin) existingLogin.remove();

  const existingSignup = document.getElementById("signup-overlay");
  if (existingSignup) existingSignup.remove();

  document.body.insertAdjacentHTML("beforeend", loginPopupTemplate());

  document
    .getElementById("login-close")
    .addEventListener("click", closeLoginPopup);

  document
    .getElementById("login-submit")
    .addEventListener("click", handleLogin);

  document.getElementById("signup-open").addEventListener("click", () => {
    closeLoginPopup();
    openSignupPopup();
  });
}

function handleLogin() {
  const username = document.getElementById("login-username").value;
  const password = document.getElementById("login-password").value;

  if (username && password) {
    isLoggedIn = true;
    closeLoginPopup();
  } else {
    alert("Username and password required");
  }
}

function closeLoginPopup() {
  const overlay = document.getElementById("login-overlay");
  if (overlay) overlay.remove();
}

// ====================
// SIGN UP POPUP FUNCTIONS
// ====================
function openSignupPopup() {
  // remove any existing signup popup
  const existing = document.getElementById("signup-overlay");
  if (existing) existing.remove();

  // open signup popup
  document.body.insertAdjacentHTML("beforeend", signupPopupTemplate());

  document
    .getElementById("signup-close")
    .addEventListener("click", closeSignupPopup);
}

function closeSignupPopup() {
  const overlay = document.getElementById("signup-overlay");
  if (overlay) overlay.remove();
}

// ====================
// ROUTE HANDLER
// ====================
function handleRoute() {
  const path = window.location.pathname;
  if (route[path]) {
    route[path]();
  } else {
    route["/"]();
  }
}

// ====================
// INITIALIZE APP
// ====================
document.addEventListener("DOMContentLoaded", () => {
  handleRoute();
});
