/**
 * Life areas for Donexto. Mail is the only source: these labels classify
 * cases and threads that already came from the user's inbox.
 */

export const LIFE_AREA_IDS = [
  "money",
  "orders",
  "subscriptions",
  "work",
  "home",
  "health",
  "bills",
  "travel",
  "security",
  "government",
  "insurance",
  "education",
  "social",
  "events",
  "promos",
] as const;

export type LifeAreaId = (typeof LIFE_AREA_IDS)[number];

export type LifeAreaMeta = {
  id: LifeAreaId;
  chip: string;
};

export const LIFE_AREAS: LifeAreaMeta[] = [
  { id: "money", chip: "a-money" },
  { id: "orders", chip: "a-orders" },
  { id: "subscriptions", chip: "a-subs" },
  { id: "work", chip: "a-work" },
  { id: "home", chip: "a-home" },
  { id: "health", chip: "a-health" },
  { id: "bills", chip: "a-bills" },
  { id: "travel", chip: "a-travel" },
  { id: "security", chip: "a-security" },
  { id: "government", chip: "a-gov" },
  { id: "insurance", chip: "a-insurance" },
  { id: "education", chip: "a-edu" },
  { id: "social", chip: "a-social" },
  { id: "events", chip: "a-events" },
  { id: "promos", chip: "a-promo" },
];

const AREA_TERMS: Record<LifeAreaId, string[]> = {
  security: [
    "inicio de sesión",
    "inicio de sesion",
    "sign-in",
    "signin",
    "new login",
    "nuevo dispositivo",
    "password",
    "contraseña",
    "contrasena",
    "verification code",
    "código de verificación",
    "codigo de verificacion",
    "2fa",
    "suspicious",
    "inusual",
    "fraude",
    "fraud",
  ],
  travel: [
    "vuelo",
    "flight",
    "check-in",
    "check in",
    "boarding",
    "aeroméxico",
    "aeromexico",
    "united",
    "delta",
    "hotel",
    "airbnb",
    "booking",
    "reservación",
    "reservacion",
    "itinerary",
  ],
  orders: [
    "pedido",
    "order",
    "enviado",
    "shipped",
    "entrega",
    "delivered",
    "tracking",
    "rastreo",
    "amazon",
    "mercado libre",
    "walmart",
    "ups",
    "dhl",
    "fedex",
    "paquete",
  ],
  subscriptions: [
    "suscrip",
    "subscription",
    "netflix",
    "spotify",
    "renueva",
    "renew",
    "plan mensual",
    "membership",
    "membresía",
    "membresia",
  ],
  health: [
    "cita",
    "appointment",
    "hospital",
    "clínica",
    "clinica",
    "kaiser",
    "imss",
    "receta",
    "prescription",
    "laboratorio",
    "dental",
    "médic",
    "medic",
    "salud",
  ],
  bills: [
    "factura",
    "invoice",
    "cfdi",
    "cfe",
    "con edison",
    "recibo",
    "utility",
    "vence",
    "due date",
    "estado de cuenta",
  ],
  government: [
    "sat",
    "irs",
    "impuesto",
    "tax",
    "gobierno",
    "government",
    "trámite",
    "tramite",
  ],
  insurance: [
    "seguro",
    "insurance",
    "póliza",
    "poliza",
    "policy",
    "deducible",
  ],
  education: [
    "colegiatura",
    "tuition",
    "escuela",
    "school",
    "universidad",
    "university",
    "tarea escolar",
  ],
  home: [
    "familia",
    "family",
    "renta",
    "rent",
    "hogar",
    "elementary",
    "fotos escolares",
  ],
  social: [
    "linkedin",
    "instagram",
    "facebook",
    "tiktok",
    "seguidor",
    "follower",
    "twitter",
  ],
  events: [
    "concierto",
    "boleto",
    "ticket",
    "evento",
    "eventbrite",
  ],
  promos: [
    "oferta",
    "% off",
    "descuento",
    "promo",
    "sale",
    "hot sale",
    "black friday",
  ],
  money: [
    "pago",
    "payment",
    "cargo",
    "charge",
    "depósito",
    "deposito",
    "deposit",
    "transfer",
    "spei",
    "paypal",
    "chase",
    "bbva",
    "banamex",
    "banco",
    "bank",
    "reembolso",
    "refund",
  ],
  work: [
    "nómina",
    "nomina",
    "payroll",
    "reunión",
    "reunion",
    "meeting",
    "contrato",
    "cotización",
    "cotizacion",
    "cliente",
  ],
};

const CASE_TYPE_AREA: Record<string, LifeAreaId> = {
  invoice: "bills",
  payment: "money",
  quotation: "work",
  meeting: "work",
  document: "work",
  support: "work",
};

export type ClassifiedText = {
  area: LifeAreaId;
  refund: boolean;
  priceIncrease: boolean;
};

export function classifyText(
  text: string,
  caseType?: string | null,
): ClassifiedText {
  const normalized = text.toLowerCase();
  const refund = /reembolso|refund|devoluci[oó]n/.test(normalized);
  const priceIncrease =
    /sube a|subi[oó]|increase|price increase|nuevo precio|went up|ahora \$/.test(
      normalized,
    );

  for (const area of LIFE_AREA_IDS) {
    if (area === "work") continue;
    if (AREA_TERMS[area].some((term) => normalized.includes(term))) {
      return { area, refund, priceIncrease };
    }
  }

  const fromType = caseType ? CASE_TYPE_AREA[caseType] : undefined;
  if (fromType) {
    return { area: fromType, refund, priceIncrease };
  }

  if (AREA_TERMS.work.some((term) => normalized.includes(term))) {
    return { area: "work", refund, priceIncrease };
  }

  if (/unsubscribe|newsletter|boletin|boletín/.test(normalized)) {
    return { area: "promos", refund, priceIncrease };
  }

  return { area: "events", refund, priceIncrease };
}

export function oneLineStatement(
  title: string | null | undefined,
  summary: string | null | undefined,
): string {
  const source = (summary || title || "")
    .replace(/\s+/g, " ")
    .replace(/\b(vs|a\.m|p\.m|sr|sra|dr)\./gi, "$1")
    .trim();
  if (!source) return "";
  const sentence = source.split(/(?<=[.!?])\s+/)[0] ?? source;
  if (sentence.length <= 160) return sentence;
  return `${sentence.slice(0, 157).trimEnd()}…`;
}

export type ParsedAmount = {
  value: number;
  raw: string;
};

export function parseAmounts(text: string): ParsedAmount[] {
  const pattern =
    /(?:US\$|MX\$|USD|MXN|\$|€)\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?|\d+(?:[.,]\d{2})?)|(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:USD|MXN|dólares|dolares|pesos|euros)/gi;
  const found: ParsedAmount[] = [];
  for (const match of text.matchAll(pattern)) {
    const rawNumber = match[1] || match[2];
    if (!rawNumber) continue;
    const value = normalizeAmount(rawNumber);
    if (value === null || value <= 0 || value > 1_000_000) continue;
    found.push({ value, raw: match[0].trim() });
  }
  return found;
}

export function normalizeAmount(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const lastComma = trimmed.lastIndexOf(",");
  const lastDot = trimmed.lastIndexOf(".");
  let normalized = trimmed;
  if (lastComma > lastDot) {
    normalized = trimmed.replace(/\./g, "").replace(",", ".");
  } else {
    normalized = trimmed.replace(/,/g, "");
  }
  const value = Number(normalized);
  return Number.isFinite(value) ? value : null;
}

export function amountsMatch(left: number, right: number): boolean {
  return Math.abs(left - right) < 0.02;
}

const OPEN_STATUSES = new Set([
  "new",
  "analyzing",
  "in_progress",
  "delegated",
  "waiting_internal",
  "waiting_external",
]);

export function isOpenStatus(status: string): boolean {
  return OPEN_STATUSES.has(status);
}

export type InboxCase = {
  id: string;
  title: string;
  case_type: string;
  status: string;
  priority: string;
  summary: string | null;
  requested_action: string | null;
  requester_name: string | null;
  requester_email: string | null;
  last_activity_at: string;
  due_at: string | null;
  source_count: number;
};

export type InboxThread = {
  latest_message_id: string;
  subject: string | null;
  summary: string | null;
  sender: string | null;
  latest_received_at: string | null;
  triage_category: string | null;
};

export type LifeItem = {
  id: string;
  source: "case" | "thread";
  caseId: string | null;
  messageId: string | null;
  title: string;
  line: string;
  area: LifeAreaId;
  sender: string;
  when: string;
  dueAt: string | null;
  status: string;
  priority: string;
  amount: number | null;
  amountRaw: string | null;
  refund: boolean;
  priceIncrease: boolean;
  reconciled: boolean;
  requestedAction: string | null;
  sourceCount: number;
};

function senderLabel(
  name: string | null | undefined,
  email: string | null | undefined,
): string {
  const value = (name || email || "").trim();
  if (!value) return "";
  const angle = value.match(/^(.*?)</);
  return (angle?.[1] || value).replace(/"/g, "").trim();
}

function subjectKey(value: string): string {
  return value
    .toLowerCase()
    .replace(/^\s*((re|rv|fw|fwd)\s*:\s*)+/gi, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function buildLifeItems(
  cases: InboxCase[],
  threads: InboxThread[],
): LifeItem[] {
  const items: LifeItem[] = cases.map((item) => {
    const blob = [item.title, item.summary, item.requested_action, item.requester_email]
      .filter(Boolean)
      .join(" ");
    const classified = classifyText(blob, item.case_type);
    const amounts = parseAmounts(blob);
    const primary = amounts[0] ?? null;
    return {
      id: `case:${item.id}`,
      source: "case",
      caseId: item.id,
      messageId: null,
      title: item.title,
      line: oneLineStatement(item.title, item.summary),
      area: classified.area,
      sender: senderLabel(item.requester_name, item.requester_email),
      when: item.last_activity_at,
      dueAt: item.due_at,
      status: item.status,
      priority: item.priority,
      amount: primary?.value ?? null,
      amountRaw: primary?.raw ?? null,
      refund: classified.refund,
      priceIncrease: classified.priceIncrease,
      reconciled: false,
      requestedAction: item.requested_action,
      sourceCount: item.source_count,
    };
  });

  const caseSubjects = new Set(
    items.map((item) => subjectKey(item.title)).filter(Boolean),
  );

  for (const thread of threads) {
    const subject = (thread.subject || "").trim();
    const key = subjectKey(subject);
    if (!thread.latest_message_id || !key) continue;
    if ([...caseSubjects].some((existing) => existing.includes(key) || key.includes(existing))) {
      continue;
    }
    const blob = [subject, thread.summary, thread.sender].filter(Boolean).join(" ");
    const classified = classifyText(
      blob,
      thread.triage_category === "promotional" ? "promotional" : null,
    );
    const area =
      thread.triage_category === "promotional" ? "promos" : classified.area;
    const amounts = parseAmounts(blob);
    items.push({
      id: `thread:${thread.latest_message_id}`,
      source: "thread",
      caseId: null,
      messageId: thread.latest_message_id,
      title: subject,
      line: oneLineStatement(subject, thread.summary),
      area,
      sender: senderLabel(thread.sender, null),
      when: thread.latest_received_at || new Date(0).toISOString(),
      dueAt: null,
      status: "new",
      priority: "normal",
      amount: amounts[0]?.value ?? null,
      amountRaw: amounts[0]?.raw ?? null,
      refund: classified.refund,
      priceIncrease: classified.priceIncrease,
      reconciled: false,
      requestedAction: null,
      sourceCount: 1,
    });
  }

  return markReconciled(items).sort((left, right) =>
    right.when.localeCompare(left.when),
  );
}

export function markReconciled(items: LifeItem[]): LifeItem[] {
  const next = items.map((item) => ({ ...item, reconciled: false }));
  const charges = next.filter(
    (item) =>
      (item.area === "money" || item.area === "bills") &&
      item.amount !== null &&
      !item.refund,
  );
  const orders = next.filter(
    (item) => item.area === "orders" && item.amount !== null,
  );
  for (const charge of charges) {
    const pair = orders.find(
      (order) =>
        charge.amount !== null &&
        order.amount !== null &&
        amountsMatch(charge.amount, order.amount),
    );
    if (!pair) continue;
    charge.reconciled = true;
    pair.reconciled = true;
  }
  return next;
}

export type MonthMoney = {
  outflows: number;
  refunds: number;
  movements: number;
  subscriptions: number;
  priceIncreases: number;
};

export function monthMoney(items: LifeItem[], now = new Date()): MonthMoney {
  const month = now.getMonth();
  const year = now.getFullYear();
  let outflows = 0;
  let refunds = 0;
  let movements = 0;
  const subs = new Set<string>();
  let priceIncreases = 0;
  for (const item of items) {
    const when = new Date(item.when);
    if (Number.isNaN(when.getTime())) continue;
    if (when.getMonth() !== month || when.getFullYear() !== year) continue;
    if (item.area === "subscriptions") {
      subs.add((item.sender || item.title).toLowerCase());
      if (item.priceIncrease) priceIncreases += 1;
    }
    if (item.amount === null) continue;
    if (
      item.area !== "money" &&
      item.area !== "bills" &&
      item.area !== "orders" &&
      item.area !== "subscriptions"
    ) {
      continue;
    }
    movements += 1;
    if (item.refund) refunds += item.amount;
    else outflows += item.amount;
  }
  return {
    outflows,
    refunds,
    movements,
    subscriptions: subs.size,
    priceIncreases,
  };
}

export type Urgency = "high" | "med" | "low";

export function urgencyOf(item: LifeItem, now = new Date()): Urgency {
  if (item.priority === "critical" || item.priority === "high") return "high";
  if (item.area === "security") return "high";
  if (!item.dueAt) return item.priority === "low" ? "low" : "med";
  const due = new Date(item.dueAt).getTime();
  if (Number.isNaN(due)) return "med";
  const hours = (due - now.getTime()) / 36e5;
  if (hours < 24) return "high";
  if (hours < 72) return "med";
  return "low";
}

export function matchesQuery(item: LifeItem, query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  const tokens = needle
    .split(/\s+/)
    .filter((token) => token.length > 2 && !STOP_WORDS.has(token));
  const haystack = [
    item.title,
    item.line,
    item.sender,
    item.area,
    item.requestedAction,
    item.amountRaw,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  const probes = tokens.length ? tokens : [needle];
  return probes.every((token) => haystack.includes(token));
}

const STOP_WORDS = new Set([
  "que",
  "qué",
  "cuanto",
  "cuánto",
  "como",
  "cómo",
  "para",
  "con",
  "los",
  "las",
  "una",
  "uno",
  "del",
  "este",
  "esta",
  "mes",
  "the",
  "and",
  "how",
  "much",
  "what",
  "did",
  "this",
  "month",
]);
