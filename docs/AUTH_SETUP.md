# Authentication setup (Google via Firebase)

The Airports app gates the whole application behind Google sign-in. Sign-in runs
in the browser with the Firebase JS SDK; the FastAPI backend verifies the
resulting Firebase ID token with the Firebase Admin SDK and issues an HTTP-only
session cookie. The auth backend is pluggable (`AUTH_PROVIDER`), so Firebase can
be swapped for another Google-compatible provider without changing routes.

This document explains how to create the required Firebase project and Google
OAuth client, where credentials are stored, and how to run the app.

## 1. Create the Firebase project and enable Google sign-in

1. Open the [Firebase console](https://console.firebase.google.com) and click
   **Add project**. Give it a name (for example, `airports`). A linked Google
   Cloud project is created automatically.
2. In the left nav, go to **Build → Authentication → Get started**.
3. On the **Sign-in method** tab, click **Add new provider → Google**, toggle it
   **Enabled**, choose a project support email, and **Save**.
   - Enabling Google here automatically provisions an **OAuth 2.0 client ID** in
     the linked Google Cloud project (visible under Google Cloud Console →
     *APIs & Services → Credentials*). You do not need to create it by hand.
4. On the **Settings → Authorized domains** tab, ensure `localhost` is present
   for local development, and add your deployment domain (for example,
   `airports.example.com`) when you deploy.

## 2. Register a Web app (browser config — not secret)

1. In **Project settings** (gear icon) → **General → Your apps**, click the web
   icon (`</>`) to register a Web app. Skip Firebase Hosting.
2. Copy the `firebaseConfig` values. The app only needs three of them:
   - `apiKey`      → `FIREBASE_API_KEY`
   - `authDomain`  → `FIREBASE_AUTH_DOMAIN`
   - `projectId`   → `FIREBASE_PROJECT_ID`

These values are **browser-visible by design** and are not secrets. The app
serves them to the client through the public `GET /api/auth-config` endpoint.

## 3. Generate a service account key (server credential — secret)

The Admin SDK needs a service account to verify ID tokens and mint/verify
session cookies.

1. **Project settings → Service accounts → Generate new private key**.
2. Save the downloaded JSON **outside the repository** (for example,
   `~/secrets/airports-firebase-adminsdk.json`).
3. Point the app at it with `GOOGLE_APPLICATION_CREDENTIALS`, or inline the JSON
   contents into `FIREBASE_SERVICE_ACCOUNT_JSON` for platforms that inject
   secrets as environment variables.

> **Never commit the service account JSON and never copy it into the container
> image.** `.gitignore` and `.dockerignore` already exclude
> `service-account*.json` and `*firebase-adminsdk*.json`. Mount it as a secret
> at runtime instead.

## 4. Configuration reference

| Variable | Scope | Required | Purpose |
|----------|-------|----------|---------|
| `AUTH_ENABLED` | server | no (default `true`) | Master switch. Set `false` for local dev/tests to bypass auth entirely. |
| `AUTH_PROVIDER` | server | no (default `firebase`) | Selects the auth provider implementation. |
| `GOOGLE_APPLICATION_CREDENTIALS` | server | one of these | Filesystem path to the service account JSON. |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | server | one of these | Inline service account JSON (alternative to the file path). |
| `FIREBASE_API_KEY` | browser | yes (firebase) | Web app API key. |
| `FIREBASE_AUTH_DOMAIN` | browser | yes (firebase) | Web app auth domain (`<project>.firebaseapp.com`). |
| `FIREBASE_PROJECT_ID` | browser | yes (firebase) | Firebase/Google Cloud project ID. |
| `SESSION_COOKIE_NAME` | server | no (default `session`) | Name of the session cookie. |
| `SESSION_EXPIRES_DAYS` | server | no (default `5`) | Session cookie lifetime in days (Firebase allows 5 min–14 days). |
| `SESSION_COOKIE_SECURE` | server | no (default `true`) | Set `false` for local HTTP dev so the cookie is sent over `http://localhost`. |

## 5. Running

### Local development without auth (fastest)

```bash
make run AUTH_ENABLED=false
```

All routes behave as before; no Firebase project is needed.

### Local development with real Google sign-in

```bash
export AUTH_ENABLED=true
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/secrets/airports-firebase-adminsdk.json"
export FIREBASE_API_KEY="AIza..."
export FIREBASE_AUTH_DOMAIN="airports-xxxx.firebaseapp.com"
export FIREBASE_PROJECT_ID="airports-xxxx"
export SESSION_COOKIE_SECURE=false   # localhost is http://
make run
```

Visit `http://localhost:8181/` — it redirects to `/login`. Sign in with Google,
and you land on `/table` with your profile shown in the navbar.

### Container

Pass the browser config as environment variables and mount the service account
JSON as a secret (do not bake it into the image):

```bash
docker run --rm -p 8181:8000 \
  -e AUTH_ENABLED=true \
  -e FIREBASE_API_KEY="AIza..." \
  -e FIREBASE_AUTH_DOMAIN="airports-xxxx.firebaseapp.com" \
  -e FIREBASE_PROJECT_ID="airports-xxxx" \
  -e GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/firebase.json \
  -v "$HOME/secrets/airports-firebase-adminsdk.json:/run/secrets/firebase.json:ro" \
  airports:latest
```
