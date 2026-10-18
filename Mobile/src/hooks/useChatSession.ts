import { acceptReviewedPlan, rejectReviewedPlan } from "../services/planningService";
import type { FinancialPlan, PlanningProfile } from "../types/plans";
import { useEffect, useRef, useState } from "react";
import { apiFetch, SessionExpiredError } from "../services/apiClient";
import type { ChatMessage, Proposal, BudgetGoal, BudgetChoice } from "../types/chat";
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
  const [rejectingPlan, setRejectingPlan] = useState<number | null>(null);
  const planLock = useRef(false);
  const budgetChoices = useRef<{ protected: string[]; targets: Record<string, number>; fingerprint?: string }>({ protected: [], targets: {} });
  const controller = useRef<AbortController | null>(null);
  const mounted = useRef(true);
  const sending = useRef(false);
  const epoch = useRef(0);
  const reset = () => {
    budgetChoices.current = { protected: [], targets: {} };
    epoch.current += 1;
    controller.current?.abort();
    sending.current = false;
    planLock.current = false; setSavingPlan(null); setRejectingPlan(null);
    onMessagesChange([]); setDraft(""); setBusy(false); setPendingQuestion(null); setError(null);
  };
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; epoch.current += 1; controller.current?.abort(); };
  }, []);
  // Same request as before: recent history (within the backend's limits),
  // with each record's status attached for the AI's context
  const send = async (question: string, reviewBudget?: { year: number; month: number }, budgetChoice?: BudgetChoice, resumeBudgetGoal = false) => {
    if (sending.current || planLock.current || !question.trim()) return;

    if (question.trim().length > 16000) {
      setError({ title: "Message too long", message: "Keep your question under 16,000 characters.", retry: false });
      return;
    }
    if (budgetChoice) {
      if (budgetChoices.current.fingerprint !== budgetChoice.fingerprint) budgetChoices.current.targets = {};
      budgetChoices.current.fingerprint = budgetChoice.fingerprint;
      if (budgetChoice.target === null) {
        budgetChoices.current.protected = [...new Set([...budgetChoices.current.protected, budgetChoice.category])];
        delete budgetChoices.current.targets[budgetChoice.category];
      } else {
        budgetChoices.current.protected = budgetChoices.current.protected.filter(name => name !== budgetChoice.category);
        budgetChoices.current.targets[budgetChoice.category] = budgetChoice.target;
      }
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
          goal_planning: !!budgetChoice || !![...messages].reverse().find(message => message.role === "assistant")?.goalPlanning,
          require_budget: true,
          plan_review_ids: [...new Set(messages.flatMap(message => message.plan?.reviewId ? [message.plan.reviewId] : []))].slice(-100),
          proposal_ids: [...new Set(messages.flatMap(message => message.proposal ? [message.proposal.id] : []))].slice(-100),
          active_proposal_id: [...messages].reverse().find(message => message.proposal)?.proposal?.id,
          record_state: [...messages].reverse().find(message => message.role === "assistant")?.recordState,
          debt_state: [...messages].reverse().find(message => message.role === "assistant")?.debtState,
          budget_draft_fingerprint: [...messages].reverse().find(message => message.plan?.budgetGoalSource)?.plan?.draftFingerprint,
          budget_draft_status: (() => { const message = [...messages].reverse().find(item => item.plan?.budgetGoalSource); return message ? message.plan!.id ? "saved" : message.planDeclined ? "declined" : "draft" : undefined; })(),
          resume_budget_goal: resumeBudgetGoal,
          budget_choices: budgetChoices.current,
          language: getRuntimeLanguage(),
          currency: selectedCurrency.currency,
          ...(selectedCurrency.currency === "CNY" ? { aed_to_cny: selectedCurrency.rate!.aedToCny } : {}),
          ...(reviewBudget ? { review_budget: reviewBudget } : {}),
          planning_profile: [...messages].reverse().find(message => message.role === "assistant")?.planningProfile ?? [...messages].reverse().find(message => message.role === "assistant")?.plan?.profile,
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

      const data: { reply: string; plan_updates?: { review_id: string; status: FinancialPlan["reviewStatus"]; plan?: FinancialPlan }[]; proposal_updates?: { id: string; status: Proposal["status"] }[]; proposal?: Proposal | null; plan?: FinancialPlan | null; planning_profile?: PlanningProfile | null; goal_planning?: boolean; budget_required?: boolean; budget_goal?: BudgetGoal | null; debt_state?: string | null; record_state?: string | null; debt_phase?: string } = await response.json();

      if (typeof data.reply !== "string" || !data.reply.trim()) {
        throw Object.assign(new Error("Could not send your message. Please try again."), { status: 0 });
      }

      if (mounted.current && epoch.current === generation) {
        if (!data.goal_planning && !data.budget_goal) budgetChoices.current = { protected: [], targets: {} };
        onMessagesChange(current => [...current.map(message => {
          const planUpdate = data.plan_updates?.find(item => item.review_id === message.plan?.reviewId);
          if (planUpdate && message.plan) return { ...message, plan: planUpdate.plan ?? { ...message.plan, reviewStatus: planUpdate.status },
            planDeclined: planUpdate.status === "rejected" || planUpdate.status === "expired" };
          const update = data.proposal_updates?.find(item => item.id === message.proposal?.id);
          return update && message.proposal ? { ...message, proposal: { ...message.proposal, status: update.status } } : message;
        }), pending, { role: "assistant", content: data.reply, proposal: data.proposal ?? undefined, plan: data.plan ?? undefined, planningProfile: data.planning_profile ?? undefined, goalPlanning: data.goal_planning, budgetRequired: data.budget_required, budgetGoal: data.budget_goal ?? undefined, debtState: data.debt_state ?? undefined, recordState: data.record_state ?? undefined, debtPhase: data.debt_phase }]);
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

  const saveFinancialPlan = async (plan: FinancialPlan, index: number, applyToBudget?: boolean) => {
    if (planLock.current || sending.current || plan.id || !plan.ready || plan.reviewStatus === "rejected" || plan.reviewStatus === "expired" || plan.reviewStatus === "saved") return;
    planLock.current = true; setSavingPlan(index); setError(null);
    const generation = epoch.current;
    try {
      const saved = await acceptReviewedPlan(apiBaseUrl, plan, applyToBudget);
      if (mounted.current && generation === epoch.current) onMessagesChange(current => current.map((message, i) => i === index ? { ...message, plan: saved, debtState: saved.debtState ?? message.debtState, debtPhase: saved.debtGoalSource ? "saved" : message.debtPhase } : message));
    } catch (err) {
      if (mounted.current && generation === epoch.current && !(err instanceof SessionExpiredError)) setError({ title: "Could not save plan", message: (err as Error).message, retry: false });
    } finally {
      if (generation === epoch.current) { planLock.current = false; setSavingPlan(null); }
    }
  };
  const rejectFinancialPlan = async (plan: FinancialPlan, index: number) => {
    if (planLock.current || sending.current || plan.id || !plan.ready) return;
    planLock.current = true; setSavingPlan(index); setRejectingPlan(index); setError(null);
    const generation = epoch.current;
    try {
      const result = await rejectReviewedPlan(apiBaseUrl, plan);
      if (mounted.current && generation === epoch.current) {
        if (result.status === "saved") throw new Error("That Financial Plan was already saved and cannot be rejected.");
        if (result.status !== "rejected" && result.status !== "expired") throw new Error("Could not verify plan rejection. Please retry.");
        const status = result.status;
        onMessagesChange(current => current.map(message => message.plan && message.plan.reviewId === plan.reviewId
          ? { ...message, plan: { ...message.plan, reviewStatus: status }, planDeclined: true,
              debtPhase: message.plan.debtGoalSource ? "declined" : message.debtPhase } : message));
      }
    } catch (err) {
      if (mounted.current && generation === epoch.current && !(err instanceof SessionExpiredError)) setError({ title: "Could not reject plan", message: (err as Error).message, retry: false });
    } finally {
      if (generation === epoch.current) { planLock.current = false; setSavingPlan(null); setRejectingPlan(null); }
    }
  };
  const renderEpoch = epoch.current;
  const addPlanPreview = (plan: FinancialPlan) => {
    if (!mounted.current || renderEpoch !== epoch.current) return;
    onMessagesChange(current => {
      const match = current.findIndex(message => message.plan && JSON.stringify(message.plan.profile) === JSON.stringify(plan.profile));
      if (match >= 0 && plan.id) return current.map((message, i) => i === match ? { ...message, plan, debtState: plan.debtState ?? message.debtState, debtPhase: plan.debtGoalSource ? "saved" : message.debtPhase } : message);
      return [...current, { role: "user", content: "Review my financial plan using the planning form." }, { role: "assistant", content: plan.debtGoalSource ? "Here is your calculated debt plan. Review the payment and deadline before saving." : "Here is your calculated plan. Review the category targets, proposed cuts and any shortfall before saving.", plan, debtState: plan.debtState }];
    });
  };
  return { savingPlan, rejectingPlan, saveFinancialPlan, rejectFinancialPlan, addPlanPreview, messages, onMessagesChange, draft, setDraft, busy, pendingQuestion, error, setError, send, reset };
}
