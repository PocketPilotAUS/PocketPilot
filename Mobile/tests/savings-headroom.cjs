const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

function summary(plan) {
  const react = { Fragment: "Fragment", createElement(type, props, ...children) {
    return typeof type === "function" ? type({ ...props, children }) : { type, props: props || {}, children };
  }};
  const source = fs.readFileSync(path.join(__dirname, "../src/components/ai/PlanConfirmationActions.tsx"), "utf8");
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, esModuleInterop: true } }).outputText;
  const module = { exports: {} };
  const mock = id => {
    if (id === "react") return { __esModule: true, default: react };
    if (id === "react-native") return { Pressable: "Pressable" };
    if (id.endsWith("LocalizedNative")) return { Text: "Text", View: "View" };
    if (id.endsWith("useDashboardTheme")) return { useDashboardTheme: () => ({ styles: {} }) };
    if (id.endsWith("useAITheme")) return { useAITheme: () => ({ palette: {} }) };
    if (id.endsWith("PlanningStyles")) return { createPlanningStyles: () => ({}) };
    if (id.endsWith("dashboard")) return { formatAED: value => "AED " + value.toFixed(2) };
    if (id.endsWith("planningDate")) return { formatPlanningDate: value => value };
    throw new Error(id);
  };
  vm.runInNewContext("(function(require,module,exports){" + code + "\n})", {})(mock, module, module.exports);
  return module.exports.default({ plan, dismissed: false, busy: false, onConfirm() {}, onEdit() {}, onDecline() {} });
}

function flatten(tree) {
  if (Array.isArray(tree)) return tree.flatMap(flatten);
  return tree && typeof tree === "object" ? [tree, ...flatten(tree.children)] : [];
}
function metrics(tree) {
  return new Map(flatten(tree).filter(node => node.type === "View" && node.children.length === 2 && node.children.every(child => child?.type === "Text"))
    .map(node => node.children.map(child => child.children.join(""))));
}
const plan = { ready: true, budgetGoalSource: true, title: "Laptop", kind: "savings", profile: {},
  targetAmount: 5000, monthlyContribution: 600, months: 9, deadline: "2027-06-30",
  availableBefore: 3013.86, availableAfter: 3013.86, remainingAfterSavings: 2413.86 };

test("C4 labels server capacity before savings and remaining after the AED 600 contribution", () => {
  const tree = summary(plan);
  const values = metrics(tree);
  assert.equal(values.get("Available before monthly savings"), "AED 3013.86");
  assert.equal(values.get("Remaining after monthly savings"), "AED 2413.86");
  assert.equal(values.get("Monthly saving"), "AED 600.00");
  assert.equal(values.get("Months"), "9");
  assert.ok(!JSON.stringify(tree).includes("Left after goal"));
});
test("savings card displays server fields without recalculating or clamping them", () => {
  for (const remaining of [0, -50, 123.45]) {
    assert.equal(metrics(summary({ ...plan, remainingAfterSavings: remaining })).get("Remaining after monthly savings"), "AED " + remaining.toFixed(2));
  }
});
test("older local cards do not relabel pre-contribution capacity as remaining", () => {
  const values = metrics(summary({ ...plan, remainingAfterSavings: undefined }));
  assert.equal(values.get("Available before monthly savings"), "AED 3013.86");
  assert.ok(!values.has("Remaining after monthly savings"));
});
test("accepted savings cards retain both verified headroom figures", () => {
  const values = metrics(summary({ ...plan, id: "saved-goal" }));
  assert.equal(values.get("Remaining after monthly savings"), "AED 2413.86");
});
test("debt card keeps its verified extra-repayment calculation", () => {
  const values = metrics(summary({ ...plan, debtGoalSource: true, leftAfterGoal: 900 }));
  assert.equal(values.get("Remaining after extra repayment"), "AED 900.00");
  assert.ok(!values.has("Remaining after monthly savings"));
});
