export type MailPriority = "high" | "medium" | "low";

export type MailAnalysisCategory =
  | "finance"
  | "approval"
  | "document"
  | "meeting"
  | "support"
  | "commercial"
  | "general";

export type MailAnalysis = {
  messageId: string;
  priority: MailPriority;
  requiresReply: boolean;
  requiresAction: boolean;
  hasDeadline: boolean;
  deadline: string | null;
  confidence: number;
  category: MailAnalysisCategory;
  summary: string;
  keywords: string[];
};

export type MailAnalysisMetrics = {
  total: number;
  highPriority: number;
  requiresReply: number;
  requiresAction: number;
  withDeadline: number;
};