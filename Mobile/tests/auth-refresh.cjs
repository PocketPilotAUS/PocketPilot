const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function harness(native = false) {
  const modules = new Map();
  const secure = new Map();
  let fetchImpl;
  const context = vm.createContext({ Headers, Response, AbortController, setTimeout, clearTimeout,
    fetch: (...args) => fetchImpl(...args) });
  function load(name) {
    if (modules.has(name)) return modules.get(name).exports;
    const module = { exports: {} };
    modules.set(name, module);
    const source = fs.readFileSync(path.join(__dirname, '../src/services', name + '.ts'), 'utf8');
    const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
    const requireMock = id => {
      if (id === 'react-native') return { Platform: { OS: native ? 'android' : 'web' } };
      if (id === 'expo-secure-store') return {
        WHEN_UNLOCKED_THIS_DEVICE_ONLY: 1,
        getItemAsync: async key => secure.get(key) ?? null,
        setItemAsync: async (key, value) => { secure.set(key, value); },
        deleteItemAsync: async key => { secure.delete(key); },
      };
      if (id === '@react-native-async-storage/async-storage') return { default: { multiRemove: async () => {} } };
      return load(id.replace('./', ''));
    };
    vm.runInContext(`(function(require,module,exports){${code}\n})`, context)(requireMock, module, module.exports);
    return module.exports;
  }
  return { storage: load('tokenStorage'), api: load('apiClient'), auth: load('authService'), secure,
    setFetch: fn => { fetchImpl = fn; } };
}
const json = (status, body = {}) => new Response(JSON.stringify(body), { status });
const oldPair = { access_token: 'expired', refresh_token: 'old-refresh' };
const newPair = { access_token: 'renewed', refresh_token: 'new-refresh' };
const tick = () => new Promise(resolve => setImmediate(resolve));

test('concurrent 401s refresh once and retry original requests', async () => {
  const h = harness();
  await h.storage.saveSession(oldPair);
  let refreshes = 0;
  const retried = [];
  h.setFetch(async (url, options) => {
    if (url.endsWith('/auth/refresh')) { refreshes++; await tick(); return json(200, newPair); }
    if (options.headers.get('Authorization') === 'Bearer expired') return json(401);
    retried.push([url, options.method, options.body]);
    return json(200);
  });
  const responses = await Promise.all([
    h.api.apiFetch('http://test', '/expense', { method: 'POST', body: '{"request_key":"same"}' }),
    h.api.apiFetch('http://test', '/budget'),
  ]);
  assert.equal(refreshes, 1);
  assert.ok(responses.every(r => r.ok));
  assert.ok(retried.some(r => r[1] === 'POST' && r[2] === '{"request_key":"same"}'));
  assert.equal((await h.storage.getSession()).refresh_token, 'new-refresh');
});

test('refresh rejection signs out once, without a retry loop', async () => {
  const h = harness();
  await h.storage.saveSession(oldPair);
  let notices = 0, refreshes = 0;
  h.api.setSessionExpiredHandler(() => notices++);
  h.setFetch(async url => { if (url.endsWith('/auth/refresh')) { refreshes++; await tick(); } return json(401); });
  await Promise.all([1, 2].map(() => assert.rejects(h.api.apiFetch('http://test', '/me'), h.api.SessionExpiredError)));
  assert.equal(notices, 1);
  assert.equal(refreshes, 1);
  assert.equal(await h.storage.getSession(), null);
});

test('offline or server failure retains session', async () => {
  for (const networkError of [true, false]) {
    const h = harness();
    await h.storage.saveSession(oldPair);
    h.setFetch(async url => {
      if (!url.endsWith('/auth/refresh')) return json(401);
      if (networkError) throw new Error('offline');
      return json(503);
    });
    await assert.rejects(h.api.apiFetch('http://test', '/me'));
    assert.equal((await h.storage.getSession()).refresh_token, 'old-refresh');
  }
});

test('late refresh cannot restore logged-out session or overwrite a new login', async () => {
  for (const newLogin of [false, true]) {
    const h = harness();
    await h.storage.saveSession(oldPair);
    let finish;
    h.setFetch(async url => url.endsWith('/auth/refresh') ? new Promise(resolve => { finish = resolve; }) : json(401));
    const request = h.api.apiFetch('http://test', '/me');
    while (!finish) await tick();
    await h.storage.clearToken();
    if (newLogin) await h.storage.saveSession({ access_token: 'other', refresh_token: 'other-refresh' });
    finish(json(200, newPair));
    await assert.rejects(request, h.api.SessionExpiredError);
    assert.equal((await h.storage.getSession())?.access_token ?? null, newLogin ? 'other' : null);
  }
});

test('startup restores with an expired access token by refreshing', async () => {
  const h = harness();
  await h.storage.saveSession(oldPair);
  h.setFetch(async (url, options) => {
    if (url.endsWith('/auth/refresh')) return json(200, newPair);
    return options.headers.get('Authorization') === 'Bearer renewed' ? json(200, { id: 1, name: 'Alice' }) : json(401);
  });
  assert.equal((await h.auth.restoreSession('http://test')).status, 'authenticated');
});

test('native storage writes one pair and clears legacy and new keys', async () => {
  const h = harness(true);
  await h.storage.saveSession(oldPair);
  assert.equal(h.secure.size, 1);
  assert.equal(JSON.parse(h.secure.get('pocketpilot_session_v2')).refresh_token, 'old-refresh');
  await h.storage.clearToken();
  assert.equal(h.secure.size, 0);
});

test('logout revokes the saved refresh family and clears local tokens', async () => {
  const h = harness();
  await h.storage.saveSession(oldPair);
  let body;
  h.setFetch(async (url, options) => {
    assert.equal(url, 'http://test/auth/logout');
    assert.equal(await h.storage.getSession(), null);
    body = JSON.parse(options.body);
    return new Response(null, { status: 204 });
  });
  await h.auth.logout('http://test');
  assert.equal(body.refresh_token, oldPair.refresh_token);
});
