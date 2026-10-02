import assert from "node:assert/strict";
import test from "node:test";

import {
  brandOf,
  cleanSubject,
  detectKind,
  explain,
  extractApp,
  extractEmail,
  extractFlight,
  extractOrder,
  localizeDate,
  localizeItems,
  type EventKind,
  type ExplainInput,
} from "./explain.ts";
import { buildLifeItems, type InboxCase } from "./lifeAreas.ts";

const LANGS = ["es", "en", "fr", "it", "pt"] as const;

/** Real subjects from Héctor's production list (Spanish + English). */
const HECTOR: Array<[ExplainInput, EventKind, RegExp]> = [
  [{ title: "Donexto Hi Héctor Marcial Salcido Roacho, Use this link to sign in to Donexto.", sender: "Donexto", area: "security" }, "magic_link", /^Donexto te mandó un enlace para iniciar sesión/],
  [{ title: "Permitiste que hms-ai-assistant-production.up.railway.app acceda a algunos de los datos de tu Cuenta de Google hmcelinfo@gmail.com", sender: "Google", area: "security" }, "app_access", /«hms-ai-assistant-production\.up\.railway\.app» a tu cuenta de Google/],
  [{ title: "Esta es una copia de una alerta de seguridad que se envió a donexto.app@gmail.com.", sender: "Google", area: "security" }, "security_copy", /^Copia de una alerta de seguridad de Google \(donexto\.app@gmail\.com\)/],
  [{ title: "Judith Cosme es alguien a quien quizás conozcas", sender: "Judith Cosme en TikTok", area: "social" }, "social_suggest", /^TikTok te sugiere a Judith Cosme como contacto/],
  [{ title: "Código de verificación de Google Hola, Hector: Hemos recibido una solicitud para acceder a tu cuenta", sender: "Google", area: "security" }, "verification_code", /^Google te envió un código de verificación/],
  [{ title: "Comienza a usar Search Console conhttps://www.donexto.com/ Ahora que lo verificaste", sender: "Google Search Console Team", area: "other" }, "welcome", /^Google Search Console te da la bienvenida/],
  [{ title: "Verifica el correo de recuperación donexto.app@gmail.com quiere utilizar tu dirección", sender: "Google", area: "other" }, "recovery_email", /correo de recuperación \(donexto\.app@gmail\.com\)/],
];

const ENGLISH: Array<[ExplainInput, EventKind, RegExp]> = [
  [{ title: "Security alert: new sign-in on Windows", sender: "Google", senderEmail: "no-reply@accounts.google.com", area: "security" }, "security_alert", /^Google avisa de un acceso o cambio de seguridad/],
  [{ title: "Your verification code is 482913", sender: "", senderEmail: "noreply@github.com", area: "security" }, "verification_code", /^Github te envió un código/],
  [{ title: "Your Amazon.com order #112-3456789-1234567 has shipped", sender: "Amazon.com", area: "orders" }, "order_shipped", /^Tu pedido #112-3456789-1234567 de Amazon\.com va en camino\.$/],
  [{ title: "Delivered: your package", summary: "Order 113-1111111-2222222 was delivered to your mailbox", sender: "Amazon", area: "orders" }, "order_delivered", /#113-1111111-2222222 de Amazon ya fue entregado/],
  [{ title: "Your receipt from Apple", summary: "You paid $2.99 for iCloud+", sender: "Apple", area: "money", amountRaw: "$2.99" }, "payment", /^Apple registró un pago o cargo por \$2\.99\.$/],
  [{ title: "Refund issued", summary: "We issued a refund of $45.00 to your card", sender: "Uber", area: "money", amountRaw: "$45.00", refund: true }, "refund", /^Uber te hará un reembolso por \$45\.00\.$/],
  [{ title: "Netflix: your price is changing", summary: "Your plan price increase to $15.49 starting Nov 5", sender: "Netflix", area: "subscriptions", amountRaw: "$15.49", priceIncrease: true }, "price_increase", /^Netflix subirá el precio de tu suscripción a \$15\.49\.$/],
  [{ title: "Your Spotify Premium subscription will renew on October 12", sender: "Spotify", area: "subscriptions", amountRaw: "$11.99" }, "subscription_renewal", /^Tu suscripción a Spotify se renovará el 12 oct por \$11\.99\.$/],
  [{ title: "Your Con Edison bill is ready", summary: "Amount due $84.20. Payment due Oct 20", sender: "Con Edison", area: "bills", amountRaw: "$84.20" }, "bill_due", /^Tienes un pago o factura de Con Edison por \$84\.20; vence el 20 oct\.$/],
  [{ title: "Your trip itinerary", summary: "Flight UA 1234 departs San Francisco Nov 3", sender: "United Airlines", area: "travel" }, "travel", /^Tu viaje con United Airlines \(vuelo UA1234\) el 3 nov: revisa los detalles\.$/],
  [{ title: "Weekly deals: 40% off everything", sender: "Old Navy", area: "promos" }, "promo", /^Promoción o boletín de Old Navy/],
  [{ title: "Reset your password", sender: "Dropbox", area: "security" }, "password", /^Dropbox avisa de un cambio o restablecimiento de contraseña/],
  [{ title: "Ana commented on your post", sender: "Facebook", area: "social" }, "social", /^Notificación de Facebook \(redes sociales\)/],
];

const SPANISH: Array<[ExplainInput, EventKind, RegExp]> = [
  [{ title: "Tu pedido 701-555 fue enviado", sender: "Mercado Libre", area: "orders" }, "order_shipped", /^Tu pedido #701-555 de Mercado Libre va en camino\.$/],
  [{ title: "Tu recibo de luz está listo", summary: "Total a pagar $1,234.50, fecha límite de pago 15 de octubre", sender: "CFE", area: "bills", amountRaw: "$1,234.50" }, "bill_due", /^Tienes un pago o factura de CFE por \$1,234\.50; vence el 15 oct\.$/],
  [{ title: "Confirmación de tu pedido #A1B2C3", summary: "Gracias por tu compra por $599.00", sender: "Liverpool", area: "orders", amountRaw: "$599.00" }, "order_placed", /^Liverpool confirmó tu pedido #A1B2C3 por \$599\.00\.$/],
  [{ title: "Nuevo inicio de sesión en tu cuenta", sender: "BBVA México", area: "security" }, "security_alert", /^BBVA México avisa de un acceso/],
  [{ title: "Reunión de padres de familia", summary: "Te esperamos el viernes", sender: "Colegio Ábaco", area: "education" }, "meeting", /^Colegio Ábaco te invita a una reunión o evento\.$/],
  [{ title: "Hola Héctor, ¿cómo vas con el proyecto?", sender: "María López", area: "work" }, "unknown", /^“María López” te envió: Hola Héctor, ¿cómo vas con el proyecto\?$/],
];

test("explain: Héctor's real production subjects get Spanish plain-language headlines", () => {
  for (const [input, kind, pattern] of HECTOR) {
    const result = explain(input, "es");
    assert.equal(result.kind, kind, input.title);
    assert.match(result.headline, pattern, input.title);
  }
});

test("explain: English sample emails explained in Spanish", () => {
  for (const [input, kind, pattern] of ENGLISH) {
    const result = explain(input, "es");
    assert.equal(result.kind, kind, input.title);
    assert.match(result.headline, pattern, `${input.title} → ${result.headline}`);
  }
});

test("explain: Spanish sample emails", () => {
  for (const [input, kind, pattern] of SPANISH) {
    const result = explain(input, "es");
    assert.equal(result.kind, kind, input.title);
    assert.match(result.headline, pattern, `${input.title} → ${result.headline}`);
  }
});

test("explain: every event type has a sentence in the five languages and none claims to be a translation", () => {
  const all = [...HECTOR, ...ENGLISH, ...SPANISH];
  for (const lang of LANGS) {
    for (const [input] of all) {
      const { headline } = explain(input, lang);
      assert.ok(headline.length > 10, `${lang}: ${input.title}`);
      assert.ok(!/undefined|null|\{|\}/.test(headline), `${lang}: ${headline}`);
      assert.ok(!/traduc|translat|tradu[iz]|tradott/i.test(headline), `${lang}: ${headline}`);
    }
  }
  assert.match(explain(HECTOR[0][0], "en").headline, /^Donexto sent you a sign-in link/);
  assert.match(explain(HECTOR[0][0], "fr").headline, /^Donexto vous a envoyé un lien de connexion/);
  assert.match(explain(HECTOR[0][0], "it").headline, /^Donexto ti ha inviato un link di accesso/);
  assert.match(explain(HECTOR[0][0], "pt").headline, /^Donexto enviou um link para entrar/);
  assert.match(explain(SPANISH[5][0], "en").headline, /^“María López” sent you: /);
});

test("explain: entity extraction", () => {
  assert.equal(extractOrder("Your order #112-3456789-1234567 has shipped"), "112-3456789-1234567");
  assert.equal(extractOrder("Pedido No. 7788123 enviado"), "7788123");
  assert.equal(extractOrder("Your order is ready"), null);
  assert.equal(extractFlight("Flight AM 404 to Madrid"), "AM404");
  assert.equal(extractFlight("Tu vuelo Y4 1203 sale mañana"), "Y41203");
  assert.equal(extractFlight("flight attendants are great"), null);
  assert.equal(extractApp("Permitiste que Zoom acceda a algunos de los datos"), "Zoom");
  assert.equal(extractApp("You allowed Notion to access some of your Google Account data"), "Notion");
  assert.equal(extractEmail("se envió a donexto.app@gmail.com."), "donexto.app@gmail.com");
  assert.equal(localizeDate("Oct 12", "es-MX", new Date(2026, 9, 2)), "12 oct");
  assert.equal(localizeDate("15 de octubre", "en-US", new Date(2026, 9, 2)), "Oct 15");
});

test("explain: brand detection from sender name or address", () => {
  assert.equal(brandOf("Judith Cosme en TikTok"), "TikTok");
  assert.equal(brandOf("Google Search Console Team"), "Google Search Console");
  assert.equal(brandOf("", "no-reply@accounts.google.com"), "Google");
  assert.equal(brandOf("", "ship-confirm@amazon.com.mx"), "Amazon");
  assert.equal(brandOf("noreply@github.com", "noreply@github.com"), "Github");
  assert.equal(cleanSubject("Donexto Hi Héctor, use this link", "Donexto"), "Hi Héctor, use this link");
  assert.equal(detectKind({ title: "Hola", sender: "María" }), "unknown");
});

test("explain: unknown sender falls back to a neutral subject", () => {
  const { headline } = explain({ title: "Re: Fwd: Documentos para el trámite", sender: "", senderEmail: "" }, "es");
  assert.equal(headline, "“Un remitente” te envió: Documentos para el trámite");
});

test("explain: localizeItems keeps the original subject as secondary text", () => {
  const cases: InboxCase[] = [{
    id: "c1",
    title: "Esta es una copia de una alerta de seguridad que se envió a donexto.app@gmail.com.",
    case_type: "general",
    status: "new",
    priority: "normal",
    summary: null,
    requested_action: null,
    requester_name: "Google",
    requester_email: "no-reply@accounts.google.com",
    last_activity_at: "2026-10-02T15:07:00Z",
    due_at: null,
    source_count: 1,
  }];
  const [item] = localizeItems(buildLifeItems(cases, []), "es");
  assert.equal(item.subject, cases[0].title);
  assert.equal(item.kind, "security_copy");
  assert.match(item.line, /^Copia de una alerta de seguridad de Google/);
  const [english] = localizeItems([item], "en");
  assert.match(english.line, /^Copy of a Google security alert/);
  assert.equal(english.subject, cases[0].title);
});
