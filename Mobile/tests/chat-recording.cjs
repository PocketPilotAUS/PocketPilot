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

function render(messages, sessionOverrides = {}) {
  const react = {
    createElement: (type, props, ...children) => ({ type, props: props || {}, children }),
    useState: value => [value, () => {}],
    useRef: value => ({ current: value }),
    useEffect: () => {},
    Fragment: "Fragment",
  };
  const screen = load("src/screens/AIChatScreen.tsx", id => {
    if (id === "react") return { __esModule: true, default: react, ...react };
    if (id === "react-native") return { Platform: { OS: "android" }, ...Object.fromEntries(
      ["KeyboardAvoidingView", "Modal", "Pressable", "ScrollView", "StatusBar"].map(name => [name, name])) };
    if (id.endsWith("useAITheme")) return { useAITheme: () => ({ ai: {}, styles: {}, palette: {}, mode: "dark" }) };
    if (id.endsWith("apiClient")) return { SessionExpiredError: class extends Error {} };
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
    budgetFingerprint: "fingerprint", draftFingerprint: "draft", confirmationKey: "key" };
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
  assert.equal(calls[1].url, "/planning/budget-plans");
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
  assert.equal(calls[2].url, "/planning/budget-plans");
  complete({ ok: true, json: async () => ({ ...plan, id: "persisted-plan" }) });
  await retry;
  session = renderHook();
  assert.equal(session.savingPlan, null);
  const savedProps = elements(render(session.messages, session), "PlanConfirmationActions")[0].props;
  assert.ok(planLabels(savedProps).some(v => v.startsWith("Plan saved")));
});
