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

type Props = {
  apiBaseUrl: string;
  onBack: () => void;
  messages: ChatMessage[];
  onMessagesChange: (messages: ChatMessage[]) => void;
};

type Section = "chat" | "plans";

type ChatError = { title: string; message: string; retry: boolean };

const GOAL_PROMPT = "Help me plan how to save for a goal by a specific date.";

export default function AIChatScreen({ apiBaseUrl, messages, onMessagesChange }: Props) {
  const { ai, styles, palette, mode } = useAITheme();

  const [section, setSection] = useState<Section>("chat");
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [error, setError] = useState<ChatError | null>(null);
  const [savingProposal, setSavingProposal] = useState<string | null>(null);

  const proposalLock = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const mounted = useRef(true);
  const sending = useRef(false);
  const scroll = useRef<ScrollView>(null);

  useEffect(() => {
    mounted.current = true;

    return () => {
      mounted.current = false;
      controller.current?.abort();
    };
  }, []);

  // Same request as before: recent history (within the backend's limits),
  // with each record's status attached for the AI's context
  const send = async (question = draft) => {
    if (sending.current || proposalLock.current || !question.trim()) return;

    sending.current = true;
    setBusy(true);
    setError(null);
    setPendingQuestion(question.trim());
    setDraft("");

    const request = new AbortController();
    controller.current = request;
    const timeout = setTimeout(() => request.abort(), 200000);

    // Keep complete user/assistant pairs within the backend's context limit.
    let history = messages.slice(-20);
    while (history.reduce((sum, item) => sum + item.content.length, 0) + question.trim().length > 24000) {
      history = history.slice(2);
    }

    const pending: ChatMessage = { role: "user", content: question.trim() };

    try {
      const response = await apiFetch(apiBaseUrl, "/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [...history, pending].map(({ role, content, ...rest }) => ({
            role,
            content: content + (rest.proposal ? `\n[Record status: ${rest.proposal.status}; details: ${JSON.stringify(rest.proposal)}]` : ""),
          })),
        }),
        signal: request.signal,
      });

      if (!response.ok) {
        const failure: { detail?: string } = await response.json().catch(() => ({}));
        const detail = typeof failure.detail === "string" ? failure.detail : "Could not send your message. Please try again.";

        throw Object.assign(new Error(detail), { status: response.status });
      }

      const data: { reply: string; proposal?: Proposal | null } = await response.json();

      if (typeof data.reply !== "string" || !data.reply.trim()) {
        throw Object.assign(new Error("Could not send your message. Please try again."), { status: 0 });
      }

      if (mounted.current) {
        onMessagesChange([...messages, pending, { role: "assistant", content: data.reply, proposal: data.proposal ?? undefined }]);
      }
    } catch (err) {
      if (!mounted.current || err instanceof SessionExpiredError) return;

      // The message is put back in the box so it can be retried
      setDraft(question);

      const status = (err as { status?: number }).status;

      if (request.signal.aborted) {
        setError({ title: "The reply took too long", message: "Your message is kept below so you can try again.", retry: true });
      } else if (status === 503) {
        setError({
          title: "AI Chat is unavailable right now",
          message: "PocketPilot's AI service isn't responding on the server. Your message is kept below; try again later.",
          retry: true,
        });
      } else if (status !== undefined) {
        setError({ title: "Message not sent", message: (err as Error).message, retry: true });
      } else {
        setError({ title: "Couldn't reach PocketPilot", message: "Check your connection. Your message is kept below so you can try again.", retry: true });
      }
    } finally {
      clearTimeout(timeout);
      sending.current = false;

      if (mounted.current) {
        setBusy(false);
        setPendingQuestion(null);
      }
    }
  };

  // Confirms or dismisses an expense/income the AI proposed (unchanged API)
  const handleProposal = async (id: string, operation: "confirm" | "dismiss") => {
    if (proposalLock.current || busy) return;

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
          onMessagesChange([]);
          setError(null);
          setDraft("");
        },
      },
    ]);
  };

  const startPlanning = () => {
    setSection("chat");
    setDraft(GOAL_PROMPT);
  };

  const canSend = !busy && savingProposal === null && draft.trim().length > 0;
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
          {proposal && (
            <ProposalCard
              proposal={proposal}
              saving={savingProposal === proposal.id}
              disabled={busy || savingProposal !== null}
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
              disabled={busy || savingProposal !== null}
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
                onPress={() => setSection(key)}
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
        // No plan storage exists yet, so there are never any plans to show
        <FinancialPlans plans={[]} onStartPlanning={startPlanning} />
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
