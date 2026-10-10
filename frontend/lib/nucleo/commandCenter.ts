/**
 * "Centro de mando" logic for the Núcleo IA dashboard.
 *
 * Everything here is deterministic and rule-based: it only reorganises the
 * cases and threads Donexto already read from the user's authorised mailbox.
 * No language model, no bank feed, no external call. Money figures are always
 * "movements identified in your mail", never a balance.
 */

import {
  amountsMatch,
  foldText,
  hasTerm,
  isOpenStatus,
  urgencyOf,
  type LifeAreaId,
  type LifeItem,
} from "./lifeAreas.ts";

const HOUR = 36e5;
const DAY = 24 * HOUR;

/** The life areas shown as tiles, in the order the product asked for. */
export const DASHBOARD_AREAS: LifeAreaId[] = [
  "money",
  "orders",
  "subscriptions",
  "work",
  "bills",
  "home",
  "health",
  "travel",
  "security",
  "government",
  "insurance",
  "education",
  "events",
];

export function startOfDay(date: Date): Date {
  const copy = new Date(date.getTime());
  copy.setHours(0, 0, 0, 0);
  return copy;
}

function parseTime(value: string | null | undefined): number | null {
  if (!value) return null;
  const time = new Date(value).getTime();
  return Number.isNaN(time) ? null : time;
}

/** Whole calendar days between today and the due date (0 = today, -1 = yesterday). */
export function dayOffset(iso: string, now = new Date()): number | null {
  const time = parseTime(iso);
  if (time === null) return null;
  const today = startOfDay(now).getTime();
  const target = startOfDay(new Date(time)).getTime();
  return Math.round((target - today) / DAY);
}

export type DueBucket = "overdue" | "today" | "tomorrow" | "week" | "later" | "none";

export function dueBucket(item: Pick<LifeItem, "dueAt">, now = new Date()): DueBucket {
  if (!item.dueAt) return "none";
  const time = parseTime(item.dueAt);
  if (time === null) return "none";
  if (time < now.getTime()) return "overdue";
  const offset = dayOffset(item.dueAt, now) ?? 99;
  if (offset <= 0) return "today";
  if (offset === 1) return "tomorrow";
  if (offset <= 7) return "week";
  return "later";
}

export type Snoozed = (item: LifeItem) => boolean;
const notSnoozed: Snoozed = () => false;

export type UpcomingDay = {
  /** 0 = today, 1 = tomorrow … ; -1 groups everything already overdue. */
  offset: number;
  date: string;
  items: LifeItem[];
};

/**
 * "Próximos vencimientos": open items due within the next `days` days,
 * grouped by calendar day. Recently overdue items (≤ 7 days) come first.
 */
export function upcomingDue(
  items: LifeItem[],
  now = new Date(),
  days = 7,
  snoozed: Snoozed = notSnoozed,
): UpcomingDay[] {
  const limit = startOfDay(now).getTime() + (days + 1) * DAY;
  const oldest = now.getTime() - 7 * DAY;
  const rows = items
    .filter((item) => isOpenStatus(item.status) && !snoozed(item))
    .map((item) => ({ item, time: parseTime(item.dueAt) }))
    .filter((row): row is { item: LifeItem; time: number } =>
      row.time !== null && row.time < limit && row.time >= oldest,
    )
    .sort((left, right) => left.time - right.time);
  const groups = new Map<number, UpcomingDay>();
  for (const row of rows) {
    const overdue = row.time < now.getTime();
    const offset = overdue ? -1 : dayOffset(row.item.dueAt as string, now) ?? 0;
    const group = groups.get(offset) ?? {
      offset,
      date: overdue ? now.toISOString() : new Date(row.time).toISOString(),
      items: [],
    };
    group.items.push(row.item);
    groups.set(offset, group);
  }
  return [...groups.values()].sort((left, right) => left.offset - right.offset);
}

function urgencyRank(item: LifeItem, now: Date): number {
  const urgency = urgencyOf(item, now);
  if (urgency === "high") return 0;
  if (urgency === "med") return 1;
  return 2;
}

/**
 * "Requiere acción hoy": open, not snoozed, and either overdue, due before
 * the end of today, high/critical priority, or a security notice.
 */
export function needsActionToday(
  items: LifeItem[],
  now = new Date(),
  snoozed: Snoozed = notSnoozed,
): LifeItem[] {
  return items
    .filter((item) => isOpenStatus(item.status) && !snoozed(item))
    .filter((item) => {
      const bucket = dueBucket(item, now);
      if (bucket === "overdue" || bucket === "today") return true;
      if (item.priority === "high" || item.priority === "critical") return true;
      return item.area === "security";
    })
    .sort((left, right) => {
      const rank = urgencyRank(left, now) - urgencyRank(right, now);
      if (rank !== 0) return rank;
      const leftDue = parseTime(left.dueAt) ?? Number.MAX_SAFE_INTEGER;
      const rightDue = parseTime(right.dueAt) ?? Number.MAX_SAFE_INTEGER;
      if (leftDue !== rightDue) return leftDue - rightDue;
      return right.when.localeCompare(left.when);
    });
}

export type AlertReason = "security" | "priority" | "priceIncrease" | "rule";

export type RecentAlert = {
  item: LifeItem;
  reason: AlertReason;
};

/** Recent alerts from the last `days` days, newest first. */
export function recentAlerts(
  items: LifeItem[],
  now = new Date(),
  matchesRule: (item: LifeItem) => boolean = () => false,
  days = 7,
): RecentAlert[] {
  const since = now.getTime() - days * DAY;
  const alerts: RecentAlert[] = [];
  for (const item of items) {
    const when = parseTime(item.when);
    if (when === null || when < since) continue;
    if (item.area === "promos") continue;
    let reason: AlertReason | null = null;
    if (item.area === "security" && isOpenStatus(item.status)) reason = "security";
    else if (item.priceIncrease) reason = "priceIncrease";
    else if (matchesRule(item)) reason = "rule";
    else if ((item.priority === "high" || item.priority === "critical") && isOpenStatus(item.status)) reason = "priority";
    if (reason) alerts.push({ item, reason });
  }
  return alerts.sort((left, right) => right.item.when.localeCompare(left.item.when));
}

export type OrderStage = "confirmed" | "shipped" | "delivered" | "cancelled" | "refunded";

/** Rule-based order status from the subject/summary of the order mail. */
export function orderStage(item: Pick<LifeItem, "title" | "line" | "requestedAction" | "refund">): OrderStage {
  const text = foldText([item.title, item.line, item.requestedAction].filter(Boolean).join(" "));
  if (/cancelad|cancelled|canceled|annul|annullat/.test(text)) return "cancelled";
  if (item.refund || /reembols|refund|rembours|rimbors/.test(text)) return "refunded";
  if (/entregad|delivered|livre|consegnat|entregue/.test(text)) return "delivered";
  if (/enviad|shipped|en camino|on the way|out for delivery|en reparto|llega|arriv|expedi|spedit|despachad|in transit|en transito/.test(text)) return "shipped";
  return "confirmed";
}

export const ORDER_STEPS: OrderStage[] = ["confirmed", "shipped", "delivered"];

export type AreaSummary = {
  area: LifeAreaId;
  /** Open items in this area. */
  open: number;
  /** Open items due in the next 7 days (overdue included). */
  dueSoon: number;
  /** Earliest upcoming due item, if any. */
  next: LifeItem | null;
  /** Most recent item in the area (open or not). */
  latest: LifeItem | null;
};

export function summarizeAreas(
  items: LifeItem[],
  now = new Date(),
  snoozed: Snoozed = notSnoozed,
): Record<LifeAreaId, AreaSummary> {
  const result = {} as Record<LifeAreaId, AreaSummary>;
  const horizon = startOfDay(now).getTime() + 8 * DAY;
  for (const item of items) {
    const row = result[item.area] ?? { area: item.area, open: 0, dueSoon: 0, next: null, latest: null };
    if (!row.latest || item.when > row.latest.when) row.latest = item;
    if (isOpenStatus(item.status) && !snoozed(item)) {
      row.open += 1;
      const due = parseTime(item.dueAt);
      if (due !== null && due < horizon) {
        row.dueSoon += 1;
        const nextDue = parseTime(row.next?.dueAt);
        if (due >= now.getTime() && (nextDue === null || due < nextDue)) row.next = item;
      }
    }
    result[item.area] = row;
  }
  return result;
}

export type OrdersSummary = {
  inTransit: number;
  delivered: number;
  latest: { item: LifeItem; stage: OrderStage } | null;
};

export function summarizeOrders(items: LifeItem[], now = new Date(), days = 30): OrdersSummary {
  const since = now.getTime() - days * DAY;
  const orders = items
    .filter((item) => item.area === "orders" && (parseTime(item.when) ?? 0) >= since)
    .sort((left, right) => right.when.localeCompare(left.when));
  let inTransit = 0;
  let delivered = 0;
  for (const item of orders) {
    const stage = orderStage(item);
    if (stage === "delivered") delivered += 1;
    else if (stage === "confirmed" || stage === "shipped") inTransit += 1;
  }
  const open = orders.find((item) => isOpenStatus(item.status)) ?? orders[0] ?? null;
  return { inTransit, delivered, latest: open ? { item: open, stage: orderStage(open) } : null };
}

export type SubscriptionsSummary = {
  renewingSoon: number;
  priceIncreases: number;
  active: number;
};

export function summarizeSubscriptions(items: LifeItem[], now = new Date()): SubscriptionsSummary {
  const horizon = startOfDay(now).getTime() + 8 * DAY;
  const services = new Set<string>();
  let renewingSoon = 0;
  let priceIncreases = 0;
  const since = now.getTime() - 45 * DAY;
  for (const item of items) {
    if (item.area !== "subscriptions") continue;
    if ((parseTime(item.when) ?? 0) < since && !isOpenStatus(item.status)) continue;
    services.add(foldText(item.sender || item.title));
    if (item.priceIncrease && isOpenStatus(item.status)) priceIncreases += 1;
    const due = parseTime(item.dueAt);
    if (isOpenStatus(item.status) && due !== null && due >= now.getTime() && due < horizon) renewingSoon += 1;
  }
  return { renewingSoon, priceIncreases, active: services.size };
}

/* ------------------------------------------------------------------------ */
/* Pregunta a Donexto — local, deterministic search over the user's cases.   */
/* ------------------------------------------------------------------------ */

const AREA_WORDS: Array<{ area: LifeAreaId; terms: string[] }> = [
  { area: "money", terms: ["dinero", "money", "pago*", "payment*", "cargo*", "charge*", "gasto*", "spent", "spend", "movimiento*", "argent", "denaro", "dinheiro", "reembolso*", "refund*"] },
  { area: "orders", terms: ["pedido*", "order*", "paquete*", "package*", "envio*", "shipping", "commande*", "ordini", "ordine", "encomenda*"] },
  { area: "subscriptions", terms: ["suscripci*", "subscription*", "renovaci*", "renewal*", "abonnement*", "abbonament*", "assinatura*"] },
  { area: "work", terms: ["trabajo", "work", "negocio*", "business", "cliente*", "client*", "travail", "lavoro", "trabalho"] },
  { area: "bills", terms: ["factura*", "bill", "bills", "invoice*", "recibo*", "facture*", "fattur*", "fatura*"] },
  { area: "home", terms: ["hogar", "familia", "family", "home", "casa", "famille", "famiglia"] },
  { area: "health", terms: ["salud", "health", "medic*", "cita*", "doctor*", "sante", "salute", "saude"] },
  { area: "travel", terms: ["viaje*", "travel*", "vuelo*", "flight*", "hotel*", "voyage*", "viaggi*", "viage*"] },
  { area: "security", terms: ["seguridad", "security", "contrasena*", "password*", "sesion", "login", "securite", "sicurezza", "seguranca"] },
  { area: "government", terms: ["gobierno", "government", "impuesto*", "tax", "taxes", "sat", "irs", "tramite*", "impots", "tasse", "imposto*"] },
  { area: "insurance", terms: ["seguro", "seguros", "insurance", "poliza*", "assurance", "assicurazion*"] },
  { area: "education", terms: ["educacion", "education", "escuela", "school", "colegiatura*", "universidad", "university", "scuola", "ecole", "escola"] },
  { area: "events", terms: ["evento*", "event*", "concierto*", "concert*", "boleto*", "ticket*", "evenement*", "eventi"] },
];

export type TimeIntent = "today" | "tomorrow" | "week" | "overdue" | "month" | null;

const TIME_WORDS: Array<{ intent: Exclude<TimeIntent, null>; terms: string[] }> = [
  { intent: "overdue", terms: ["vencid*", "overdue", "atrasad*", "late", "en retard", "scadut*"] },
  { intent: "today", terms: ["hoy", "today", "aujourd'hui", "aujourdhui", "oggi", "hoje"] },
  { intent: "tomorrow", terms: ["manana", "tomorrow", "demain", "domani", "amanha"] },
  { intent: "week", terms: ["semana", "week", "7 dias", "7 days", "semaine", "settimana", "proxim*", "upcoming", "vence*", "vencimiento*", "due"] },
  { intent: "month", terms: ["mes", "month", "mois", "mese", "mes"] },
];

const STATUS_WORDS: Array<{ status: "open" | "done"; terms: string[] }> = [
  { status: "open", terms: ["pendiente*", "pending", "abierto*", "open", "por hacer", "en attente", "in sospeso"] },
  { status: "done", terms: ["resuelto*", "hecho*", "done", "resolved", "cerrado*", "closed", "termine*", "risolt*", "resolvid*"] },
];

const QUERY_STOP_WORDS = new Set([
  "que", "cuanto", "cuantos", "cuantas", "como", "para", "con", "los", "las", "una", "uno",
  "unos", "del", "este", "esta", "estos", "mis", "mi", "hay", "tengo", "sobre", "correo",
  "correos", "donde", "cual", "cuales", "algo", "the", "and", "how", "much", "many", "what",
  "did", "this", "that", "my", "in", "on", "is", "are", "about", "any", "mail", "email",
  "do", "have", "i", "de", "el", "la", "en", "y", "o", "a", "al", "me", "por", "un",
  "le", "les", "des", "du", "et", "mon", "mes", "il", "lo", "gli", "di", "e", "o", "os",
  "as", "do", "da", "meu", "minha", "es", "ya", "sus", "su", "tus", "tu", "show", "list",
  "muestra", "muestrame", "dime", "ver", "cual", "cuanta", "cuanta", "son", "fue", "sera", "esta", "estan", "hay", "del", "los", "nos", "les", "quiero", "saber", "favor", "porfa",
]);

export type AskIntent = {
  areas: LifeAreaId[];
  time: TimeIntent;
  status: "open" | "done" | null;
  amount: number | null;
  /** Remaining free-text tokens (folded). */
  terms: string[];
};

function matchAny(folded: string, terms: string[]): boolean {
  return terms.some((term) => hasTerm(folded, term));
}

function tokenConsumed(token: string, groups: string[][]): boolean {
  return groups.some((terms) => terms.some((term) => hasTerm(token, term)));
}

export function parseAsk(query: string): AskIntent {
  const folded = foldText(query)
    .replace(/[¿?¡!;:()"]/g, " ")
    // Keep decimal separators ("58,47", "58.47"); drop other commas/periods.
    .replace(/,(?!\d)|(?<!\d),/g, " ")
    .replace(/\.(?!\d)|(?<!\d)\./g, " ")
    .replace(/\s+/g, " ")
    .trim();
  const areas = AREA_WORDS.filter((entry) => matchAny(folded, entry.terms)).map((entry) => entry.area);
  const time = TIME_WORDS.find((entry) => matchAny(folded, entry.terms))?.intent ?? null;
  const status = STATUS_WORDS.find((entry) => matchAny(folded, entry.terms))?.status ?? null;
  const amount = parseAskAmount(folded);
  const consumed = [
    ...AREA_WORDS.map((entry) => entry.terms),
    ...TIME_WORDS.map((entry) => entry.terms),
    ...STATUS_WORDS.map((entry) => entry.terms),
  ];
  const terms = folded
    .split(" ")
    .filter((token) => token.length > 1 && !QUERY_STOP_WORDS.has(token) && !CURRENCY_WORDS.has(token))
    // Amount-like tokens become the amount filter; plain integers (order or
    // flight numbers such as "1547") stay as free text.
    .filter((token) => !(amount !== null && AMOUNT_TOKEN.test(token) && Number(token.replace(/[^\d.,]/g, "").replace(",", ".")) === amount))
    .filter((token) => !tokenConsumed(token, consumed));
  return { areas, time, status, amount, terms };
}

const CURRENCY_WORDS = new Set([
  "usd", "mxn", "eur", "brl", "dolar", "dolares", "dollar", "dollars", "peso", "pesos",
  "euro", "euros", "reais", "real",
]);
const AMOUNT_TOKEN = /^(?:[$€]|us\$|mx\$)?\d+(?:[.,]\d{1,2})?(?:[$€])?$/;

/**
 * Amount in a question: "$58.47", "58.47", "58,47", "58.47 usd" or
 * "200 pesos". A bare integer without a currency hint is not an amount.
 */
export function parseAskAmount(folded: string): number | null {
  const toNumber = (raw: string) => {
    const value = Number(raw.replace(",", "."));
    return Number.isFinite(value) ? value : null;
  };
  const withSymbol = folded.match(/(?:^|\s)(?:us\$|mx\$|\$|€)\s*(\d+(?:[.,]\d{1,2})?)(?=$|\s)/);
  if (withSymbol) return toNumber(withSymbol[1]);
  const trailingSymbol = folded.match(/(?:^|\s)(\d+(?:[.,]\d{1,2})?)\s*(?:\$|€)(?=$|\s)/);
  if (trailingSymbol) return toNumber(trailingSymbol[1]);
  const withWord = folded.match(/(?:^|\s)(\d+(?:[.,]\d{1,2})?)\s+(usd|mxn|eur|brl|dolar(?:es)?|dollars?|pesos?|euros?|reais)(?=$|\s)/);
  if (withWord) return toNumber(withWord[1]);
  const decimal = folded.match(/(?:^|\s)(\d+[.,]\d{2})(?=$|\s)/);
  if (decimal) return toNumber(decimal[1]);
  return null;
}

function haystack(item: LifeItem): string {
  return foldText([item.title, item.line, item.sender, item.requestedAction, item.amountRaw].filter(Boolean).join(" "));
}

function matchesTime(item: LifeItem, time: TimeIntent, now: Date): boolean {
  if (!time) return true;
  const bucket = dueBucket(item, now);
  if (time === "overdue") return bucket === "overdue" && isOpenStatus(item.status);
  if (time === "today") return bucket === "today" || bucket === "overdue" || dayOffset(item.when, now) === 0;
  if (time === "tomorrow") return bucket === "tomorrow";
  if (time === "week") return bucket === "today" || bucket === "tomorrow" || bucket === "week" || bucket === "overdue";
  // "month": the due date decides when there is one, like the other windows;
  // the received date is only a fallback for items without a due date.
  const reference = bucket === "none" ? item.when : (item.dueAt as string);
  const date = new Date(reference);
  if (Number.isNaN(date.getTime())) return false;
  return date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear();
}

export type AskResult = {
  intent: AskIntent;
  hits: LifeItem[];
  /** True when the question had nothing to search for (only stop words). */
  vague: boolean;
};

/** True when the parsed question has at least one usable criterion. */
export function hasAskCriteria(intent: AskIntent): boolean {
  return (
    intent.areas.length > 0 ||
    intent.time !== null ||
    intent.status !== null ||
    intent.amount !== null ||
    intent.terms.length > 0
  );
}

/**
 * Local "Pregunta a Donexto": parses the question with fixed vocabularies
 * (area, time window, status, amount) and ranks the user's own items.
 */
/** Synonyms so "costo" finds "precio"/"cargo" and "suscripción" finds "membresía". */
const ASK_SYNONYMS: string[][] = [
  ["costo", "precio", "cargo", "cobro", "importe", "monto", "cost", "price", "charge", "prix", "prezzo", "preco"],
  ["suscripcion", "suscripciones", "membresia", "plan", "renovacion", "subscription", "membership", "abonnement", "abbonamento", "assinatura"],
  ["pedido", "orden", "compra", "order", "commande", "ordine", "encomenda"],
  ["factura", "recibo", "invoice", "bill", "cfdi"],
  ["envio", "paquete", "entrega", "rastreo", "shipping", "package", "delivery", "tracking"],
];

/** Term variants: synonyms + stem (accent-insensitive, partial). */
export function termVariants(term: string): string[] {
  const out = new Set([term]);
  for (const group of ASK_SYNONYMS) {
    if (group.some((word) => word === term || (term.length >= 5 && word.startsWith(term.slice(0, 5))))) {
      for (const word of group) out.add(word);
    }
  }
  return [...out];
}

function words(text: string): string[] {
  return text.split(/[^a-z0-9]+/).filter(Boolean);
}

/** Whole-word prefix match only: never a substring inside another word. */
function termHit(text: string, term: string): boolean {
  const list = words(text);
  // The user's own word: plural/singular tolerance ("facturas" ≈ "factura").
  const stem = term.length >= 5 ? term.slice(0, Math.max(4, term.length - 2)) : term;
  if (list.some((word) => word === term || word.startsWith(stem))) return true;
  // Synonyms: the whole synonym, optionally pluralised ("precio" → "precios").
  return termVariants(term)
    .filter((variant) => variant !== term)
    .some((variant) => list.some((word) => word === variant || (variant.length >= 5 && word.startsWith(variant) && word.length - variant.length <= 2)));
}

function runAsk(items: LifeItem[], intent: AskIntent, now: Date): Array<{ item: LifeItem; score: number }> {
  const scored: Array<{ item: LifeItem; score: number }> = [];
  for (const item of items) {
    if (intent.areas.length && !intent.areas.includes(item.area)) continue;
    if (!matchesTime(item, intent.time, now)) continue;
    if (intent.status === "open" && !isOpenStatus(item.status)) continue;
    if (intent.status === "done" && isOpenStatus(item.status)) continue;
    if (intent.amount !== null && (item.amount === null || !amountsMatch(item.amount, intent.amount))) continue;
    const text = haystack(item);
    const title = foldText(item.title);
    let score = 0;
    let missing = 0;
    for (const term of intent.terms) {
      if (termHit(text, term)) score += termHit(title, term) ? 3 : 2;
      else missing += 1;
    }
    const structured = intent.areas.length > 0 || intent.time !== null || intent.status !== null || intent.amount !== null;
    if (intent.terms.length && missing === intent.terms.length) continue;
    if (!structured && missing > 0 && intent.terms.length > 1 && score < 2 * Math.ceil(intent.terms.length / 2)) continue;
    if (isOpenStatus(item.status)) score += 1;
    scored.push({ item, score });
  }
  return scored;
}

export function askLocal(items: LifeItem[], query: string, now = new Date()): AskResult {
  const intent = parseAsk(query);
  // "qué hay", "show me", "?" …: never dump the whole mailbox.
  if (!hasAskCriteria(intent)) return { intent, hits: [], vague: true };
  let scored = runAsk(items, intent, now);
  // An area word ("suscripción") must not hide everything: if the area filter
  // leaves nothing, search all areas, treating the area words as text.
  if (!scored.length && intent.areas.length) {
    const areaTerms = foldText(query)
      .split(/[^a-z0-9]+/)
      // Only the words that triggered the area filter; time/status words stay filters.
      .filter((token) => !intent.terms.includes(token) && AREA_WORDS.some((entry) => matchAny(token, entry.terms)));
    const relaxed: AskIntent = { ...intent, areas: [], terms: [...intent.terms, ...areaTerms] };
    scored = runAsk(items, relaxed, now).filter((row) => row.score > 1);
  }
  scored.sort((left, right) => right.score - left.score || right.item.when.localeCompare(left.item.when));
  return { intent, hits: scored.map((row) => row.item), vague: false };
}

/**
 * The spoken/on-screen summary names at most `max` items and reports the
 * rest as a count, so "4 things need attention" never names only three.
 */
export function summaryParts(lines: Array<string | null | undefined>, total: number, max = 3): { named: string[]; more: number } {
  const named = lines
    .map((line) => (line ?? "").trim())
    .filter(Boolean)
    .slice(0, max)
    // Each item is its own sentence so the joined/spoken line stays readable.
    .map((line) => (/[.!?…]$/.test(line) ? line : `${line}.`));
  return { named, more: Math.max(0, total - named.length) };
}
