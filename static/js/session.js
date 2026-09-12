/** Logged-in navbar: render the current user's profile and handle sign-out. */

// Pick a display label and a single-letter avatar fallback from user claims.
function profileLabel(user) {
  return user.name || user.email || "Account";
}

function avatarInitial(user) {
  const label = profileLabel(user);
  return label.trim().charAt(0).toUpperCase() || "?";
}

function renderProfile(user) {
  const profile = document.getElementById("navProfile");
  if (!profile) return;
  document.getElementById("navUsername").textContent = profileLabel(user);

  const avatar = document.getElementById("navAvatar");
  if (avatar) {
    if (user.picture) {
      avatar.style.backgroundImage = `url("${user.picture}")`;
      avatar.style.backgroundSize = "cover";
      avatar.textContent = "";
    } else {
      avatar.textContent = avatarInitial(user);
    }
  }
  profile.hidden = false;
}

async function signOut() {
  try {
    await fetch("/auth/logout", { method: "POST" });
  } catch (error) {
    console.error("Sign-out request failed:", error);
  }
  window.location.assign("/login");
}

async function initSession() {
  const signOutBtn = document.getElementById("signOutBtn");
  if (signOutBtn) signOutBtn.addEventListener("click", signOut);

  try {
    const response = await fetch("/api/me", { signal: AbortSignal.timeout(10000) });
    if (!response.ok) return; // Page middleware already gates access; stay quiet.
    renderProfile(await response.json());
  } catch (error) {
    console.error("Could not load profile:", error);
  }
}

document.addEventListener("DOMContentLoaded", initSession);
