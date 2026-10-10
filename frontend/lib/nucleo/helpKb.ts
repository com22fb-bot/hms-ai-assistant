/**
 * Local help knowledge base for "Pregunta a Donexto" and for Nexto's
 * hover/drop explanations. Fully rule-based: keyword + synonym matching,
 * accent-insensitive, with a small typo tolerance. No language model.
 *
 * Each entry has a deep-link target: the view / settings tab to open and the
 * `data-help-key` of the element to highlight.
 */

import { foldText } from "./lifeAreas.ts";

export type HelpLang = "es" | "en" | "fr" | "it" | "pt";
export type HelpView = "today" | "areas" | "money" | "orders" | "subs" | "alerts" | "settings";
export type HelpTab = "account" | "mail" | "notifications" | "appearance" | "privacy" | "alerts";

export type HelpTarget = {
  view?: HelpView;
  tab?: HelpTab;
  /** `data-help-key` of the element to focus and highlight. */
  focus?: string;
  action?: "shortcuts" | "ask";
};

type Copy = { title: string; body: string; cta: string };

export type HelpEntry = {
  id: string;
  target: HelpTarget;
  /** Enough on their own ("cerrar sesión", "logout"). */
  strong: string[];
  /** Need a how-to word ("cómo", "dónde", "how"…) or a second hit. */
  weak: string[];
  /** Hover-only entries are not offered as answers to questions. */
  hoverOnly?: boolean;
  copy: Record<HelpLang, Copy>;
};

const e = (
  id: string,
  target: HelpTarget,
  strong: string[],
  weak: string[],
  copy: Record<HelpLang, Copy>,
  hoverOnly = false,
): HelpEntry => ({ id, target, strong, weak, copy, hoverOnly });

export const HELP_ENTRIES: HelpEntry[] = [
  // --- Producto: precio, planes, prueba, importación (mismo texto que /asistencia y Términos) ---
  e("pricing", { view: "settings", tab: "account" },
    ["costo de la suscripcion", "precio de la suscripcion", "cuanto cuesta donexto", "precio de donexto", "costo de donexto", "cuanto cuesta la suscripcion", "cuanto cuesta el plan", "plan anual", "plan mensual", "planes de donexto", "cuanto cobran", "how much is donexto", "donexto price", "subscription price", "subscription cost", "annual plan", "monthly plan", "prix de l abonnement", "prezzo dell abbonamento", "preco da assinatura"],
    ["costo", "precio", "cuesta", "cuestan", "cobran", "tarifa", "suscripcion", "plan", "planes", "mensualidad", "anual", "price", "pricing", "cost", "subscription", "prix", "abonnement", "prezzo", "abbonamento", "preco", "assinatura", "cuanto"],
    {
      es: { title: "Precio de Donexto", body: "Plan mensual: US$19.99 al mes en América (€19.99 en la Unión Europea y el resto del mundo). Plan anual: US$175.99 / €175.99 al año: lo de 3 cafés latte al mes más 1 mes gratis, unos 26.7% menos que 12 meses del mensual. Prueba gratis de 3 días (próximamente). Puedes cancelar cuando quieras.", cta: "Ver mi cuenta" },
      en: { title: "Donexto pricing", body: "Monthly plan: US$19.99 per month in the Americas (€19.99 in the EU and the rest of the world). Annual plan: US$175.99 / €175.99 per year: 3 lattes a month plus 1 month free, about 26.7% less than 12 monthly payments. 3-day free trial (coming soon). Cancel anytime.", cta: "See my account" },
      fr: { title: "Prix de Donexto", body: "Mensuel : 19,99 US$ par mois sur le continent américain (19,99 € dans l’UE et le reste du monde). Annuel : 175,99 US$ / 175,99 € par an, environ 26,7 % de moins que 12 mois. Essai gratuit de 3 jours (bientôt). Annulable à tout moment.", cta: "Voir mon compte" },
      it: { title: "Prezzo di Donexto", body: "Mensile: US$19,99 al mese nelle Americhe (€19,99 nell’UE e nel resto del mondo). Annuale: US$175,99 / €175,99 all’anno, circa il 26,7% in meno di 12 mesi. Prova gratuita di 3 giorni (prossimamente). Annulli quando vuoi.", cta: "Vedi il mio account" },
      pt: { title: "Preço da Donexto", body: "Mensal: US$19,99 por mês nas Américas (€19,99 na UE e no resto do mundo). Anual: US$175,99 / €175,99 por ano, cerca de 26,7% menos que 12 meses. Teste grátis de 3 dias (em breve). Cancele quando quiser.", cta: "Ver minha conta" },
    }),
  e("trial", { view: "settings", tab: "account" },
    ["prueba gratis", "prueba gratuita", "periodo de prueba", "dias de prueba", "free trial", "trial", "essai gratuit", "prova gratuita", "teste gratis"],
    ["prueba", "gratis", "gratuita", "free", "essai", "prova", "teste"],
    {
      es: { title: "Prueba gratis", body: "La prueba gratis dura 3 días (próximamente). Al terminar no se cobra nada si no te suscribes. Si no te suscribes, conservamos tu cuenta 1 semana y después se borra de forma automática; te avisamos antes por correo.", cta: "Ver mi cuenta" },
      en: { title: "Free trial", body: "The free trial lasts 3 days (coming soon). Nothing is charged when it ends unless you subscribe. If you don’t, we keep your account 1 week and then it is deleted automatically; we email you first.", cta: "See my account" },
      fr: { title: "Essai gratuit", body: "L’essai gratuit dure 3 jours (bientôt). Rien n’est facturé à la fin sauf si vous vous abonnez. Sinon, le compte est conservé 1 semaine puis supprimé ; nous vous prévenons par courriel.", cta: "Voir mon compte" },
      it: { title: "Prova gratuita", body: "La prova gratuita dura 3 giorni (prossimamente). Alla fine non si paga nulla se non ti abboni. Altrimenti conserviamo l’account 1 settimana e poi viene eliminato; ti avvisiamo prima via email.", cta: "Vedi il mio account" },
      pt: { title: "Teste grátis", body: "O teste grátis dura 3 dias (em breve). Nada é cobrado no fim se você não assinar. Se não assinar, mantemos a conta 1 semana e depois ela é excluída; avisamos antes por e-mail.", cta: "Ver minha conta" },
    }),
  e("importWindow", { view: "settings", tab: "mail", focus: "importMail" },
    ["cuantos dias importa", "cuanto correo importa", "cuanto historial", "historial de correo", "cuantos meses", "ultimos 90 dias", "6 meses de correo", "how much history", "how far back", "import window", "combien d historique", "quanto storico", "quanto historico"],
    ["historial", "importa", "importar", "meses", "history", "import", "historique", "storico", "historico"],
    {
      es: { title: "Cuánto correo traemos", body: "Al conectar tu buzón, el plan mensual trae los últimos 90 días de correo y el plan anual los últimos 6 meses. Donexto solo lee: no envía, no borra ni mueve correos.", cta: "Abrir Configuración › Correo" },
      en: { title: "How much mail we bring in", body: "When you connect your mailbox, the monthly plan brings in the last 90 days and the annual plan the last 6 months. Donexto only reads: it never sends, deletes or moves mail.", cta: "Open Settings › Mail" },
      fr: { title: "Quelle quantité de courrier", body: "À la connexion, l’abonnement mensuel importe les 90 derniers jours et l’annuel les 6 derniers mois. Donexto lit seulement.", cta: "Ouvrir Réglages › Courrier" },
      it: { title: "Quanta posta importiamo", body: "Collegando la casella, il piano mensile importa gli ultimi 90 giorni e quello annuale gli ultimi 6 mesi. Donexto legge soltanto.", cta: "Apri Impostazioni › Posta" },
      pt: { title: "Quanto e-mail trazemos", body: "Ao conectar a caixa, o plano mensal traz os últimos 90 dias e o anual os últimos 6 meses. A Donexto só lê.", cta: "Abrir Configuração › E-mail" },
    }),
  e("logout", { view: "settings", tab: "account", focus: "logout" },
    ["cerrar sesion", "cerrar la sesion", "cierro sesion", "cierre de sesion", "salir de la app", "salir de la aplicacion", "salir de donexto", "uscire dall app", "uscire dall applicazione", "esci dall app", "uscire da donexto", "sair do app", "sair do aplicativo", "sair da aplicacao", "sair da conta", "sair da donexto", "exit the app", "quit the app", "leave the app", "quitter l application", "quitter l app", "sortir de l application", "logout", "log out", "sign out", "signout", "log off", "se deconnecter", "deconnexion", "me deconnecter", "disconnettersi", "terminar sessao", "encerrar sessao", "desloguear", "deslogear"],
    // Generic verbs ("salir de netflix") only count with a how-to word.
    ["sesion", "session", "sessao", "sessione", "exit", "quit", "irme", "salir", "salirme", "esci", "uscire", "sair"],
    {
      es: { title: "Cerrar sesión", body: "Abajo a la izquierda, junto a tu nombre (en el celular: Menú), toca «Cerrar sesión». También está en Configuración › Cuenta. Para volver, solo inicia sesión otra vez.", cta: "Ir a Cerrar sesión" },
      en: { title: "Sign out", body: "Bottom left, next to your name (on a phone: Menu), tap “Sign out”. It is also in Settings › Account. To come back, just sign in again.", cta: "Go to Sign out" },
      fr: { title: "Se déconnecter", body: "En bas à gauche, à côté de votre nom (sur mobile : Menu), touchez « Se déconnecter ». C’est aussi dans Réglages › Compte. Pour revenir, reconnectez-vous.", cta: "Aller à Se déconnecter" },
      it: { title: "Esci", body: "In basso a sinistra, accanto al tuo nome (sul telefono: Menu), tocca «Esci». È anche in Impostazioni › Account. Per tornare, accedi di nuovo.", cta: "Vai a Esci" },
      pt: { title: "Sair", body: "No canto inferior esquerdo, ao lado do seu nome (no celular: Menu), toque em «Sair». Também está em Configuração › Conta. Para voltar, entre novamente.", cta: "Ir para Sair" },
    }),
  e("connectMail", { view: "settings", tab: "mail", focus: "connect-mail" },
    ["conectar correo", "conectar mi correo", "conectar buzon", "agregar correo", "anadir correo", "cambiar correo", "otro correo", "connect mail", "connect email", "connect mailbox", "add mailbox", "connecter", "connetti", "conectar caixa", "conectar e-mail", "conectar email", "microsoft 365", "office 365", "conectar un correo", "conectar otro correo", "conectar otro buzon", "agregar un correo", "agregar otro correo", "agrego un correo", "anadir un correo", "add a mailbox", "add another mailbox", "connect another", "connect a new email", "connect a new mailbox", "add a new email", "add new email", "conectar un correo nuevo", "agregar un correo nuevo"],
    // Provider names alone are normal searches ("gmail", "outlook factura").
    ["conectar", "conecto", "connect", "buzon", "mailbox", "cuenta de correo", "casella", "caixa", "gmail", "outlook", "hotmail", "yahoo", "icloud"],
    {
      es: { title: "Conectar tu correo", body: "En Configuración › Correo toca «Conectar buzón» y elige Gmail, Outlook/Microsoft, Yahoo o iCloud. Donexto solo lee: no envía, no borra ni mueve correos.", cta: "Abrir Configuración › Correo" },
      en: { title: "Connect your mail", body: "In Settings › Mail tap “Connect mailbox” and pick Gmail, Outlook/Microsoft, Yahoo or iCloud. Donexto only reads: it never sends, deletes or moves mail.", cta: "Open Settings › Mail" },
      fr: { title: "Connecter votre courrier", body: "Dans Réglages › Courrier, touchez « Connecter la boîte » et choisissez Gmail, Outlook/Microsoft, Yahoo ou iCloud. Donexto lit seulement : il n’envoie, ne supprime ni ne déplace rien.", cta: "Ouvrir Réglages › Courrier" },
      it: { title: "Collegare la posta", body: "In Impostazioni › Posta tocca «Connetti casella» e scegli Gmail, Outlook/Microsoft, Yahoo o iCloud. Donexto legge soltanto: non invia, non elimina e non sposta nulla.", cta: "Apri Impostazioni › Posta" },
      pt: { title: "Conectar seu e-mail", body: "Em Configuração › E-mail toque em «Conectar caixa» e escolha Gmail, Outlook/Microsoft, Yahoo ou iCloud. A Donexto só lê: não envia, não apaga nem move e-mails.", cta: "Abrir Configuração › E-mail" },
    }),
  e("disconnectMail", { view: "settings", tab: "mail", focus: "mail-card" },
    ["desconectar correo", "desconectar mi correo", "quitar el acceso", "quito el acceso", "desconectar buzon", "quitar correo", "quitar acceso", "revocar acceso", "revocar permiso", "disconnect mail", "disconnect email", "disconnect mailbox", "remove mailbox", "revoke access", "deconnecter la boite", "revoquer", "disconnetti", "revocare", "desconectar e-mail", "revogar acesso"],
    ["desconectar", "desconecto", "disconnect", "revocar", "revoco", "revoke", "quitar", "quito"],
    {
      es: { title: "Desconectar tu correo", body: "Tu buzón aparece en Configuración › Correo. Para quitarle el acceso a Donexto, revoca el permiso desde tu cuenta (Google, Microsoft) o borra la contraseña de app (Yahoo, iCloud). Después puedes conectar otro buzón.", cta: "Abrir Configuración › Correo" },
      en: { title: "Disconnect your mail", body: "Your mailbox is listed in Settings › Mail. To remove Donexto’s access, revoke it from your account (Google, Microsoft) or delete the app password (Yahoo, iCloud). You can then connect another mailbox.", cta: "Open Settings › Mail" },
      fr: { title: "Déconnecter votre courrier", body: "Votre boîte figure dans Réglages › Courrier. Pour retirer l’accès de Donexto, révoquez-le depuis votre compte (Google, Microsoft) ou supprimez le mot de passe d’application (Yahoo, iCloud).", cta: "Ouvrir Réglages › Courrier" },
      it: { title: "Scollegare la posta", body: "La tua casella è in Impostazioni › Posta. Per togliere l’accesso a Donexto, revocalo dal tuo account (Google, Microsoft) o elimina la password per app (Yahoo, iCloud).", cta: "Apri Impostazioni › Posta" },
      pt: { title: "Desconectar seu e-mail", body: "Sua caixa aparece em Configuração › E-mail. Para tirar o acesso da Donexto, revogue-o na sua conta (Google, Microsoft) ou apague a senha de app (Yahoo, iCloud).", cta: "Abrir Configuração › E-mail" },
    }),
  e("refreshMail", { view: "settings", tab: "mail", focus: "refresh-mail" },
    [
      // es
      "traer correo", "traer el correo", "traer mi correo", "traer correos", "traigo el correo", "traigo correo", "traigo mi correo", "traigo los correos",
      "correo nuevo", "correos nuevos", "nuevo correo", "nuevos correos", "mensajes nuevos", "correo reciente", "correos recientes",
      "actualizar correo", "actualizar el correo", "actualizar mi correo", "actualizar correos", "actualizo el correo", "actualizo mi correo", "actualizar bandeja", "actualizar la bandeja",
      "sincronizar", "sincronizo", "sincronizacion", "sincronizar correo",
      "descargar correo", "descargar correos", "descargar el correo", "descargo el correo", "descargo correo", "bajar correo", "bajar correos", "bajar el correo",
      "refrescar", "refresco", "refrescar correo", "recargar correo", "recargar la bandeja", "revisar correo nuevo", "buscar correo nuevo", "checar correo",
      "no me llegan", "no aparecen mis correos", "no veo mis correos nuevos", "no llegan los correos",
      // en
      "sync", "sync mail", "refresh mail", "refresh inbox", "fetch mail", "fetch new mail", "fetch email", "new mail", "new email", "new emails", "get new mail", "get my mail", "check mail", "check for new mail", "pull mail", "download mail", "download new mail", "update mail", "update inbox", "reload mail",
      // fr / it / pt
      "synchroniser", "nouveau courrier", "nouveaux courriels", "actualiser le courrier", "relever le courrier",
      "sincronizza", "posta nuova", "nuova posta", "nuove email", "scaricare la posta", "aggiornare la posta", "aggiorna la posta",
      "sincronizar e-mail", "atualizar e-mail", "atualizar email", "e-mail novo", "emails novos", "e-mails novos", "buscar e-mail", "baixar e-mail", "baixar emails",
    ],
    ["actualizar", "actualizo", "refresh", "update", "recargar", "traer", "traigo", "descargar", "descargo", "bajar", "refrescar", "actualiser", "aggiornare", "aggiorna", "atualizar", "baixar", "scaricare"],
    {
      es: { title: "Traer correo nuevo", body: "Donexto revisa tu correo solo. Para traerlo ahora, ve a Configuración › Correo y toca «Traer correo nuevo»: verás cuántos correos nuevos llegaron y tu lista se actualiza.", cta: "Ir a Traer correo nuevo" },
      en: { title: "Fetch new mail", body: "Donexto checks your mail on its own. To fetch it now, go to Settings › Mail and tap “Fetch new mail”: you’ll see how many new emails arrived and your list updates.", cta: "Go to Fetch new mail" },
      fr: { title: "Chercher le nouveau courrier", body: "Donexto vérifie votre courrier tout seul. Pour le récupérer maintenant, allez dans Réglages › Courrier et touchez « Chercher le nouveau courrier » : vous verrez combien de courriels sont arrivés.", cta: "Aller à Chercher le courrier" },
      it: { title: "Scaricare la posta nuova", body: "Donexto controlla la posta da solo. Per scaricarla subito, vai in Impostazioni › Posta e tocca «Scarica la posta nuova»: vedrai quante email nuove sono arrivate.", cta: "Vai a Scarica la posta" },
      pt: { title: "Buscar e-mail novo", body: "A Donexto verifica seu e-mail sozinha. Para buscar agora, vá em Configuração › E-mail e toque em «Buscar e-mail novo»: você verá quantos e-mails novos chegaram.", cta: "Ir para Buscar e-mail" },
    }),
  e("inbox", { view: "settings", tab: "mail", focus: "open-inbox" },
    ["ver correos", "ver mis correos", "abrir correos", "bandeja de entrada", "inbox", "open mail", "read mail", "boite de reception", "posta in arrivo", "caixa de entrada", "leer correo", "leer un correo"],
    ["correos", "emails", "mails", "leer", "read"],
    {
      es: { title: "Ver tus correos", body: "Toca cualquier caso para leer su correo original, o abre la lista completa en Configuración › Correo › «Abrir correos».", cta: "Ir a Abrir correos" },
      en: { title: "See your mail", body: "Tap any case to read its original email, or open the full list in Settings › Mail › “Open mail”.", cta: "Go to Open mail" },
      fr: { title: "Voir vos courriels", body: "Touchez un dossier pour lire le courriel d’origine, ou ouvrez la liste complète dans Réglages › Courrier › « Ouvrir le courrier ».", cta: "Y aller" },
      it: { title: "Vedere la posta", body: "Tocca un caso per leggere l’email originale, oppure apri l’elenco completo in Impostazioni › Posta › «Apri la posta».", cta: "Vai lì" },
      pt: { title: "Ver seus e-mails", body: "Toque em um caso para ler o e-mail original, ou abra a lista completa em Configuração › E-mail › «Abrir e-mails».", cta: "Ir para lá" },
    }),
  e("today", { view: "today", focus: "nav-today" },
    ["centro de mando", "pantalla principal", "dashboard", "home screen", "tableau de bord", "pannello", "painel"],
    ["inicio", "hoy", "today", "resumen", "summary", "principal"],
    {
      es: { title: "Hoy (centro de mando)", body: "Muestra en una pantalla lo que requiere acción hoy, los vencimientos de los próximos 7 días, las alertas recientes y tus áreas de vida.", cta: "Ir a Hoy" },
      en: { title: "Today (command center)", body: "One screen with what needs action today, the next 7 days of due dates, recent alerts and your life areas.", cta: "Go to Today" },
      fr: { title: "Aujourd’hui", body: "Un écran avec ce qui demande une action aujourd’hui, les échéances des 7 prochains jours, les alertes récentes et vos domaines de vie.", cta: "Aller à Aujourd’hui" },
      it: { title: "Oggi", body: "Una schermata con ciò che richiede azione oggi, le scadenze dei prossimi 7 giorni, gli avvisi recenti e le tue aree di vita.", cta: "Vai a Oggi" },
      pt: { title: "Hoje", body: "Uma tela com o que exige ação hoje, os vencimentos dos próximos 7 dias, alertas recentes e suas áreas da vida.", cta: "Ir para Hoje" },
    }),
  e("areas", { view: "areas", focus: "nav-areas" },
    ["areas de vida", "area de vida", "life areas", "life area", "domaines de vie", "aree di vita", "areas da vida", "filtrar por area", "categorias"],
    ["areas", "area", "filtrar", "filter", "categoria", "category"],
    {
      es: { title: "Áreas de vida", body: "Cada correo cae en un área: dinero, pedidos, suscripciones, trabajo, facturas, hogar, salud, viajes, seguridad, gobierno, seguros, educación o eventos. Toca un área para ver solo esos casos.", cta: "Ir a Áreas de vida" },
      en: { title: "Life areas", body: "Each email lands in an area: money, orders, subscriptions, work, bills, home, health, travel, security, government, insurance, education or events. Tap one to see only those cases.", cta: "Go to Life areas" },
      fr: { title: "Domaines de vie", body: "Chaque courriel tombe dans un domaine : argent, commandes, abonnements, travail, factures, maison, santé, voyages, sécurité, administration, assurances, éducation ou événements. Touchez-en un pour filtrer.", cta: "Aller aux domaines" },
      it: { title: "Aree di vita", body: "Ogni email finisce in un’area: denaro, ordini, abbonamenti, lavoro, bollette, casa, salute, viaggi, sicurezza, governo, assicurazioni, istruzione o eventi. Toccane una per filtrare.", cta: "Vai alle aree" },
      pt: { title: "Áreas da vida", body: "Cada e-mail cai em uma área: dinheiro, pedidos, assinaturas, trabalho, contas, casa, saúde, viagens, segurança, governo, seguros, educação ou eventos. Toque em uma para filtrar.", cta: "Ir para Áreas" },
    }),
  e("money", { view: "money", focus: "nav-money" },
    ["money view"],
    ["movimientos", "gastos", "depenses", "spese", "dinero", "money", "pagos", "cargos", "argent", "denaro", "dinheiro", "saldo", "balance"],
    {
      es: { title: "Dinero", body: "Muestra movimientos identificados en tu correo (cargos, pagos, reembolsos). No es un saldo ni un estado de cuenta: Donexto no se conecta a tu banco.", cta: "Ir a Dinero" },
      en: { title: "Money", body: "Shows movements identified in your mail (charges, payments, refunds). It is not a balance or statement: Donexto never connects to your bank.", cta: "Go to Money" },
      fr: { title: "Argent", body: "Mouvements identifiés dans votre courrier (débits, paiements, remboursements). Ce n’est pas un solde : Donexto ne se connecte jamais à votre banque.", cta: "Aller à Argent" },
      it: { title: "Denaro", body: "Movimenti identificati nella tua posta (addebiti, pagamenti, rimborsi). Non è un saldo: Donexto non si collega mai alla tua banca.", cta: "Vai a Denaro" },
      pt: { title: "Dinheiro", body: "Movimentos identificados no seu e-mail (cobranças, pagamentos, reembolsos). Não é um saldo: a Donexto nunca se conecta ao seu banco.", cta: "Ir para Dinheiro" },
    }),
  e("orders", { view: "orders", focus: "nav-orders" },
    ["seguimiento de pedido", "donde esta mi pedido", "track order", "suivi de commande", "stato ordine", "rastrear pedido"],
    ["rastrear", "pedidos", "pedido", "orders", "order", "paquete", "envio", "commandes", "ordini"],
    {
      es: { title: "Pedidos", body: "Agrupa tus compras con su estado: pedido, enviado, en reparto y entregado, según los correos de la tienda.", cta: "Ir a Pedidos" },
      en: { title: "Orders", body: "Groups your purchases with their status: ordered, shipped, out for delivery and delivered, based on the store’s emails.", cta: "Go to Orders" },
      fr: { title: "Commandes", body: "Regroupe vos achats avec leur état : commandé, expédié, en livraison, livré, d’après les courriels du marchand.", cta: "Aller aux commandes" },
      it: { title: "Ordini", body: "Raggruppa gli acquisti con lo stato: ordinato, spedito, in consegna e consegnato, in base alle email del negozio.", cta: "Vai agli ordini" },
      pt: { title: "Pedidos", body: "Agrupa suas compras com o status: pedido, enviado, em entrega e entregue, segundo os e-mails da loja.", cta: "Ir para Pedidos" },
    }),
  e("subs", { view: "subs", focus: "nav-subs" },
    ["cancelar suscripcion", "cancel subscription"],
    ["renovaciones", "subida de precio", "aumento de precio", "price increase", "renewals", "suscripciones", "suscripcion", "subscriptions", "subscription", "abonnements", "abbonamenti", "assinaturas"],
    {
      es: { title: "Suscripciones", body: "Ve qué servicios se renuevan pronto y cuáles subieron de precio, según los avisos que llegan a tu correo. Donexto no cancela nada por ti.", cta: "Ir a Suscripciones" },
      en: { title: "Subscriptions", body: "See which services renew soon and which raised their price, from the notices in your mail. Donexto never cancels anything for you.", cta: "Go to Subscriptions" },
      fr: { title: "Abonnements", body: "Voyez quels services se renouvellent bientôt et lesquels augmentent, d’après vos courriels. Donexto n’annule rien à votre place.", cta: "Aller aux abonnements" },
      it: { title: "Abbonamenti", body: "Vedi quali servizi si rinnovano presto e quali hanno aumentato il prezzo, dalle email ricevute. Donexto non annulla nulla per te.", cta: "Vai agli abbonamenti" },
      pt: { title: "Assinaturas", body: "Veja quais serviços renovam em breve e quais subiram de preço, pelos avisos do seu e-mail. A Donexto não cancela nada por você.", cta: "Ir para Assinaturas" },
    }),
  e("alerts", { view: "alerts", focus: "nav-alerts" },
    ["alertas recientes", "ver alertas", "recent alerts", "alertes recentes", "avvisi recenti"],
    ["alertas", "alerta", "alerts", "alert", "alertes", "avvisi", "avisos"],
    {
      es: { title: "Alertas", body: "Reúne avisos de seguridad, cargos importantes, subidas de precio y lo que coincide con tus reglas. Cada alerta dice por qué está ahí.", cta: "Ir a Alertas" },
      en: { title: "Alerts", body: "Collects security notices, important charges, price increases and anything matching your rules. Each alert says why it is there.", cta: "Go to Alerts" },
      fr: { title: "Alertes", body: "Réunit les avis de sécurité, débits importants, hausses de prix et ce qui correspond à vos règles. Chaque alerte dit pourquoi.", cta: "Aller aux alertes" },
      it: { title: "Avvisi", body: "Raccoglie avvisi di sicurezza, addebiti importanti, aumenti di prezzo e ciò che corrisponde alle tue regole, con il motivo.", cta: "Vai agli avvisi" },
      pt: { title: "Alertas", body: "Reúne avisos de segurança, cobranças importantes, aumentos de preço e o que bate com suas regras, com o motivo.", cta: "Ir para Alertas" },
    }),
  e("snooze", { view: "today", focus: "snooze" },
    ["posponer", "pospongo", "pospon", "aplazar", "aplazo", "recordarme", "recordatorio", "recuerdame", "mas tarde", "snooze", "remind me", "reminder", "later", "reporter", "rappel", "rimanda", "ricordamelo", "promemoria", "adiar", "lembrar", "lembrete"],
    ["recordar", "remind", "despues"],
    {
      es: { title: "Posponer o recordar", body: "En «Requiere acción hoy», toca el reloj de un caso y elige «En 1 hora», «Mañana» o «En 3 días». Volverá a aparecer en ese momento.", cta: "Ir a Recordarme" },
      en: { title: "Snooze or remind me", body: "In “Needs action today”, tap a case’s clock and choose 1 hour, tomorrow or 3 days. It comes back at that time.", cta: "Go to Remind me" },
      fr: { title: "Reporter ou rappeler", body: "Dans « À traiter aujourd’hui », touchez l’horloge d’un dossier et choisissez 1 heure, demain ou 3 jours. Il reviendra à ce moment-là.", cta: "Y aller" },
      it: { title: "Rimandare o ricordare", body: "In «Da fare oggi», tocca l’orologio di un caso e scegli 1 ora, domani o 3 giorni. Tornerà in quel momento.", cta: "Vai lì" },
      pt: { title: "Adiar ou lembrar", body: "Em «Exige ação hoje», toque no relógio de um caso e escolha 1 hora, amanhã ou 3 dias. Ele volta nesse momento.", cta: "Ir para lá" },
    }),
  e("done", { view: "today", focus: "done" },
    ["marcar como hecho", "marcar hecho", "marco como hecho", "lo marco como hecho", "ya lo hice", "terminado", "completar", "mark done", "mark as done", "complete", "marquer comme fait", "segna come fatto", "marcar como feito", "resolver caso"],
    ["hecho", "done", "resuelto", "fait", "fatto", "feito"],
    {
      es: { title: "Marcar como hecho", body: "Toca la palomita ✓ de un caso (o «Marcar como hecho» dentro del caso). Sale de tus pendientes; el correo no se toca.", cta: "Ir a Marcar como hecho" },
      en: { title: "Mark done", body: "Tap a case’s ✓ (or “Mark done” inside the case). It leaves your to-dos; the email itself is not touched.", cta: "Go to Mark done" },
      fr: { title: "Marquer comme fait", body: "Touchez le ✓ d’un dossier (ou « Marquer comme fait » dans le dossier). Il quitte vos tâches ; le courriel n’est pas modifié.", cta: "Y aller" },
      it: { title: "Segnare come fatto", body: "Tocca la ✓ di un caso (o «Segna come fatto» nel caso). Esce dalle cose da fare; l’email non viene toccata.", cta: "Vai lì" },
      pt: { title: "Marcar como feito", body: "Toque no ✓ de um caso (ou «Marcar como feito» dentro dele). Ele sai das pendências; o e-mail não é alterado.", cta: "Ir para lá" },
    }),
  e("listen", { view: "settings", tab: "appearance", focus: "read-aloud" },
    ["leer en voz alta", "escuchar", "lectura en voz alta", "que me lea", "read aloud", "listen", "text to speech", "lire a voix haute", "ecouter", "leggi ad alta voce", "ascolta", "ler em voz alta", "ouvir"],
    ["voz", "voice", "audio", "hablar", "speak"],
    {
      es: { title: "Escuchar (leer en voz alta)", body: "Toca «Escuchar» en el resumen, en un caso o en un correo y Donexto lo lee con la voz de tu dispositivo. Actívalo o cambia la velocidad en Configuración › Apariencia.", cta: "Ir a Leer en voz alta" },
      en: { title: "Listen (read aloud)", body: "Tap “Listen” on the summary, a case or an email and Donexto reads it with your device voice. Turn it on or change speed in Settings › Appearance.", cta: "Go to Read aloud" },
      fr: { title: "Écouter (lecture à voix haute)", body: "Touchez « Écouter » sur le résumé, un dossier ou un courriel. Activez-le ou changez la vitesse dans Réglages › Apparence.", cta: "Y aller" },
      it: { title: "Ascolta (lettura ad alta voce)", body: "Tocca «Ascolta» sul riepilogo, su un caso o su un’email. Attivalo o cambia la velocità in Impostazioni › Aspetto.", cta: "Vai lì" },
      pt: { title: "Ouvir (ler em voz alta)", body: "Toque em «Ouvir» no resumo, em um caso ou e-mail. Ative ou mude a velocidade em Configuração › Aparência.", cta: "Ir para lá" },
    }),
  e("settings", { view: "settings", tab: "account", focus: "nav-settings" },
    ["configuracion", "ajustes", "preferencias", "settings", "preferences", "reglages", "parametres", "impostazioni", "configuracao", "configuracoes"],
    ["configurar", "configure", "opciones", "options"],
    {
      es: { title: "Configuración", body: "Abajo en el menú: Cuenta, Correo, Notificaciones, Apariencia (tema, texto, accesibilidad, voz), Privacidad y Reglas.", cta: "Abrir Configuración" },
      en: { title: "Settings", body: "At the bottom of the menu: Account, Mail, Notifications, Appearance (theme, text, accessibility, voice), Privacy and Rules.", cta: "Open Settings" },
      fr: { title: "Réglages", body: "En bas du menu : Compte, Courrier, Notifications, Apparence (thème, texte, accessibilité, voix), Confidentialité et Règles.", cta: "Ouvrir Réglages" },
      it: { title: "Impostazioni", body: "In fondo al menu: Account, Posta, Notifiche, Aspetto (tema, testo, accessibilità, voce), Privacy e Regole.", cta: "Apri Impostazioni" },
      pt: { title: "Configuração", body: "No fim do menu: Conta, E-mail, Notificações, Aparência (tema, texto, acessibilidade, voz), Privacidade e Regras.", cta: "Abrir Configuração" },
    }),
  e("theme", { view: "settings", tab: "appearance", focus: "theme" },
    ["modo oscuro", "modo claro", "tema claro", "tema oscuro", "dark mode", "light mode", "theme", "mode sombre", "mode clair", "theme sombre", "modalita scura", "tema scuro", "modo escuro", "colores"],
    ["tema", "oscuro", "claro", "dark", "light", "color", "colors", "apariencia", "appearance"],
    {
      es: { title: "Tema claro u oscuro", body: "En Configuración › Apariencia › Tema elige Núcleo IA (oscuro), Núcleo claro u otro. El cambio se aplica al momento.", cta: "Ir a Tema" },
      en: { title: "Light or dark theme", body: "In Settings › Appearance › Theme pick Núcleo IA (dark), Núcleo light or another. It applies instantly.", cta: "Go to Theme" },
      fr: { title: "Thème clair ou sombre", body: "Dans Réglages › Apparence › Thème, choisissez Núcleo IA (sombre), Núcleo clair ou un autre.", cta: "Aller au thème" },
      it: { title: "Tema chiaro o scuro", body: "In Impostazioni › Aspetto › Tema scegli Núcleo IA (scuro), Núcleo chiaro o un altro.", cta: "Vai al tema" },
      pt: { title: "Tema claro ou escuro", body: "Em Configuração › Aparência › Tema escolha Núcleo IA (escuro), Núcleo claro ou outro.", cta: "Ir para Tema" },
    }),
  e("textSize", { view: "settings", tab: "appearance", focus: "text-size" },
    ["texto grande", "letra grande", "tamano de texto", "tamano de letra", "agrandar", "larger text", "text size", "font size", "bigger text", "taille du texte", "grand texte", "testo grande", "dimensione del testo", "texto maior", "tamanho do texto", "zoom"],
    ["letra", "texto", "text", "font", "leer mejor", "grande", "tamano", "bigger", "larger"],
    {
      es: { title: "Texto grande", body: "En Configuración › Apariencia › Lectura mueve el control «Tamaño de texto». Todo Donexto se agranda.", cta: "Ir a Tamaño de texto" },
      en: { title: "Larger text", body: "In Settings › Appearance › Reading move the “Text size” slider. All of Donexto scales up.", cta: "Go to Text size" },
      fr: { title: "Texte plus grand", body: "Dans Réglages › Apparence › Lecture, déplacez « Taille du texte ».", cta: "Y aller" },
      it: { title: "Testo più grande", body: "In Impostazioni › Aspetto › Lettura sposta «Dimensione del testo».", cta: "Vai lì" },
      pt: { title: "Texto maior", body: "Em Configuração › Aparência › Leitura mova «Tamanho do texto».", cta: "Ir para lá" },
    }),
  e("contrast", { view: "settings", tab: "appearance", focus: "contrast" },
    ["alto contraste", "mas contraste", "high contrast", "contraste eleve", "alto contrasto", "contraste"],
    ["contrast", "ver mejor", "accesibilidad", "accessibility"],
    {
      es: { title: "Alto contraste", body: "En Configuración › Apariencia › Lectura activa «Alto contraste» para bordes y textos más marcados.", cta: "Ir a Alto contraste" },
      en: { title: "High contrast", body: "In Settings › Appearance › Reading turn on “High contrast” for stronger borders and text.", cta: "Go to High contrast" },
      fr: { title: "Contraste élevé", body: "Dans Réglages › Apparence › Lecture, activez « Contraste élevé ».", cta: "Y aller" },
      it: { title: "Alto contrasto", body: "In Impostazioni › Aspetto › Lettura attiva «Alto contrasto».", cta: "Vai lì" },
      pt: { title: "Alto contraste", body: "Em Configuração › Aparência › Leitura ative «Alto contraste».", cta: "Ir para lá" },
    }),
  e("motion", { view: "settings", tab: "appearance", focus: "motion" },
    ["reducir animaciones", "reducir movimiento", "menos movimiento", "movimiento reducido", "quitar animaciones", "reduce motion", "reduced motion", "animations", "reduire les animations", "riduci animazioni", "reduzir animacoes", "mareo"],
    ["animaciones", "animacion", "movimiento", "motion", "reducir"],
    {
      es: { title: "Reducir animaciones", body: "En Configuración › Apariencia › Lectura activa «Reducir animaciones». Nexto y las transiciones se quedan quietos.", cta: "Ir a Reducir animaciones" },
      en: { title: "Reduce motion", body: "In Settings › Appearance › Reading turn on “Reduce motion”. Nexto and transitions stay still.", cta: "Go to Reduce motion" },
      fr: { title: "Réduire les animations", body: "Dans Réglages › Apparence › Lecture, activez « Réduire les animations ».", cta: "Y aller" },
      it: { title: "Ridurre le animazioni", body: "In Impostazioni › Aspetto › Lettura attiva «Riduci animazioni».", cta: "Vai lì" },
      pt: { title: "Reduzir animações", body: "Em Configuração › Aparência › Leitura ative «Reduzir animações».", cta: "Ir para lá" },
    }),
  e("notifications", { view: "settings", tab: "notifications", focus: "push" },
    ["notificaciones", "avisos en el celular", "push", "notifications", "notify me", "notifiche", "notificacoes", "activar avisos", "sonido de alerta"],
    ["notificar", "avisar", "sonido", "sound", "telefono", "celular", "phone"],
    {
      es: { title: "Notificaciones", body: "En Configuración › Notificaciones toca «Activar notificaciones» para recibir avisos en este dispositivo. Ahí también ajustas el sonido y ves tus dispositivos.", cta: "Ir a Notificaciones" },
      en: { title: "Notifications", body: "In Settings › Notifications tap “Enable notifications” to get alerts on this device. Sound and devices are there too.", cta: "Go to Notifications" },
      fr: { title: "Notifications", body: "Dans Réglages › Notifications, touchez « Activer les notifications » pour cet appareil. Le son et les appareils s’y trouvent aussi.", cta: "Y aller" },
      it: { title: "Notifiche", body: "In Impostazioni › Notifiche tocca «Attiva le notifiche» per questo dispositivo. Lì trovi anche suono e dispositivi.", cta: "Vai lì" },
      pt: { title: "Notificações", body: "Em Configuração › Notificações toque em «Ativar notificações» neste dispositivo. Som e dispositivos também ficam lá.", cta: "Ir para lá" },
    }),
  e("language", { view: "settings", tab: "account", focus: "language" },
    ["idioma", "cambiar idioma", "language", "change language", "english", "ingles", "espanol", "langue", "lingua", "francais", "italiano", "portugues"],
    ["lenguaje", "traducir", "translate"],
    {
      es: { title: "Idioma", body: "En Configuración › Cuenta › Idioma elige español, English, français, italiano o português.", cta: "Ir a Idioma" },
      en: { title: "Language", body: "In Settings › Account › Language pick español, English, français, italiano or português.", cta: "Go to Language" },
      fr: { title: "Langue", body: "Dans Réglages › Compte › Langue, choisissez español, English, français, italiano ou português.", cta: "Aller à Langue" },
      it: { title: "Lingua", body: "In Impostazioni › Account › Lingua scegli español, English, français, italiano o português.", cta: "Vai a Lingua" },
      pt: { title: "Idioma", body: "Em Configuração › Conta › Idioma escolha español, English, français, italiano ou português.", cta: "Ir para Idioma" },
    }),
  e("privacy", { view: "settings", tab: "privacy", focus: "privacy" },
    ["privacidad", "solo lectura", "que lee donexto", "mis datos", "seguridad de mis datos", "privacy", "read only", "read-only", "my data", "confidentialite", "lecture seule", "sola lettura", "privacidade", "somente leitura", "leen mi correo", "envia correos"],
    ["datos", "data", "permisos", "permissions", "leer"],
    {
      es: { title: "Privacidad y solo lectura", body: "Donexto solo lee el correo que autorizaste: no envía, no borra, no mueve ni marca como leído. No usa IA de pago ni se conecta a tu banco.", cta: "Ir a Privacidad" },
      en: { title: "Privacy and read-only", body: "Donexto only reads the mail you authorised: it never sends, deletes, moves or marks as read. No paid AI, no bank connection.", cta: "Go to Privacy" },
      fr: { title: "Confidentialité et lecture seule", body: "Donexto lit seulement le courrier autorisé : il n’envoie, ne supprime, ne déplace rien. Pas d’IA payante, pas de lien bancaire.", cta: "Aller à Confidentialité" },
      it: { title: "Privacy e sola lettura", body: "Donexto legge solo la posta autorizzata: non invia, non elimina, non sposta nulla. Nessuna IA a pagamento, nessuna banca.", cta: "Vai a Privacy" },
      pt: { title: "Privacidade e somente leitura", body: "A Donexto só lê o e-mail autorizado: não envia, não apaga, não move nada. Sem IA paga, sem conexão bancária.", cta: "Ir para Privacidade" },
    }),
  e("deleteAccount", { view: "settings", tab: "privacy", focus: "privacy" },
    ["borrar cuenta", "borrar mi cuenta", "eliminar cuenta", "eliminar mi cuenta", "darme de baja de donexto", "baja de donexto", "cancelar cuenta", "delete account", "delete my account", "close account", "supprimer mon compte", "supprimer le compte", "eliminare account", "cancellare account", "excluir conta", "apagar conta", "borrar mis datos"],
    [],
    {
      es: { title: "Borrar tu cuenta", body: "Todavía no se borra desde la app. Puedes cerrar sesión y quitar el acceso a tu correo; para borrar la cuenta y tus datos, pídelo desde el formulario de contacto de donexto.com.", cta: "Ir a Privacidad" },
      en: { title: "Delete your account", body: "It can’t be deleted from the app yet. You can sign out and revoke mail access; to delete the account and data, ask through the contact form on donexto.com.", cta: "Go to Privacy" },
      fr: { title: "Supprimer votre compte", body: "Pas encore possible depuis l’app. Déconnectez-vous et révoquez l’accès ; pour supprimer compte et données, demandez-le via le formulaire de contact de donexto.com.", cta: "Aller à Confidentialité" },
      it: { title: "Eliminare l’account", body: "Non ancora dall’app. Puoi uscire e revocare l’accesso alla posta; per eliminare account e dati, chiedilo dal modulo di contatto su donexto.com.", cta: "Vai a Privacy" },
      pt: { title: "Excluir sua conta", body: "Ainda não dá pelo app. Você pode sair e revogar o acesso; para excluir conta e dados, peça pelo formulário de contato em donexto.com.", cta: "Ir para Privacidade" },
    }),
  e("rules", { view: "settings", tab: "alerts", focus: "rules" },
    ["crear regla", "nueva regla", "regla de alerta", "reglas", "create rule", "alert rule", "rules", "creer une regle", "regles", "crea regola", "regole", "criar regra", "regras", "avisame cuando"],
    ["regla", "rule", "regle", "regola", "regra"],
    {
      es: { title: "Crear una regla", body: "En Configuración › Reglas elige remitente, tipo de caso, asunto o concepto, escribe el valor y toca «Guardar regla». Lo que coincida aparecerá en Alertas.", cta: "Ir a Reglas" },
      en: { title: "Create a rule", body: "In Settings › Rules pick sender, case type, subject or concept, type the value and tap “Save rule”. Matches show up in Alerts.", cta: "Go to Rules" },
      fr: { title: "Créer une règle", body: "Dans Réglages › Règles, choisissez expéditeur, type, objet ou concept, saisissez la valeur et touchez « Enregistrer la règle ».", cta: "Aller aux règles" },
      it: { title: "Creare una regola", body: "In Impostazioni › Regole scegli mittente, tipo, oggetto o concetto, scrivi il valore e tocca «Salva regola».", cta: "Vai alle regole" },
      pt: { title: "Criar uma regra", body: "Em Configuração › Regras escolha remetente, tipo, assunto ou conceito, digite o valor e toque em «Salvar regra».", cta: "Ir para Regras" },
    }),
  e("ask", { action: "ask", focus: "ask" },
    ["pregunta a donexto", "ask donexto", "como busco", "como buscar", "how to search"],
    ["buscar", "busqueda", "search", "chercher", "rechercher", "cercare", "pesquisar", "preguntar", "ask", "encontrar", "find"],
    {
      es: { title: "Pregunta a Donexto", body: "Escribe o dicta lo que buscas: un área, un remitente, una fecha o un monto (p. ej. «facturas este mes», «58.47»). También responde dudas sobre la app. Todo se busca aquí mismo, sin IA de pago.", cta: "Ir a la búsqueda" },
      en: { title: "Ask Donexto", body: "Type or dictate what you need: an area, a sender, a date or an amount (e.g. “bills this month”, “58.47”). It also answers questions about the app. All local, no paid AI.", cta: "Go to search" },
      fr: { title: "Demander à Donexto", body: "Écrivez ou dictez : un domaine, un expéditeur, une date ou un montant. Répond aussi aux questions sur l’app. Tout en local, sans IA payante.", cta: "Aller à la recherche" },
      it: { title: "Chiedi a Donexto", body: "Scrivi o detta: un’area, un mittente, una data o un importo. Risponde anche alle domande sull’app. Tutto in locale, senza IA a pagamento.", cta: "Vai alla ricerca" },
      pt: { title: "Pergunte à Donexto", body: "Digite ou dite: uma área, um remetente, uma data ou um valor. Também responde dúvidas sobre o app. Tudo local, sem IA paga.", cta: "Ir para a busca" },
    }),
  e("guide", { view: "settings", tab: "appearance", focus: "guide" },
    ["robot", "nexto", "asistente guia", "ayudante", "guide assistant", "assistant guide", "assistente guida", "robo", "assistente guia"],
    ["guia", "guide", "asistente", "assistant", "ayuda", "help"],
    {
      es: { title: "Nexto, tu guía", body: "Pasa el cursor o el foco por cualquier opción y Nexto te dice qué hace. Arrástralo (o muévelo con las flechas) encima de algo para que te lo explique. Puedes apagarlo en Configuración › Apariencia.", cta: "Ir a Asistente guía" },
      en: { title: "Nexto, your guide", body: "Hover or focus any option and Nexto tells you what it does. Drag it (or move it with the arrow keys) over something to get an explanation. Turn it off in Settings › Appearance.", cta: "Go to Guide assistant" },
      fr: { title: "Nexto, votre guide", body: "Survolez ou focalisez une option et Nexto l’explique. Faites-le glisser (ou déplacez-le avec les flèches) sur un élément. Désactivable dans Réglages › Apparence.", cta: "Y aller" },
      it: { title: "Nexto, la tua guida", body: "Passa il cursore o il focus su un’opzione e Nexto la spiega. Trascinalo (o spostalo con le frecce) sopra un elemento. Disattivabile in Impostazioni › Aspetto.", cta: "Vai lì" },
      pt: { title: "Nexto, seu guia", body: "Passe o cursor ou o foco por uma opção e o Nexto explica. Arraste-o (ou mova com as setas) sobre um item. Desative em Configuração › Aparência.", cta: "Ir para lá" },
    }),
  e("shortcuts", { action: "shortcuts" },
    ["atajos", "atajos de teclado", "teclado", "keyboard shortcuts", "shortcuts", "raccourcis", "scorciatoie", "atalhos"],
    ["keyboard", "tecla"],
    {
      es: { title: "Atajos de teclado", body: "Ctrl+K (⌘K en Mac) abre la búsqueda, Esc cierra lo que esté abierto y ? muestra los atajos.", cta: "Ver atajos" },
      en: { title: "Keyboard shortcuts", body: "Ctrl+K (⌘K on Mac) opens search, Esc closes whatever is open and ? shows the shortcuts.", cta: "Show shortcuts" },
      fr: { title: "Raccourcis clavier", body: "Ctrl+K (⌘K sur Mac) ouvre la recherche, Échap ferme, ? affiche les raccourcis.", cta: "Voir les raccourcis" },
      it: { title: "Scorciatoie da tastiera", body: "Ctrl+K (⌘K su Mac) apre la ricerca, Esc chiude, ? mostra le scorciatoie.", cta: "Mostra scorciatoie" },
      pt: { title: "Atalhos de teclado", body: "Ctrl+K (⌘K no Mac) abre a busca, Esc fecha e ? mostra os atalhos.", cta: "Ver atalhos" },
    }),
  // ----- Hover-only explanations (Nexto) -----
  e("upcoming", {}, [], [], {
    es: { title: "Próximos vencimientos", body: "Lo que vence en los próximos 7 días, agrupado por día. Toca uno para abrir el caso.", cta: "" },
    en: { title: "Upcoming due dates", body: "What is due in the next 7 days, grouped by day. Tap one to open the case.", cta: "" },
    fr: { title: "Prochaines échéances", body: "Ce qui arrive à échéance dans les 7 prochains jours, par jour. Touchez pour ouvrir.", cta: "" },
    it: { title: "Prossime scadenze", body: "Ciò che scade nei prossimi 7 giorni, per giorno. Tocca per aprire il caso.", cta: "" },
    pt: { title: "Próximos vencimentos", body: "O que vence nos próximos 7 dias, por dia. Toque para abrir o caso.", cta: "" },
  }, true),
  e("recentAlerts", {}, [], [], {
    es: { title: "Alertas recientes", body: "Avisos de los últimos días y por qué aparecen (seguridad, prioridad alta, subida de precio o una regla tuya).", cta: "" },
    en: { title: "Recent alerts", body: "Notices from the last few days and why they appear (security, high priority, price increase or one of your rules).", cta: "" },
    fr: { title: "Alertes récentes", body: "Avis des derniers jours et leur raison (sécurité, priorité, hausse de prix ou règle).", cta: "" },
    it: { title: "Avvisi recenti", body: "Avvisi degli ultimi giorni e il motivo (sicurezza, priorità, aumento di prezzo o regola).", cta: "" },
    pt: { title: "Alertas recentes", body: "Avisos dos últimos dias e o motivo (segurança, prioridade, aumento de preço ou regra).", cta: "" },
  }, true),
  e("areaTile", {}, [], [], {
    es: { title: "Área de vida", body: "El número cuenta los casos pendientes de esta área identificados en tu correo. Tócala para ver solo esos casos.", cta: "" },
    en: { title: "Life area", body: "The number counts open cases in this area identified in your mail. Tap it to see only those cases.", cta: "" },
    fr: { title: "Domaine de vie", body: "Le nombre compte les dossiers ouverts de ce domaine. Touchez pour les voir.", cta: "" },
    it: { title: "Area di vita", body: "Il numero conta i casi aperti di quest’area. Tocca per vederli.", cta: "" },
    pt: { title: "Área da vida", body: "O número conta os casos abertos desta área. Toque para vê-los.", cta: "" },
  }, true),
  e("summary", {}, [], [], {
    es: { title: "Resumen del día", body: "Cuántas cosas necesitan tu atención hoy y cuáles son las más urgentes. «Escuchar resumen» lo lee en voz alta.", cta: "" },
    en: { title: "Daily summary", body: "How many things need your attention today and the most urgent ones. “Listen” reads it aloud.", cta: "" },
    fr: { title: "Résumé du jour", body: "Combien de choses demandent votre attention et les plus urgentes. « Écouter » le lit.", cta: "" },
    it: { title: "Riepilogo del giorno", body: "Quante cose richiedono attenzione oggi e le più urgenti. «Ascolta» lo legge.", cta: "" },
    pt: { title: "Resumo do dia", body: "Quantas coisas pedem atenção hoje e as mais urgentes. «Ouvir» lê em voz alta.", cta: "" },
  }, true),
  e("mailbox", {}, [], [], {
    es: { title: "Tu buzón", body: "El correo conectado y su estado. Donexto solo tiene acceso de lectura.", cta: "" },
    en: { title: "Your mailbox", body: "The connected mailbox and its status. Donexto only has read access.", cta: "" },
    fr: { title: "Votre boîte", body: "La boîte connectée et son état. Donexto a seulement un accès en lecture.", cta: "" },
    it: { title: "La tua casella", body: "La casella collegata e il suo stato. Donexto ha solo accesso in lettura.", cta: "" },
    pt: { title: "Sua caixa", body: "A caixa conectada e seu status. A Donexto só tem acesso de leitura.", cta: "" },
  }, true),
  e("profile", {}, [], [], {
    es: { title: "Tu perfil", body: "Abre el menú de tu cuenta. «Cerrar sesión» está justo al lado.", cta: "" },
    en: { title: "Your profile", body: "Opens your account menu. “Sign out” is right next to it.", cta: "" },
    fr: { title: "Votre profil", body: "Ouvre le menu du compte. « Se déconnecter » est juste à côté.", cta: "" },
    it: { title: "Il tuo profilo", body: "Apre il menu dell’account. «Esci» è proprio accanto.", cta: "" },
    pt: { title: "Seu perfil", body: "Abre o menu da conta. «Sair» fica ao lado.", cta: "" },
  }, true),
  e("listenItem", {}, [], [], {
    es: { title: "Escuchar", body: "Lee este elemento en voz alta con la voz de tu dispositivo.", cta: "" },
    en: { title: "Listen", body: "Reads this item aloud with your device voice.", cta: "" },
    fr: { title: "Écouter", body: "Lit cet élément à voix haute.", cta: "" },
    it: { title: "Ascolta", body: "Legge questo elemento ad alta voce.", cta: "" },
    pt: { title: "Ouvir", body: "Lê este item em voz alta.", cta: "" },
  }, true),
  e("openCase", {}, [], [], {
    es: { title: "Abrir caso", body: "Abre el caso con su historia, el siguiente paso y los correos originales.", cta: "" },
    en: { title: "Open case", body: "Opens the case with its history, the next step and the original emails.", cta: "" },
    fr: { title: "Ouvrir le dossier", body: "Ouvre le dossier avec son historique, la prochaine étape et les courriels.", cta: "" },
    it: { title: "Apri il caso", body: "Apre il caso con la storia, il prossimo passo e le email originali.", cta: "" },
    pt: { title: "Abrir caso", body: "Abre o caso com o histórico, o próximo passo e os e-mails originais.", cta: "" },
  }, true),
  e("tabAccount", {}, [], [], {
    es: { title: "Cuenta", body: "Tu correo de acceso, el idioma de la app y el botón para cerrar sesión.", cta: "" },
    en: { title: "Account", body: "Your sign-in email, the app language and the sign-out button.", cta: "" },
    fr: { title: "Compte", body: "Votre e-mail de connexion, la langue et le bouton pour se déconnecter.", cta: "" },
    it: { title: "Account", body: "La tua email di accesso, la lingua e il pulsante per uscire.", cta: "" },
    pt: { title: "Conta", body: "Seu e-mail de acesso, o idioma e o botão para sair.", cta: "" },
  }, true),
  e("tabMail", {}, [], [], {
    es: { title: "Correo", body: "Conecta, actualiza o cambia tu buzón (Gmail, Outlook, Yahoo, iCloud). Donexto solo lee; nunca envía ni borra.", cta: "" },
    en: { title: "Mail", body: "Connect, refresh or change your mailbox (Gmail, Outlook, Yahoo, iCloud). Donexto only reads; it never sends or deletes.", cta: "" },
    fr: { title: "Courrier", body: "Connectez, actualisez ou changez votre boîte (Gmail, Outlook, Yahoo, iCloud). Lecture seule.", cta: "" },
    it: { title: "Posta", body: "Collega, aggiorna o cambia la casella (Gmail, Outlook, Yahoo, iCloud). Solo lettura.", cta: "" },
    pt: { title: "E-mail", body: "Conecte, atualize ou troque sua caixa (Gmail, Outlook, Yahoo, iCloud). Somente leitura.", cta: "" },
  }, true),
  e("tabNotifications", {}, [], [], {
    es: { title: "Notificaciones", body: "Activa avisos en este dispositivo, prueba el sonido y revisa tus dispositivos.", cta: "" },
    en: { title: "Notifications", body: "Turn on alerts on this device, test the sound and review your devices.", cta: "" },
    fr: { title: "Notifications", body: "Activez les alertes sur cet appareil, testez le son et gérez vos appareils.", cta: "" },
    it: { title: "Notifiche", body: "Attiva gli avvisi su questo dispositivo, prova il suono e gestisci i dispositivi.", cta: "" },
    pt: { title: "Notificações", body: "Ative alertas neste dispositivo, teste o som e veja seus dispositivos.", cta: "" },
  }, true),
  e("tabAppearance", {}, [], [], {
    es: { title: "Apariencia y accesibilidad", body: "Tema claro u oscuro, tamaño de texto, alto contraste, movimiento reducido, voz y el robot guía.", cta: "" },
    en: { title: "Appearance & accessibility", body: "Light or dark theme, text size, high contrast, reduced motion, voice and the guide robot.", cta: "" },
    fr: { title: "Apparence et accessibilité", body: "Thème clair ou sombre, taille du texte, contraste, mouvement réduit, voix et robot guide.", cta: "" },
    it: { title: "Aspetto e accessibilità", body: "Tema chiaro o scuro, dimensione del testo, contrasto, movimento ridotto, voce e robot guida.", cta: "" },
    pt: { title: "Aparência e acessibilidade", body: "Tema claro ou escuro, tamanho do texto, contraste, movimento reduzido, voz e robô guia.", cta: "" },
  }, true),
  e("tabPrivacy", {}, [], [], {
    es: { title: "Privacidad", body: "Qué lee Donexto y qué no: acceso de solo lectura, sin enviar ni borrar correos.", cta: "" },
    en: { title: "Privacy", body: "What Donexto reads and what it doesn’t: read-only access, never sends or deletes mail.", cta: "" },
    fr: { title: "Confidentialité", body: "Ce que Donexto lit : accès en lecture seule, sans envoyer ni supprimer.", cta: "" },
    it: { title: "Privacy", body: "Cosa legge Donexto: accesso in sola lettura, senza inviare né eliminare.", cta: "" },
    pt: { title: "Privacidade", body: "O que a Donexto lê: acesso somente leitura, sem enviar nem apagar.", cta: "" },
  }, true),
  e("tabAlerts", {}, [], [], {
    es: { title: "Reglas de alerta", body: "Crea reglas por remitente, asunto o concepto para que esos correos aparezcan como alerta.", cta: "" },
    en: { title: "Alert rules", body: "Create rules by sender, subject or concept so those emails show up as alerts.", cta: "" },
    fr: { title: "Règles d’alerte", body: "Créez des règles par expéditeur, objet ou concept pour être alerté.", cta: "" },
    it: { title: "Regole di avviso", body: "Crea regole per mittente, oggetto o concetto per ricevere avvisi.", cta: "" },
    pt: { title: "Regras de alerta", body: "Crie regras por remetente, assunto ou conceito para receber alertas.", cta: "" },
  }, true),
  e("mail-card", {}, [], [], {
    es: { title: "Tu correo", body: "El buzón conectado a Donexto (solo lectura). Aquí lo conectas o cambias, traes correo nuevo, abres tus correos o importas historial.", cta: "" },
    en: { title: "Your mail", body: "The mailbox connected to Donexto (read-only). Connect or change it, fetch new mail, open your email or import history here.", cta: "" },
    fr: { title: "Votre courrier", body: "La boîte connectée à Donexto (lecture seule). Connectez-la, récupérez le nouveau courrier, ouvrez vos courriels ou importez l’historique.", cta: "" },
    it: { title: "La tua posta", body: "La casella collegata a Donexto (sola lettura). Qui la colleghi, scarichi la posta nuova, apri le email o importi lo storico.", cta: "" },
    pt: { title: "Seu e-mail", body: "A caixa conectada à Donexto (somente leitura). Aqui você conecta, busca e-mail novo, abre seus e-mails ou importa o histórico.", cta: "" },
  }, true),
  e("top10", {}, [], [], {
    es: { title: "Tus 10 pendientes", body: "Lo más importante de tu correo, ordenado con reglas por urgencia, fecha límite e importancia.", cta: "" },
    en: { title: "Your top 10", body: "The most important things in your mail, ranked with rules by urgency, due date and importance.", cta: "" },
    fr: { title: "Vos 10 tâches", body: "L’essentiel de votre courrier, classé par règles : urgence, échéance et importance.", cta: "" },
    it: { title: "Le tue 10 cose", body: "Le cose più importanti della posta, ordinate con regole per urgenza, scadenza e importanza.", cta: "" },
    pt: { title: "Suas 10 pendências", body: "O mais importante do seu e-mail, ordenado por regras: urgência, prazo e importância.", cta: "" },
  }, true),
  e("importMail", {}, [], [], {
    es: { title: "Importar correo", body: "Trae correos anteriores de tu buzón para que Donexto arme los casos con más historia.", cta: "" },
    en: { title: "Import mail", body: "Brings older emails from your mailbox so Donexto builds cases with more history.", cta: "" },
    fr: { title: "Importer le courrier", body: "Récupère des courriels plus anciens pour enrichir les dossiers.", cta: "" },
    it: { title: "Importa posta", body: "Recupera email più vecchie per arricchire i casi.", cta: "" },
    pt: { title: "Importar e-mail", body: "Traz e-mails antigos para montar casos com mais histórico.", cta: "" },
  }, true),
  e("actionToday", {}, [], [], {
    es: { title: "Qué hacer hoy", body: "Lo que vence hoy o ya está atrasado, ordenado por urgencia. Abre, pospón o marca como hecho cada fila.", cta: "" },
    en: { title: "To do today", body: "What is due today or overdue, sorted by urgency. Open, snooze or mark each row done.", cta: "" },
    fr: { title: "À faire aujourd’hui", body: "Ce qui arrive à échéance ou est en retard, trié par urgence.", cta: "" },
    it: { title: "Da fare oggi", body: "Ciò che scade oggi o è in ritardo, ordinato per urgenza.", cta: "" },
    pt: { title: "Fazer hoje", body: "O que vence hoje ou está atrasado, por urgência.", cta: "" },
  }, true),
  e("dictate", {}, [], [], {
    es: { title: "Dictar", body: "Haz tu pregunta con la voz; el navegador la convierte en texto.", cta: "" },
    en: { title: "Dictate", body: "Ask with your voice; the browser turns it into text.", cta: "" },
    fr: { title: "Dicter", body: "Posez votre question à voix haute ; le navigateur la transcrit.", cta: "" },
    it: { title: "Detta", body: "Fai la domanda a voce; il browser la trascrive.", cta: "" },
    pt: { title: "Ditar", body: "Pergunte com a voz; o navegador transcreve.", cta: "" },
  }, true),
  e("robot", {}, [], [], {
    es: { title: "Nexto, tu guía", body: "Pasa el cursor por una opción y te explico qué hace. Arrástrame (o usa las flechas con el foco en mí) encima de algo y te lo explico. Inicio me regresa a mi lugar.", cta: "" },
    en: { title: "Nexto, your guide", body: "Hover an option and I explain it. Drag me (or use the arrow keys while I’m focused) over something and I’ll explain it. Home puts me back.", cta: "" },
    fr: { title: "Nexto, votre guide", body: "Survolez une option et je l’explique. Faites-moi glisser (ou flèches du clavier) sur un élément. Début me remet à ma place.", cta: "" },
    it: { title: "Nexto, la tua guida", body: "Passa sopra un’opzione e te la spiego. Trascinami (o usa le frecce) sopra qualcosa. Home mi riporta al mio posto.", cta: "" },
    pt: { title: "Nexto, seu guia", body: "Passe o cursor numa opção e eu explico. Arraste-me (ou use as setas) sobre algo. Home me devolve ao lugar.", cta: "" },
  }, true),
];

const BY_ID = new Map(HELP_ENTRIES.map((entry) => [entry.id, entry]));

export function helpEntry(id: string | null | undefined): HelpEntry | null {
  return id ? BY_ID.get(id) ?? null : null;
}

/** Copy for a `data-help-key`: an entry id, or the focus key of an entry's target. */
export function helpForKey(key: string | null | undefined, lang: HelpLang): Copy | null {
  if (!key) return null;
  const entry = BY_ID.get(key) ?? HELP_ENTRIES.find((item) => item.target.focus === key) ?? null;
  return entry ? entry.copy[lang] ?? entry.copy.es : null;
}

export function helpCopy(id: string | null | undefined, lang: HelpLang): Copy | null {
  const entry = helpEntry(id);
  return entry ? entry.copy[lang] ?? entry.copy.es : null;
}

/** Words that mark a how-to question about the app itself. */
const INTENT = new Set([
  "como", "donde", "puedo", "hago", "hacer", "ayuda", "quiero", "necesito", "sirve",
  "funciona", "configurar", "activar", "desactivar", "cambiar", "encuentro", "veo",
  "how", "where", "can", "help", "want", "change", "enable", "disable", "turn", "find", "use",
  "comment", "ou", "puis", "aide", "changer", "activer", "come", "dove", "posso", "aiuto",
  "cambiare", "attivare", "onde", "ajuda", "mudar", "ativar", "consigo",
  "crear", "create", "agregar", "add", "poner", "creer", "creare", "criar",
]);

function tokens(folded: string): string[] {
  return folded.split(/[^a-z0-9+]+/).filter(Boolean);
}

/** Levenshtein distance capped at 2 (enough for typo tolerance). */
export function editDistance(a: string, b: string): number {
  if (a === b) return 0;
  if (Math.abs(a.length - b.length) > 2) return 3;
  let prev = Array.from({ length: b.length + 1 }, (_, index) => index);
  for (let i = 1; i <= a.length; i++) {
    const row = [i];
    for (let j = 1; j <= b.length; j++) {
      row[j] = Math.min(prev[j] + 1, row[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    }
    prev = row;
  }
  return prev[b.length];
}

let vocabulary: Set<string> | null = null;
/** Every keyword word; a query word that is a known keyword is never fuzzy-matched to another. */
function knownWords(): Set<string> {
  if (!vocabulary) {
    vocabulary = new Set();
    for (const entry of HELP_ENTRIES) {
      for (const phrase of [...entry.strong, ...entry.weak]) for (const part of tokens(foldText(phrase))) vocabulary.add(part);
    }
  }
  return vocabulary;
}

function wordMatches(word: string, keyword: string): boolean {
  if (word === keyword) return true;
  if (knownWords().has(word)) return false; // "texto" ≠ "nexto", "pedidos" ≠ "pedido"
  if (keyword.length >= 5 && word.length >= 5) return editDistance(word, keyword) <= 1;
  return false;
}

/** Index of the first query word where the phrase matches consecutively (typo-tolerant), or -1. */
function phraseAt(words: string[], phrase: string): number {
  const parts = tokens(foldText(phrase));
  if (!parts.length) return -1;
  for (let start = 0; start + parts.length <= words.length; start++) {
    if (parts.every((part, offset) => wordMatches(words[start + offset], part))) return start;
  }
  return -1;
}

/** Number of distinct query words hit by the phrases (so "pedidos" ≈ "pedido" counts once). */
function hits(words: string[], phrases: string[]): number {
  const at = new Set<number>();
  for (const phrase of phrases) {
    const index = phraseAt(words, phrase);
    if (index >= 0) at.add(index);
  }
  return at.size;
}

export type HelpMatch = { entry: HelpEntry; score: number };

/** A one-word query that is exactly a visible button label ("Salir", "Esci", "Sair"). */
const SOLO: Record<string, string[]> = {
  logout: ["salir", "salirme", "sair", "esci", "uscire", "exit", "quit", "logout", "signout"],
};

/**
 * Rule-based matcher. Strong keywords answer on their own; weak ones need a
 * how-to word ("cómo", "dónde", "how"…) or a second hit. Returns up to `max`
 * entries, best first.
 */
export function matchHelp(query: string, max = 3): HelpMatch[] {
  const words = tokens(foldText(query));
  if (!words.length) return [];
  const intent = words.some((word) => INTENT.has(word));
  const out: HelpMatch[] = [];
  for (const entry of HELP_ENTRIES) {
    if (entry.hoverOnly) continue;
    const strong = hits(words, entry.strong);
    const weak = hits(words, entry.weak);
    const solo = words.length === 1 && Boolean(SOLO[entry.id]?.includes(words[0]));
    const ok = solo || strong > 0 || (weak > 0 && intent) || weak > 1;
    if (!ok) continue;
    out.push({ entry, score: (solo ? 3 : 0) + strong * 3 + weak + (intent ? 1 : 0) });
  }
  out.sort((left, right) => right.score - left.score);
  if (!out.length) return [];
  const best = out[0].score;
  return out.filter((match) => match.score >= Math.max(2, best / 2)).slice(0, max);
}
