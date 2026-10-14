import React, { useRef, useState } from "react";
import { ActivityIndicator, Pressable, StatusBar } from "react-native";
import { Text, TextInput, View } from "../preferences/LocalizedNative";
import { SafeAreaView } from "react-native-safe-area-context";
import { Check, ChevronRight, Globe, Moon, SlidersHorizontal, Sun, UserRound, Wallet, LogOut } from "lucide-react-native";
import BackButton from "../components/BackButton";
import { navigationStyles } from "../styles/NavigationStyles";
import KeyboardFormScrollView from "../components/KeyboardFormScrollView";
import { useDashboardTheme } from "../components/dashboard/useDashboardTheme";
import { createSettingsStyles } from "../styles/SettingsStyles";
import type { AuthUser } from "../services/authService";
import PersonalDetailsScreen from "./PersonalDetailsScreen";
import { useAppTheme } from "../theme/ThemeContext";
import { usePreferences } from "../preferences/PreferencesContext";
import { LANGUAGES, Language } from "../preferences/languages";
import CurrencyNotice from "../components/CurrencyNotice";
import { localize } from "../preferences/localize";

type Props = { apiBaseUrl: string; onBack: () => void; onUpdated: (user: AuthUser) => void; onPasswordChanged: () => Promise<void>; onLogout: () => Promise<void> };
type Section = "menu" | "personal" | "language" | "currency" | "preferences";

export default function SettingsScreen(props: Props) {
  const { palette, mode } = useDashboardTheme();
  const { setTheme } = useAppTheme();
  const { language, setLanguage, currency, setCurrency, ready, t } = usePreferences();
  const s = createSettingsStyles(palette);
  const [section, setSection] = useState<Section>("menu");
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const logoutLock = useRef(false);
  const signOut = async () => {
    if (busy || logoutLock.current) return;
    logoutLock.current = true; setBusy(true); setError("");
    try { await props.onLogout(); }
    catch { setError("Could not log out. Please try again."); }
    finally { logoutLock.current = false; setBusy(false); }
  };
  const select = async (operation: () => Promise<void>) => {
    if (busy) return;
    setBusy(true); setError("");
    try { await operation(); } catch { setError(section === "currency" ? "Could not update currency. Check your connection and try again." : "Could not save this preference. Please try again."); }
    finally { setBusy(false); }
  };
  const back = () => { if (busy) return; setError(""); if (section === "menu") props.onBack(); else setSection("menu"); };
  if (section === "personal") return <PersonalDetailsScreen {...props} onBack={() => setSection("menu")} />;
  const options = [
    { id: "personal" as const, icon: UserRound, title: t("personal"), description: "Name, email, phone and password" },
    { id: "language" as const, icon: Globe, title: t("language"), description: LANGUAGES.find(item => item.code === language)?.native ?? "English" },
    { id: "currency" as const, icon: Wallet, title: t("currency"), description: currency === "CNY" ? "CNY · Chinese yuan" : "AED · UAE Dirham" },
    { id: "preferences" as const, icon: SlidersHorizontal, title: t("preferences"), description: t(mode === "dark" ? "dark" : "light") },
  ];
  const languageRows = LANGUAGES.filter(item => `${item.name} ${item.native}`.toLowerCase().includes(search.trim().toLowerCase()));
  const chooseLanguage = (code: Language) => { void select(() => setLanguage(code)); };

  return <SafeAreaView style={s.screen} edges={["top", "left", "right"]}>
    <StatusBar barStyle={mode === "dark" ? "light-content" : "dark-content"} />
    <KeyboardFormScrollView contentContainerStyle={s.content}>
      <View style={[s.header, navigationStyles.header]}>
        <BackButton disabled={busy} onPress={back} label={t("back")} />
        <View style={s.headingText}><Text style={s.title}>{t(section === "menu" ? "settings" : section)}</Text>{section === "menu" && <Text style={s.subtitle}>Make PocketPilot feel like yours</Text>}</View>
      </View>
      {!!error && <Text style={s.error} accessibilityRole="alert">{error}</Text>}
      {section === "menu" && <View style={s.menu}>
        {options.map((item, i) => <Pressable key={item.id} onPress={() => { setError(""); setSection(item.id); }} accessibilityRole="button" accessibilityLabel={item.title}
          style={({ pressed }) => [s.menuRow, i < options.length - 1 && s.rowBorder, pressed && s.selectedOption]}>
          <View style={s.menuIcon}><item.icon size={21} color={palette.accent} /></View>
          <View style={s.menuText}><Text style={s.rowTitle}>{item.title}</Text><Text localize={item.id !== "currency"} style={s.subtitle}>{item.id === "currency" ? localize(item.description, language) : item.description}</Text></View>
          <ChevronRight size={20} color={palette.textMuted} />
        </Pressable>)}
      </View>}
      {section === "menu" && <Pressable accessibilityRole="button" accessibilityLabel="Log out" disabled={busy} onPress={() => { void signOut(); }} style={({ pressed }) => [s.logoutButton, (pressed || busy) && s.disabled]}>
        <LogOut size={20} color={palette.danger} /><Text style={s.logoutText}>{busy ? "Logging out…" : "Log out"}</Text>
      </Pressable>}
      {section === "language" && <View style={s.options}>
        <Text style={s.subtitle}>Choose a language. Mandarin and Arabic translate the app interface. Other languages currently translate menus and navigation.</Text>
        <TextInput style={s.input} value={search} onChangeText={setSearch} placeholder="Search languages" placeholderTextColor={palette.textMuted} accessibilityLabel="Search languages" autoCorrect={false} />
        {!ready ? <ActivityIndicator color={palette.accent} /> : languageRows.map(item => <Pressable key={item.code} disabled={busy} onPress={() => chooseLanguage(item.code)} accessibilityRole="radio" accessibilityState={{ checked: language === item.code, disabled: busy }}
          style={[s.optionRow, language === item.code && s.selectedOption, busy && s.disabled]}>
          <View style={s.menuText}><Text style={s.rowTitle}>{item.native}</Text><Text style={s.subtitle}>{item.name}</Text></View>
          {language === item.code && <Check size={21} color={palette.accent} />}
        </Pressable>)}
        {!languageRows.length && <Text style={s.subtitle}>No matching languages.</Text>}
      </View>}
      {section === "currency" && <View style={s.options}>
        {([{ code: "AED", name: "UAE Dirham · د.إ" }, { code: "CNY", name: "Chinese yuan · 人民币 ¥" }] as const).map(item => <Pressable key={item.code} disabled={busy || !ready} onPress={() => { void select(() => setCurrency(item.code)); }} accessibilityRole="radio" accessibilityLabel={item.code} accessibilityState={{ checked: currency === item.code, disabled: busy || !ready }} style={[s.optionRow, currency === item.code && s.selectedOption, busy && s.disabled]}>
          <View style={s.menuIcon}><Wallet size={22} color={palette.accent} /></View><View style={s.menuText}><Text localize={false} style={s.rowTitle}>{item.code}</Text><Text localize={false} style={s.subtitle}>{localize(item.name, language)}</Text></View>{currency === item.code && <Check size={21} color={palette.accent} />}
        </Pressable>)}
        {busy && <ActivityIndicator color={palette.accent} />}
        <Text style={s.subtitle}>Your history, income, budgets and plans are shown in the selected currency. New amounts are entered in that currency. Original records are preserved.</Text>
        <Text style={s.subtitle}>Yuan amounts are approximate conversions using the displayed reference rate, including older records. They are not historical exchange rates.</Text>
        <CurrencyNotice always />
        {currency === "CNY" && <Pressable disabled={busy} style={s.optionRow} onPress={() => { void select(() => setCurrency("CNY")); }} accessibilityRole="button"><Text style={s.rowTitle}>Refresh exchange rate</Text></Pressable>}
      </View>}
      {section === "preferences" && <View style={s.options}>
        <Text style={s.sectionTitle}>Appearance</Text><Text style={s.subtitle}>Choose how PocketPilot looks. Your choice is remembered on this device.</Text>
        {(["light", "dark"] as const).map(option => <Pressable key={option} disabled={busy} onPress={() => { void select(() => setTheme(option)); }} accessibilityRole="radio" accessibilityState={{ checked: mode === option, disabled: busy }}
          style={[s.optionRow, mode === option && s.selectedOption, busy && s.disabled]}>
          <View style={s.menuIcon}>{option === "light" ? <Sun size={22} color={palette.accent} /> : <Moon size={22} color={palette.accent} />}</View>
          <View style={s.menuText}><Text style={s.rowTitle}>{t(option)}</Text><Text style={s.subtitle}>{option === "light" ? "Bright surfaces and crisp text" : "Charcoal surfaces and mint accents"}</Text></View>
          <View style={[s.radio, mode === option && s.selectedRadio]}>{mode === option && <View style={s.radioDot} />}</View>
        </Pressable>)}
      </View>}
    </KeyboardFormScrollView>
  </SafeAreaView>;
}
