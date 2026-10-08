
import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ActivityIndicator,
  StatusBar,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { ArrowLeft, Eye, EyeOff } from "lucide-react-native";

import AmbientBackground from "../components/AmbientBackground";
import MetallicGlassCard from "../components/MetallicGlassCard";
import MetallicGlassButton from "../components/MetallicGlassButton";
import { useAppTheme } from "../theme/ThemeContext";
import { createRegisterStyles } from "../styles/RegisterStyles";
import { register, DemoUser } from "../services/authService";

type Props = {
  onRegister: (user: DemoUser) => void;
  onLogin: () => void;
  onBack: () => void;
};

export default function RegisterScreen({
  onRegister,
  onLogin,
  onBack,
}: Props) {
  const { colors, mode } = useAppTheme();
  const styles = createRegisterStyles(colors);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleRegister = async () => {
    if (loading) return;

    setError("");

    // Check for empty fields
    if (
      !name.trim() ||
      !email.trim() ||
      !password ||
      !confirmPassword
    ) {
      setError("Please fill in all fields.");
      return;
    }

    // Check password confirmation
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      // Register using our dummy authentication service
      const result = await register(name, email, password);

      if (result.success && result.user) {
        onRegister(result.user);
      } else {
        setError(result.message);
      }
    } catch {
      setError(
        "Unable to create your account. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar
        barStyle={
          mode === "dark"
            ? "light-content"
            : "dark-content"
        }
      />

      <AmbientBackground />

      <KeyboardAvoidingView
        style={styles.keyboardContainer}
        behavior={
          Platform.OS === "ios" ? "padding" : undefined
        }
      >
        <ScrollView
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
            <ArrowLeft
              size={22}
              color={colors.text}
            />

            <Text style={styles.backText}>
              Back
            </Text>
          </Pressable>

          {/* Header */}
          <Text style={styles.eyebrow}>
            POCKETPILOT
          </Text>

          <Text style={styles.title}>
            Create your account.
          </Text>

          <Text style={styles.subtitle}>
            Start building better financial habits today.
          </Text>

          {/* Registration Form */}
          <MetallicGlassCard>
            <Text style={styles.label}>
              Full name
            </Text>

            <TextInput
              value={name}
              onChangeText={setName}
              placeholder="Your full name"
              placeholderTextColor={colors.textMuted}
              autoCapitalize="words"
              autoComplete="name"
              style={styles.input}
            />

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
                placeholder="At least 6 characters"
                placeholderTextColor={colors.textMuted}
                secureTextEntry={!showPassword}
                autoCapitalize="none"
                autoCorrect={false}
                autoComplete="new-password"
                style={styles.passwordInput}
              />

              <Pressable
                onPress={() =>
                  setShowPassword(!showPassword)
                }
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

            <Text style={styles.label}>
              Confirm password
            </Text>

            <TextInput
              value={confirmPassword}
              onChangeText={setConfirmPassword}
              placeholder="Re-enter your password"
              placeholderTextColor={colors.textMuted}
              secureTextEntry={!showPassword}
              autoCapitalize="none"
              autoCorrect={false}
              style={styles.confirmPasswordInput}
            />

            {/* Error Message */}
            {error ? (
              <Text style={styles.error}>
                {error}
              </Text>
            ) : null}

            {/* Register Button */}
            <View style={styles.submitContainer}>
              {loading ? (
                <ActivityIndicator
                  color={colors.primary}
                />
              ) : (
                <MetallicGlassButton
                  title="Create Account  →"
                  onPress={handleRegister}
                />
              )}
            </View>
          </MetallicGlassCard>

          {/* Login Navigation */}
          <View style={styles.loginRow}>
            <Text style={styles.loginPrompt}>
              Already have an account?{" "}
            </Text>

            <Pressable
              onPress={onLogin}
              accessibilityRole="button"
            >
              <Text style={styles.loginLink}>
                Sign In
              </Text>
            </Pressable>
          </View>

          {/* Demo Notice */}
          <Text style={styles.demoNote}>
            Demo authentication only. Use fictional credentials.
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
