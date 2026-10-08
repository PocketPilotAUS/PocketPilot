import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StatusBar,
  TouchableOpacity,
  ScrollView,
  Alert,
  ActivityIndicator,
} from "react-native";

import LoginScreen from "./src/screens/LoginScreen";
import RegisterScreen from "./src/screens/RegisterScreen";

import { DemoUser, getCurrentUser, logout } from "./src/services/authService";

import { SafeAreaView, SafeAreaProvider } from "react-native-safe-area-context";
import { ThemeProvider } from "./src/theme/ThemeContext";
import { Sun, Moon } from "lucide-react-native";
import MetallicGlassCard from "./src/components/MetallicGlassCard";
import AmbientBackground from "./src/components/AmbientBackground";
import MetallicGlassButton from "./src/components/MetallicGlassButton";
import AnimatedWelcome from "./src/components/AnimatedWelcome";

import AddTransactionScreen from "./src/screens/AddTransactionScreen";
import TransactionHistoryScreen from "./src/screens/TransactionHistoryScreen";

import { createAppStyles } from "./src/styles/AppStyles";
import { useAppTheme } from "./src/theme/ThemeContext";

function PocketPilotApp() {
  const { colors, mode, toggleTheme } = useAppTheme();
  const styles = createAppStyles(colors);
  type Screen =
    | "welcome"
    | "login"
    | "register"
    | "dashboard"
    | "addTransaction"
    | "history";

  const [screen, setScreen] = useState<Screen>("welcome");

  const [currentUser, setCurrentUser] = useState<DemoUser | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    const restoreSession = async () => {
      try {
        const user = await getCurrentUser();

        if (user) {
          setCurrentUser(user);
          setScreen("dashboard");
        }
      } catch (error) {
        console.error("Failed to restore session:", error);
      } finally {
        setCheckingSession(false);
      }
    };

    restoreSession();
  }, []);

  const handleAuthenticated = (user: DemoUser) => {
    setCurrentUser(user);
    setScreen("dashboard");
  };

  const handleLogout = async () => {
    try {
      await logout();
      setCurrentUser(null);
      setSpending(null);
      setScreen("welcome");
    } catch {
      Alert.alert("Error", "Unable to log out. Please try again.");
    }
  };

  const API_BASE_URL = "http://192.168.1.15:8000";

  type SpendingSummary = {
    total_spending: number;
    category_spending: Record<string, number>;
    category_percentages: Record<string, number>;
  };

  const [spending, setSpending] = useState<SpendingSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (screen !== "dashboard") return;

    const fetchSpending = async () => {
      setLoading(true);
      setError("");

      try {
        const response = await fetch(`${API_BASE_URL}/spending/summary`);

        if (!response.ok) {
          throw new Error("Failed to load spending data");
        }

        const data: SpendingSummary = await response.json();
        setSpending(data);
      } catch (err) {
        setError("Could not connect to PocketPilot backend.");
      } finally {
        setLoading(false);
      }
    };

    fetchSpending();
  }, [screen]);

  if (checkingSession) {
    return (
      <SafeAreaView style={styles.container}>
        <AmbientBackground />
        <ActivityIndicator
          size="large"
          color={colors.primary}
          style={styles.sessionLoader}
        />
      </SafeAreaView>
    );
  }

  if (screen === "login") {
    return (
      <LoginScreen
        onLogin={handleAuthenticated}
        onRegister={() => setScreen("register")}
        onBack={() => setScreen("welcome")}
      />
    );
  }

  if (screen === "register") {
    return (
      <RegisterScreen
        onRegister={handleAuthenticated}
        onLogin={() => setScreen("login")}
        onBack={() => setScreen("welcome")}
      />
    );
  }

  if (screen === "addTransaction") {
    return (
      <AddTransactionScreen
        apiBaseUrl={API_BASE_URL}
        onBack={() => setScreen("dashboard")}
        onSaved={() => setScreen("dashboard")}
      />
    );
  }

  if (screen === "history") {
    return (
      <TransactionHistoryScreen
        apiBaseUrl={API_BASE_URL}
        onBack={() => setScreen("dashboard")}
      />
    );
  }

  if (screen === "welcome") {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar
          barStyle={mode === "dark" ? "light-content" : "dark-content"}
        />

        <AnimatedWelcome onGetStarted={() => setScreen("login")} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView
      style={styles.container}
      edges={["top", "left", "right", "bottom"]}
    >
      <StatusBar
        barStyle={mode === "dark" ? "light-content" : "dark-content"}
      />

      <AmbientBackground />

      <ScrollView contentContainerStyle={styles.dashboard}>
        {/* Dashboard header */}
        <View style={styles.headerRow}>
          <View style={styles.headerText}>
            <Text style={styles.greeting}>YOUR FINANCIAL OVERVIEW</Text>
            <Text style={styles.heading}>Dashboard</Text>
          </View>

          <TouchableOpacity
            style={styles.themeToggle}
            onPress={toggleTheme}
            activeOpacity={0.7}
            accessibilityRole="button"
            accessibilityLabel="Toggle dark and light mode"
          >
            {mode === "dark" ? (
              <Sun size={20} color={colors.text} strokeWidth={1.8} />
            ) : (
              <Moon size={20} color={colors.text} strokeWidth={1.8} />
            )}
          </TouchableOpacity>
        </View>

        {/* Spending overview */}
        {error ? (
          <Text style={{ color: colors.error, marginBottom: 15 }}>{error}</Text>
        ) : null}

        <MetallicGlassCard>
          <Text style={styles.cardLabel}>TOTAL SPENDING</Text>

          <Text style={styles.amount}>
            {loading
              ? "Loading..."
              : spending
                ? `AED ${spending.total_spending.toFixed(2)}`
                : "AED 0.00"}
          </Text>

          <Text style={styles.cardHint}>All recorded expenses</Text>
        </MetallicGlassCard>

        {/* Quick actions */}
        <Text style={styles.sectionTitle}>Quick Actions</Text>

        <View style={styles.quickActions}>
          <View style={styles.quickActionItem}>
            <MetallicGlassButton
              title="+ Add Transaction"
              onPress={() => setScreen("addTransaction")}
            />
          </View>

          <View style={styles.quickActionItem}>
            <MetallicGlassButton
              title="View History"
              variant="secondary"
              onPress={() => setScreen("history")}
            />
          </View>
        </View>

        {/* Spending categories */}
        <Text style={styles.sectionTitle}>Spending by Category</Text>

        <MetallicGlassCard>
          {spending && Object.keys(spending.category_spending).length > 0 ? (
            Object.entries(spending.category_spending).map(
              ([category, amount]) => (
                <View key={category} style={{ marginBottom: 18 }}>
                  <View style={styles.categoryRow}>
                    <Text style={styles.cardLabel}>{category}</Text>
                    <Text style={styles.categoryAmount}>
                      AED {amount.toFixed(2)}
                    </Text>
                  </View>

                  <View style={styles.progressTrack}>
                    <View
                      style={[
                        styles.progressFill,
                        {
                          width: `${Math.min(
                            100,
                            Math.max(
                              0,
                              spending.category_percentages[category] ?? 0,
                            ),
                          )}%`,
                        },
                      ]}
                    />
                  </View>

                  <Text style={styles.cardHint}>
                    {spending.category_percentages[category]}% of spending
                  </Text>
                </View>
              ),
            )
          ) : (
            <Text style={styles.emptyText}>
              {loading ? "Loading categories..." : "No transactions yet."}
            </Text>
          )}
        </MetallicGlassCard>

        {/* Insights */}
        <Text style={styles.sectionTitle}>Financial Insights</Text>

        <MetallicGlassCard>
          <Text style={styles.emptyText}>
            Your personalized recommendations will appear here.
          </Text>
        </MetallicGlassCard>

        <View style={styles.logoutContainer}>
          <MetallicGlassButton
            title="Log Out"
            variant="secondary"
            onPress={handleLogout}
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <PocketPilotApp />
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
