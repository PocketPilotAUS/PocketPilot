import useChatSession from "./src/hooks/useChatSession";
import React, { useEffect, useRef, useState } from "react";
import { StatusBar, TouchableOpacity, Pressable, ActivityIndicator } from "react-native";
import { View, Text, Alert } from "./src/preferences/LocalizedNative";

import LoginScreen from "./src/screens/LoginScreen";
import RegisterScreen from "./src/screens/RegisterScreen";
import SettingsScreen from "./src/screens/SettingsScreen";
import { PreferencesProvider, usePreferences } from "./src/preferences/PreferencesContext";
import { localize } from "./src/preferences/localize";

import { AuthUser, restoreSession, logout } from "./src/services/authService";
import {
  apiFetch,
  SessionExpiredError,
  setSessionExpiredHandler,
} from "./src/services/apiClient";

import { SafeAreaView, SafeAreaProvider } from "react-native-safe-area-context";
import { ThemeProvider } from "./src/theme/ThemeContext";
import { TriangleAlert, Settings } from "lucide-react-native";
import KeyboardFormScrollView from "./src/components/KeyboardFormScrollView";
import BottomNavigation, { AppTab } from "./src/components/BottomNavigation";
import AmbientBackground from "./src/components/AmbientBackground";
import AnimatedWelcome from "./src/components/AnimatedWelcome";
import FinancialOverview from "./src/components/dashboard/FinancialOverview";
import SpendingBreakdown from "./src/components/dashboard/SpendingBreakdown";
import BudgetTracker from "./src/components/dashboard/BudgetTracker";
import { useDashboardTheme } from "./src/components/dashboard/useDashboardTheme";
import type { DashboardData } from "./src/utils/dashboard";

import AIChatScreen from "./src/screens/AIChatScreen";
import AIInsightsScreen from "./src/screens/AIInsightsScreen";
import TransactionsScreen from "./src/screens/TransactionsScreen";

import { createAppStyles } from "./src/styles/AppStyles";
import { useAppTheme } from "./src/theme/ThemeContext";

function PocketPilotApp() {
  const { t, language } = usePreferences();
  const { colors, mode } = useAppTheme();
  const styles = createAppStyles(colors);
  const dashboard = useDashboardTheme();
  type Screen =
    | "welcome"
    | "login"
    | "register"
    | "dashboard"
    | "history"
    | "aiInsights"
    | "aiChat"
    | "settings";

  const [screen, setScreen] = useState<Screen>("welcome");
  const [startAddingTransaction, setStartAddingTransaction] = useState(false);
  const openAddTransaction = () => { setStartAddingTransaction(true); setScreen("history"); };
  const screenRef = useRef<Screen>(screen);
  const settingsReturn = useRef<Screen>("dashboard");
  const openSettings = () => { settingsReturn.current = screen; setScreen("settings"); };

  const API_BASE_URL = "http://192.168.1.240:8000";
  const chatSession = useChatSession(API_BASE_URL);

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
      chatSession.reset();
      setCurrentUser(null);
      setSpending(null);
      setScreen("welcome");
    } catch {
      Alert.alert("Error", "Unable to log out. Please try again.");
    }
  };



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
      const signedInScreens: Screen[] = ["dashboard", "history", "aiInsights", "aiChat", "settings"];

      // Ignore late responses once the user is already signed out
      if (!signedInScreens.includes(screenRef.current)) return;

      // Updated immediately so simultaneous 401s show only one alert
      screenRef.current = "login";
      chatSession.reset();
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
      <BottomNavigation active={screen as AppTab} onSelect={tab => { setStartAddingTransaction(false); setScreen(tab); }} />
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

  if (screen === "settings") {
    return <SettingsScreen apiBaseUrl={API_BASE_URL} onBack={() => setScreen(settingsReturn.current)} onUpdated={setCurrentUser} onLogout={handleLogout} onPasswordChanged={async () => {
      await logout(); chatSession.reset(); setCurrentUser(null); setSpending(null); screenRef.current = "login"; setScreen("login");
    }} />;
  }

  if (screen === "aiChat") {
    return withNavigation(<AIChatScreen apiBaseUrl={API_BASE_URL} onBack={() => setScreen("dashboard")} session={chatSession} />);
  }

  if (screen === "aiInsights") {
    return withNavigation(<AIInsightsScreen apiBaseUrl={API_BASE_URL} onBack={() => setScreen("dashboard")} />);
  }

  if (screen === "history") {
    return withNavigation(
      <TransactionsScreen
        apiBaseUrl={API_BASE_URL}
        budgetCategories={spending?.ideal_budget?.allocations.map(row => row.category)}
        initiallyAdding={startAddingTransaction}
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
            <Text localize={false} style={dashboard.styles.eyebrow}>
              {firstName ? `${localize("Hi,", language)} ${firstName}` : localize("Your finances", language)}
            </Text>
            <Text style={dashboard.styles.title}>Dashboard</Text>
          </View>

          <TouchableOpacity style={dashboard.styles.iconButton} onPress={openSettings} accessibilityRole="button" accessibilityLabel={t("settings")}>
            <Settings size={19} color={dashboard.palette.text} />
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
          onAddExpense={openAddTransaction}
        />

        <BudgetTracker
          data={spending}
          apiBaseUrl={API_BASE_URL}
          onSaved={setSpending}
          aiBusy={chatSession.busy}
          onReview={() => { if (!spending?.ideal_budget || chatSession.busy) return; setScreen("aiChat"); void chatSession.send("Review my saved monthly budget. Check my income, category targets, recorded spending, affordability and missing costs. Suggest adjustments for me to approve; do not save or record anything.", { year: spending.year, month: spending.month }); }}
        />

      </KeyboardFormScrollView>
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <PreferencesProvider><ThemeProvider>
        <PocketPilotApp />
      </ThemeProvider></PreferencesProvider>
    </SafeAreaProvider>
  );
}
