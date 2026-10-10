/**
 * Life areas for Donexto. Mail is the only source: these labels classify
 * cases and threads that already came from the user's inbox.
 */

import { cleanDisplayText, stripCssNoise } from "./cleanText.ts";
import { insightArea, insightLine, type MailInsight } from "./insights.ts";

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
  "other",
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
  { id: "other", chip: "a-other" },
];

export function areaChip(area: LifeAreaId): string {
  return LIFE_AREAS.find((meta) => meta.id === area)?.chip ?? "a-other";
}

/**
 * Deterministic vocabulary per area (es/en/fr/it/pt). Terms are written
 * lowercase without accents. A trailing `*` matches a word stem; every other
 * term must match a whole word or phrase, so "sat" never matches "saturday"
 * and "order" never matches "border".
 */
const AREA_TERMS: Record<Exclude<LifeAreaId, "other">, string[]> = {
  security: [
    "inicio de sesion", "sign-in", "sign in", "signin", "new login", "nuevo acceso",
    "nuevo dispositivo", "new device", "password", "contrasena", "verification code",
    "codigo de verificacion", "codigo de seguridad", "security code", "security alert",
    "alerta de seguridad", "2fa", "suspicious", "sospechos*", "inusual", "unusual",
    "fraude", "fraud*", "mot de passe", "senha", "accesso sospetto", "nouvelle connexion",
    // Third-party app access to the account ("Permitiste que … acceda a … tu Cuenta de Google").
    "permitiste que", "acceda a algunos de los datos", "acceso a tu cuenta", "you allowed",
    "granted access", "has access to your google account", "access to your google account",
    "third-party access", "acceso de terceros", "vous avez autorise", "hai consentito", "voce permitiu",
    "correo de recuperacion", "recovery email",
  ],
  travel: [
    "vuelo*", "flight*", "check-in", "boarding", "pase de abordar", "embarque",
    "aeromexico", "united airlines", "united.com", "delta", "american airlines",
    "volaris", "viva aerobus", "hotel*", "airbnb", "booking.com", "expedia",
    "reservacion", "itinerar*", "volo", "voo", "voyage", "viaggio", "viagem",
  ],
  orders: [
    "pedido*", "order", "orders", "tu orden", "enviado", "shipped", "shipping", "envio",
    "entrega*", "delivered", "delivery", "out for delivery", "tracking", "rastreo",
    "amazon", "mercado libre", "mercadolibre", "walmart", "ups", "dhl", "fedex",
    "estafeta", "paquete*", "package", "commande", "livraison", "ordine", "spedizion*",
    "encomenda",
  ],
  subscriptions: [
    "suscripci*", "subscription*", "netflix", "spotify", "disney+", "hbo", "apple music",
    "youtube premium", "prime video", "renueva*", "renovacion", "renew*", "auto-renew",
    "plan mensual", "monthly plan", "membership", "membresia", "abonnement",
    "abbonamento", "assinatura",
  ],
  health: [
    "cita medica", "appointment", "hospital", "clinica", "clinic", "kaiser", "imss",
    "issste", "receta", "prescription", "laboratorio", "lab results", "dental", "dentista",
    "medic*", "salud", "health", "farmacia", "pharmacy", "vacuna*", "vaccin*", "sante",
    "salute", "saude",
  ],
  bills: [
    "factura*", "invoice*", "cfdi", "cfe", "con edison", "recibo*", "utility", "utilities",
    "vence", "vencimiento", "due date", "payment due", "fecha limite", "estado de cuenta",
    "statement", "telmex", "izzi", "totalplay", "recibo de luz", "recibo de agua",
    "facture", "fattura", "fatura", "bolleta",
  ],
  government: [
    "sat", "irs", "impuesto*", "tax", "taxes", "gobierno", "government", "tramite*",
    "gob.mx", ".gov", "declaracion anual", "declaracion mensual", "curp", "rfc",
    "pasaporte", "passport", "multa*", "impots", "tasse", "imposto*",
  ],
  insurance: [
    "seguro", "seguro de", "seguros", "insurance", "poliza*", "policy number", "deducible",
    "deductible", "aseguradora", "gnp", "axa", "mapfre", "qualitas", "metlife",
    "assurance", "assicurazion*", "apolice",
  ],
  education: [
    "colegiatura*", "tuition", "escuela", "school", "universidad", "university",
    "college", "inscripcion", "enrollment", "calificaciones", "grades", "curso",
    "course", "ecole", "scuola", "escola",
  ],
  home: [
    "familia", "family", "renta", "rent", "hogar", "elementary", "fotos escolares",
    "guarderia", "daycare", "condominio", "mantenimiento", "mascota*", "veterinari*",
    "famille", "famiglia",
  ],
  social: [
    "linkedin", "instagram", "facebook", "tiktok", "seguidor*", "follower*", "twitter",
    "whatsapp", "commented", "mentioned you",
  ],
  events: [
    "concierto", "concert", "boleto*", "tickets", "ticketmaster", "evento*", "event",
    "eventbrite", "invitacion", "invitation", "rsvp", "boda", "wedding", "webinar",
    "conferencia",
  ],
  promos: [
    "oferta*", "% off", "descuento*", "promo*", "sale", "hot sale", "black friday",
    "cyber monday", "cupon", "coupon", "newsletter", "unsubscribe", "boletin",
  ],
  money: [
    "pago*", "payment*", "cargo", "charge", "charged", "deposito", "deposit",
    "transferencia", "transfer", "spei", "paypal", "chase", "bbva", "banamex",
    "santander", "banorte", "hsbc", "banco", "bank", "reembolso", "refund*", "retiro",
    "withdrawal", "zelle", "venmo", "mercado pago", "virement", "bonifico",
  ],
  work: [
    "nomina", "payroll", "reunion", "meeting", "contrato", "contract", "cotizacion",
    "quotation", "cliente", "client", "proyecto", "project", "propuesta", "proposal",
    "entrevista", "interview",
  ],
};

/** Tie-break order: the most consequential area wins an equal score. */
export const AREA_PRIORITY: Array<Exclude<LifeAreaId, "other">> = [
  "security",
  "travel",
  "government",
  "health",
  "insurance",
  "education",
  "bills",
  "subscriptions",
  "orders",
  "home",
  "events",
  "work",
  "money",
  "social",
  "promos",
];

const CASE_TYPE_AREA: Record<string, { area: LifeAreaId; weight: number }> = {
  invoice: { area: "bills", weight: 1 },
  payment: { area: "money", weight: 0.5 },
  quotation: { area: "work", weight: 0.5 },
  meeting: { area: "work", weight: 0.5 },
  document: { area: "work", weight: 0.5 },
  support: { area: "work", weight: 0.5 },
};

/** Lowercase and strip accents so "Contraseña" matches "contrasena". */
export function foldText(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

const TERM_CACHE = new Map<string, RegExp>();

function termPattern(term: string): RegExp {
  const cached = TERM_CACHE.get(term);
  if (cached) return cached;
  const stem = term.endsWith("*");
  const body = stem ? term.slice(0, -1) : term;
  const lead = /^[a-z0-9]/.test(body) ? "(?:^|[^a-z0-9])" : "";
  const tail = !stem && /[a-z0-9]$/.test(body) ? "(?=$|[^a-z0-9])" : "";
  const pattern = new RegExp(`${lead}${escapeRegExp(body)}${tail}`);
  TERM_CACHE.set(term, pattern);
  return pattern;
}

/** True when the folded text contains the term as a word, phrase or stem. */
export function hasTerm(folded: string, term: string): boolean {
  return termPattern(term).test(folded);
}

/**
 * "Seguro" is also the Spanish adjective "safe/sure" ("pago seguro",
 * "¿estás seguro?"). Drop that adjective before scoring so only the noun
 * (an insurance policy) counts. Other words in the phrase are kept.
 */
const SEGURO_ADJECTIVE =
  /(^|[^a-z0-9])(pago|pagos|compra|compras|sitio|conexion|enlace|acceso|entorno|lugar|metodo|estas|estoy|esta|es|sea|muy|mas|totalmente|100%)\s+segur[oa]s?(?=$|[^a-z0-9])/g;
const SEGURO_THAT = /(^|[^a-z0-9])segur[oa]s?\s+que(?=$|[^a-z0-9])/g;

export function neutralizeFalseFriends(folded: string): string {
  return folded.replace(SEGURO_ADJECTIVE, "$1$2").replace(SEGURO_THAT, "$1");
}

export function areaScores(
  text: string,
  caseType?: string | null,
): Partial<Record<LifeAreaId, number>> {
  const folded = neutralizeFalseFriends(foldText(text));
  const scores: Partial<Record<LifeAreaId, number>> = {};
  for (const area of AREA_PRIORITY) {
    const hits = AREA_TERMS[area].filter((term) => hasTerm(folded, term)).length;
    if (hits > 0) scores[area] = hits;
  }
  const hint = caseType ? CASE_TYPE_AREA[caseType] : undefined;
  if (hint) scores[hint.area] = (scores[hint.area] ?? 0) + hint.weight;
  return scores;
}

export type ClassifiedText = {
  area: LifeAreaId;
  refund: boolean;
  priceIncrease: boolean;
};

export function classifyText(
  text: string,
  caseType?: string | null,
): ClassifiedText {
  const folded = foldText(text);
  const refund = /reembols|refund|devoluci|rembours|rimbors/.test(folded);
  const priceIncrease =
    /sube a|subi[oó]|aumento de precio|aumenta|price increase|increase|nuevo precio|new price|went up|ahora \$|augmentation|aumentou|aumento del prezzo/.test(
      folded,
    );

  const scores = areaScores(text, caseType);
  let best: LifeAreaId | null = null;
  let bestScore = 0;
  for (const area of AREA_PRIORITY) {
    const score = scores[area] ?? 0;
    if (score > bestScore) {
      best = area;
      bestScore = score;
    }
  }
  return { area: best ?? "other", refund, priceIncrease };
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
  /** Backend mail insight of the case's primary email (read-only, computed on the fly). */
  insight?: MailInsight | null;
};

export type InboxThread = {
  latest_message_id: string;
  subject: string | null;
  summary: string | null;
  sender: string | null;
  latest_received_at: string | null;
  triage_category: string | null;
  insight?: MailInsight | null;
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
  /** Cleaned preview/summary text from the backend (entity extraction). */
  preview?: string | null;
  /** Sender address (brand detection for plain-language headlines). */
  senderEmail?: string | null;
  /** Original email subject, kept as secondary text under the headline. */
  subject?: string;
  /** Event type detected by `explain.ts` (security alert, order shipped…). */
  kind?: string;
  /** Backend insight (main idea + exact quotes). Its area/kind win over keywords. */
  insight?: MailInsight | null;
  /** Avisos del mismo evento unidos en este (grouping.ts). */
  groupCount?: number;
  groupIds?: string[];
  groupCaseIds?: string[];
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
  const items: LifeItem[] = cases.map((raw) => {
    // Titles/summaries built from HTML mail can carry raw CSS (stored cases
    // included); clean them before anything is classified or displayed.
    const summary = stripCssNoise(raw.summary) || null;
    const item: InboxCase = {
      ...raw,
      title: cleanDisplayText(raw.title, summary || senderLabel(raw.requester_name, raw.requester_email) || "—"),
      summary,
      requested_action: stripCssNoise(raw.requested_action) || null,
    };
    const blob = [item.title, item.summary, item.requested_action, item.requester_email]
      .filter(Boolean)
      .join(" ");
    const classified = classifyText(blob, item.case_type);
    const insight = raw.insight ?? null;
    const amounts = parseAmounts([insight?.facts?.amount, blob].filter(Boolean).join(" "));
    const primary = amounts[0] ?? null;
    return {
      id: `case:${item.id}`,
      source: "case",
      caseId: item.id,
      messageId: null,
      title: item.title,
      line: insightLine(insight) || oneLineStatement(item.title, item.summary),
      // The backend event type decides the area (an ISSSTE notice is not
      // Health, a bank card notice is not Orders); keywords are a fallback.
      area: insightArea(insight, classified.area),
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
      senderEmail: item.requester_email,
      preview: insight?.preview || item.summary,
      insight,
    };
  });

  const caseSubjects = new Set(
    items.map((item) => subjectKey(item.title)).filter(Boolean),
  );

  for (const rawThread of threads) {
    const thread: InboxThread = { ...rawThread, summary: stripCssNoise(rawThread.summary) || null };
    const subject = cleanDisplayText(rawThread.subject, "");
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
    const insight = rawThread.insight ?? null;
    const area = insightArea(
      insight,
      thread.triage_category === "promotional" ? "promos" : classified.area,
    );
    const amounts = parseAmounts([insight?.facts?.amount, blob].filter(Boolean).join(" "));
    items.push({
      id: `thread:${thread.latest_message_id}`,
      source: "thread",
      caseId: null,
      messageId: thread.latest_message_id,
      title: subject,
      line: insightLine(insight) || oneLineStatement(subject, thread.summary),
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
      preview: insight?.preview || thread.summary,
      insight,
      senderEmail: thread.sender?.match(/<([^>]+)>/)?.[1] ?? (thread.sender?.includes("@") ? thread.sender : null),
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
  if (item.kind === "verification_code") return "low";
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
