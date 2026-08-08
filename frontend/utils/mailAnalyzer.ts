import type { GmailMessage } from "@/types/mail";
import type {
  MailAnalysis,
  MailAnalysisCategory,
  MailPriority,
} from "@/types/analysis";

type KeywordRule = {
  words: string[];
  weight: number;
};

const HIGH_PRIORITY_RULES: KeywordRule[] = [
  {
    words: [
      "urgente",
      "urgent",
      "inmediato",
      "inmediatamente",
      "immediately",
      "asap",
      "crítico",
      "critical",
      "prioridad alta",
      "high priority",
    ],
    weight: 3,
  },
  {
    words: [
      "vencido",
      "overdue",
      "fecha límite",
      "deadline",
      "último día",
      "last day",
      "hoy",
      "today",
    ],
    weight: 2,
  },
];

const ACTION_RULES: KeywordRule[] = [
  {
    words: [
      "favor de enviar",
      "por favor enviar",
      "please send",
      "please provide",
      "se solicita",
      "solicitamos",
      "necesitamos",
      "we need",
      "required",
      "requerido",
      "favor de revisar",
      "please review",
      "favor de confirmar",
      "please confirm",
      "favor de aprobar",
      "please approve",
    ],
    weight: 2,
  },
  {
    words: [
      "enviar",
      "send",
      "revisar",
      "review",
      "confirmar",
      "confirm",
      "aprobar",
      "approve",
      "completar",
      "complete",
      "firmar",
      "sign",
      "adjuntar",
      "attach",
    ],
    weight: 1,
  },
];

const REPLY_RULES: KeywordRule[] = [
  {
    words: [
      "quedo atento",
      "quedo pendiente",
      "esperamos su respuesta",
      "awaiting your response",
      "please reply",
      "favor de responder",
      "confirme por favor",
      "please confirm",
      "could you",
      "would you",
      "can you",
      "nos confirma",
      "me confirma",
    ],
    weight: 2,
  },
  {
    words: [
      "?",
      "respuesta",
      "reply",
      "confirmación",
      "confirmation",
    ],
    weight: 1,
  },
];

const CATEGORY_KEYWORDS: Record<
  MailAnalysisCategory,
  string[]
> = {
  finance: [
    "pago",
    "payment",
    "factura",
    "invoice",
    "transferencia",
    "transfer",
    "depósito",
    "deposit",
    "presupuesto",
    "budget",
    "monto",
    "amount",
    "cotización",
    "quotation",
  ],
  approval: [
    "aprobación",
    "approval",
    "autorizar",
    "authorize",
    "visto bueno",
    "validación",
    "validation",
    "firma",
    "signature",
  ],
  document: [
    "documento",
    "document",
    "archivo",
    "file",
    "adjunto",
    "attached",
    "contrato",
    "contract",
    "oficio",
    "reporte",
    "report",
  ],
  meeting: [
    "reunión",
    "meeting",
    "junta",
    "videollamada",
    "video call",
    "agenda",
    "calendar",
    "cita",
    "appointment",
  ],
  support: [
    "soporte",
    "support",
    "error",
    "problema",
    "issue",
    "incidente",
    "incident",
    "acceso",
    "access",
    "contraseña",
    "password",
  ],
  commercial: [
    "propuesta",
    "proposal",
    "venta",
    "sales",
    "cliente",
    "customer",
    "servicio",
    "service",
    "producto",
    "product",
    "oferta",
    "offer",
  ],
  general: [],
};

const DEADLINE_PATTERNS: RegExp[] = [
  /\b(?:antes del|para el|fecha límite|vence el)\s+(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b/i,
  /\b(?:before|by|deadline)\s+(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b/i,
  /\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b/i,
  /\b(?:hoy|today)\b/i,
  /\b(?:mañana|tomorrow)\b/i,
  /\b(?:lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)\b/i,
  /\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b/i,
];

function normalizeText(value: string): string {
  return value
    .toLocaleLowerCase("es-MX")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function getMessageText(message: GmailMessage): string {
  return normalizeText(
    [
      message.subject,
      message.sender,
      message.sender_email ?? "",
      message.snippet,
    ].join(" "),
  );
}

function countRuleMatches(
  text: string,
  rules: KeywordRule[],
): number {
  return rules.reduce((total, rule) => {
    const matches = rule.words.filter((word) =>
      text.includes(normalizeText(word)),
    );

    return total + matches.length * rule.weight;
  }, 0);
}

function extractKeywords(text: string): string[] {
  const allKeywords = [
    ...HIGH_PRIORITY_RULES.flatMap((rule) => rule.words),
    ...ACTION_RULES.flatMap((rule) => rule.words),
    ...REPLY_RULES.flatMap((rule) => rule.words),
    ...Object.values(CATEGORY_KEYWORDS).flat(),
  ];

  const detected = allKeywords.filter((keyword) =>
    text.includes(normalizeText(keyword)),
  );

  return Array.from(
    new Set(detected.map((keyword) => normalizeText(keyword))),
  ).slice(0, 10);
}

function detectCategory(
  text: string,
): MailAnalysisCategory {
  let selectedCategory: MailAnalysisCategory = "general";
  let highestScore = 0;

  for (const [category, keywords] of Object.entries(
    CATEGORY_KEYWORDS,
  ) as Array<[MailAnalysisCategory, string[]]>) {
    const score = keywords.reduce((total, keyword) => {
      return text.includes(normalizeText(keyword))
        ? total + 1
        : total;
    }, 0);

    if (score > highestScore) {
      selectedCategory = category;
      highestScore = score;
    }
  }

  return selectedCategory;
}

function detectDeadline(text: string): string | null {
  for (const pattern of DEADLINE_PATTERNS) {
    const match = text.match(pattern);

    if (match) {
      return match[1] ?? match[0];
    }
  }

  return null;
}

function detectPriority(
  text: string,
  requiresAction: boolean,
  requiresReply: boolean,
  hasDeadline: boolean,
): MailPriority {
  let score = countRuleMatches(text, HIGH_PRIORITY_RULES);

  if (requiresAction) {
    score += 1;
  }

  if (requiresReply) {
    score += 1;
  }

  if (hasDeadline) {
    score += 2;
  }

  if (score >= 5) {
    return "high";
  }

  if (score >= 2) {
    return "medium";
  }

  return "low";
}

function createSummary(message: GmailMessage): string {
  const subject = message.subject?.trim();
  const snippet = message.snippet?.trim();

  if (subject && snippet) {
    return `${subject}: ${snippet}`.slice(0, 220);
  }

  if (subject) {
    return subject.slice(0, 220);
  }

  if (snippet) {
    return snippet.slice(0, 220);
  }

  return "Correo sin asunto ni vista previa disponible.";
}

function calculateConfidence(
  keywordCount: number,
  requiresAction: boolean,
  requiresReply: boolean,
  hasDeadline: boolean,
): number {
  let confidence = 0.45;

  confidence += Math.min(keywordCount * 0.05, 0.25);

  if (requiresAction) {
    confidence += 0.1;
  }

  if (requiresReply) {
    confidence += 0.1;
  }

  if (hasDeadline) {
    confidence += 0.1;
  }

  return Math.min(Number(confidence.toFixed(2)), 0.98);
}

export function analyzeMail(
  message: GmailMessage,
): MailAnalysis {
  const text = getMessageText(message);

  const actionScore = countRuleMatches(text, ACTION_RULES);
  const replyScore = countRuleMatches(text, REPLY_RULES);

  const requiresAction = actionScore > 0;
  const requiresReply =
    replyScore > 0 || message.subject.includes("?");

  const deadline = detectDeadline(text);
  const hasDeadline = deadline !== null;

  const keywords = extractKeywords(text);
  const category = detectCategory(text);

  const priority = detectPriority(
    text,
    requiresAction,
    requiresReply,
    hasDeadline,
  );

  const confidence = calculateConfidence(
    keywords.length,
    requiresAction,
    requiresReply,
    hasDeadline,
  );

  return {
    messageId: message.id,
    priority,
    requiresReply,
    requiresAction,
    hasDeadline,
    deadline,
    confidence,
    category,
    summary: createSummary(message),
    keywords,
  };
}

export function analyzeMails(
  messages: GmailMessage[],
): MailAnalysis[] {
  return messages.map(analyzeMail);
}