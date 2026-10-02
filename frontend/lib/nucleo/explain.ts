/**
 * Plain-language headlines for cases, in the user's UI language, built with
 * deterministic templates (no AI, no paid service). Each email is mapped to
 * an event type with regular expressions; a few entities (sender brand,
 * amount, order number, flight, app name, email address, date) are pulled
 * out with regex and dropped into a short sentence. The original subject is
 * still shown as secondary text: this is an explanation, not a translation.
 */

import { cleanDisplayText } from "./cleanText.ts";
import type { LifeItem } from "./lifeAreas.ts";

export type ExplainLang = "es" | "en" | "fr" | "it" | "pt";

export type EventKind =
  | "verification_code"
  | "magic_link"
  | "app_access"
  | "recovery_email"
  | "password"
  | "security_copy"
  | "security_alert"
  | "refund"
  | "order_delivered"
  | "order_shipped"
  | "price_increase"
  | "subscription_renewal"
  | "bill_due"
  | "order_placed"
  | "payment"
  | "travel"
  | "meeting"
  | "social_suggest"
  | "social"
  | "welcome"
  | "promo"
  | "unknown";

export type ExplainInput = {
  title: string;
  summary?: string | null;
  sender?: string | null;
  senderEmail?: string | null;
  area?: string | null;
  amountRaw?: string | null;
  dueAt?: string | null;
  priceIncrease?: boolean;
  refund?: boolean;
};

export type ExplainFacts = {
  brand: string;
  amount: string | null;
  order: string | null;
  flight: string | null;
  app: string | null;
  email: string | null;
  date: string | null;
  person: string | null;
  subject: string;
};

export type Explanation = {
  kind: EventKind;
  headline: string;
  facts: ExplainFacts;
};

function fold(text: string): string {
  return text.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

/** Ordered rules: the first match wins (most specific first). */
const RULES: Array<{ kind: EventKind; test: RegExp }> = [
  { kind: "verification_code", test: /(codigo de verificacion|verification code|security code|codigo de seguridad|codigo de acceso|one[- ]time (?:pass(?:word|code)|code)|\botp\b|tu codigo|your code|is your .{0,30}code|es tu codigo|code de verification|code de securite|codice di verifica|codice di sicurezza|codigo de verificacao)/ },
  { kind: "magic_link", test: /(link to (?:sign|log) ?in|sign[- ]?in link|log[- ]?in link|magic link|enlace (?:para|de) (?:iniciar sesion|acceso|inicio de sesion|entrar)|inicia sesion con este enlace|lien de connexion|link di accesso|link de acesso)/ },
  { kind: "app_access", test: /(permitiste que|you allowed|you gave .{1,60} access|granted access|now has access to your|has access to your (?:google )?account|tiene acceso a (?:algunos (?:de los )?datos|tu cuenta)|acceda a algunos de los datos|vous avez autorise|hai consentito|hai autorizzato|voce permitiu|você permitiu)/ },
  { kind: "recovery_email", test: /(correo (?:electronico )?de recuperacion|recovery e-?mail|e-?mail de recuperacao|adresse (?:e-mail )?de recuperation|e-?mail di recupero)/ },
  { kind: "password", test: /(restablec\w* (?:tu |la |su )?contrasena|cambio de contrasena|contrasena (?:se ha )?(?:cambiado|actualizado)|reset (?:your )?password|password (?:reset|changed|was changed|updated)|mot de passe (?:modifie|reinitialis\w*)|password modificata|reimposta(?:re)? la password|senha (?:alterada|redefinida)|redefinir (?:sua )?senha)/ },
  { kind: "security_copy", test: /(copia de una alerta de seguridad|copy of a security alert|copie d.une alerte de securite|copia di un avviso di sicurezza|copia de um alerta de seguranca)/ },
  { kind: "security_alert", test: /(alerta de seguridad|security alert|nuevo inicio de sesion|inicio de sesion nuevo|new sign-?in|new login|sign-?in attempt|login attempt|intento de inicio de sesion|someone (?:signed|logged) in|se inicio sesion|nuevo dispositivo|new device|actividad (?:inusual|sospechosa)|unusual activity|suspicious (?:activity|sign)|nouvelle connexion|alerte de securite|accesso sospetto|nuovo accesso|avviso di sicurezza|novo acesso|alerta de seguranca)/ },
  { kind: "order_delivered", test: /(was delivered|has been delivered|\bdelivered\b|fue entregado|ha sido entregado|\bentregado\b|pedido entregado|a ete livre|\blivree?\b|consegnato|\bentregue\b)/ },
  { kind: "order_shipped", test: /(\bshipped\b|has shipped|on (?:its|the) way|out for delivery|en camino|fue enviado|ha sido enviado|salio (?:a|para) (?:entrega|reparto)|en reparto|a ete expedie|\bexpedie\b|\bspedito\b|in consegna|foi enviado|a caminho|saiu para entrega)/ },
  { kind: "subscription_renewal", test: /(se renovara|se renueva|renovacion automatica|will (?:auto-?)?renew|renews on|auto-?renew|renewal (?:notice|reminder)|your subscription|tu suscripcion|trial (?:ends|is ending|will end)|prueba gratuita (?:termina|finaliza|vence)|votre abonnement|il tuo abbonamento|sua assinatura)/ },
  { kind: "bill_due", test: /(\bvence\b|vencimiento|fecha limite de pago|due date|payment due|amount due|is due|saldo (?:a pagar|pendiente)|pago pendiente|bill is (?:ready|due|available)|statement is (?:ready|available)|estado de cuenta|factura (?:disponible|lista|electronica)|invoice (?:is )?(?:due|available|ready)|\bcfdi\b|echeance|a payer avant|scadenza|da pagare entro|vencimento|fatura (?:disponivel|fechada))/ },
  { kind: "order_placed", test: /(order confirm|order (?:#|no\.|number)|confirmacion de (?:tu |su )?(?:pedido|compra|orden)|pedido confirmado|compra confirmada|thanks for your (?:order|purchase)|gracias por tu (?:compra|pedido)|your order|tu pedido|tu orden|merci pour votre commande|votre commande|grazie per il tuo ordine|il tuo ordine|obrigado pelo seu pedido|seu pedido)/ },
  { kind: "payment", test: /(receipt|\brecibo\b|comprobante|payment (?:received|confirm|successful)|pago (?:recibido|exitoso|confirmado|realizado)|we received your payment|recibimos tu pago|you paid|you sent|pagaste|enviaste|cargo (?:a tu|en tu|realizado)|you were charged|\bcharged\b|transaccion|transaction|compra aprobada|purchase (?:approved|confirmed)|paiement|recu de paiement|pagamento|ricevuta|transferencia|deposito)/ },
  { kind: "travel", test: /(itinerar|boarding pass|pase de abordar|tarjeta de embarque|check-?in|reservation confirm|confirmacion de reserva|reservacion|reserva confirmada|booking confirm|your trip|tu viaje|\bvuelo\b|\bflight\b|carte d.embarquement|carta d.imbarco|cartao de embarque)/ },
  { kind: "meeting", test: /(\breunion de\b|\bjunta de\b|^invitation:|^invitacion:|^invitacion actualizada|meeting (?:invite|request|scheduled)|reunion (?:programada|agendada)|te invita a|invited you to|webinar|\brsvp\b|calendar invite|invitation a|invito a|convite para)/ },
  { kind: "social_suggest", test: /(quizas conozcas|people you may know|someone you may know|you may know|peut-etre connaissez|potresti conoscere|talvez conheca)/ },
  { kind: "social", test: /(commented|comento|mentioned you|te menciono|new follower|nuevo seguidor|empezo a seguirte|started following|friend request|solicitud de amistad|le gusto tu|liked your|tagged you|te etiqueto|invitation to connect|quiere conectar|a commente|ha commentato|comentou)/ },
  { kind: "welcome", test: /(\bwelcome\b|bienvenid|comienza a usar|empieza a usar|get started|getting started|primeros pasos|bienvenue|benvenut|bem-vind|comece a usar)/ },
  { kind: "promo", test: /(unsubscribe|newsletter|\d+ ?% (?:off|de descuento|dto)|\boferta|\bdescuento|\bsale\b|\bpromo|\bcupon|\bcoupon|boletin|black friday|cyber monday|hot sale|solo hoy|only today|soldes|saldi|promocao)/ },
];

const SOCIAL_BRANDS = /(facebook|instagram|tiktok|linkedin|twitter|x\.com|threads|pinterest|snapchat|reddit|youtube)/i;

/** Event type for an email (subject + preview + sender). */
export function detectKind(input: ExplainInput): EventKind {
  const text = fold([input.title, input.summary].filter(Boolean).join(" \n "));
  if (input.refund && /(reembols|refund|devoluci|rembours|rimbors)/.test(text)) return "refund";
  if (input.priceIncrease && /(suscrip|subscription|plan|membres|abonnement|abbonamento|assinatura|precio|price|prix|prezzo|preco)/.test(text)) return "price_increase";
  for (const rule of RULES) {
    if (rule.kind === "promo" && input.area && input.area !== "promos" && input.area !== "other") continue;
    if (rule.test.test(text)) return rule.kind;
  }
  if (input.area === "promos") return "promo";
  if (input.area === "social" || SOCIAL_BRANDS.test(`${input.sender || ""} ${input.senderEmail || ""}`)) return "social";
  if (input.area === "travel") return "travel";
  if (input.area === "bills" && input.amountRaw) return "bill_due";
  return "unknown";
}

const GENERIC_LOCALS = new Set(["mail", "email", "e-mail", "accounts", "account", "notifications", "notification", "notify", "info", "noreply", "no-reply", "news", "newsletter", "alerts", "alert", "messages", "message", "support", "hello", "hi", "team", "updates", "em", "e", "mg", "m", "t", "www", "send", "bounce", "reply", "comms", "marketing", "service", "services", "contact", "us", "mx", "com", "co"]);
const SECOND_LEVEL = new Set(["com", "co", "net", "org", "gob", "gov", "edu", "ac"]);

function titleCase(word: string): string {
  return word ? word.charAt(0).toUpperCase() + word.slice(1) : word;
}

/** Brand from an email domain: accounts.google.com → Google, amazon.com.mx → Amazon. */
export function brandFromEmail(email: string | null | undefined): string {
  const domain = String(email || "").split("@")[1]?.toLowerCase().replace(/>.*/, "").trim();
  if (!domain) return "";
  const labels = domain.split(".").filter(Boolean);
  // Drop the TLD and an optional second-level (com.mx, co.uk).
  if (labels.length > 1) labels.pop();
  if (labels.length > 1 && SECOND_LEVEL.has(labels[labels.length - 1])) labels.pop();
  const main = labels[labels.length - 1] || "";
  if (!main || GENERIC_LOCALS.has(main)) return "";
  return titleCase(main);
}

/** Brand/sender to name in the sentence ("Judith Cosme en TikTok" → TikTok). */
export function brandOf(sender: string | null | undefined, senderEmail?: string | null): string {
  let name = cleanDisplayText(sender, "").replace(/["“”]/g, "").trim();
  if (/@/.test(name)) name = "";
  const via = name.match(/\s(?:en|on|via|vía|through|sur|su|no|na)\s+([A-Z][\w.&' -]{1,30})$/);
  if (via) name = via[1].trim();
  name = name
    .replace(/\b(?:no[- ]?reply|noreply|do[- ]not[- ]reply)\b/gi, "")
    .replace(/\s+(?:team|equipo|support|soporte|notifications?|notificaciones|alerts?|alertas|accounts?|cuentas|updates|news|newsletter|info)$/i, "")
    .replace(/\s{2,}/g, " ")
    .trim();
  if (name.length > 40) name = `${name.slice(0, 38).trimEnd()}…`;
  return name || brandFromEmail(senderEmail);
}

const MONTHS = "enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre|january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec|janvier|fevrier|février|mars|avril|mai|juin|juillet|aout|août|septembre|octobre|novembre|decembre|décembre|gennaio|febbraio|aprile|maggio|giugno|luglio|settembre|ottobre|dicembre|janeiro|fevereiro|março|marco|maio|junho|julho|setembro|outubro|novembro|dezembro";

export function extractOrder(text: string): string | null {
  const keyed = text.match(/(?:order|pedido|orden|commande|ordine|encomenda)\s*(?:#|n[°ºo]\.?|num(?:ero|ber|\.)?|no\.)?\s*:?\s*#?\s*([A-Z0-9][A-Z0-9-]{3,24})/i);
  if (keyed && /\d/.test(keyed[1])) return keyed[1].replace(/-+$/, "");
  const hash = text.match(/#\s?(\d[\d-]{3,24})/);
  return hash ? hash[1] : null;
}

export function extractFlight(text: string): string | null {
  const match = text.match(/\b(?:[Ff]light|FLIGHT|[Vv]uelo|VUELO|[Vv]ol|[Vv]olo|[Vv]oo)\s*(?:#|No\.?|n[°º]\.?|número|number)?\s*:?\s*([A-Z]{2}|[A-Z]\d|\d[A-Z])\s?(\d{1,4})\b/);
  return match ? `${match[1]}${match[2]}` : null;
}

export function extractApp(text: string): string | null {
  const patterns = [
    /permitiste que\s+(.{2,70}?)\s+(?:acceda|tenga acceso)/i,
    /you allowed\s+(.{2,70}?)\s+(?:to\s+)?access/i,
    /you gave\s+(.{2,70}?)\s+access/i,
    /vous avez autoris[ée]\s+(.{2,70}?)\s+à\s+acc[ée]der/i,
    /hai (?:consentito|autorizzato)\s+(?:a\s+)?(.{2,70}?)\s+(?:di\s+)?acced/i,
    /voc[êe] permitiu (?:que\s+)?(.{2,70}?)\s+acess/i,
    /(\S{2,70}) (?:now )?has access to your/i,
  ];
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) return match[1].replace(/^["“«]|["”»]$/g, "").trim();
  }
  return null;
}

export function extractEmail(text: string): string | null {
  const match = text.match(/[\w.+-]+@[\w-]+(?:\.[\w-]+)+/);
  return match ? match[0].replace(/\.$/, "") : null;
}

export function extractPerson(text: string): string | null {
  const match = text.match(/^(.{2,40}?)\s+(?:es alguien a quien quiz[aá]s conozcas|is someone you may know|est peut-être quelqu.un que vous connaissez|potrebbe essere qualcuno che conosci|talvez seja algu[eé]m que voc[eê] conhe[cç]a)/i);
  return match ? match[1].trim() : null;
}

export function extractDate(text: string): string | null {
  const patterns = [
    new RegExp(`\\b(\\d{1,2})\\s+(?:de\\s+)?(${MONTHS})\\.?(?:\\s+(?:de\\s+)?(\\d{4}))?\\b`, "i"),
    new RegExp(`\\b(${MONTHS})\\.?\\s+(\\d{1,2})(?:st|nd|rd|th)?(?:,?\\s+(\\d{4}))?\\b`, "i"),
    /\b\d{4}-\d{2}-\d{2}\b/,
    /\b\d{1,2}\/\d{1,2}\/\d{2,4}\b/,
  ];
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) return match[0].trim();
  }
  return null;
}

/** Subject without the brand prefix, "Re:/Fwd:" and over-long tails. */
export function cleanSubject(title: string, brand: string): string {
  let subject = cleanDisplayText(title, "").replace(/^\s*((re|rv|fw|fwd|tr)\s*:\s*)+/i, "").trim();
  if (brand && subject.toLowerCase().startsWith(brand.toLowerCase()) && subject.length > brand.length + 3) {
    subject = subject.slice(brand.length).replace(/^[\s:–—-]+/, "");
  }
  if (subject.length > 90) {
    const cut = subject.slice(0, 88);
    const space = cut.lastIndexOf(" ");
    subject = `${(space > 50 ? cut.slice(0, space) : cut).replace(/[\s,.;:]+$/, "")}…`;
  }
  return subject;
}

const MONTH_INDEX: Array<[RegExp, number]> = [
  [/^(jan|ene|gen|janv)/, 0], [/^(feb|fev|fév)/, 1], [/^(mar(?!t))/, 2], [/^(apr|abr|avr)/, 3],
  [/^(may|mai|mag)/, 4], [/^(jun|juin|giu)/, 5], [/^(jul|juil|lug)/, 6], [/^(aug|ago|aou|aoû)/, 7],
  [/^(sep|set)/, 8], [/^(oct|out|ott)/, 9], [/^nov/, 10], [/^(dec|dic|dez|déc)/, 11],
];

function monthIndex(name: string): number | null {
  const value = name.toLowerCase();
  for (const [pattern, index] of MONTH_INDEX) if (pattern.test(value)) return index;
  return null;
}

/** "Oct 12" / "12 de octubre" / "2026-10-12" → "12 oct" in the UI locale (raw text when unsure). */
export function localizeDate(raw: string | null, locale: string, now = new Date()): string | null {
  if (!raw) return null;
  let day: number | null = null;
  let month: number | null = null;
  let year: number | null = null;
  const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  const dayFirst = raw.match(/^(\d{1,2})\s+(?:de\s+)?([^\s.\d]+)\.?(?:\s+(?:de\s+)?(\d{4}))?$/i);
  const monthFirst = raw.match(/^([^\s.\d]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?$/i);
  if (iso) {
    year = Number(iso[1]);
    month = Number(iso[2]) - 1;
    day = Number(iso[3]);
  } else if (dayFirst) {
    day = Number(dayFirst[1]);
    month = monthIndex(dayFirst[2]);
    year = dayFirst[3] ? Number(dayFirst[3]) : null;
  } else if (monthFirst) {
    month = monthIndex(monthFirst[1]);
    day = Number(monthFirst[2]);
    year = monthFirst[3] ? Number(monthFirst[3]) : null;
  }
  if (day === null || month === null || day < 1 || day > 31) return raw;
  const date = new Date(year ?? now.getFullYear(), month, day, 12);
  if (Number.isNaN(date.getTime())) return raw;
  return new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", ...(year && year !== now.getFullYear() ? { year: "numeric" } : {}) }).format(date);
}

function formatDue(iso: string | null | undefined, locale: string): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat(locale, { day: "numeric", month: "short" }).format(date);
}

const LOCALES: Record<ExplainLang, string> = { es: "es-MX", en: "en-US", fr: "fr-FR", it: "it-IT", pt: "pt-BR" };

export function extractFacts(input: ExplainInput, lang: ExplainLang = "es"): ExplainFacts {
  const raw = [input.title, input.summary].filter(Boolean).join(" \n ");
  const brand = brandOf(input.sender, input.senderEmail);
  return {
    brand,
    amount: input.amountRaw || null,
    order: extractOrder(raw),
    flight: extractFlight(raw),
    app: extractApp(raw),
    email: extractEmail(raw),
    date: formatDue(input.dueAt, LOCALES[lang]) || localizeDate(extractDate(raw), LOCALES[lang]),
    person: extractPerson(cleanDisplayText(input.title, "")),
    subject: cleanSubject(input.title, brand),
  };
}

type Pieces = {
  someone: string;
  amt: (value: string) => string;
  to: (value: string) => string;
  due: (value: string) => string;
  on: (value: string) => string;
  flight: (value: string) => string;
  forEmail: (value: string) => string;
  about: (value: string) => string;
  anApp: string;
};

const PIECES: Record<ExplainLang, Pieces> = {
  es: { someone: "Un remitente", amt: (v) => ` por ${v}`, to: (v) => ` a ${v}`, due: (v) => `; vence el ${v}`, on: (v) => ` el ${v}`, flight: (v) => ` (vuelo ${v})`, forEmail: (v) => ` (${v})`, about: (v) => ` ${v}`, anApp: "una app" },
  en: { someone: "A sender", amt: (v) => ` for ${v}`, to: (v) => ` to ${v}`, due: (v) => `; due ${v}`, on: (v) => ` on ${v}`, flight: (v) => ` (flight ${v})`, forEmail: (v) => ` (${v})`, about: (v) => ` ${v}`, anApp: "an app" },
  fr: { someone: "Un expéditeur", amt: (v) => ` de ${v}`, to: (v) => ` à ${v}`, due: (v) => ` ; échéance le ${v}`, on: (v) => ` le ${v}`, flight: (v) => ` (vol ${v})`, forEmail: (v) => ` (${v})`, about: (v) => ` ${v}`, anApp: "une application" },
  it: { someone: "Un mittente", amt: (v) => ` di ${v}`, to: (v) => ` a ${v}`, due: (v) => `; scade il ${v}`, on: (v) => ` il ${v}`, flight: (v) => ` (volo ${v})`, forEmail: (v) => ` (${v})`, about: (v) => ` ${v}`, anApp: "un’app" },
  pt: { someone: "Um remetente", amt: (v) => ` de ${v}`, to: (v) => ` para ${v}`, due: (v) => `; vence em ${v}`, on: (v) => ` em ${v}`, flight: (v) => ` (voo ${v})`, forEmail: (v) => ` (${v})`, about: (v) => ` ${v}`, anApp: "um app" },
};

type Vars = {
  brand: string;
  amt: string;
  to: string;
  due: string;
  on: string;
  ord: string;
  flight: string;
  email: string;
  app: string;
  person: string;
  subject: string;
};

type Template = (v: Vars) => string;

const TEMPLATES: Record<ExplainLang, Record<EventKind, Template>> = {
  es: {
    verification_code: (v) => `${v.brand} te envió un código de verificación. Úsalo solo si tú lo pediste y no lo compartas.`,
    magic_link: (v) => `${v.brand} te mandó un enlace para iniciar sesión. Si no lo pediste, ignóralo.`,
    app_access: (v) => `Le diste acceso a «${v.app}» a tu cuenta de ${v.brand}. Si no lo reconoces, quítale el permiso.`,
    recovery_email: (v) => `${v.brand} pide verificar un correo de recuperación${v.email}. Hazlo solo si tú lo configuraste.`,
    password: (v) => `${v.brand} avisa de un cambio o restablecimiento de contraseña. Si no fuiste tú, protege tu cuenta.`,
    security_copy: (v) => `Copia de una alerta de seguridad de ${v.brand}${v.email}. Revisa que hayas sido tú.`,
    security_alert: (v) => `${v.brand} avisa de un acceso o cambio de seguridad en tu cuenta. Revisa que hayas sido tú.`,
    refund: (v) => `${v.brand} te hará un reembolso${v.amt}.`,
    order_delivered: (v) => `Tu pedido${v.ord} de ${v.brand} ya fue entregado.`,
    order_shipped: (v) => `Tu pedido${v.ord} de ${v.brand} va en camino.`,
    price_increase: (v) => `${v.brand} subirá el precio de tu suscripción${v.to}.`,
    subscription_renewal: (v) => `Tu suscripción a ${v.brand} se renovará${v.on}${v.amt}.`,
    bill_due: (v) => `Tienes un pago o factura de ${v.brand}${v.amt}${v.due}.`,
    order_placed: (v) => `${v.brand} confirmó tu pedido${v.ord}${v.amt}.`,
    payment: (v) => `${v.brand} registró un pago o cargo${v.amt}.`,
    travel: (v) => `Tu viaje con ${v.brand}${v.flight}${v.on}: revisa los detalles.`,
    meeting: (v) => `${v.brand} te invita a una reunión o evento${v.on}.`,
    social_suggest: (v) => `${v.brand} te sugiere a ${v.person} como contacto. Nada urgente.`,
    social: (v) => `Notificación de ${v.brand} (redes sociales). Nada urgente.`,
    welcome: (v) => `${v.brand} te da la bienvenida con consejos para empezar. Nada urgente.`,
    promo: (v) => `Promoción o boletín de ${v.brand}. Puedes ignorarlo si no te interesa.`,
    unknown: (v) => `“${v.brand}” te envió: ${v.subject}`,
  },
  en: {
    verification_code: (v) => `${v.brand} sent you a verification code. Use it only if you asked for it, and never share it.`,
    magic_link: (v) => `${v.brand} sent you a sign-in link. If you didn’t ask for it, ignore it.`,
    app_access: (v) => `You gave “${v.app}” access to your ${v.brand} account. If you don’t recognize it, remove the permission.`,
    recovery_email: (v) => `${v.brand} asks to verify a recovery email${v.email}. Do it only if you set it up.`,
    password: (v) => `${v.brand} reports a password change or reset. If it wasn’t you, secure your account.`,
    security_copy: (v) => `Copy of a ${v.brand} security alert${v.email}. Check that it was you.`,
    security_alert: (v) => `${v.brand} reports a sign-in or security change on your account. Check that it was you.`,
    refund: (v) => `${v.brand} will refund you${v.amt}.`,
    order_delivered: (v) => `Your ${v.brand} order${v.ord} was delivered.`,
    order_shipped: (v) => `Your ${v.brand} order${v.ord} is on its way.`,
    price_increase: (v) => `${v.brand} is raising the price of your subscription${v.to}.`,
    subscription_renewal: (v) => `Your ${v.brand} subscription will renew${v.on}${v.amt}.`,
    bill_due: (v) => `You have a payment or bill from ${v.brand}${v.amt}${v.due}.`,
    order_placed: (v) => `${v.brand} confirmed your order${v.ord}${v.amt}.`,
    payment: (v) => `${v.brand} recorded a payment or charge${v.amt}.`,
    travel: (v) => `Your trip with ${v.brand}${v.flight}${v.on}: check the details.`,
    meeting: (v) => `${v.brand} invites you to a meeting or event${v.on}.`,
    social_suggest: (v) => `${v.brand} suggests ${v.person} as a contact. Nothing urgent.`,
    social: (v) => `${v.brand} notification (social media). Nothing urgent.`,
    welcome: (v) => `${v.brand} welcomes you with tips to get started. Nothing urgent.`,
    promo: (v) => `Promotion or newsletter from ${v.brand}. Ignore it if you’re not interested.`,
    unknown: (v) => `“${v.brand}” sent you: ${v.subject}`,
  },
  fr: {
    verification_code: (v) => `${v.brand} vous a envoyé un code de vérification. Utilisez-le seulement si vous l’avez demandé, sans le partager.`,
    magic_link: (v) => `${v.brand} vous a envoyé un lien de connexion. Si vous ne l’avez pas demandé, ignorez-le.`,
    app_access: (v) => `Vous avez donné accès à « ${v.app} » à votre compte ${v.brand}. Si vous ne le reconnaissez pas, retirez l’autorisation.`,
    recovery_email: (v) => `${v.brand} demande de vérifier une adresse de récupération${v.email}. Faites-le seulement si c’est vous.`,
    password: (v) => `${v.brand} signale un changement ou une réinitialisation de mot de passe. Si ce n’était pas vous, protégez votre compte.`,
    security_copy: (v) => `Copie d’une alerte de sécurité ${v.brand}${v.email}. Vérifiez que c’était bien vous.`,
    security_alert: (v) => `${v.brand} signale une connexion ou un changement de sécurité sur votre compte. Vérifiez que c’était vous.`,
    refund: (v) => `${v.brand} va vous rembourser${v.amt}.`,
    order_delivered: (v) => `Votre commande${v.ord} ${v.brand} a été livrée.`,
    order_shipped: (v) => `Votre commande${v.ord} ${v.brand} est en route.`,
    price_increase: (v) => `${v.brand} augmente le prix de votre abonnement${v.to}.`,
    subscription_renewal: (v) => `Votre abonnement ${v.brand} sera renouvelé${v.on}${v.amt}.`,
    bill_due: (v) => `Vous avez un paiement ou une facture de ${v.brand}${v.amt}${v.due}.`,
    order_placed: (v) => `${v.brand} a confirmé votre commande${v.ord}${v.amt}.`,
    payment: (v) => `${v.brand} a enregistré un paiement ou un débit${v.amt}.`,
    travel: (v) => `Votre voyage avec ${v.brand}${v.flight}${v.on} : vérifiez les détails.`,
    meeting: (v) => `${v.brand} vous invite à une réunion ou un événement${v.on}.`,
    social_suggest: (v) => `${v.brand} vous suggère ${v.person} comme contact. Rien d’urgent.`,
    social: (v) => `Notification ${v.brand} (réseaux sociaux). Rien d’urgent.`,
    welcome: (v) => `${v.brand} vous souhaite la bienvenue avec des conseils pour démarrer. Rien d’urgent.`,
    promo: (v) => `Promotion ou newsletter de ${v.brand}. Ignorez-la si elle ne vous intéresse pas.`,
    unknown: (v) => `« ${v.brand} » vous a envoyé : ${v.subject}`,
  },
  it: {
    verification_code: (v) => `${v.brand} ti ha inviato un codice di verifica. Usalo solo se l’hai richiesto e non condividerlo.`,
    magic_link: (v) => `${v.brand} ti ha inviato un link di accesso. Se non l’hai richiesto, ignoralo.`,
    app_access: (v) => `Hai dato accesso a «${v.app}» al tuo account ${v.brand}. Se non lo riconosci, revoca l’autorizzazione.`,
    recovery_email: (v) => `${v.brand} chiede di verificare un’email di recupero${v.email}. Fallo solo se l’hai impostata tu.`,
    password: (v) => `${v.brand} segnala una modifica o un ripristino della password. Se non sei stato tu, proteggi l’account.`,
    security_copy: (v) => `Copia di un avviso di sicurezza di ${v.brand}${v.email}. Verifica che fossi tu.`,
    security_alert: (v) => `${v.brand} segnala un accesso o una modifica di sicurezza sul tuo account. Verifica che fossi tu.`,
    refund: (v) => `${v.brand} ti farà un rimborso${v.amt}.`,
    order_delivered: (v) => `Il tuo ordine${v.ord} di ${v.brand} è stato consegnato.`,
    order_shipped: (v) => `Il tuo ordine${v.ord} di ${v.brand} è in arrivo.`,
    price_increase: (v) => `${v.brand} aumenterà il prezzo del tuo abbonamento${v.to}.`,
    subscription_renewal: (v) => `Il tuo abbonamento a ${v.brand} si rinnoverà${v.on}${v.amt}.`,
    bill_due: (v) => `Hai un pagamento o una bolletta di ${v.brand}${v.amt}${v.due}.`,
    order_placed: (v) => `${v.brand} ha confermato il tuo ordine${v.ord}${v.amt}.`,
    payment: (v) => `${v.brand} ha registrato un pagamento o un addebito${v.amt}.`,
    travel: (v) => `Il tuo viaggio con ${v.brand}${v.flight}${v.on}: controlla i dettagli.`,
    meeting: (v) => `${v.brand} ti invita a una riunione o un evento${v.on}.`,
    social_suggest: (v) => `${v.brand} ti suggerisce ${v.person} come contatto. Niente di urgente.`,
    social: (v) => `Notifica di ${v.brand} (social). Niente di urgente.`,
    welcome: (v) => `${v.brand} ti dà il benvenuto con consigli per iniziare. Niente di urgente.`,
    promo: (v) => `Promozione o newsletter di ${v.brand}. Ignorala se non ti interessa.`,
    unknown: (v) => `«${v.brand}» ti ha scritto: ${v.subject}`,
  },
  pt: {
    verification_code: (v) => `${v.brand} enviou um código de verificação. Use só se você pediu e não compartilhe.`,
    magic_link: (v) => `${v.brand} enviou um link para entrar. Se você não pediu, ignore.`,
    app_access: (v) => `Você deu acesso a «${v.app}» à sua conta ${v.brand}. Se não reconhece, remova a permissão.`,
    recovery_email: (v) => `${v.brand} pede para verificar um e-mail de recuperação${v.email}. Faça isso só se foi você que configurou.`,
    password: (v) => `${v.brand} avisa de uma troca ou redefinição de senha. Se não foi você, proteja sua conta.`,
    security_copy: (v) => `Cópia de um alerta de segurança de ${v.brand}${v.email}. Confira se foi você.`,
    security_alert: (v) => `${v.brand} avisa de um acesso ou mudança de segurança na sua conta. Confira se foi você.`,
    refund: (v) => `${v.brand} vai te reembolsar${v.amt}.`,
    order_delivered: (v) => `Seu pedido${v.ord} de ${v.brand} foi entregue.`,
    order_shipped: (v) => `Seu pedido${v.ord} de ${v.brand} está a caminho.`,
    price_increase: (v) => `${v.brand} vai aumentar o preço da sua assinatura${v.to}.`,
    subscription_renewal: (v) => `Sua assinatura de ${v.brand} será renovada${v.on}${v.amt}.`,
    bill_due: (v) => `Você tem um pagamento ou conta de ${v.brand}${v.amt}${v.due}.`,
    order_placed: (v) => `${v.brand} confirmou seu pedido${v.ord}${v.amt}.`,
    payment: (v) => `${v.brand} registrou um pagamento ou cobrança${v.amt}.`,
    travel: (v) => `Sua viagem com ${v.brand}${v.flight}${v.on}: confira os detalhes.`,
    meeting: (v) => `${v.brand} te convida para uma reunião ou evento${v.on}.`,
    social_suggest: (v) => `${v.brand} sugere ${v.person} como contato. Nada urgente.`,
    social: (v) => `Notificação de ${v.brand} (redes sociais). Nada urgente.`,
    welcome: (v) => `${v.brand} te dá as boas-vindas com dicas para começar. Nada urgente.`,
    promo: (v) => `Promoção ou newsletter de ${v.brand}. Ignore se não tiver interesse.`,
    unknown: (v) => `“${v.brand}” te enviou: ${v.subject}`,
  },
};

/** Headline (one or two short sentences) for an email in the UI language. */
export function explain(input: ExplainInput, lang: ExplainLang): Explanation {
  const language: ExplainLang = TEMPLATES[lang] ? lang : "es";
  const kind = detectKind(input);
  const facts = extractFacts(input, language);
  const piece = PIECES[language];
  const brand = facts.brand || piece.someone;
  // Due dates only make sense for bills/renewals/trips/meetings.
  const datedKinds: EventKind[] = ["bill_due", "subscription_renewal", "travel", "meeting"];
  const date = datedKinds.includes(kind) ? facts.date : null;
  const vars: Vars = {
    brand,
    amt: facts.amount && kind !== "price_increase" ? piece.amt(facts.amount) : "",
    to: facts.amount ? piece.to(facts.amount) : "",
    due: date ? piece.due(date) : "",
    on: date ? piece.on(date) : "",
    ord: facts.order ? ` #${facts.order}` : "",
    flight: facts.flight ? piece.flight(facts.flight) : "",
    email: facts.email ? piece.forEmail(facts.email) : "",
    app: facts.app || piece.anApp,
    person: facts.person || "",
    subject: facts.subject || "—",
  };
  let resolved = kind;
  if (kind === "social_suggest" && !facts.person) resolved = "social";
  if (kind === "unknown" && !facts.subject) resolved = "unknown";
  return { kind: resolved, headline: TEMPLATES[language][resolved](vars).replace(/\s{2,}/g, " ").trim(), facts };
}

/**
 * Items with `line` replaced by the plain-language headline in `lang`; the
 * original subject stays in `subject` (shown as secondary text).
 */
export function localizeItems(items: LifeItem[], lang: ExplainLang): LifeItem[] {
  return items.map((item) => {
    const subject = item.subject ?? item.title;
    const result = explain(
      {
        title: subject,
        summary: item.preview ?? (item.line && item.line !== subject ? item.line : null),
        sender: item.sender,
        senderEmail: item.senderEmail ?? null,
        area: item.area,
        amountRaw: item.amountRaw,
        dueAt: item.dueAt,
        priceIncrease: item.priceIncrease,
        refund: item.refund,
      },
      lang,
    );
    return { ...item, subject, line: result.headline, kind: result.kind };
  });
}
