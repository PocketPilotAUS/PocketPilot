const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

function load(relative, requireMock) {
  const source = fs.readFileSync(path.join(__dirname, "..", relative), "utf8");
  const code = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, esModuleInterop: true,
  }}).outputText;
  const module = { exports: {} };
  vm.runInNewContext("(function(require,module,exports){" + code + "\n})", { AbortController, setTimeout, clearTimeout })(requireMock, module, module.exports);
  return module.exports;
}

function render(messages, sessionOverrides = {}, apiOverrides = {}, effects = []) {
  const react = {
    createElement: (type, props, ...children) => ({ type, props: props || {}, children }),
    useState: value => [value, () => {}],
    useRef: value => ({ current: value }),
    useEffect: effect => effects.push(effect()),
    Fragment: "Fragment",
  };
  const screen = load("src/screens/AIChatScreen.tsx", id => {
    if (id === "react") return { __esModule: true, default: react, ...react };
    if (id === "react-native") return { Platform: { OS: "android" }, ...Object.fromEntries(
      ["KeyboardAvoidingView", "Modal", "Pressable", "ScrollView", "StatusBar"].map(name => [name, name])) };
    if (id.endsWith("useAITheme")) return { useAITheme: () => ({ ai: {}, styles: {}, palette: {}, mode: "dark" }) };
    if (id.endsWith("apiClient")) return { SessionExpiredError: class extends Error {}, ...apiOverrides };
    const name = id.split("/").pop();
    return { __esModule: true, default: name, ...Object.fromEntries(
      ["View", "Text", "TextInput", "SafeAreaView", "Sparkles", "ArrowUp", "SquarePen"].map(n => [n, n])) };
  }).default;
  return screen({ apiBaseUrl: "unused", onSetupBudget() {}, onReviewProfile() {},
    session: { messages, draft: "", busy: false, pendingQuestion: null, error: null,
      savingPlan: null, onMessagesChange() {}, setDraft() {}, setError() {}, ...sessionOverrides } });
}

function elements(tree, type) {
  if (!tree || typeof tree !== "object") return [];
  if (Array.isArray(tree)) return tree.flatMap(item => elements(item, type));
  return [...(tree.type === type ? [tree] : []), ...elements(tree.children, type)];
}

test("a mixed response renders only transaction controls; older plan cards survive", () => {
  const proposal = { id: "p", kind: "expense", amount: 50, category: "Food",
    date: "2026-10-17", status: "pending" };
  const plan = { ready: true, profile: {} };
  const tree = render([
    { role: "assistant", content: "Earlier plan", plan },
    { role: "assistant", content: "Ready to record", proposal, plan, budgetGoal: {}, planningProfile: {} },
  ]);
  assert.equal(elements(tree, "PlanConfirmationActions").length, 1);
  assert.equal(elements(tree, "BudgetGoalCard").length, 0);
  const cards = elements(tree, "ProposalCard");
  assert.equal(cards.length, 1);
  assert.equal(cards[0].props.proposal.date, "2026-10-17");
});

test("ISO proposal dates format as the same local calendar date", () => {
  const dates = load("src/utils/transactions.ts", () => { throw new Error("Unexpected dependency"); });
  assert.equal(dates.formatLongDate("2026-10-17"), "Saturday, 17 October 2026");
  assert.equal(dates.formatLongDate("2026-10-31"), "Saturday, 31 October 2026");
});


function planLabels(props) {
  const react = { createElement: (type, props, ...children) => ({ type, props, children }),
    Fragment: "Fragment" };
  const actions = load("src/components/ai/PlanConfirmationActions.tsx", id => {
    if (id === "react") return { __esModule: true, default: react };
    if (id.endsWith("useDashboardTheme")) return { useDashboardTheme: () => ({ styles: {} }) };
    return { __esModule: true, default: id, Text: "Text", View: "View", Pressable: "Pressable" };
  }).default;
  const tree = actions(props);
  return elements(tree, "Text").flatMap(node => node.children).filter(v => typeof v === "string");
}

test("unrelated loading disables a plan without claiming to save it", () => {
  const message = { role: "assistant", content: "Draft", plan: { ready: true, profile: {} } };
  const props = elements(render([message], { busy: true }), "PlanConfirmationActions")[0].props;
  assert.equal(props.busy, true);
  assert.equal(props.saving, false);
  assert.ok(planLabels(props).includes("Accept plan"));
  assert.equal(planLabels(props).some(v => v.startsWith("Saving")), false);
  const two = elements(render([message, message], { savingPlan: 1 }), "PlanConfirmationActions");
  assert.equal(two[0].props.saving, false);
  assert.equal(two[1].props.saving, true);
  assert.ok(planLabels(two[0].props).includes("Accept plan"));
  assert.ok(planLabels(two[1].props).some(v => v.startsWith("Saving")));
});

test("sending after a draft never accepts it; only explicit acceptance shows saving", async () => {
  const slots = [];
  let cursor = 0;
  const react = { useState(initial) {
    const i = cursor++;
    if (!(i in slots)) slots[i] = initial;
    return [slots[i], value => { slots[i] = typeof value === "function" ? value(slots[i]) : value; }];
  }, useRef(initial) {
    const i = cursor++;
    if (!(i in slots)) slots[i] = { current: initial };
    return slots[i];
  }, useEffect() {} };
  let complete;
  const calls = [];
  const api = { SessionExpiredError: class extends Error {},
    apiFetch(base, url, options) {
      calls.push({ url, payload: JSON.parse(options.body) });
      return new Promise(resolve => { complete = resolve; });
    } };
  const planning = load("src/services/planningService.ts", () => api);
  const hook = load("src/hooks/useChatSession.ts", id => {
    if (id === "react") return react;
    if (id.endsWith("planningService")) return planning;
    if (id.endsWith("apiClient")) return api;
    if (id.endsWith("localize")) return { getRuntimeLanguage: () => "en" };
    if (id.endsWith("currency")) return { getCurrencyPreference: () => ({ currency: "AED" }) };
    throw new Error(id);
  }).default;
  const renderHook = () => { cursor = 0; return hook("unused"); };
  let session = renderHook();
  const plan = { ready: true, title: "Vacation", budgetGoalSource: true, profile: { goal: "Vacation" },
    budgetFingerprint: "fingerprint", draftFingerprint: "draft", confirmationKey: "key", reviewId: "key" };
  session.onMessagesChange([{ role: "user", content: "Create a Vacation plan" },
    { role: "assistant", content: "Draft", plan, goalPlanning: true }]);
  session = renderHook();
  const sending = session.send("Record an expense of AED 25 for Food today.");
  session = renderHook();
  assert.equal(session.busy, true);
  assert.equal(session.savingPlan, null);
  const pendingProps = elements(render(session.messages, session), "PlanConfirmationActions")[0].props;
  assert.equal(pendingProps.saving, false);
  assert.ok(planLabels(pendingProps).includes("Accept plan"));
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "/ai/chat");
  assert.equal(calls[0].payload.budget_draft_status, "draft");
  complete({ ok: true, json: async () => ({ reply: "Ready to record", proposal: {
    id: "expense", kind: "expense", amount: 25, date: "2026-10-17", status: "pending" } }) });
  await sending;
  session = renderHook();
  assert.equal(calls.length, 1);
  assert.equal(session.messages[1].plan.id, undefined);
  const saving = session.saveFinancialPlan(plan, 1);
  session = renderHook();
  assert.equal(calls[1].url, "/planning/reviews/key/accept");
  assert.equal(session.savingPlan, 1);
  const savingProps = elements(render(session.messages, session), "PlanConfirmationActions")[0].props;
  assert.ok(planLabels(savingProps).some(v => v.startsWith("Saving")));
  assert.equal(planLabels(savingProps).some(v => v.startsWith("Plan saved")), false);
  complete({ ok: false, json: async () => ({ detail: "Budget changed" }) });
  await saving;
  session = renderHook();
  assert.equal(session.savingPlan, null);
  assert.equal(session.messages[1].plan.id, undefined);
  const failedProps = elements(render(session.messages, session), "PlanConfirmationActions")[0].props;
  assert.ok(planLabels(failedProps).includes("Accept plan"));
  assert.equal(planLabels(failedProps).some(v => v.startsWith("Plan saved")), false);
  const retry = session.saveFinancialPlan(plan, 1);
  assert.equal(calls[2].url, "/planning/reviews/key/accept");
  complete({ ok: true, json: async () => ({ ...plan, id: "persisted-plan" }) });
  await retry;
  session = renderHook();
  assert.equal(session.savingPlan, null);
  const savedProps = elements(render(session.messages, session), "PlanConfirmationActions")[0].props;
  assert.ok(planLabels(savedProps).some(v => v.startsWith("Plan saved")));
});


test("E5 keeps the pending expense and history for Today, then clears state on completion/reset", async () => {
  const slots = []; let cursor = 0;
  const react = {
    useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = initial;
      return [slots[i], value => slots[i] = typeof value === "function" ? value(slots[i]) : value]; },
    useRef(initial) { const i = cursor++; return slots[i] ?? (slots[i] = { current: initial }); }, useEffect() {},
  };
  const calls = [];
  let next = { reply: "When did you pay for groceries? Nothing has been saved.", record_state: "owner-bound-expense" };
  const api = { SessionExpiredError: class extends Error {}, apiFetch: async (base, url, options) => {
    calls.push({ url, payload: JSON.parse(options.body) });
    return { ok: true, json: async () => next };
  }};
  const hook = load("src/hooks/useChatSession.ts", id => {
    if (id === "react") return react;
    if (id.endsWith("planningService")) return {};
    if (id.endsWith("apiClient")) return api;
    if (id.endsWith("localize")) return { getRuntimeLanguage: () => "en" };
    if (id.endsWith("currency")) return { getCurrencyPreference: () => ({ currency: "AED" }) };
    throw new Error(id);
  }).default;
  const renderHook = () => { cursor = 0; return hook("unused"); };
  let session = renderHook();
  await session.send("I just bought groceries for 120."); session = renderHook();
  assert.equal(session.messages.at(-1).recordState, "owner-bound-expense");
  next = { reply: "Ready to record", proposal: { id: "p", kind: "expense", amount: "120", category: "Groceries",
      description: "groceries", date: "2026-10-18", status: "pending" } };
  await session.send("Today."); session = renderHook();
  const payload = calls[1].payload;
  assert.equal(payload.record_state, "owner-bound-expense");
  assert.equal(payload.messages.length, 3);
  assert.match(payload.messages[0].content, /^I just bought groceries for 120\./);
  assert.match(payload.messages[2].content, /^Today\./);
  assert.equal(session.messages.at(-1).proposal.category, "Groceries");
  assert.equal(session.messages.at(-1).recordState, undefined);
  next = { reply: "Your budget is loaded." };
  await session.send("How is my budget?"); session = renderHook();
  assert.equal(calls.at(-1).payload.record_state, undefined);
  next = { reply: "When did you pay?", record_state: "new-draft" };
  await session.send("Bought food for 20"); session = renderHook();
  session.reset(); session = renderHook();
  next = { reply: "What would you like to do?" };
  await session.send("Today.");
  assert.equal(calls.at(-1).payload.record_state, undefined);
  assert.ok(calls.every(call => call.url === "/ai/chat"));
});


test("income receipt cards show addition and before/after totals; monthly settings show replacement", () => {
  const react = { createElement: (type, props, ...children) => ({ type, props: props || {}, children }) };
  const Card = load("src/components/ai/ProposalCard.tsx", id => {
    if (id === "react") return { __esModule: true, default: react };
    if (id === "react-native") return { ActivityIndicator: "ActivityIndicator", Pressable: "Pressable" };
    if (id.endsWith("LocalizedNative")) return { Text: "Text", View: "View" };
    if (id.endsWith("useAITheme")) return { useAITheme: () => ({ ai: {}, styles: {}, palette: {} }) };
    if (id.endsWith("dashboard")) return { formatAED: value => `AED ${value.toFixed(2)}`, monthName: () => "October" };
    if (id.endsWith("transactions")) return { formatLongDate: value => value };
    return {};
  }).default;
  function text(tree) {
    if (Array.isArray(tree)) return tree.map(text).join(" ");
    return tree && typeof tree === "object" ? text(tree.children) : typeof tree === "string" ? tree : "";
  }
  const common = { id: "income", kind: "income", amount: "2000", year: 2026, month: 10, date: "2026-10-17", status: "pending" };
  const props = { saving: false, disabled: false, onConfirm() {}, onDismiss() {} };
  const addition = text(Card({ ...props, proposal: { ...common, income_operation: "add", income_before: "10000", income_after: "12000" } }));
  assert.match(addition, /Add one-time income/);
  assert.match(addition, /AED 10000.00.*AED 12000.00/);
  assert.match(addition, /other months unchanged/);
  assert.doesNotMatch(addition, /Replaces income/);
  const replacement = text(Card({ ...props, proposal: { ...common, income_operation: "replace" } }));
  assert.match(replacement, /Set monthly income/);
  assert.match(replacement, /Replaces income for this month/);
});

test("income date follow-up sends the same pending-record token and retains the original amount", async () => {
  const slots = []; let cursor = 0;
  const react = { useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = initial;
    return [slots[i], value => slots[i] = typeof value === "function" ? value(slots[i]) : value]; },
    useRef(initial) { const i = cursor++; return slots[i] ?? (slots[i] = { current: initial }); }, useEffect() {} };
  const calls = [];
  let next = { reply: "When did you receive this income?", record_state: "income-owner-bound-draft" };
  const api = { SessionExpiredError: class extends Error {}, apiFetch: async (base, url, options) => {
    calls.push({ url, payload: JSON.parse(options.body) }); return { ok: true, json: async () => next };
  }};
  const hook = load("src/hooks/useChatSession.ts", id => {
    if (id === "react") return react;
    if (id.endsWith("planningService")) return {};
    if (id.endsWith("apiClient")) return api;
    if (id.endsWith("localize")) return { getRuntimeLanguage: () => "en" };
    if (id.endsWith("currency")) return { getCurrencyPreference: () => ({ currency: "AED" }) };
    throw new Error(id);
  }).default;
  const renderHook = () => { cursor = 0; return hook("unused"); };
  let session = renderHook(); await session.send("I earned 2k"); session = renderHook();
  next = { reply: "Confirm to add", proposal: { id: "receipt", kind: "income", income_operation: "add", amount: "2000",
    income_before: "10000", income_after: "12000", date: "2026-10-17", year: 2026, month: 10, status: "pending" } };
  await session.send("Yesterday."); session = renderHook();
  assert.equal(calls[1].payload.record_state, "income-owner-bound-draft");
  assert.equal(calls[1].payload.currency, "AED");
  assert.match(calls[1].payload.messages[0].content, /^I earned 2k/);
  assert.equal(session.messages.at(-1).proposal.income_operation, "add");
  assert.equal(session.messages.at(-1).recordState, undefined);
  assert.ok(calls.every(call => call.url === "/ai/chat"));
});


test("new chat drops prior goal profiles, choices and plan status; affordability has no Accept action", async () => {
  const slots = []; let cursor = 0;
  const react = {
    useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = initial;
      return [slots[i], value => slots[i] = typeof value === "function" ? value(slots[i]) : value]; },
    useRef(initial) { const i = cursor++; return slots[i] ?? (slots[i] = { current: initial }); }, useEffect() {},
  };
  const calls = [];
  let next = { reply: "Draft", goal_planning: true, planning_profile: { goal: "iPhone", target_amount: 5000 },
    plan: { ready: true, budgetGoalSource: true, draftFingerprint: "old", profile: { goal: "iPhone" } } };
  const hook = load("src/hooks/useChatSession.ts", id => {
    if (id === "react") return react;
    if (id.endsWith("planningService")) return {};
    if (id.endsWith("apiClient")) return { SessionExpiredError: class extends Error {}, apiFetch: async (base, url, options) => {
      calls.push(JSON.parse(options.body)); return { ok: true, json: async () => next };
    }};
    if (id.endsWith("localize")) return { getRuntimeLanguage: () => "en" };
    if (id.endsWith("currency")) return { getCurrencyPreference: () => ({ currency: "AED" }) };
    throw new Error(id);
  }).default;
  const renderHook = () => { cursor = 0; return hook("unused"); };
  let session = renderHook();
  await session.send("Save 5000 for an iPhone"); session = renderHook();
  assert.equal(session.messages.at(-1).planningProfile.goal, "iPhone");
  session.reset(); session = renderHook();
  next = { reply: "Saving AED 1,000 monthly leaves AED 2,580 of planned headroom." };
  await session.send("Can I save 1k a month?"); session = renderHook();
  const payload = calls.at(-1);
  assert.equal(payload.messages.length, 1);
  assert.equal(payload.planning_profile, undefined);
  assert.equal(payload.goal_planning, false);
  assert.equal(payload.budget_draft_fingerprint, undefined);
  assert.equal(payload.budget_draft_status, undefined);
  assert.equal(elements(render(session.messages, session), "PlanConfirmationActions").length, 0);
});

test("R4 cancellation updates the original card across rerenders and Yes never confirms", async () => {
  const slots = []; let cursor = 0;
  const react = {
    useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = initial;
      return [slots[i], value => slots[i] = typeof value === "function" ? value(slots[i]) : value]; },
    useRef(initial) { const i = cursor++; return slots[i] ?? (slots[i] = { current: initial }); }, useEffect() {},
  };
  const calls = [];
  const replies = [
    { reply: "Ready to record", proposal: { id: "lunch", kind: "expense", amount: 50, category: "Food", date: "2026-10-18", status: "pending" } },
    { reply: "Okay, I've canceled that expense. Nothing was saved.", proposal_updates: [{ id: "lunch", status: "dismissed" }] },
    { reply: "That record is canceled. Nothing was saved." },
  ];
  const hook = load("src/hooks/useChatSession.ts", id => {
    if (id === "react") return react;
    if (id.endsWith("planningService")) return {};
    if (id.endsWith("apiClient")) return { SessionExpiredError: class extends Error {}, apiFetch: async (base, url, options) => {
      calls.push({ url, payload: JSON.parse(options.body) }); return { ok: true, json: async () => replies.shift() };
    }};
    if (id.endsWith("localize")) return { getRuntimeLanguage: () => "en" };
    if (id.endsWith("currency")) return { getCurrencyPreference: () => ({ currency: "AED" }) };
    throw new Error(id);
  }).default;
  const renderHook = () => { cursor = 0; return hook("test"); };
  let session = renderHook();
  await session.send("I spent 50 on lunch today."); session = renderHook();
  assert.equal(session.messages[1].proposal.status, "pending");
  await session.send("Actually, I don't want to record this expense."); session = renderHook();
  assert.equal(calls[1].payload.active_proposal_id, "lunch");
  assert.equal(session.messages[1].proposal.status, "dismissed");
  // A fresh screen render gets the app-owned canceled status.
  assert.equal(elements(render(session.messages, session), "ProposalCard")[0].props.proposal.status, "dismissed");
  await session.send("Yes."); session = renderHook();
  assert.equal(session.messages[1].proposal.status, "dismissed");
  assert.equal(session.messages.at(-1).proposal, undefined);
  assert.ok(calls.every(call => call.url === "/ai/chat"));
});

test("Dismiss status survives navigation while its API request is pending", async () => {
  let messages = [{ role: "assistant", content: "Pending", proposal: { id: "p", kind: "expense", amount: 50, status: "pending" } }];
  const effects = []; let complete;
  const tree = render(messages, { onMessagesChange(update) { messages = typeof update === "function" ? update(messages) : update; } },
    { apiFetch: async () => new Promise(resolve => complete = resolve) }, effects);
  const dismissing = elements(tree, "ProposalCard")[0].props.onDismiss();
  effects.filter(effect => typeof effect === "function").forEach(cleanup => cleanup());
  complete({ ok: true, json: async () => ({ status: "dismissed" }) });
  await dismissing;
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(messages[0].proposal.status, "dismissed");
  assert.equal(elements(render(messages), "ProposalCard")[0].props.proposal.status, "dismissed");
});

test("canceled proposal cards expose no Confirm or Dismiss controls", () => {
  const react = { createElement: (type, props, ...children) => ({ type, props: props || {}, children }) };
  const Card = load("src/components/ai/ProposalCard.tsx", id => {
    if (id === "react") return { __esModule: true, default: react };
    if (id === "react-native") return { Pressable: "Pressable", ActivityIndicator: "ActivityIndicator" };
    if (id.endsWith("LocalizedNative")) return { Text: "Text", View: "View" };
    if (id.endsWith("useAITheme")) return { useAITheme: () => ({ ai: {}, styles: {}, palette: {} }) };
    if (id.endsWith("dashboard")) return { formatAED: n => "AED " + n, monthName: () => "October" };
    if (id.endsWith("transactions")) return { formatLongDate: value => value };
    return {};
  }).default;
  for (const kind of ["expense", "income"]) for (const status of ["dismissed", "expired", "saved"]) {
    const tree = Card({ proposal: { id: "p", kind, amount: 50, status }, saving: false, disabled: false });
    assert.equal(elements(tree, "Pressable").length, 0);
  }
});


for (const kind of ["expense", "income"]) {
  test("C1 " + kind + " Yes retains one pending card; only button confirmation calls the save endpoint", async () => {
    const slots = []; let cursor = 0;
    const react = {
      useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = initial;
        return [slots[i], value => slots[i] = typeof value === "function" ? value(slots[i]) : value]; },
      useRef(initial) { const i = cursor++; return slots[i] ?? (slots[i] = { current: initial }); }, useEffect() {},
    };
    const proposal = { id: "c1", kind, amount: "50", category: kind === "expense" ? "Food" : undefined,
      date: "2026-10-18", year: 2026, month: 10, status: "pending" };
    const replies = [{ reply: "Ready to record. Confirm to save.", proposal },
      { reply: "Your proposal is still pending. Use Confirm or Dismiss.", proposal_updates: [{ id: "c1", status: "pending" }] }];
    const calls = [];
    const hook = load("src/hooks/useChatSession.ts", id => {
      if (id === "react") return react;
      if (id.endsWith("planningService")) return {};
      if (id.endsWith("apiClient")) return { SessionExpiredError: class extends Error {}, apiFetch: async (base, url, options) => {
        calls.push({ url, payload: JSON.parse(options.body) }); return { ok: true, json: async () => replies.shift() };
      }};
      if (id.endsWith("localize")) return { getRuntimeLanguage: () => "en" };
      if (id.endsWith("currency")) return { getCurrencyPreference: () => ({ currency: "AED" }) };
      throw new Error(id);
    }).default;
    const renderHook = () => { cursor = 0; return hook("test"); };
    let session = renderHook();
    await session.send(kind === "expense" ? "I spent 50 on lunch today." : "I earned 50 today."); session = renderHook();
    await session.send("Yes."); session = renderHook();
    assert.equal(calls[1].payload.active_proposal_id, "c1");
    assert.equal(calls[1].payload.record_state, undefined);
    assert.match(calls[1].payload.messages[1].content, /Record status: pending/);
    assert.ok(calls.every(call => call.url === "/ai/chat"));
    const cards = elements(render(session.messages, session), "ProposalCard");
    assert.equal(cards.length, 1);
    assert.equal(cards[0].props.proposal.status, "pending");
    assert.equal(cards[0].props.proposal.amount, "50");
    assert.equal(cards[0].props.proposal.date, "2026-10-18");
    const buttonCalls = [];
    const tree = render(session.messages, session, { apiFetch: async (base, url) => {
      buttonCalls.push(url); return { ok: true, json: async () => ({ status: "saved" }) };
    }});
    elements(tree, "ProposalCard")[0].props.onConfirm();
    await new Promise(resolve => setImmediate(resolve));
    session = renderHook();
    assert.deepEqual(buttonCalls, ["/ai/proposals/c1/confirm"]);
    assert.equal(session.messages[1].proposal.status, "saved");
  });
}

test("C2 retains dismissed proposal IDs across topic switches and clears them for a new chat", async () => {
  const slots = []; let cursor = 0;
  const react = {
    useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = initial;
      return [slots[i], value => slots[i] = typeof value === "function" ? value(slots[i]) : value]; },
    useRef(initial) { const i = cursor++; return slots[i] ?? (slots[i] = { current: initial }); }, useEffect() {},
  };
  const calls = [];
  const replies = [
    { reply: "Confirm to save.", proposal: { id: "dismissed-lunch", kind: "expense", amount: 50, category: "Food", status: "pending" } },
    { reply: "Your budget is unchanged." },
    { reply: "That AED 50 Food expense was dismissed.", proposal_updates: [{ id: "dismissed-lunch", status: "dismissed" }] },
    { reply: "There is no matching proposal in this chat." },
  ];
  const hook = load("src/hooks/useChatSession.ts", id => {
    if (id === "react") return react;
    if (id.endsWith("planningService")) return {};
    if (id.endsWith("apiClient")) return { SessionExpiredError: class extends Error {}, apiFetch: async (base, url, options) => {
      calls.push({ url, payload: JSON.parse(options.body) }); return { ok: true, json: async () => replies.shift() };
    }};
    if (id.endsWith("localize")) return { getRuntimeLanguage: () => "en" };
    if (id.endsWith("currency")) return { getCurrencyPreference: () => ({ currency: "AED" }) };
    throw new Error(id);
  }).default;
  const renderHook = () => { cursor = 0; return hook("test"); };
  let session = renderHook();
  await session.send("I spent 50 on lunch today."); session = renderHook();
  const tree = render(session.messages, session, { apiFetch: async () => ({ ok: true, json: async () => ({ status: "dismissed" }) }) });
  elements(tree, "ProposalCard")[0].props.onDismiss();
  await new Promise(resolve => setImmediate(resolve)); session = renderHook();
  assert.equal(session.messages[1].proposal.status, "dismissed");
  await session.send("How is my budget?"); session = renderHook();
  await session.send("Can you confirm that expense now?"); session = renderHook();
  assert.deepEqual(Array.from(calls[2].payload.proposal_ids), ["dismissed-lunch"]);
  assert.equal(session.messages[1].proposal.status, "dismissed");
  assert.equal(session.messages.at(-1).proposal, undefined);
  session.reset(); session = renderHook();
  await session.send("confirm it"); session = renderHook();
  assert.equal(calls[3].payload.proposal_ids.length, 0);
  assert.equal(calls[3].payload.active_proposal_id, undefined);
  assert.ok(calls.every(call => call.url === "/ai/chat"));
});


for (const fails of [false, true]) {
  test("C5 rejection " + (fails ? "failure keeps the plan pending" : "persists across topic switches and blocks local acceptance"), async () => {
    const slots = []; let cursor = 0;
    const react = {
      useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = initial;
        return [slots[i], value => slots[i] = typeof value === "function" ? value(slots[i]) : value]; },
      useRef(initial) { const i = cursor++; return slots[i] ?? (slots[i] = { current: initial }); }, useEffect() {},
    };
    const calls = []; let finish;
    const api = { SessionExpiredError: class extends Error {}, apiFetch: async (base, url, options) => {
      calls.push({ url, payload: options.body ? JSON.parse(options.body) : undefined });
      if (url.endsWith("/reject")) return new Promise(resolve => { finish = resolve; });
      return { ok: true, json: async () => ({ reply: "Your vacation savings plan was rejected. Create a new plan.",
        plan_updates: [{ review_id: "c5", status: "rejected" }] }) };
    }};
    const planning = load("src/services/planningService.ts", () => api);
    const hook = load("src/hooks/useChatSession.ts", id => {
      if (id === "react") return react;
      if (id.endsWith("planningService")) return planning;
      if (id.endsWith("apiClient")) return api;
      if (id.endsWith("localize")) return { getRuntimeLanguage: () => "en" };
      if (id.endsWith("currency")) return { getCurrencyPreference: () => ({ currency: "AED" }) };
      throw new Error(id);
    }).default;
    const renderHook = () => { cursor = 0; return hook("test"); };
    let session = renderHook();
    const plan = { ready: true, budgetGoalSource: true, reviewId: "c5", reviewStatus: "pending", title: "Vacation", targetAmount: 3000, monthlyContribution: 300, profile: {} };
    session.onMessagesChange([{ role: "user", content: "Save 3000 for vacation" }, { role: "assistant", content: "Review your plan.", plan }]);
    session = renderHook();
    elements(render(session.messages, session), "PlanConfirmationActions")[0].props.onDecline();
    session = renderHook();
    assert.equal(calls[0].url, "/planning/reviews/c5/reject");
    assert.ok(!session.messages[1].planDeclined);
    const pendingProps = elements(render(session.messages, session), "PlanConfirmationActions")[0].props;
    assert.equal(pendingProps.saving, false);
    assert.equal(pendingProps.busy, true);
    finish({ ok: !fails, json: async () => fails ? { detail: "Please retry rejection" } : { status: "rejected" } });
    await new Promise(resolve => setImmediate(resolve));
    session = renderHook();
    if (fails) {
      assert.ok(!session.messages[1].planDeclined);
      assert.equal(session.messages[1].plan.reviewStatus, "pending");
      assert.equal(session.error.title, "Could not reject plan");
      return;
    }
    assert.equal(session.messages[1].planDeclined, true);
    assert.equal(session.messages[1].plan.reviewStatus, "rejected");
    assert.equal(elements(render(session.messages, session), "PlanConfirmationActions")[0].props.dismissed, true);
    await session.saveFinancialPlan(session.messages[1].plan, 1);
    assert.equal(calls.length, 1);
    await session.send("How is my budget?"); session = renderHook();
    await session.send("Actually can you accept that vacation savings plan now?"); session = renderHook();
    assert.deepEqual(Array.from(calls.at(-1).payload.plan_review_ids), ["c5"]);
    assert.equal(session.messages[1].planDeclined, true);
    assert.equal(session.messages.at(-1).plan, undefined);
    assert.ok(calls.slice(1).every(call => call.url === "/ai/chat"));
    session.reset(); session = renderHook();
    await session.send("accept that plan"); session = renderHook();
    assert.equal(calls.at(-1).payload.plan_review_ids.length, 0);
  });
}

test("C7 keeps two cards and updates only the selected proposal across rerenders and New Chat", async () => {
  const slots = []; let cursor = 0;
  const react = {
    useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = initial;
      return [slots[i], value => slots[i] = typeof value === "function" ? value(slots[i]) : value]; },
    useRef(initial) { const i = cursor++; return slots[i] ?? (slots[i] = { current: initial }); }, useEffect() {},
  };
  const calls = [];
  const groceries = { id: "c7-groceries", kind: "expense", amount: "40", category: "Groceries", date: "2026-10-18", status: "pending" };
  const transport = { ...groceries, id: "c7-transport", amount: "25", category: "Transport" };
  const replies = [
    { reply: "Confirm groceries.", proposal: groceries },
    { reply: "Confirm transport.", proposal: transport },
    { reply: "Use groceries Confirm.", proposal_updates: [{ id: groceries.id, status: "pending" }] },
    { reply: "Canceled groceries.", proposal_updates: [{ id: groceries.id, status: "dismissed" }] },
    { reply: "Which proposal?" },
  ];
  const hook = load("src/hooks/useChatSession.ts", id => {
    if (id === "react") return react;
    if (id.endsWith("planningService")) return {};
    if (id.endsWith("apiClient")) return { SessionExpiredError: class extends Error {}, apiFetch: async (base, url, options) => {
      calls.push({ url, payload: JSON.parse(options.body) }); return { ok: true, json: async () => replies.shift() };
    }};
    if (id.endsWith("localize")) return { getRuntimeLanguage: () => "en" };
    if (id.endsWith("currency")) return { getCurrencyPreference: () => ({ currency: "AED" }) };
    throw new Error(id);
  }).default;
  const renderHook = () => { cursor = 0; return hook("test"); };
  let session = renderHook();
  for (const text of ["I spent 40 AED on groceries today.", "I also spent 25 AED on transport today."]) {
    await session.send(text); session = renderHook();
  }
  let cards = elements(render(session.messages, session), "ProposalCard");
  assert.deepEqual(cards.map(card => card.props.proposal.id), [groceries.id, transport.id]);
  assert.equal(session.messages[1].proposal.amount, "40");
  assert.equal(session.messages[3].proposal.amount, "25");
  await session.send("Can you confirm the 40 AED groceries expense?"); session = renderHook();
  assert.deepEqual(Array.from(calls[2].payload.proposal_ids), [groceries.id, transport.id]);
  assert.equal(calls[2].payload.active_proposal_id, transport.id);
  await session.send("Actually, cancel the 40 AED groceries expense."); session = renderHook();
  assert.equal(session.messages[1].proposal.status, "dismissed");
  assert.equal(session.messages[3].proposal.status, "pending");
  const buttons = [];
  cards = elements(render(session.messages, session, { apiFetch: async (base, url) => {
    buttons.push(url); return { ok: true, json: async () => ({ status: "saved" }) };
  }}), "ProposalCard");
  cards[1].props.onConfirm();
  await new Promise(resolve => setImmediate(resolve)); session = renderHook();
  assert.deepEqual(buttons, ["/ai/proposals/c7-transport/confirm"]);
  assert.equal(session.messages[1].proposal.status, "dismissed");
  assert.equal(session.messages[3].proposal.status, "saved");
  assert.ok(calls.every(call => call.url === "/ai/chat"));
  session.reset(); session = renderHook();
  await session.send("Confirm it.");
  assert.equal(calls.at(-1).payload.proposal_ids.length, 0);
  assert.equal(calls.at(-1).payload.active_proposal_id, undefined);
});

test("C7 each card's Dismiss and Confirm controls use its own ID", async () => {
  const proposals = [
    { id: "groceries-40", kind: "expense", amount: 40, category: "Groceries", status: "pending" },
    { id: "transport-25", kind: "expense", amount: 25, category: "Transport", status: "pending" },
  ];
  let messages = proposals.map(proposal => ({ role: "assistant", content: "Review", proposal }));
  const onMessagesChange = update => { messages = typeof update === "function" ? update(messages) : update; };
  const calls = [];
  const tree = render(messages, { onMessagesChange }, { apiFetch: async (base, url) => {
    calls.push(url); return { ok: true, json: async () => ({ status: url.endsWith("/dismiss") ? "dismissed" : "saved" }) };
  }});
  const cards = elements(tree, "ProposalCard");
  cards[0].props.onDismiss(); await new Promise(resolve => setImmediate(resolve));
  assert.equal(messages[0].proposal.status, "dismissed");
  assert.equal(messages[1].proposal.status, "pending");
  cards[1].props.onConfirm(); await new Promise(resolve => setImmediate(resolve));
  assert.equal(messages[1].proposal.status, "saved");
  assert.deepEqual(calls, ["/ai/proposals/groceries-40/dismiss", "/ai/proposals/transport-25/confirm"]);
});
