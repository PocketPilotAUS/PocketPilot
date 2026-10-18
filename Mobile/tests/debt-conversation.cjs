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
    plan: { ready: true, debtGoalSource: true, budgetGoalSource: true, debtConfirmation: 'signed-review', profile: {} } };
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
  assert.equal(calls[1].url, '/planning/debt-plans');
  assert.equal(calls[1].body.token, 'signed-review');
  assert.equal(calls[1].body.apply_to_budget, true);
  assert.equal(session.messages.at(-1).debtState, 'saved-context');
  next = { reply: 'Sure, we can discuss something else.', debt_state: null };
  await session.send('new topic'); session = render();
  assert.equal(session.messages.at(-1).debtState, undefined);
  next = { reply: 'Hello' };
  await session.send('hello');
  assert.equal(calls.at(-1).body.debt_state, undefined);
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
