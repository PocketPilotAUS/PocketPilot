import type { PlanningProfile } from "../types/plans";
import FinancialPlanCard from "../components/ai/FinancialPlanCard";
import React, { useEffect, useRef, useState } from "react";
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StatusBar,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { ArrowUp, CloudOff, MessageCircle, RefreshCw, Sparkles, SquarePen, Target } from "lucide-react-native";

import ChatWelcome from "../components/ai/ChatWelcome";
import FinancialPlans from "../components/ai/FinancialPlans";
import FormattedMessage from "../components/ai/FormattedMessage";
import ProposalCard from "../components/ai/ProposalCard";
import TypingIndicator from "../components/ai/TypingIndicator";
import { useAITheme } from "../components/ai/useAITheme";
import { apiFetch, SessionExpiredError } from "../services/apiClient";
import type { ChatMessage, Proposal } from "../types/chat";

export type { ChatMessage } from "../types/chat";

import type useChatSession from "../hooks/useChatSession";

type Props = {
  apiBaseUrl: string;
  onBack: () => void;
  session: ReturnType<typeof useChatSession>;
};

type Section = "chat" | "plans";


const GOAL_PROMPT = "Help me plan how to save for a goal by a specific date.";

export default function AIChatScreen({ apiBaseUrl, session }: Props) {
  const { messages, onMessagesChange, draft, setDraft, busy, pendingQuestion, error, setError } = session;
  const send = (question = draft) => {
    if (proposalLock.current || session.savingPlan !== null) return;
    return session.send(question);
  };
  const { ai, styles, palette, mode } = useAITheme();

  const [reviewProfile, setReviewProfile] = useState<PlanningProfile | undefined>(undefined);
  const [section, setSection] = useState<Section>("chat");
  const [savingProposal, setSavingProposal] = useState<string | null>(null);

  const proposalLock = useRef(false);
  const mounted = useRef(true);
  const scroll = useRef<ScrollView>(null);

  useEffect(() => {
    mounted.current = true;

    return () => {
      mounted.current = false;
    };
  }, []);

  // Confirms or dismisses an expense/income the AI proposed (unchanged API)
  const handleProposal = async (id: string, operation: "confirm" | "dismiss") => {
    if (proposalLock.current || busy || session.savingPlan !== null) return;

    proposalLock.current = true;
    setSavingProposal(id);
    setError(null);

    try {
      const response = await apiFetch(apiBaseUrl, `/ai/proposals/${id}/${operation}`, { method: "POST" });

      if (!response.ok) throw new Error("save");

      const data: { status: Proposal["status"] } = await response.json();

      if (mounted.current) {
        onMessagesChange(messages.map((message) =>
          message.proposal?.id === id ? { ...message, proposal: { ...message.proposal, status: data.status } } : message
        ));
      }
    } catch (err) {
      if (mounted.current && !(err instanceof SessionExpiredError)) {
        setError({ title: "Couldn't update this record", message: "Please try again.", retry: false });
      }
    } finally {
      proposalLock.current = false;

      if (mounted.current) setSavingProposal(null);
    }
  };

  const startNewChat = () => {
    Alert.alert("Start a new chat?", "This conversation will be cleared. Anything you confirmed stays saved.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "New chat",
        style: "destructive",
        onPress: () => {
          if (busy || proposalLock.current || session.savingPlan !== null) return;
          session.reset();
        },
      },
    ]);
  };

  const startPlanning = () => {
    setSection("chat");
    setDraft(GOAL_PROMPT);
  };

  const canSend = !busy && session.savingPlan === null && savingProposal === null && draft.trim().length > 0;
  const showWelcome = messages.length === 0 && pendingQuestion === null;

  const renderMessage = (message: ChatMessage, index: number) => {
    if (message.role === "user") {
      return (
        <View key={index} style={[ai.messageRow, ai.messageRowUser]}>
          <View style={[ai.bubble, ai.userBubble]}>
            <Text selectable style={ai.userText}>{message.content}</Text>
          </View>
        </View>
      );
    }

    const proposal = message.proposal;

    return (
      <View key={index} style={ai.messageRow}>
        <View style={ai.avatar}>
          <Sparkles size={14} color={palette.accent} strokeWidth={2.2} />
        </View>
        <View style={[ai.bubble, ai.assistantBubble]}>
          <FormattedMessage content={message.content} />
          {message.planningProfile && <Pressable onPress={() => { setReviewProfile(message.planningProfile); setSection("plans"); }}><Text style={ai.composerNote}>Review proposed household and goal details</Text></Pressable>}
          {message.plan && <FinancialPlanCard plan={message.plan} busy={busy || session.savingPlan !== null} onSave={!message.plan.id ? () => { void session.saveFinancialPlan(message.plan!, index); } : undefined} />}
          {proposal && (
            <ProposalCard
              proposal={proposal}
              saving={savingProposal === proposal.id}
              disabled={busy || savingProposal !== null || session.savingPlan !== null}
              onConfirm={() => { void handleProposal(proposal.id, "confirm"); }}
              onDismiss={() => { void handleProposal(proposal.id, "dismiss"); }}
            />
          )}
        </View>
      </View>
    );
  };

  // Shown above the welcome screen (so it is never off-screen), or after
  // the latest message in a conversation
  const errorCard = error ? (
    <View style={ai.errorCard} accessibilityRole="alert">
      <View style={ai.errorHeader}>
        <CloudOff size={17} color={palette.danger} strokeWidth={2.2} />
        <Text style={ai.errorTitle}>{error.title}</Text>
      </View>
      <Text style={ai.errorText}>{error.message}</Text>

      {error.retry && draft.trim().length > 0 && (
        <Pressable
          onPress={() => { void send(); }}
          style={({ pressed }) => [styles.pill, ai.retryPill, pressed && styles.buttonDisabled]}
          accessibilityRole="button"
        >
          <RefreshCw size={13} color={palette.accent} strokeWidth={2.4} />
          <Text style={styles.pillText}>Try again</Text>
        </Pressable>
      )}
    </View>
  ) : null;

  return (
    <SafeAreaView style={ai.screen} edges={["top", "left", "right"]}>
      <StatusBar barStyle={mode === "dark" ? "light-content" : "dark-content"} />

      <View style={ai.header}>
        <View style={ai.headerRow}>
          <View>
            <Text style={styles.eyebrow}>PocketPilot AI</Text>
            <Text style={styles.title}>Assistant</Text>
          </View>

          {section === "chat" && messages.length > 0 && (
            <Pressable
              onPress={startNewChat}
              disabled={busy || savingProposal !== null || session.savingPlan !== null}
              style={({ pressed }) => [ai.newChat, (pressed || busy) && styles.buttonDisabled]}
              accessibilityRole="button"
              accessibilityLabel="Start a new chat"
            >
              <SquarePen size={14} color={palette.textSecondary} strokeWidth={2.2} />
              <Text style={ai.newChatText}>New chat</Text>
            </Pressable>
          )}
        </View>

        <View style={ai.segmented} accessibilityRole="tablist">
          {([
            { key: "chat", label: "AI Chat", Icon: MessageCircle },
            { key: "plans", label: "My Financial Plans", Icon: Target },
          ] as const).map(({ key, label, Icon }) => {
            const active = section === key;

            return (
              <Pressable
                key={key}
                onPress={() => { if (key === "plans") setReviewProfile(undefined); setSection(key); }}
                style={[ai.segment, active && ai.segmentActive]}
                accessibilityRole="tab"
                accessibilityState={{ selected: active }}
              >
                <Icon size={15} color={active ? palette.accent : palette.textSecondary} strokeWidth={2.2} />
                <Text style={[ai.segmentText, active && ai.segmentTextActive]} numberOfLines={1}>
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      {section === "plans" ? (
        // Saved plans and the guided form share the confirmed planning profile.
        <FinancialPlans apiBaseUrl={apiBaseUrl} initialProfile={reviewProfile} onPreview={session.addPlanPreview} onStartPlanning={startPlanning} />
      ) : (
        <KeyboardAvoidingView style={ai.flex} behavior={Platform.OS === "ios" ? "padding" : "height"}>
          <ScrollView
            ref={scroll}
            style={ai.flex}
            contentContainerStyle={ai.conversation}
            keyboardShouldPersistTaps="handled"
            keyboardDismissMode={Platform.OS === "ios" ? "interactive" : "on-drag"}
            onContentSizeChange={() => {
              if (!showWelcome) scroll.current?.scrollToEnd({ animated: true });
            }}
          >
            {showWelcome ? (
              <>
                {errorCard}
                <ChatWelcome disabled={busy} onSuggestion={(prompt) => { void send(prompt); }} />
              </>
            ) : (
              messages.map(renderMessage)
            )}

            {pendingQuestion !== null && (
              <>
                {renderMessage({ role: "user", content: pendingQuestion }, messages.length)}
                <View style={ai.messageRow}>
                  <View style={ai.avatar}>
                    <Sparkles size={14} color={palette.accent} strokeWidth={2.2} />
                  </View>
                  <View style={[ai.bubble, ai.assistantBubble]}>
                    <TypingIndicator />
                    <Text style={ai.typingNote}>Thinking… this can take a minute.</Text>
                  </View>
                </View>
              </>
            )}

            {!showWelcome && errorCard}
          </ScrollView>

          <View style={ai.composer}>
            <TextInput
              value={draft}
              onChangeText={setDraft}
              placeholder="Ask about budgeting, saving or debt…"
              placeholderTextColor={palette.textMuted}
              multiline
              maxLength={4000}
              editable={!busy}
              style={ai.composerInput}
              accessibilityLabel="Message PocketPilot AI"
            />
            <Pressable
              onPress={() => { void send(); }}
              disabled={!canSend}
              style={[ai.sendButton, !canSend && ai.sendButtonDisabled]}
              accessibilityRole="button"
              accessibilityLabel="Send message"
            >
              <ArrowUp size={20} color={canSend ? palette.onAccent : palette.textMuted} strokeWidth={2.6} />
            </Pressable>
          </View>
          <Text style={ai.composerNote}>Conversation kept for this session. Sign out to clear it.</Text>
        </KeyboardAvoidingView>
      )}
    </SafeAreaView>
  );
}
