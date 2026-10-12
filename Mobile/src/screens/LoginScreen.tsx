
import React, { useState } from "react";
import { ScrollView, KeyboardAvoidingView, Platform, Pressable, ActivityIndicator, StatusBar } from "react-native";
import { View, Text, TextInput } from "../preferences/LocalizedNative";
import { SafeAreaView } from "react-native-safe-area-context";
import { Eye, EyeOff, ArrowLeft } from "lucide-react-native";

import KeyboardFormScrollView from "../components/KeyboardFormScrollView";
import AmbientBackground from "../components/AmbientBackground";
import MetallicGlassCard from "../components/MetallicGlassCard";
import MetallicGlassButton from "../components/MetallicGlassButton";
import { useAppTheme } from "../theme/ThemeContext";
import { createLoginStyles } from "../styles/LoginStyles";
import { login, AuthUser } from "../services/authService";

type Props = {
  apiBaseUrl: string;
  onLogin: (user: AuthUser) => void;
  onRegister: () => void;
  onBack: () => void;
};

export default function LoginScreen({
  apiBaseUrl,
  onLogin,
  onRegister,
  onBack,
}: Props) {
  const { colors, mode } = useAppTheme();
  const styles = createLoginStyles(colors);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async () => {
    if (loading) return;

    setError("");

    if (!email.trim() || !password) {
      setError("Please enter your email and password.");
      return;
    }

    setLoading(true);

    try {
      const result = await login(apiBaseUrl, email, password);

      if (result.success && result.user) {
        onLogin(result.user);
      } else {
        setError(result.message);
      }
    } catch {
      setError("Unable to log in. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar
        barStyle={mode === "dark" ? "light-content" : "dark-content"}
      />

      <AmbientBackground />

      <KeyboardAvoidingView
        style={styles.keyboardContainer}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <KeyboardFormScrollView avoidKeyboard={false}
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
        >
          {/* Back Button */}
          <Pressable
            onPress={onBack}
            style={styles.backButton}
            accessibilityRole="button"
            accessibilityLabel="Back to welcome"
          >
            <ArrowLeft size={22} color={colors.text} />

            <Text style={styles.backText}>
              Back
            </Text>
          </Pressable>

          {/* Header */}
          <Text style={styles.eyebrow}>
            POCKETPILOT
          </Text>

          <Text style={styles.title}>
            Welcome back.
          </Text>

          <Text style={styles.subtitle}>
            Sign in to continue your financial journey.
          </Text>

          {/* Login Form */}
          <MetallicGlassCard>
            <Text style={styles.label}>
              Email address
            </Text>

            <TextInput
              value={email}
              onChangeText={setEmail}
              placeholder="you@example.com"
              placeholderTextColor={colors.textMuted}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="email"
              style={styles.input}
            />

            <Text style={styles.label}>
              Password
            </Text>

            <View style={styles.passwordContainer}>
              <TextInput
                value={password}
                onChangeText={setPassword}
                placeholder="Enter your password"
                placeholderTextColor={colors.textMuted}
                secureTextEntry={!showPassword}
                autoCapitalize="none"
                autoCorrect={false}
                autoComplete="password"
                style={styles.passwordInput}
              />

              <Pressable
                onPress={() => setShowPassword(!showPassword)}
                accessibilityRole="button"
                accessibilityLabel={
                  showPassword
                    ? "Hide password"
                    : "Show password"
                }
              >
                {showPassword ? (
                  <EyeOff
                    size={20}
                    color={colors.textSecondary}
                  />
                ) : (
                  <Eye
                    size={20}
                    color={colors.textSecondary}
                  />
                )}
              </Pressable>
            </View>

            {/* Error Message */}
            {error ? (
              <Text style={styles.error}>
                {error}
              </Text>
            ) : null}

            {/* Sign In Button */}
            <View style={styles.submitContainer}>
              {loading ? (
                <ActivityIndicator
                  color={colors.primary}
                />
              ) : (
                <MetallicGlassButton
                  title="Sign In  →"
                  onPress={handleLogin}
                />
              )}
            </View>
          </MetallicGlassCard>

          {/* Register Navigation */}
          <View style={styles.registerRow}>
            <Text style={styles.registerPrompt}>
              New to PocketPilot?{" "}
            </Text>

            <Pressable
              onPress={onRegister}
              accessibilityRole="button"
            >
              <Text style={styles.registerLink}>
                Create an account
              </Text>
            </Pressable>
          </View>

          {/* Development Notice */}
          <Text style={styles.demoNote}>
            Development build. Use test credentials only.
          </Text>
        </KeyboardFormScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
