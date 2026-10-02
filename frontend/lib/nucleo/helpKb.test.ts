import assert from "node:assert/strict";
import test from "node:test";

import { HELP_ENTRIES, editDistance, helpCopy, matchHelp } from "./helpKb.ts";

const LANGS = ["es", "en", "fr", "it", "pt"] as const;
const top = (q: string) => matchHelp(q)[0]?.entry.id ?? null;

test("help: every entry has copy in the five languages", () => {
  for (const entry of HELP_ENTRIES) {
    for (const lang of LANGS) {
      const copy = helpCopy(entry.id, lang);
      assert.ok(copy, `${entry.id}/${lang}`);
      assert.ok(copy.title.trim().length > 0, `${entry.id}/${lang} title`);
      assert.ok(copy.body.trim().length > 0, `${entry.id}/${lang} body`);
    }
  }
});

test("help: Héctor's question answers how to sign out", () => {
  assert.equal(top("cómo puedo salir de la aplicación?"), "logout");
  assert.equal(top("como puedo salir de la aplicacion"), "logout");
  assert.equal(top("cerrar sesión"), "logout");
  assert.equal(top("how do I log out"), "logout");
  assert.equal(top("comment me déconnecter"), "logout");
  assert.equal(top("come faccio a uscire dall'app"), "logout");
  assert.equal(top("como sair da conta"), "logout");
  const logout = matchHelp("cómo puedo salir de la aplicación?")[0].entry;
  assert.equal(logout.target?.focus, "logout");
  assert.equal(logout.target?.view, "settings");
});

test("help: features and settings are found with synonyms and accents", () => {
  assert.equal(top("modo oscuro"), "theme");
  assert.equal(top("tema claro"), "theme");
  assert.equal(top("conectar gmail"), "connectMail");
  assert.equal(top("cómo conecto outlook"), "connectMail");
  assert.equal(top("desconectar correo"), "disconnectMail");
  assert.equal(top("texto más grande"), "textSize");
  assert.equal(top("alto contraste"), "contrast");
  assert.equal(top("reducir movimiento"), "motion");
  assert.equal(top("cambiar idioma"), "language");
  assert.equal(top("leer en voz alta"), "listen");
  assert.equal(top("posponer un aviso"), "snooze");
  assert.equal(top("cómo pospongo algo"), "snooze");
  assert.equal(top("marcar como hecho"), "done");
  assert.equal(top("borrar mi cuenta"), "deleteAccount");
  assert.equal(top("activar notificaciones"), "notifications");
  assert.equal(top("crear una regla"), "rules");
  assert.equal(top("dark mode"), "theme");
  assert.equal(top("change language"), "language");
});

test("help: small typos still match (accent-insensitive fuzzy)", () => {
  assert.equal(top("cerar sesion"), "logout");
  assert.equal(top("notificasiones"), "notifications");
  assert.equal(editDistance("sesion", "sesión".normalize("NFD").replace(/\p{M}/gu, "")), 0);
  assert.equal(editDistance("gmail", "gmial"), 2);
});

test("help: case searches are not hijacked by help answers", () => {
  assert.equal(top("pedidos amazon"), null);
  assert.equal(top("factura de luz"), null);
  assert.equal(top("Netflix"), null);
  assert.equal(top("zzzz qqq"), null);
  assert.deepEqual(matchHelp(""), []);
});

test("help: results are capped and ordered by score", () => {
  const hits = matchHelp("configuración tema idioma notificaciones", 3);
  assert.ok(hits.length <= 3);
  for (let i = 1; i < hits.length; i += 1) assert.ok(hits[i - 1].score >= hits[i].score);
});

test("help: unsubscribing from a sender is not 'delete my account'", () => {
  assert.notEqual(top("darme de baja de netflix"), "deleteAccount");
  assert.equal(top("darme de baja de donexto"), "deleteAccount");
});

test("help: data-help-key resolves by entry id or by focus key", async () => {
  const { helpForKey } = await import("./helpKb.ts");
  assert.equal(helpForKey("logout", "es")?.title, "Cerrar sesión");
  assert.equal(helpForKey("nav-orders", "en")?.title, "Orders");
  assert.equal(helpForKey("text-size", "es")?.title, helpCopy("textSize", "es")?.title);
  assert.equal(helpForKey("areaTile", "pt")?.title, "Área da vida");
  assert.equal(helpForKey("nope", "es"), null);
});

test("help: provider names and generic verbs alone stay case searches", () => {
  assert.equal(top("gmail"), null);
  assert.equal(top("outlook factura"), null);
  assert.equal(top("salir de netflix"), null);
  assert.equal(top("cómo conecto gmail"), "connectMail");
  assert.equal(top("conectar yahoo"), "connectMail");
  assert.equal(top("salir de la app"), "logout");
});

test("help: logout in Italian/Portuguese/English without a how-to word", () => {
  for (const q of ["Esci", "Sair", "salir", "uscire dall'app", "sair do app", "sair da conta", "quit the app"]) {
    assert.equal(top(q), "logout", q);
  }
  assert.equal(top("sair do trabalho cedo"), null);
});

test("help: every way of asking to fetch new mail answers «Traer correo nuevo»", () => {
  const phrasings = [
    "cómo traigo el correo nuevo?",
    "como traigo el correo nuevo",
    "cómo traigo mi correo",
    "traer correo",
    "quiero traer los correos nuevos",
    "cómo actualizo mi correo?",
    "actualizar el correo",
    "actualizar bandeja",
    "cómo sincronizo?",
    "sincronizar correo",
    "descargar correos nuevos",
    "cómo descargo el correo",
    "bajar correos",
    "refrescar",
    "refrescar bandeja",
    "no me llegan los correos nuevos",
    "correo nuevo",
    "how do I fetch new mail",
    "refresh inbox",
    "sync mail",
    "check for new mail",
    "comment synchroniser le courrier",
    "nouveau courrier",
    "come scaricare la posta nuova",
    "aggiornare la posta",
    "como atualizar e-mail",
    "buscar e-mail novo",
  ];
  for (const q of phrasings) {
    assert.equal(top(q), "refreshMail", q);
  }
  const entry = matchHelp("cómo traigo el correo nuevo?")[0].entry;
  assert.deepEqual(entry.target, { view: "settings", tab: "mail", focus: "refresh-mail" });
});

test("help: fetching mail never answers «Desconectar» and disconnect still works", () => {
  for (const q of ["cómo traigo el correo nuevo?", "actualizar correo", "correo nuevo", "sincronizar"]) {
    assert.ok(!matchHelp(q).some((match) => match.entry.id === "disconnectMail"), q);
  }
  assert.equal(top("desconectar correo"), "disconnectMail");
  assert.equal(top("cómo quito el acceso a mi correo"), "disconnectMail");
});

test("help: connecting a new mailbox is not mistaken for fetching mail", () => {
  assert.equal(top("conectar un correo nuevo"), "connectMail");
  assert.equal(top("how do I connect a new email"), "connectMail");
  assert.equal(top("conectar buzón"), "connectMail");
});

test("help: hovering the mail card describes the card, not disconnecting", async () => {
  const { helpForKey } = await import("./helpKb.ts");
  assert.equal(helpForKey("mail-card", "es")?.title, "Tu correo");
  assert.equal(helpForKey("refresh-mail", "es")?.title, "Traer correo nuevo");
  assert.equal(helpForKey("refresh-mail", "en")?.title, "Fetch new mail");
});
