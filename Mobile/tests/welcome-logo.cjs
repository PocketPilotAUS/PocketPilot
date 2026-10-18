const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

function load(relative, mock) {
  const filename = path.join(__dirname, "..", relative);
  const code = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, esModuleInterop: true },
  }).outputText;
  const module = { exports: {} };
  vm.runInNewContext("(function(require,module,exports){" + code + "\n})", {})(mock, module, module.exports);
  return module.exports;
}
function nodes(tree) {
  if (Array.isArray(tree)) return tree.flatMap(nodes);
  return tree && typeof tree === "object" ? [tree, ...nodes(tree.children)] : [];
}
for (const [width, height] of [[390, 844], [280, 500], [844, 390]]) {
  test("welcome logo overrides intrinsic PNG size and fits " + width + "x" + height, () => {
    const createWelcomeStyles = load("src/styles/WelcomeStyles.ts", id => {
      if (id === "react-native") return { StyleSheet: { create: value => value } };
      if (id.endsWith("LoginStyles")) return { createLoginStyles: () => ({ container: { flex: 1 } }) };
      throw new Error(id);
    }).createWelcomeStyles;
    const react = { createElement: (type, props, ...children) => ({ type, props: props || {}, children }),
      useRef: current => ({ current }), useEffect() {} };
    const animated = { Value: class { constructor(value) { this.value = value; } }, View: "Animated.View" };
    const Component = load("src/components/AnimatedWelcome.tsx", id => {
      if (id === "react") return { __esModule: true, default: react, ...react };
      if (id === "react-native") return { Animated: animated, Image: "Image", Pressable: "Pressable",
        ScrollView: "ScrollView", useWindowDimensions: () => ({ width, height }) };
      if (id.endsWith("LocalizedNative")) return { View: "View", Text: "Text" };
      if (id.endsWith("useDashboardTheme")) return { useDashboardTheme: () => ({ palette: {}, styles: {} }) };
      if (id.endsWith("WelcomeStyles")) return { createWelcomeStyles };
      if (id.endsWith(".png")) {
        assert.equal(id, "../../assets/pocketpilot-logo.png");
        // Resolve the real static require path relative to the component.
        const png = fs.readFileSync(path.resolve(__dirname, "../src/components", id));
        assert.equal(png.subarray(1, 4).toString(), "PNG");
        return { width: png.readUInt32BE(16), height: png.readUInt32BE(20) };
      }
      throw new Error(id);
    }).default;
    let started = false;
    const tree = Component({ onGetStarted: () => { started = true; } });
    const all = nodes(tree);
    const image = all.find(node => node.type === "Image");
    assert.equal(image.props.source.width, image.props.source.height);
    assert.equal(image.props.resizeMode, "contain");
    // React Native merges intrinsic source dimensions before the provided style.
    const measured = { ...image.props.source, ...image.props.style };
    assert.equal(measured.width, measured.height);
    assert.ok(measured.width > 0 && measured.width <= Math.min(176, width - 36));
    assert.ok(measured.height <= height * 0.32);
    assert.equal(measured.width, Math.min(220, width - 36, height * 0.32) * 0.8);
    const parent = all.find(node => node.type === "Animated.View");
    assert.equal(parent.props.style.width, measured.width);
    assert.equal(parent.props.style.height, measured.height);
    assert.equal(parent.props.style.flexShrink, 0);
    assert.notEqual(parent.props.style.overflow, "hidden");
    assert.ok(all.some(node => node.type === "ScrollView"));
    assert.ok(all.some(node => node.type === "Text" && node.children.includes("PocketPilot")));
    const text = all.filter(node => node.type === "Text").flatMap(node => node.children).join(" ");
    assert.ok(text.includes("Your personal finance companion"));
    assert.ok(text.includes("Get Started"));
    assert.ok(!text.includes("Take control of your spending"));
    const button = all.find(node => node.type === "Pressable");
    const buttonContainer = all.find(node => node.children.includes(button));
    assert.equal(buttonContainer.props.style.width, "70%");
    assert.equal(buttonContainer.props.style.alignSelf, "center");
    const buttonStyle = Object.assign({}, ...button.props.style({ pressed: false }).filter(Boolean));
    assert.ok(buttonStyle.minHeight >= 48);
    assert.equal(button.props.accessibilityRole, "button");
    button.props.onPress();
    assert.equal(started, true);
  });
}
