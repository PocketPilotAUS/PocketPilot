import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable, StatusBar } from "react-native";
import { Alert, Text, TextInput, View } from "../preferences/LocalizedNative";
import { SafeAreaView } from "react-native-safe-area-context";
import { ArrowLeft, Eye, EyeOff } from "lucide-react-native";
import KeyboardFormScrollView from "../components/KeyboardFormScrollView";
import { useDashboardTheme } from "../components/dashboard/useDashboardTheme";
import { createSettingsStyles } from "../styles/SettingsStyles";
import { AuthUser, PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH } from "../services/authService";
import { changeAccountPassword, getAccount, updateAccount } from "../services/settingsService";
import { SessionExpiredError } from "../services/apiClient";
import { usePreferences } from "../preferences/PreferencesContext";

type Props = { apiBaseUrl: string; onBack: () => void; onUpdated: (user: AuthUser) => void; onPasswordChanged: () => Promise<void> };

export default function PersonalDetailsScreen({ apiBaseUrl, onBack, onUpdated, onPasswordChanged }: Props) {
  const { t } = usePreferences();
  const { palette, mode } = useDashboardTheme();
  const s = createSettingsStyles(palette);
  const [account, setAccount] = useState<AuthUser | null>(null);
  const [name, setName] = useState(""); const [email, setEmail] = useState(""); const [phone, setPhone] = useState("");
  const [emailPassword, setEmailPassword] = useState("");
  const [currentPassword, setCurrentPassword] = useState(""); const [newPassword, setNewPassword] = useState(""); const [confirmPassword, setConfirmPassword] = useState("");
  const [visible, setVisible] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true); const [busy, setBusy] = useState(false); const [retry, setRetry] = useState(0);
  const [profileError, setProfileError] = useState(""); const [passwordError, setPasswordError] = useState(""); const [success, setSuccess] = useState("");
  const mounted = useRef(true); const saving = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    let active = true; setLoading(true); setProfileError("");
    getAccount(apiBaseUrl).then(user => { if (active) { setAccount(user); setName(user.name); setEmail(user.email); setPhone(user.phone ?? ""); } })
      .catch(err => { if (active && !(err instanceof SessionExpiredError)) setProfileError("Could not load your account. Check the backend connection and try again."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiBaseUrl, retry]);
  const emailChanged = !!account && email.trim().toLowerCase() !== account.email;
  const dirty = !!account && (name.trim() !== account.name || emailChanged || phone.trim() !== (account.phone ?? "") || !!emailPassword || !!currentPassword || !!newPassword || !!confirmPassword);
  const back = () => { if (busy) return; if (dirty) Alert.alert("Discard unsaved changes?", "Your saved account details will stay the same.", [{ text: "Keep editing", style: "cancel" }, { text: "Discard", style: "destructive", onPress: onBack }]); else onBack(); };
  const passwordField = (label: string, key: string, value: string, change: (value: string) => void) => <View style={s.field}>
    <Text style={s.label}>{label}</Text>
    <View style={s.passwordRow}><TextInput style={[s.input, s.passwordInput]} value={value} onChangeText={change} secureTextEntry={!visible[key]} editable={!busy} autoCapitalize="none" autoCorrect={false} maxLength={PASSWORD_MAX_LENGTH} accessibilityLabel={label} />
      <Pressable style={s.eye} accessibilityRole="button" accessibilityLabel={`${visible[key] ? "Hide" : "Show"} ${label.toLowerCase()}`} onPress={() => setVisible(current => ({ ...current, [key]: !current[key] }))}>{visible[key] ? <EyeOff color={palette.textSecondary} size={20} /> : <Eye color={palette.textSecondary} size={20} />}</Pressable></View>
  </View>;
  const saveProfile = async () => {
    if (saving.current || !account) return;
    setProfileError(""); setSuccess("");
    if (!name.trim()) { setProfileError("Enter your name."); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) { setProfileError("Enter a valid email address."); return; }
    if (emailChanged && !emailPassword) { setProfileError("Enter your current password to change your email."); return; }
    saving.current = true; setBusy(true);
    try {
      const user = await updateAccount(apiBaseUrl, { name: name.trim(), email: email.trim(), phone: phone.trim() || null, ...(emailChanged ? { current_password: emailPassword } : {}) });
      if (!mounted.current) return;
      setAccount(user); setName(user.name); setEmail(user.email); setPhone(user.phone ?? ""); setEmailPassword(""); setSuccess("Account details saved."); onUpdated(user);
    } catch (err) { if (mounted.current && !(err instanceof SessionExpiredError)) setProfileError(err instanceof Error ? err.message : "Unable to save your account."); }
    finally { saving.current = false; if (mounted.current) setBusy(false); }
  };
  const savePassword = async () => {
    if (saving.current) return;
    setPasswordError(""); setSuccess("");
    if (!currentPassword) { setPasswordError("Enter your current password."); return; }
    if (newPassword.length < PASSWORD_MIN_LENGTH || newPassword.length > PASSWORD_MAX_LENGTH) { setPasswordError(`New password must be ${PASSWORD_MIN_LENGTH} to ${PASSWORD_MAX_LENGTH} characters.`); return; }
    if (newPassword !== confirmPassword) { setPasswordError("The new passwords do not match."); return; }
    if (newPassword === currentPassword) { setPasswordError("Choose a different new password."); return; }
    saving.current = true; setBusy(true);
    try {
      await changeAccountPassword(apiBaseUrl, currentPassword, newPassword);
      if (!mounted.current) return;
      setCurrentPassword(""); setNewPassword(""); setConfirmPassword("");
      await onPasswordChanged();
      Alert.alert("Password changed", "Sign in again using your new password. Previous sessions have been signed out.");
    } catch (err) { if (mounted.current && !(err instanceof SessionExpiredError)) setPasswordError(err instanceof Error ? err.message : "Unable to change your password."); }
    finally { saving.current = false; if (mounted.current) setBusy(false); }
  };

  return <SafeAreaView style={s.screen} edges={["top", "left", "right"]}>
    <StatusBar barStyle={mode === "dark" ? "light-content" : "dark-content"} />
    <KeyboardFormScrollView contentContainerStyle={s.content}>
      <View style={s.header}><Pressable disabled={busy} onPress={back} style={s.back} accessibilityRole="button" accessibilityLabel={t("back")}><ArrowLeft color={palette.text} size={22} /></Pressable><View style={s.headingText}><Text style={s.title}>{t("personal")}</Text><Text style={s.subtitle}>Your account, your details</Text></View></View>
      {loading ? <ActivityIndicator color={palette.accent} /> : !account ? <View style={s.card}><Text style={s.error}>{profileError}</Text><Pressable style={s.button} onPress={() => setRetry(n => n + 1)}><Text style={s.buttonText}>Retry</Text></Pressable></View> : <>
        <View style={s.card}><Text style={s.sectionTitle}>Personal details</Text>
          <View style={s.field}><Text style={s.label}>Full name</Text><TextInput style={s.input} value={name} onChangeText={setName} editable={!busy} maxLength={100} accessibilityLabel="Full name" autoCapitalize="words" /></View>
          <View style={s.field}><Text style={s.label}>Email address</Text><TextInput style={s.input} value={email} onChangeText={setEmail} editable={!busy} keyboardType="email-address" autoCapitalize="none" autoCorrect={false} maxLength={254} accessibilityLabel="Email address" /></View>
          <View style={s.field}><Text style={s.label}>Phone number (optional)</Text><TextInput style={s.input} value={phone} onChangeText={setPhone} editable={!busy} keyboardType="phone-pad" placeholder="+971 50 123 4567" placeholderTextColor={palette.textMuted} maxLength={40} accessibilityLabel="Phone number" /><Text style={s.subtitle}>Include your country code. This is a contact number; it is not verified by SMS.</Text></View>
          {emailChanged && <>{passwordField("Current password to change email", "email", emailPassword, setEmailPassword)}<Text style={s.subtitle}>Use your new email the next time you sign in.</Text></>}
          {!!profileError && <Text accessibilityRole="alert" style={s.error}>{profileError}</Text>}{!!success && <Text accessibilityRole="alert" style={s.success}>{success}</Text>}
          <Pressable style={[s.button, busy && s.disabled]} disabled={busy} onPress={() => { void saveProfile(); }}><Text style={s.buttonText}>{busy ? "Saving…" : "Save Details"}</Text></Pressable>
        </View>
        <View style={s.card}><Text style={s.sectionTitle}>Change password</Text><Text style={s.subtitle}>Use at least 8 characters. Changing your password signs out existing sessions.</Text>
          {passwordField("Current password", "current", currentPassword, setCurrentPassword)}
          {passwordField("New password", "new", newPassword, setNewPassword)}
          {passwordField("Confirm new password", "confirm", confirmPassword, setConfirmPassword)}
          {!!passwordError && <Text accessibilityRole="alert" style={s.error}>{passwordError}</Text>}
          <Pressable style={[s.button, busy && s.disabled]} disabled={busy} onPress={() => { void savePassword(); }}><Text style={s.buttonText}>{busy ? "Saving…" : "Update Password"}</Text></Pressable>
        </View>
      </>}
    </KeyboardFormScrollView>
  </SafeAreaView>;
}
