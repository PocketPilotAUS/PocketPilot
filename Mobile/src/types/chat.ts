// AI Chat types (same shapes as the /ai/chat and /ai/proposals API)

export type Proposal = {
  id: string;
  kind: "expense" | "income";
  amount: string | number;
  category?: string;
  date?: string;
  year?: number;
  month?: number;
  status: "pending" | "saved" | "dismissed";
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  proposal?: Proposal;
};
