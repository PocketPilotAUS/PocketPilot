import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView, StatusBar, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import AmbientBackground from "../components/AmbientBackground";
import MetallicGlassButton from "../components/MetallicGlassButton";
import MetallicGlassCard from "../components/MetallicGlassCard";
import { apiFetch, SessionExpiredError } from "../services/apiClient";
import { useAppTheme } from "../theme/ThemeContext";
import { createAIChatStyles } from "../styles/AIChatStyles";

type Proposal = { id: string; kind: "expense" | "income"; amount: string | number; category?: string; date?: string; year?: number; month?: number; status: "pending" | "saved" | "dismissed" };
export type ChatMessage = { role: "user" | "assistant"; content: string; proposal?: Proposal };
type Props = {
  apiBaseUrl: string; onBack: () => void;
  messages: ChatMessage[]; onMessagesChange: (messages: ChatMessage[]) => void;
};

export default function AIChatScreen({ apiBaseUrl, onBack, messages, onMessagesChange }: Props) {
  const { colors, mode } = useAppTheme();
  const styles = createAIChatStyles(colors);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [savingProposal, setSavingProposal] = useState<string | null>(null);
  const proposalLock = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const mounted = useRef(true);
  const sending = useRef(false);
  const scroll = useRef<ScrollView>(null);
  useEffect(() => {
    mounted.current = true;
    const handleProposal = async (id: string, operation: "confirm" | "dismiss") => {
    if (proposalLock.current || busy) return;
    proposalLock.current = true; setSavingProposal(id); setError("");
    try {
      const response = await apiFetch(apiBaseUrl, `/ai/proposals/${id}/${operation}`, { method: "POST" });
      if (!response.ok) throw new Error("save");
      const data: { status: Proposal["status"] } = await response.json();
      if (mounted.current) onMessagesChange(messages.map(message => message.proposal?.id === id ? { ...message, proposal: { ...message.proposal, status: data.status } } : message));
    } catch (err) { if (mounted.current && !(err instanceof SessionExpiredError)) setError("Could not update this record. Please try again."); }
    finally { proposalLock.current = false; if (mounted.current) setSavingProposal(null); }
  };

  return () => { mounted.current = false; controller.current?.abort(); };
  }, []);

  const send = async (question = draft) => {
    if (sending.current || proposalLock.current || !question.trim()) return;
    sending.current = true;
    setBusy(true);
    setError("");
    const request = new AbortController();
    controller.current = request;
    const timeout = setTimeout(() => request.abort(), 200000);
    // Keep complete user/assistant pairs within the backend's context limit.
    let history = messages.slice(-20);
    while (history.reduce((sum, item) => sum + item.content.length, 0) + question.trim().length > 24000) history = history.slice(2);
    const pending: ChatMessage = { role: "user", content: question.trim() };
    try {
      const response = await apiFetch(apiBaseUrl, "/ai/chat", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: [...history, pending].map(({ role, content, ...rest }) => ({ role, content: content + (rest.proposal ? `\n[Record status: ${rest.proposal.status}; details: ${JSON.stringify(rest.proposal)}]` : "") })) }), signal: request.signal,
      });
      if (!response.ok) {
        const failure: { detail?: string } = await response.json().catch(() => ({}));
        const detail = typeof failure.detail === "string" ? failure.detail : "Could not send your message. Please try again.";
        throw new Error(`Chat error: ${detail}`);
      }
      const data: { reply: string; proposal?: Proposal | null } = await response.json();
      if (typeof data.reply !== "string" || !data.reply.trim()) throw new Error("Could not send your message. Please try again.");
      if (mounted.current) {
        onMessagesChange([...messages, pending, { role: "assistant", content: data.reply, proposal: data.proposal ?? undefined }]);
        setDraft("");
      }
    } catch (err) {
      if (!mounted.current || err instanceof SessionExpiredError) return;
      setDraft(question);
      setError(request.signal.aborted ? "The reply took too long. Your message is kept below so you can retry." : err instanceof Error && (err.message.startsWith("Chat error:") || err.message.startsWith("Could not send")) ? err.message.replace(/^Chat error: /, "") : "Could not connect. Your message is kept below so you can retry.");
    } finally {
      clearTimeout(timeout);
      sending.current = false;
      if (mounted.current) setBusy(false);
    }
  };

  const handleProposal = async (id: string, operation: "confirm" | "dismiss") => {
    if (proposalLock.current || busy) return;
    proposalLock.current = true; setSavingProposal(id); setError("");
    try {
      const response = await apiFetch(apiBaseUrl, `/ai/proposals/${id}/${operation}`, { method: "POST" });
      if (!response.ok) throw new Error("save");
      const data: { status: Proposal["status"] } = await response.json();
      if (mounted.current) onMessagesChange(messages.map(message => message.proposal?.id === id ? { ...message, proposal: { ...message.proposal, status: data.status } } : message));
    } catch (err) { if (mounted.current && !(err instanceof SessionExpiredError)) setError("Could not update this record. Please try again."); }
    finally { proposalLock.current = false; if (mounted.current) setSavingProposal(null); }
  };

  return (
    <SafeAreaView style={styles.container} edges={["top", "left", "right"]}>
      <StatusBar barStyle={mode === "dark" ? "light-content" : "dark-content"} />
      <AmbientBackground />
      <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === "ios" ? "padding" : "height"}>
        <View style={styles.header}>
          <Text style={styles.title}>AI Chat</Text>
          <Text style={styles.subtitle}>Talk through your budget, savings and debt using your recorded spending.</Text>
        </View>
        <ScrollView ref={scroll} contentContainerStyle={styles.conversation} keyboardShouldPersistTaps="handled" onContentSizeChange={() => scroll.current?.scrollToEnd({ animated: true })}>
          {messages.length === 0 && !busy && <MetallicGlassCard>
            <Text style={styles.heading}>What would you like help with?</Text>
            <Text style={styles.body}>I can use your recorded expenses. Tell me your income, debts or goals when needed for a personalised plan.</Text>
            {["How should I budget my income?", "Where could I cut my spending?", "Help me make a debt repayment plan."].map(question => <MetallicGlassButton key={question} title={question} variant="secondary" onPress={() => { setDraft(question); void send(question); }} />)}
          </MetallicGlassCard>}
          {messages.map((message, index) => <View key={index} style={[styles.bubble, message.role === "user" ? styles.userBubble : styles.assistantBubble]}>
            <Text style={styles.label}>{message.role === "user" ? "YOU" : "POCKETPILOT"}</Text>
            <Text selectable style={styles.message}>{message.content}</Text>
            {message.proposal && <View>
              <Text style={styles.body}>{message.proposal.kind === "expense" ? "Add expense" : "Set monthly income"}: AED {Number(message.proposal.amount).toFixed(2)}</Text>
              <Text style={styles.body}>{message.proposal.kind === "expense" ? `${message.proposal.category} · ${message.proposal.date}` : `${message.proposal.year}-${String(message.proposal.month).padStart(2, "0")} · Replaces income for this month`}</Text>
              {message.proposal.status === "pending" ? <>
                <MetallicGlassButton title={savingProposal === message.proposal.id ? "Saving…" : "Confirm"} onPress={() => { void handleProposal(message.proposal!.id, "confirm"); }} disabled={busy || savingProposal !== null} />
                <MetallicGlassButton title="Dismiss" variant="secondary" onPress={() => { void handleProposal(message.proposal!.id, "dismiss"); }} disabled={busy || savingProposal !== null} />
              </> : <Text style={styles.body}>{message.proposal.status === "saved" ? "Saved to your account" : "Dismissed — nothing saved"}</Text>}
            </View>}
          </View>)}
          {busy && <MetallicGlassCard><ActivityIndicator color={colors.primary} /><Text style={styles.body}>Thinking about your question…</Text><Text style={styles.body}>{draft}</Text></MetallicGlassCard>}
          {!!error && <Text style={styles.error} accessibilityRole="alert">{error}</Text>}
        </ScrollView>
        <View style={styles.composer}>
          <TextInput accessibilityLabel="Message PocketPilot AI" style={styles.input} placeholder="Ask about budgeting, saving or debt…" placeholderTextColor={colors.textMuted} multiline maxLength={4000} value={draft} onChangeText={setDraft} editable={!busy} />
          <MetallicGlassButton title={busy ? "Replying…" : "Send Message"} onPress={() => { void send(); }} disabled={busy || !draft.trim()} />
          <Text style={styles.note}>Conversation kept for this session. Sign out to clear it.</Text>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
