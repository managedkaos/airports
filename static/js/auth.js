/** Login page: Google sign-in via Firebase, exchanged for an HTTP-only session cookie. */

// Read a cookie value by name (used for the double-submit CSRF token).
function readCookie(name) {
  const match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
  return match ? decodeURIComponent(match[1]) : "";
}

function showError(message) {
  const el = document.getElementById("authError");
  el.textContent = message;
  el.hidden = false;
}

function setStatus(message) {
  document.getElementById("authStatus").textContent = message;
}

// Exchange a Firebase ID token for a server session cookie, then go to the app.
async function establishSession(idToken) {
  const csrfToken = readCookie("csrfToken");
  const response = await fetch("/auth/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ idToken, csrfToken }),
  });
  if (!response.ok) throw new Error(`Session request failed (HTTP ${response.status})`);
  window.location.assign("/table");
}

async function signInWithGoogle() {
  showErrorReset();
  setStatus("Opening Google sign-in…");
  try {
    const provider = new firebase.auth.GoogleAuthProvider();
    const result = await firebase.auth().signInWithPopup(provider);
    const idToken = await result.user.getIdToken();
    setStatus("Signing you in…");
    await establishSession(idToken);
  } catch (error) {
    setStatus("");
    showError("Sign-in failed. Please try again.");
    console.error("Google sign-in failed:", error);
  }
}

function showErrorReset() {
  const el = document.getElementById("authError");
  el.hidden = true;
  el.textContent = "";
}

// Fetch public auth config and initialize the Firebase client SDK.
async function initAuth() {
  let config;
  try {
    const response = await fetch("/api/auth-config", { signal: AbortSignal.timeout(10000) });
    config = await response.json();
  } catch (error) {
    showError("Unable to load sign-in configuration. Reload to try again.");
    console.error("auth-config load failed:", error);
    return;
  }

  // If auth is disabled server-side, the app is open — go straight in.
  if (!config.auth_enabled) {
    window.location.assign("/table");
    return;
  }

  firebase.initializeApp({
    apiKey: config.firebase.apiKey,
    authDomain: config.firebase.authDomain,
    projectId: config.firebase.projectId,
  });

  // HTTP-only session cookie is the source of truth; do not persist client state.
  await firebase.auth().setPersistence(firebase.auth.Auth.Persistence.NONE);

  const button = document.getElementById("googleSignInBtn");
  if (button) button.addEventListener("click", signInWithGoogle);
}

document.addEventListener("DOMContentLoaded", initAuth);
