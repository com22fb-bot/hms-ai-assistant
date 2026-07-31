export type CaseStatus =
  | "new"
  | "analyzing"
  | "in_progress"
  | "delegated"
  | "waiting_internal"
  | "waiting_external"
  | "resolved"
  | "closed"
  | "archived";

export type CasePriority =
  | "low"
  | "normal"
  | "high"
  | "critical";

export type IntelligentCase = {
  id: string;
  title: string;
  case_type: string;
  status: CaseStatus;
  priority: CasePriority;
  risk_score: number;
  confidence: number;
  summary: string | null;
  requested_action: string | null;
  requester_name: string | null;
  requester_email: string | null;
  current_owner_email: string | null;
  waiting_on: "internal" | "external" | "none";
  opened_at: string;
  last_activity_at: string;
  due_at: string | null;
  resolved_at: string | null;
  source_count: number;
  reminder_count: number;
};

export type CaseEvent = {
  id: string;
  case_id: string;
  message_id: string | null;
  event_type: string;
  level: number;
  title: string;
  description: string | null;
  actor_type: string;
  actor_identifier: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type CaseDashboardMetrics = {
  total_open: number;
  critical: number;
  waiting_internal: number;
  waiting_external: number;
  overdue: number;
  resolved_today: number;
  unread_notifications: number;
};

export type CaseDashboardResponse = {
  status: string;
  metrics: CaseDashboardMetrics;
  attention: IntelligentCase[];
  recent_events: CaseEvent[];
};

export type CaseProcessResponse = {
  status: string;
  account_id: string;
  requested_limit: number;
  found: number;
  processed: number;
  created_cases: number;
  linked_to_existing: number;
  errors: number;
  error_details: Array<{
    message_id: string;
    error: string;
  }>;
};
