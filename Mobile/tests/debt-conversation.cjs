const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function load(file, requireMock) {
  const source = fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, esModuleInterop: true } }).outputText;
  const module = { exports: {} };
  vm.runInNewContext('(function(require,module,exports){' + code + '\n})', { AbortController, setTimeout, clearTimeout })(requireMock, module, module.exports);
  return module.exports;
}

test('pending debt context survives message trimming; agreement never auto-saves', async () => {
  const state = [];
  let index = 0;
  const react = { useState(initial) { const slot = index++; if (!(slot in state)) state[slot] = initial;
    return [state[slot], value => state[slot] = typeof value === 'function' ? value(state[slot]) : value]; },
    useRef(initial) { const slot = index++; return state[slot] ?? (state[slot] = { current: initial }); }, useEffect() {} };
  const calls = [];
  let next = { reply: 'Here is the review card.', debt_state: 'next-context', debt_phase: 'review',
    plan: { ready: true, debtGoalSource: true, budgetGoalSource: true, debtConfirmation: 'signed-review', reviewId: 'debt-review', profile: {} } };
  const api = { SessionExpiredError: class extends Error {}, apiFetch: async (base, url, options) => {
    calls.push({ url, body: JSON.parse(options.body) });
    return { ok: true, json: async () => next };
  } };
  const planning = load('src/services/planningService.ts', () => api);
  const hook = load('src/hooks/useChatSession.ts', id => {
    if (id === 'react') return react;
    if (id.endsWith('planningService')) return planning;
    if (id.endsWith('apiClient')) return api;
    if (id.endsWith('localize')) return { getRuntimeLanguage: () => 'en' };
    if (id.endsWith('currency')) return { getCurrencyPreference: () => ({ currency: 'AED' }) };
    throw new Error(id);
  }).default;
  const render = () => { index = 0; return hook('test'); };
  let session = render();
  const messages = Array.from({ length: 24 }, (_, i) => ({ role: i % 2 ? 'assistant' : 'user', content: 'Earlier conversation' }));
  messages[messages.length - 1].debtState = 'pending-proposal';
  messages[messages.length - 1].planningProfile = { goal: 'Old savings goal', target_amount: 5000 };
  messages[messages.length - 1].goalPlanning = true;
  session.onMessagesChange(messages); session = render();
  await session.send('yes please'); session = render();
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, '/ai/chat');
  assert.equal(calls[0].body.debt_state, 'pending-proposal');
  assert.equal(calls[0].body.messages.length, 21);
  assert.equal(session.messages.at(-1).debtState, 'next-context');
  const plan = session.messages.at(-1).plan;
  next = { ...plan, id: 'saved', debtState: 'saved-context' };
  await session.saveFinancialPlan(plan, session.messages.length - 1, true); session = render();
  assert.equal(calls[1].url, '/planning/reviews/debt-review/accept');
  assert.equal(calls[0].body.plan_review_ids.length, 0);
  assert.equal(calls[1].body.apply_to_budget, true);
  assert.equal(session.messages.at(-1).debtState, 'saved-context');
  next = { reply: 'Sure, we can discuss something else.', debt_state: null };
  await session.send('new topic'); session = render();
  assert.equal(session.messages.at(-1).debtState, undefined);
  next = { reply: 'Hello' };
  await session.send('hello');
  assert.equal(calls.at(-1).body.debt_state, undefined);
  assert.equal(calls.at(-1).body.planning_profile, undefined);
  assert.equal(calls.at(-1).body.goal_planning, false);
  session = render(); session.reset(); session = render();
  assert.equal(session.messages.length, 0);
});

test('explaining a debt draft keeps Accept available; rejection disables it', () => {
  const react = { createElement: (type, props, ...children) => ({ type, props: props || {}, children }),
    useState: value => [value, () => {}], useRef: value => ({ current: value }), useEffect() {}, Fragment: 'Fragment' };
  const screen = load('src/screens/AIChatScreen.tsx', id => {
    if (id === 'react') return { __esModule: true, default: react, ...react };
    if (id === 'react-native') return { Platform: { OS: 'android' }, Pressable: 'Pressable' };
    if (id.endsWith('useAITheme')) return { useAITheme: () => ({ ai: {}, styles: {}, palette: {} }) };
    if (id.endsWith('apiClient')) return { SessionExpiredError: class extends Error {} };
    return { __esModule: true, default: id.split('/').pop(), Text: 'Text', View: 'View', SafeAreaView: 'SafeAreaView' };
  }).default;
  function flatten(value) { return Array.isArray(value) ? value.flatMap(flatten) : value && typeof value === 'object' ? [value, ...flatten(value.children)] : []; }
  for (const [phase, disabled] of [['review', false], ['declined', true], ['discuss', true]]) {
    const messages = [{ role: 'assistant', content: 'Draft', plan: { ready: true, debtGoalSource: true, profile: {} } },
      { role: 'user', content: 'Explain that' }, { role: 'assistant', content: 'Explanation', debtState: 'context', debtPhase: phase }];
    const tree = screen({ apiBaseUrl: 'unused', onSetupBudget() {}, onReviewProfile() {}, session: {
      messages, draft: '', busy: false, pendingQuestion: null, error: null, savingPlan: null } });
    const controls = flatten(tree).find(node => node.type === 'PlanConfirmationActions');
    assert.equal(controls.props.busy, disabled);
  }
});

test('accepting a debt plan asks whether to apply its budget target before saving', () => {
  const state = []; let index = 0;
  const react = { createElement: (type, props, ...children) => ({ type, props: props || {}, children }),
    useState(initial) { const slot = index++; if (!(slot in state)) state[slot] = initial;
      return [state[slot], value => state[slot] = value]; },
    useRef(initial) { const slot = index++; return state[slot] ?? (state[slot] = { current: initial }); }, useEffect() {}, Fragment: 'Fragment' };
  const screen = load('src/screens/AIChatScreen.tsx', id => {
    if (id === 'react') return { __esModule: true, default: react, ...react };
    if (id === 'react-native') return { Platform: { OS: 'web' }, Pressable: 'Pressable', Modal: 'Modal' };
    if (id.endsWith('useAITheme')) return { useAITheme: () => ({ ai: {}, styles: {}, palette: {} }) };
    if (id.endsWith('apiClient')) return { SessionExpiredError: class extends Error {} };
    return { __esModule: true, default: id.split('/').pop(), Text: 'Text', View: 'View', SafeAreaView: 'SafeAreaView' };
  }).default;
  const plan = { ready: true, debtGoalSource: true, profile: {} };
  const saves = [];
  const session = { messages: [{ role: 'assistant', content: 'Draft', plan }], draft: '', busy: false,
    pendingQuestion: null, error: null, savingPlan: null, saveFinancialPlan: (...args) => saves.push(args) };
  const render = () => { index = 0; return screen({ apiBaseUrl: 'unused', onSetupBudget() {}, onReviewProfile() {}, session }); };
  function flatten(value) { return Array.isArray(value) ? value.flatMap(flatten) : value && typeof value === 'object' ? [value, ...flatten(value.children)] : []; }
  const choiceModal = tree => flatten(tree).find(node => node.type === 'Modal');
  const button = (tree, label) => flatten(tree).find(node => node.type === 'Pressable' && flatten(node).some(child => child.type === 'Text' && child.children.includes(label)));
  let tree = render();
  assert.equal(choiceModal(tree).props.visible, false);
  for (const [label, applies] of [['Cancel', null], ['Save plan only', false], ['Apply and save', true]]) {
    flatten(tree).find(node => node.type === 'PlanConfirmationActions').props.onConfirm();
    tree = render();
    assert.equal(choiceModal(tree).props.visible, true);
    const before = saves.length;
    button(choiceModal(tree), label).props.onPress();
    tree = render();
    assert.equal(choiceModal(tree).props.visible, false);
    assert.equal(saves.length, before + (applies === null ? 0 : 1));
    if (applies !== null) { assert.equal(saves.at(-1)[0], plan); assert.equal(saves.at(-1)[1], 0); assert.equal(saves.at(-1)[2], applies); }
  }
});

test('D1 sends the full loan conversation and latest signed state without applying a plan', async () => {
  const slots = []; let cursor = 0;
  const react = { useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = initial;
    return [slots[i], value => slots[i] = typeof value === 'function' ? value(slots[i]) : value]; },
    useRef(initial) { const i = cursor++; return slots[i] ?? (slots[i] = { current: initial }); }, useEffect() {} };
  const calls = [];
  const replies = [
    { reply: 'Your saved Car Loan is AED 30,000 at 5% annual interest. What timeframe?', debt_state: 'car-loan-selected' },
    { reply: '24 months: AED 1,316.15 monthly.', debt_state: 'car-loan-24-months' },
    { reply: '36 months: AED 899.13 monthly.', debt_state: 'car-loan-36-months' },
  ];
  const hook = load('src/hooks/useChatSession.ts', id => {
    if (id === 'react') return react;
    if (id.endsWith('planningService')) return {};
    if (id.endsWith('apiClient')) return { SessionExpiredError: class extends Error {}, apiFetch: async (base, url, options) => {
      calls.push({ url, body: JSON.parse(options.body) }); return { ok: true, json: async () => replies.shift() };
    }};
    if (id.endsWith('localize')) return { getRuntimeLanguage: () => 'en' };
    if (id.endsWith('currency')) return { getCurrencyPreference: () => ({ currency: 'AED' }) };
    throw new Error(id);
  }).default;
  const render = () => { cursor = 0; return hook('test'); };
  let session = render();
  for (const text of ['I wanna pay off my car loan faster.', 'Could I finish it in two years?', "Actually, let's do three."]) {
    await session.send(text); session = render();
  }
  assert.equal(calls[0].body.debt_state, undefined);
  assert.equal(calls[1].body.debt_state, 'car-loan-selected');
  assert.equal(calls[2].body.debt_state, 'car-loan-24-months');
  assert.equal(calls[2].body.messages.length, 5);
  assert.match(calls[2].body.messages[0].content, /^I wanna pay off my car loan faster/);
  assert.match(calls[2].body.messages[2].content, /^Could I finish it in two years/);
  assert.match(calls[2].body.messages[4].content, /^Actually, let's do three/);
  assert.equal(session.messages.at(-1).debtState, 'car-loan-36-months');
  assert.ok(calls.every(call => call.url === '/ai/chat'));
  assert.ok(session.messages.every(message => !message.proposal && !message.plan));
});

test('T2 clears obsolete loan state across budget and income lookups before an ambiguous amount', async () => {
  const slots = []; let cursor = 0;
  const react = { useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = initial;
    return [slots[i], value => slots[i] = typeof value === 'function' ? value(slots[i]) : value]; },
    useRef(initial) { const i = cursor++; return slots[i] ?? (slots[i] = { current: initial }); }, useEffect() {} };
  const calls = [];
  const replies = [
    { reply: 'What timeframe?', debt_state: 'car-loan-selected' },
    { reply: 'Your planned headroom is AED 3,580.' },
    { reply: 'Your saved monthly income is AED 10,000.' },
    { reply: 'What does AED 800 refer to?' },
  ];
  const hook = load('src/hooks/useChatSession.ts', id => {
    if (id === 'react') return react;
    if (id.endsWith('planningService')) return {};
    if (id.endsWith('apiClient')) return { SessionExpiredError: class extends Error {}, apiFetch: async (base, url, options) => {
      calls.push({ url, body: JSON.parse(options.body) }); return { ok: true, json: async () => replies.shift() };
    }};
    if (id.endsWith('localize')) return { getRuntimeLanguage: () => 'en' };
    if (id.endsWith('currency')) return { getCurrencyPreference: () => ({ currency: 'AED' }) };
    throw new Error(id);
  }).default;
  const render = () => { cursor = 0; return hook('test'); };
  let session = render();
  for (const text of ['I wanna pay off my car loan faster.', "How's my budget looking?", "What's my monthly income?", '800']) {
    await session.send(text); session = render();
  }
  assert.equal(calls[1].body.debt_state, 'car-loan-selected');
  for (const call of calls.slice(2)) {
    assert.equal(call.body.debt_state, undefined);
    assert.equal(call.body.record_state, undefined);
    assert.equal(call.body.planning_profile, undefined);
    assert.ok(!call.body.goal_planning);
  }
  assert.equal(calls[3].body.messages.length, 7);
  assert.match(calls[3].body.messages[6].content, /^800/);
  assert.ok(calls.every(call => call.url === '/ai/chat'));
  assert.ok(session.messages.every(message => !message.proposal && !message.plan));
});

test('lookup clears incomplete income state before the next numeric reply', async () => {
  const slots = []; let cursor = 0;
  const react = { useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = initial;
    return [slots[i], value => slots[i] = typeof value === 'function' ? value(slots[i]) : value]; },
    useRef(initial) { const i = cursor++; return slots[i] ?? (slots[i] = { current: initial }); }, useEffect() {} };
  const calls = [];
  const replies = [
    { reply: 'When did you receive/pay it?', record_state: 'incomplete-record-token' },
    { reply: 'Your saved monthly income is AED 10,000.' },
    { reply: 'What does AED 800 refer to?' },
  ];
  const hook = load('src/hooks/useChatSession.ts', id => {
    if (id === 'react') return react;
    if (id.endsWith('planningService')) return {};
    if (id.endsWith('apiClient')) return { SessionExpiredError: class extends Error {}, apiFetch: async (base, url, options) => {
      calls.push({ url, body: JSON.parse(options.body) }); return { ok: true, json: async () => replies.shift() };
    }};
    if (id.endsWith('localize')) return { getRuntimeLanguage: () => 'en' };
    if (id.endsWith('currency')) return { getCurrencyPreference: () => ({ currency: 'AED' }) };
    throw new Error(id);
  }).default;
  const render = () => { cursor = 0; return hook('test'); };
  let session = render();
  for (const text of ['I earned 2k.', "What's my monthly income?", '800']) {
    await session.send(text); session = render();
  }
  assert.equal(calls[1].body.record_state, 'incomplete-record-token');
  assert.equal(calls[2].body.record_state, undefined);
  assert.equal(calls[2].body.debt_state, undefined);
  assert.equal(calls[2].body.planning_profile, undefined);
  assert.ok(calls.every(call => call.url === '/ai/chat'));
  assert.ok(session.messages.every(message => !message.proposal && !message.plan));
});

test('lookup clears incomplete expense state before the next numeric reply', async () => {
  const slots = []; let cursor = 0;
  const react = { useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = initial;
    return [slots[i], value => slots[i] = typeof value === 'function' ? value(slots[i]) : value]; },
    useRef(initial) { const i = cursor++; return slots[i] ?? (slots[i] = { current: initial }); }, useEffect() {} };
  const calls = [];
  const replies = [
    { reply: 'When did you receive/pay it?', record_state: 'incomplete-record-token' },
    { reply: 'Your saved monthly income is AED 10,000.' },
    { reply: 'What does AED 800 refer to?' },
  ];
  const hook = load('src/hooks/useChatSession.ts', id => {
    if (id === 'react') return react;
    if (id.endsWith('planningService')) return {};
    if (id.endsWith('apiClient')) return { SessionExpiredError: class extends Error {}, apiFetch: async (base, url, options) => {
      calls.push({ url, body: JSON.parse(options.body) }); return { ok: true, json: async () => replies.shift() };
    }};
    if (id.endsWith('localize')) return { getRuntimeLanguage: () => 'en' };
    if (id.endsWith('currency')) return { getCurrencyPreference: () => ({ currency: 'AED' }) };
    throw new Error(id);
  }).default;
  const render = () => { cursor = 0; return hook('test'); };
  let session = render();
  for (const text of ['Lunch was 50.', "What's my monthly income?", '800']) {
    await session.send(text); session = render();
  }
  assert.equal(calls[1].body.record_state, 'incomplete-record-token');
  assert.equal(calls[2].body.record_state, undefined);
  assert.equal(calls[2].body.debt_state, undefined);
  assert.equal(calls[2].body.planning_profile, undefined);
  assert.ok(calls.every(call => call.url === '/ai/chat'));
  assert.ok(session.messages.every(message => !message.proposal && !message.plan));
});
