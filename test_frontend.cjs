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
