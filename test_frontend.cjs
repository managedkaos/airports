const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function appContext() {
  const elements = new Map();
  const listeners = {};
  const timers = [];
  const document = {
    hidden: false,
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, { hidden: true, textContent: '', addEventListener(event, fn) { this[event] = fn; } });
      return elements.get(id);
    },
    addEventListener(event, fn) { listeners[event] = fn; },
  };
  const context = vm.createContext({ document, console: { error() {} }, AbortSignal, setInterval(fn, delay) { timers.push({ fn, delay }); } });
  vm.runInContext(fs.readFileSync('static/js/common.js', 'utf8'), context);
  return { context, document, listeners, timers };
}
const airport = { local_time: '2026-09-12T00:15:00+05:45', timezone: 'Asia/Kathmandu', is_weekend: true };
const snapshot = { generated_at: '2026-09-11T18:30:00Z', count: 1, results: [airport] };

test('preserves local calendar date and fractional offset regardless of browser zone', () => {
  const { context } = appContext();
  assert.equal(context.formatLocalTime(airport), '2026-09-12 00:15');
  assert.equal(context.formatTimeZone(airport), 'Asia/Kathmandu (UTC+05:45)');
  assert.equal(context.formatWeekend(airport), 'Weekend');
  assert.equal(context.formatWeekend({ is_weekend: false }), 'Weekday');
  assert.equal(context.formatLocalTime({ local_time: '2026-11-01T01:30:00-05:00' }), '2026-11-01 01:30');
});

test('load, retained snapshot on failure, retry, interval and tab return', async () => {
  const { context, document, timers, listeners } = appContext();
  let calls = 0;
  let fail = false;
  const rendered = [];
  context.fetch = async (url, options) => {
    calls++;
    assert.equal(url, '/api/airports');
    assert.equal(options.cache, 'no-store');
    if (fail) throw new Error('offline');
    return { ok: true, json: async () => snapshot };
  };
  context.initPolling(data => rendered.push(data));
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(calls, 1);
  assert.equal(rendered.length, 1);
  assert.equal(timers[0].delay, 60000);
  fail = true;
  await context.fetchAirports();
  assert.equal(rendered.length, 1);
  assert.equal(document.getElementById('errorBanner').hidden, false);
  assert.match(document.getElementById('errorMessage').textContent, /last updated 2026-09-11 18:30:00 UTC/);
  fail = false;
  await document.getElementById('errorRetryBtn').click();
  assert.equal(document.getElementById('errorBanner').hidden, true);
  document.hidden = true;
  listeners.visibilitychange();
  assert.equal(calls, 3);
  document.hidden = false;
  listeners.visibilitychange();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(calls, 4);
  await timers[0].fn();
  assert.equal(calls, 5);
});

test('initial failure exits loading state and retry can recover', async () => {
  const { context, document } = appContext();
  context.fetch = async () => ({ ok: false, status: 503 });
  context.initPolling(() => {});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(document.getElementById('updatedText').textContent, 'Airport times unavailable');
  assert.equal(document.getElementById('airportTableBody').textContent, '');
  assert.equal(document.getElementById('refreshBtn').disabled, false);
  context.fetch = async () => ({ ok: true, json: async () => snapshot });
  await document.getElementById('errorRetryBtn').click();
  assert.equal(document.getElementById('errorBanner').hidden, true);
});

function authContext({ authEnabled = true, cookie = 'csrfToken=tok123', firebase } = {}) {
  const elements = new Map();
  const listeners = {};
  const location = { assigned: null, assign(url) { this.assigned = url; } };
  const document = {
    cookie,
    getElementById(id) {
      if (!elements.has(id)) {
        elements.set(id, {
          hidden: true, textContent: '',
          addEventListener(event, fn) { this[event] = fn; },
        });
      }
      return elements.get(id);
    },
    addEventListener(event, fn) { listeners[event] = fn; },
  };
  const fetchCalls = [];
  const fetch = async (url, options) => {
    fetchCalls.push({ url, options });
    if (url === '/api/auth-config') {
      return { ok: true, json: async () => ({ auth_enabled: authEnabled, provider: 'firebase', firebase: { apiKey: 'k', authDomain: 'd', projectId: 'p' } }) };
    }
    if (url === '/auth/session') return { ok: true, json: async () => ({ status: 'success' }) };
    return { ok: false, status: 404 };
  };
  const context = vm.createContext({
    document, fetch, firebase, console: { error() {}, warn() {} },
    AbortSignal, window: { location },
  });
  vm.runInContext(fs.readFileSync('static/js/auth.js', 'utf8'), context);
  return { context, document, listeners, location, fetchCalls, elements };
}

function fakeFirebase() {
  const calls = { init: null, persistence: null, signedIn: false };
  const auth = () => ({
    setPersistence: async (p) => { calls.persistence = p; },
    signInWithPopup: async () => { calls.signedIn = true; return { user: { getIdToken: async () => 'ID_TOKEN' } }; },
  });
  auth.GoogleAuthProvider = function () {};
  auth.Auth = { Persistence: { NONE: 'NONE' } };
  return {
    initializeApp: (cfg) => { calls.init = cfg; },
    auth,
    __calls: calls,
  };
}

test('login: initializes Firebase and exchanges Google token for a session', async () => {
  const firebase = fakeFirebase();
  const { context, document, listeners, location, fetchCalls } = authContext({ firebase });
  await listeners.DOMContentLoaded();
  // Config fetched and Firebase initialized with the returned web config.
  assert.equal(fetchCalls[0].url, '/api/auth-config');
  assert.equal(firebase.__calls.init.apiKey, 'k');
  assert.equal(firebase.__calls.init.authDomain, 'd');
  assert.equal(firebase.__calls.init.projectId, 'p');
  assert.equal(firebase.__calls.persistence, 'NONE');
  // Clicking the button signs in and posts the token + CSRF cookie value.
  await document.getElementById('googleSignInBtn').click();
  assert.equal(firebase.__calls.signedIn, true);
  const post = fetchCalls.find(c => c.url === '/auth/session');
  assert.ok(post);
  const body = JSON.parse(post.options.body);
  assert.equal(body.idToken, 'ID_TOKEN');
  assert.equal(body.csrfToken, 'tok123');
  assert.equal(location.assigned, '/table');
});

test('login: redirects straight to app when auth is disabled', async () => {
  const firebase = fakeFirebase();
  const { listeners, location } = authContext({ authEnabled: false, firebase });
  await listeners.DOMContentLoaded();
  assert.equal(location.assigned, '/table');
  assert.equal(firebase.__calls.init, null);
});

test('login: shows a friendly error when sign-in fails', async () => {
  const firebase = fakeFirebase();
  // Replace auth() with one whose popup rejects.
  const failingAuth = () => ({
    setPersistence: async () => {},
    signInWithPopup: async () => { throw new Error('popup closed'); },
  });
  failingAuth.GoogleAuthProvider = function () {};
  failingAuth.Auth = { Persistence: { NONE: 'NONE' } };
  firebase.auth = failingAuth;
  const { document, listeners } = authContext({ firebase });
  await listeners.DOMContentLoaded();
  await document.getElementById('googleSignInBtn').click();
  assert.equal(document.getElementById('authError').hidden, false);
  assert.match(document.getElementById('authError').textContent, /Sign-in failed/);
});

function sessionContext({ me = { uid: 'u1', email: 'a@b.com', name: 'Ada Lovelace', picture: null }, meOk = true } = {}) {
  const elements = new Map();
  const listeners = {};
  const location = { assigned: null, assign(url) { this.assigned = url; } };
  const document = {
    getElementById(id) {
      if (!elements.has(id)) {
        elements.set(id, {
          hidden: true, textContent: '', style: {},
          addEventListener(event, fn) { this[event] = fn; },
        });
      }
      return elements.get(id);
    },
    addEventListener(event, fn) { listeners[event] = fn; },
  };
  const fetchCalls = [];
  const fetch = async (url, options) => {
    fetchCalls.push({ url, options });
    if (url === '/api/me') return { ok: meOk, status: meOk ? 200 : 401, json: async () => me };
    if (url === '/auth/logout') return { ok: true, json: async () => ({ status: 'success' }) };
    return { ok: false, status: 404 };
  };
  const context = vm.createContext({ document, fetch, console: { error() {} }, AbortSignal, window: { location } });
  vm.runInContext(fs.readFileSync('static/js/session.js', 'utf8'), context);
  return { context, document, listeners, location, fetchCalls, elements };
}

test('session: renders the profile name and initial-letter avatar from /api/me', async () => {
  const { document, listeners } = sessionContext();
  await listeners.DOMContentLoaded();
  assert.equal(document.getElementById('navProfile').hidden, false);
  assert.equal(document.getElementById('navUsername').textContent, 'Ada Lovelace');
  assert.equal(document.getElementById('navAvatar').textContent, 'A');
});

test('session: uses picture as avatar background when present', async () => {
  const { document, listeners } = sessionContext({ me: { uid: 'u1', name: 'Ada', picture: 'http://pic/x.png' } });
  await listeners.DOMContentLoaded();
  assert.equal(document.getElementById('navAvatar').style.backgroundImage, 'url("http://pic/x.png")');
  assert.equal(document.getElementById('navAvatar').textContent, '');
});

test('session: sign-out posts to /auth/logout and redirects to /login', async () => {
  const { document, listeners, location, fetchCalls } = sessionContext();
  await listeners.DOMContentLoaded();
  await document.getElementById('signOutBtn').click();
  const post = fetchCalls.find(c => c.url === '/auth/logout');
  assert.ok(post);
  assert.equal(post.options.method, 'POST');
  assert.equal(location.assigned, '/login');
});

test('session: stays quiet and hides profile when /api/me is unauthorized', async () => {
  const { document, listeners } = sessionContext({ meOk: false });
  await listeners.DOMContentLoaded();
  assert.equal(document.getElementById('navProfile').hidden, true);
});
