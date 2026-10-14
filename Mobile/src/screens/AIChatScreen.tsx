import type { PlanningProfile } from "../types/plans";
import BudgetGoalCard from "../components/ai/BudgetGoalCard";
import { formatAED } from "../utils/dashboard";
import type { BudgetChoice } from "../types/chat";
import PlanConfirmationActions from "../components/ai/PlanConfirmationActions";
import BudgetPlanEditor from "../components/ai/BudgetPlanEditor";
import BackButton from "../components/BackButton";
import type { FinancialPlan } from "../types/plans";
import React, { useEffect, useRef, useState } from "react";
import { KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, StatusBar } from "react-native";
import { Alert, Text, TextInput, View } from "../preferences/LocalizedNative";
import { SafeAreaView } from "react-native-safe-area-context";
import { ArrowUp, CloudOff, RefreshCw, Sparkles, SquarePen } from "lucide-react-native";

import ChatWelcome from "../components/ai/ChatWelcome";
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
  onSetupBudget: () => void;
  onReviewProfile: (profile: PlanningProfile) => void;
  session: ReturnType<typeof useChatSession>;
};




export default function AIChatScreen({ apiBaseUrl, session, onReviewProfile, onSetupBudget }: Props) {
  const { messages, onMessagesChange, draft, setDraft, busy, pendingQuestion, error, setError } = session;
  const send = (question = draft) => {
    if (proposalLock.current || session.savingPlan !== null) return;
    return session.send(question);
  };
  const { ai, styles, palette, mode } = useAITheme();

  const [savingProposal, setSavingProposal] = useState<string | null>(null);
  const [editingGoal, setEditingGoal] = useState<FinancialPlan | null>(null);
  const [editingGoalBusy, setEditingGoalBusy] = useState(false);

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

  const canSend = !busy && session.savingPlan === null && savingProposal === null && draft.trim().length > 0;
  const showWelcome = messages.length === 0 && pendingQuestion === null;

  const renderMessage = (message: ChatMessage, index: number) => {
    if (message.role === "user") {
      return (
        <View key={index} style={[ai.messageRow, ai.messageRowUser]}>
          <View style={[ai.bubble, ai.userBubble]}>
            <Text localize={false} selectable style={ai.userText}>{message.content}</Text>
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
          {message.budgetRequired && !messages.slice(index + 1).some(item => item.budgetGoal) && <Pressable disabled={busy || session.savingPlan !== null} onPress={onSetupBudget} style={[styles.primaryButton, styles.budgetSetupAction, busy && styles.buttonDisabled]} accessibilityRole="button"><Text style={styles.primaryButtonText}>Set up my budget</Text></Pressable>}
          {message.budgetGoal && <BudgetGoalCard assessment={message.budgetGoal} disabled={busy || savingProposal !== null || session.savingPlan !== null || messages.slice(index + 1).some(item => item.budgetGoal)} onChoice={(choice: BudgetChoice) => {
            const prompt = choice.category === "*" ? (choice.target === null ? "My budget cannot be reduced. Keep all categories protected and suggest a later goal deadline." : "I am willing to explore possible budget cuts again. Ask what is realistic for me.") : choice.target === null ? `I cannot reduce ${choice.category}. Keep it protected for this goal.` : `For this goal scenario, I can manage ${choice.category} on ${formatAED(choice.target)} per month. My saved budget should stay unchanged.`;
            void session.send(prompt, undefined, choice);
          }} />}
          {message.planningProfile && !message.goalPlanning && !message.plan?.ready && <Pressable onPress={() => { onReviewProfile(message.planningProfile!); }}><Text style={ai.composerNote}>Review proposed household and goal details</Text></Pressable>}
          {message.plan?.ready && <PlanConfirmationActions plan={message.plan} dismissed={!!message.planDeclined} busy={busy || savingProposal !== null || session.savingPlan !== null || messages.slice(index + 1).some(item => item.plan)}
            onConfirm={() => { void session.saveFinancialPlan(message.plan!, index); }}
            onEdit={() => { if (message.plan!.budgetGoalSource) { setEditingGoal(message.plan!); } else { onReviewProfile(message.plan!.profile); } }}
            onDecline={() => { onMessagesChange(current => current.map((item, i) => i === index ? { ...item, planDeclined: true } : item)); }} />}
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
      <Modal visible={editingGoal !== null} animationType="slide" onRequestClose={() => { if (!editingGoalBusy) setEditingGoal(null); }}>
        <SafeAreaView style={ai.screen} edges={["top", "left", "right"]}><ScrollView contentContainerStyle={ai.conversation} keyboardShouldPersistTaps="handled">
          <BackButton label="Back to AI Chat" disabled={editingGoalBusy} onPress={() => setEditingGoal(null)} />
          {editingGoal && <BudgetPlanEditor plan={editingGoal} apiBaseUrl={apiBaseUrl} onBusyChange={setEditingGoalBusy} onCancel={() => setEditingGoal(null)} onPreview={plan => { session.addPlanPreview(plan); setEditingGoal(null); }} />}
        </ScrollView></SafeAreaView>
      </Modal>
      <StatusBar barStyle={mode === "dark" ? "light-content" : "dark-content"} />

      <View style={ai.header}>
        <View style={ai.headerRow}>
          <View>
            <Text style={styles.eyebrow}>PocketPilot AI</Text>
            <Text style={styles.title}>Assistant</Text>
          </View>

          {messages.length > 0 && (
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

      </View>

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
    </SafeAreaView>
  );
}
