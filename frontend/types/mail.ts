export type GoogleConnectionStatus = {
  status: string;
  connected: boolean;
  email: string | null;
  provider?: string | null;
  has_access_token: boolean;
  has_refresh_token: boolean;
  scopes: string[];
  login_url: string | null;
  message: string | null;
  mail_read_available?: boolean;
};

export type GmailMessage = {
  id: string;
  thread_id: string;
  subject: string;
  sender: string;
  sender_email: string | null;
  recipient: string | null;
  received_at: string | null;
  snippet: string;
  is_unread: boolean;
  labels: string[];
};

export type GmailMessagesResponse = {
  status: string;
  connected: boolean;
  total: number;
  messages: GmailMessage[];
};

export type MailFilter =
  | "all"
  | "unread"
  | "personal"
  | "promotions"
  | "social"
  | "updates";

export type MailFilterOption = {
  id: MailFilter;
  label: string;
};

export type MailCategory = {
  label: string;
  className: string;
};

export const MAIL_FILTERS: MailFilterOption[] = [
  { id: "all", label: "Todos" },
  { id: "unread", label: "No leídos" },
  { id: "personal", label: "Personal" },
  { id: "promotions", label: "Promociones" },
  { id: "social", label: "Social" },
  { id: "updates", label: "Actualizaciones" },
];
