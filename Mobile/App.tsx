import IdealBudgetCard from "./src/components/IdealBudgetCard";
import React, { useEffect, useRef, useState } from "react";
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

import { AuthUser, restoreSession, logout } from "./src/services/authService";
import {
  apiFetch,
  SessionExpiredError,
  setSessionExpiredHandler,
} from "./src/services/apiClient";

import { SafeAreaView, SafeAreaProvider } from "react-native-safe-area-context";
import { ThemeProvider } from "./src/theme/ThemeContext";
import { Sun, Moon } from "lucide-react-native";
import KeyboardFormScrollView from "./src/components/KeyboardFormScrollView";
import BottomNavigation, { AppTab } from "./src/components/BottomNavigation";
import MonthlyIncomeCard, { MonthlyBudget } from "./src/components/MonthlyIncomeCard";
import MetallicGlassCard from "./src/components/MetallicGlassCard";
import AmbientBackground from "./src/components/AmbientBackground";
import MetallicGlassButton from "./src/components/MetallicGlassButton";
import AnimatedWelcome from "./src/components/AnimatedWelcome";

import AIChatScreen, { ChatMessage } from "./src/screens/AIChatScreen";
import AIInsightsScreen from "./src/screens/AIInsightsScreen";
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
    | "history"
    | "aiInsights"
    | "aiChat";

  const [screen, setScreen] = useState<Screen>("welcome");
  const screenRef = useRef<Screen>(screen);

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);

  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    screenRef.current = screen;
  }, [screen]);

  const handleAuthenticated = (user: AuthUser) => {
    setCurrentUser(user);
    setScreen("dashboard");
  };

  const handleLogout = async () => {
    try {
      await logout();
      setChatMessages([]);
      setCurrentUser(null);
      setSpending(null);
      setScreen("welcome");
    } catch {
      Alert.alert("Error", "Unable to log out. Please try again.");
    }
  };

  const API_BASE_URL = "http://192.168.1.185:8000";

  type SpendingSummary = MonthlyBudget & {
    total_spending: number;
    category_spending: Record<string, number>;
    category_percentages: Record<string, number>;
  };

  const [spending, setSpending] = useState<SpendingSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const restore = async () => {
      try {
        // Checks the saved login token with the backend
        const result = await restoreSession(API_BASE_URL);

        if (result.status === "authenticated") {
          setCurrentUser(result.user);
          setScreen("dashboard");
        } else if (result.status === "offline") {
          // Token kept: the dashboard shows the connection error, and
          // the next request either works or returns to sign-in
          setScreen("dashboard");
        }
      } catch (error) {
        console.error("Failed to restore session:", error);
      } finally {
        setCheckingSession(false);
      }
    };

    restore();
  }, []);

  useEffect(() => {
    // Called when any request is rejected with 401 (expired or invalid token)
    setSessionExpiredHandler(() => {
      const signedInScreens: Screen[] = ["dashboard", "addTransaction", "history", "aiInsights", "aiChat"];

      // Ignore late responses once the user is already signed out
      if (!signedInScreens.includes(screenRef.current)) return;

      // Updated immediately so simultaneous 401s show only one alert
      screenRef.current = "login";
      setChatMessages([]);
      setCurrentUser(null);
      setSpending(null);
      setScreen("login");

      Alert.alert(
        "Session expired",
        "Your session has expired. Please sign in again."
      );
    });

    return () => setSessionExpiredHandler(null);
  }, []);

  useEffect(() => {
    if (screen !== "dashboard") return;

    // Set when the user leaves the dashboard (e.g. logs out), so a late
    // response can never show one user's totals to the next user
    let cancelled = false;

    const fetchSpending = async () => {
      setLoading(true);
      setError("");

      try {
        // Summary of the logged-in user's transactions only
        const now = new Date();
        const response = await apiFetch(API_BASE_URL, `/budget/monthly?year=${now.getFullYear()}&month=${now.getMonth() + 1}`);

        if (!response.ok) {
          throw new Error("Failed to load spending data");
        }

        const data: SpendingSummary = await response.json();

        if (!cancelled) setSpending(data);
      } catch (err) {
        // An expired session is handled above by returning to sign-in
        if (err instanceof SessionExpiredError || cancelled) return;

        setError("Could not connect to PocketPilot backend.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchSpending();

    return () => {
      cancelled = true;
    };
  }, [screen]);

  const withNavigation = (content: React.ReactNode) => (
    <View style={styles.container}>
      <View style={styles.container}>{content}</View>
      <BottomNavigation active={screen as AppTab} onSelect={setScreen} />
    </View>
  );
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
        apiBaseUrl={API_BASE_URL}
        onLogin={handleAuthenticated}
        onRegister={() => setScreen("register")}
        onBack={() => setScreen("welcome")}
      />
    );
  }

  if (screen === "register") {
    return (
      <RegisterScreen
        apiBaseUrl={API_BASE_URL}
        onRegister={handleAuthenticated}
        onLogin={() => setScreen("login")}
        onBack={() => setScreen("welcome")}
      />
    );
  }

  if (screen === "addTransaction") {
    return withNavigation(
      <AddTransactionScreen
        apiBaseUrl={API_BASE_URL}
        onBack={() => setScreen("dashboard")}
        onSaved={() => setScreen("dashboard")}
      />
    );
  }

  if (screen === "aiChat") {
    return withNavigation(<AIChatScreen apiBaseUrl={API_BASE_URL} onBack={() => setScreen("dashboard")} messages={chatMessages} onMessagesChange={setChatMessages} />);
  }

  if (screen === "aiInsights") {
    return withNavigation(<AIInsightsScreen apiBaseUrl={API_BASE_URL} onBack={() => setScreen("dashboard")} />);
  }

  if (screen === "history") {
    return withNavigation(
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

  return withNavigation(
    <SafeAreaView
      style={styles.container}
      edges={["top", "left", "right"]}
    >
      <StatusBar
        barStyle={mode === "dark" ? "light-content" : "dark-content"}
      />

      <AmbientBackground />

      <KeyboardFormScrollView contentContainerStyle={styles.dashboard}>
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

        <MonthlyIncomeCard budget={spending} loading={loading} apiBaseUrl={API_BASE_URL} onSaved={(budget) => setSpending(budget as SpendingSummary)} />
        <IdealBudgetCard budget={spending} apiBaseUrl={API_BASE_URL} onSaved={(budget) => setSpending(budget as SpendingSummary)} />

        {/* Spending categories */}
        <Text style={styles.sectionTitle}>This Month by Category</Text>

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

        <View style={styles.logoutContainer}>
          <MetallicGlassButton
            title="Log Out"
            variant="secondary"
            onPress={handleLogout}
          />
        </View>
      </KeyboardFormScrollView>
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
