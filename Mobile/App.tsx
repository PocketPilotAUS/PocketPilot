import React, { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  StatusBar,
  TouchableOpacity,
  Pressable,
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
import { Sun, Moon, LogOut, TriangleAlert } from "lucide-react-native";
import KeyboardFormScrollView from "./src/components/KeyboardFormScrollView";
import BottomNavigation, { AppTab } from "./src/components/BottomNavigation";
import AmbientBackground from "./src/components/AmbientBackground";
import AnimatedWelcome from "./src/components/AnimatedWelcome";
import FinancialOverview from "./src/components/dashboard/FinancialOverview";
import SpendingBreakdown from "./src/components/dashboard/SpendingBreakdown";
import BudgetTracker from "./src/components/dashboard/BudgetTracker";
import { useDashboardTheme } from "./src/components/dashboard/useDashboardTheme";
import type { DashboardData } from "./src/utils/dashboard";

import AIChatScreen, { ChatMessage } from "./src/screens/AIChatScreen";
import AIInsightsScreen from "./src/screens/AIInsightsScreen";
import AddTransactionScreen from "./src/screens/AddTransactionScreen";
import TransactionHistoryScreen from "./src/screens/TransactionHistoryScreen";

import { createAppStyles } from "./src/styles/AppStyles";
import { useAppTheme } from "./src/theme/ThemeContext";

function PocketPilotApp() {
  const { colors, mode, toggleTheme } = useAppTheme();
  const styles = createAppStyles(colors);
  const dashboard = useDashboardTheme();
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

  type SpendingSummary = DashboardData;

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
        onAddExpense={() => setScreen("addTransaction")}
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

  const firstName = currentUser?.name.trim().split(/\s+/)[0];

  return withNavigation(
    <SafeAreaView style={dashboard.styles.screen} edges={["top", "left", "right"]}>
      <StatusBar
        barStyle={mode === "dark" ? "light-content" : "dark-content"}
      />

      <KeyboardFormScrollView contentContainerStyle={dashboard.styles.content}>
        <View style={dashboard.styles.header}>
          <View style={dashboard.styles.headerText}>
            <Text style={dashboard.styles.eyebrow}>
              {firstName ? `Hi, ${firstName}` : "Your finances"}
            </Text>
            <Text style={dashboard.styles.title}>Dashboard</Text>
          </View>

          <TouchableOpacity
            style={dashboard.styles.iconButton}
            onPress={toggleTheme}
            activeOpacity={0.7}
            accessibilityRole="button"
            accessibilityLabel="Toggle dark and light mode"
          >
            {mode === "dark" ? (
              <Sun size={19} color={dashboard.palette.text} strokeWidth={1.8} />
            ) : (
              <Moon size={19} color={dashboard.palette.text} strokeWidth={1.8} />
            )}
          </TouchableOpacity>
        </View>

        {error ? (
          <View style={dashboard.styles.errorBanner}>
            <TriangleAlert size={16} color={dashboard.palette.danger} strokeWidth={2.2} />
            <Text style={dashboard.styles.errorBannerText}>{error}</Text>
          </View>
        ) : null}

        <FinancialOverview
          data={spending}
          loading={loading}
          apiBaseUrl={API_BASE_URL}
          onSaved={setSpending}
        />

        <SpendingBreakdown
          data={spending}
          loading={loading}
          onAddExpense={() => setScreen("addTransaction")}
        />

        <BudgetTracker
          data={spending}
          apiBaseUrl={API_BASE_URL}
          onSaved={setSpending}
        />

        <Pressable
          onPress={handleLogout}
          style={({ pressed }) => [dashboard.styles.logoutButton, pressed && dashboard.styles.buttonDisabled]}
          accessibilityRole="button"
        >
          <LogOut size={17} color={dashboard.palette.textSecondary} strokeWidth={2} />
          <Text style={dashboard.styles.logoutText}>Log out</Text>
        </Pressable>
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
