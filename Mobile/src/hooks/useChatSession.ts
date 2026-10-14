import { savePlan } from "../services/planningService";
import type { FinancialPlan, PlanningProfile } from "../types/plans";
import { useEffect, useRef, useState } from "react";
import { apiFetch, SessionExpiredError } from "../services/apiClient";
import type { ChatMessage, Proposal } from "../types/chat";
import { getRuntimeLanguage } from "../preferences/localize";
import { getCurrencyPreference } from "../preferences/currency";
export type ChatError = { title: string; message: string; retry: boolean };

// Owned by the app, not the tab: navigation must not cancel an active reply.
export default function useChatSession(apiBaseUrl: string) {
  const [messages, onMessagesChange] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [error, setError] = useState<ChatError | null>(null);
  const [savingPlan, setSavingPlan] = useState<number | null>(null);
  const planLock = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const mounted = useRef(true);
  const sending = useRef(false);
  const epoch = useRef(0);
  const reset = () => {
    epoch.current += 1;
    controller.current?.abort();
    sending.current = false;
    planLock.current = false; setSavingPlan(null);
    onMessagesChange([]); setDraft(""); setBusy(false); setPendingQuestion(null); setError(null);
  };
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; epoch.current += 1; controller.current?.abort(); };
  }, []);
  // Same request as before: recent history (within the backend's limits),
  // with each record's status attached for the AI's context
  const send = async (question: string, reviewBudget?: { year: number; month: number }) => {
    if (sending.current || planLock.current || !question.trim()) return;

    if (question.trim().length > 16000) {
      setError({ title: "Message too long", message: "Keep your question under 16,000 characters.", retry: false });
      return;
    }
    sending.current = true;
    setBusy(true);
    setError(null);
    setPendingQuestion(question.trim());
    setDraft("");

    const generation = epoch.current;
    const request = new AbortController();
    controller.current = request;
    const timeout = setTimeout(() => request.abort(), 200000);

    // Keep complete user/assistant pairs within the backend's context limit.
    let history = messages.slice(-20);
    while (history.reduce((sum, item) => sum + item.content.length, 0) + question.trim().length > 24000) {
      history = history.slice(2);
    }

    const selectedCurrency = getCurrencyPreference();
    const pending: ChatMessage = { role: "user", content: question.trim(), currency: selectedCurrency.currency };

    try {
      const response = await apiFetch(apiBaseUrl, "/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          language: getRuntimeLanguage(),
          currency: selectedCurrency.currency,
          ...(selectedCurrency.currency === "CNY" ? { aed_to_cny: selectedCurrency.rate!.aedToCny } : {}),
          ...(reviewBudget ? { review_budget: reviewBudget } : {}),
          planning_profile: [...messages].reverse().find(message => message.planningProfile || message.plan)?.planningProfile ?? [...messages].reverse().find(message => message.planningProfile || message.plan)?.plan?.profile,
          messages: [...history, pending].map(({ role, content, ...rest }) => ({
            role,
            content: content + (role === "user" ? `\n[Currency for untagged amounts in this message: ${rest.currency ?? "AED"}]` : "") + (rest.proposal ? `\n[Record status: ${rest.proposal.status}; details: ${JSON.stringify(rest.proposal)}]` : ""),
          })),
        }),
        signal: request.signal,
      });

      if (!response.ok) {
        const failure: { detail?: string } = await response.json().catch(() => ({}));
        const detail = typeof failure.detail === "string" ? failure.detail : "Could not send your message. Please try again.";

        throw Object.assign(new Error(detail), { status: response.status });
      }

      const data: { reply: string; proposal?: Proposal | null; plan?: FinancialPlan | null; planning_profile?: PlanningProfile | null } = await response.json();

      if (typeof data.reply !== "string" || !data.reply.trim()) {
        throw Object.assign(new Error("Could not send your message. Please try again."), { status: 0 });
      }

      if (mounted.current && epoch.current === generation) {
        onMessagesChange(current => [...current, pending, { role: "assistant", content: data.reply, proposal: data.proposal ?? undefined, plan: data.plan ?? undefined, planningProfile: data.planning_profile ?? undefined }]);
      }
    } catch (err) {
      if (!mounted.current || epoch.current !== generation || err instanceof SessionExpiredError) return;

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
      if (epoch.current === generation) sending.current = false;

      if (mounted.current && epoch.current === generation) {
        setBusy(false);
        setPendingQuestion(null);
      }
    }
  };

  const saveFinancialPlan = async (plan: FinancialPlan, index: number) => {
    if (planLock.current || sending.current || plan.id) return;
    planLock.current = true; setSavingPlan(index); setError(null);
    const generation = epoch.current;
    try {
      const saved = await savePlan(apiBaseUrl, plan.profile);
      if (mounted.current && generation === epoch.current) onMessagesChange(current => current.map((message, i) => i === index ? { ...message, plan: saved } : message));
    } catch (err) {
      if (mounted.current && generation === epoch.current && !(err instanceof SessionExpiredError)) setError({ title: "Could not save plan", message: (err as Error).message, retry: false });
    } finally {
      if (generation === epoch.current) { planLock.current = false; setSavingPlan(null); }
    }
  };
  const renderEpoch = epoch.current;
  const addPlanPreview = (plan: FinancialPlan) => {
    if (!mounted.current || renderEpoch !== epoch.current) return;
    onMessagesChange(current => {
      const match = current.findIndex(message => message.plan && JSON.stringify(message.plan.profile) === JSON.stringify(plan.profile));
      if (match >= 0 && plan.id) return current.map((message, i) => i === match ? { ...message, plan } : message);
      return [...current, { role: "user", content: "Review my financial plan using the planning form." }, { role: "assistant", content: "Here is your calculated plan. Review the category targets, proposed cuts and any shortfall before saving.", plan }];
    });
  };
  return { savingPlan, saveFinancialPlan, addPlanPreview, messages, onMessagesChange, draft, setDraft, busy, pendingQuestion, error, setError, send, reset };
}
