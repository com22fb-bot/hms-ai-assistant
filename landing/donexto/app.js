const strings = {
  es: {
    nav_video: "Historia",
    nav_levels: "Criterio",
    nav_console: "Consola",
    nav_how: "Cómo",
    nav_app: "Abrir app",
    lang_label: "Idioma",
    kicker: "Atención sobre tu correo",
    hero_title: "Donexto",
    hero_tagline: "Do Next To… lo siguiente que sí importa.",
    hero_lede:
      "Lee Outlook, Hotmail, Gmail, Yahoo o iCloud y sube lo que pide acción. El ruido promocional no ocupa la portada. No es otra bandeja.",
    cta_app: "Entrar a Donexto",
    cta_video: "Ver la consola",
    cta_app2: "Probar la app",
    cta_app3: "Abrir la app",
    cta_mail: "support@donexto.com",
    trust_1: "Outlook y Hotmail: en vivo con Microsoft",
    trust_2: "Yahoo e iCloud: contraseña de app, solo lectura",
    trust_3: "Gmail: OAuth en Google (app aún no verificada)",
    video_title: "El criterio, en 40 segundos",
    video_lede: "Se dice Do-NEX-to. Marca, criterio y tablero.",
    video_caption: "Imágenes de marca. El clip con voz se publica cuando esté listo.",
    story_play: "Reproducir",
    story_pause: "Pausar",
    story_prev: "Anterior",
    story_next: "Siguiente",
    story_vo_toggle: "Guion (voz en off)",
    story_vo_full:
      "Donexto. Do Next To… Atención sobre tu correo personal. Lo que pide acción sube; la oferta espera. Outlook en Microsoft; Gmail en Google; Yahoo e iCloud con contraseña de app. Confirmas, autorizas la lectura y ves qué sigue. app.donexto.com",
    scope_title: 'Mis esferas',
    scope_lede:
      'Donexto ordena tu correo en tres esferas de tu vida. La app decide sola a cuál pertenece cada aviso y aprende cuando la corriges.',
    scope_1_t: 'Hogar',
    scope_1_p: 'Casa, familia, escuela, servicios, pedidos y salud de los tuyos.',
    scope_2_t: 'Ocupación',
    scope_2_p: 'Trabajo, negocio o profesión: clientes, juntas, facturas y documentos.',
    scope_3_t: 'Personal',
    scope_3_p: 'Lo tuyo: tus compras, suscripciones, viajes, amigos y finanzas.',
    scope_areas:
      '13 áreas: Dinero y finanzas · Compras y pedidos · Suscripciones y servicios · Trabajo y negocios · Hogar y familia · Salud y bienestar · Facturas y vencimientos · Viajes y reservas · Seguridad y cuentas · Gobierno y documentos · Educación · Agenda (eventos, boletos, conciertos, conferencias, partidos) · Social y comunicaciones. Las áreas se están incorporando por etapas; la clasificación al inicio puede equivocarse y tú la corriges.',
    price_title: 'Precio claro',
    price_lede: 'Prueba gratis de 3 días (próximamente). Después, un plan mensual o anual.',
    price_plan_t: 'Plan mensual: US$19.99 / €19.99',
    price_plan_p: 'Lo que cuestan 4 cafés latte al mes (uno por semana, unos US$26), con descuento a US$19.99. Cancelas cuando quieras. Al terminar la prueba no se cobra nada, a menos que contrates el plan.',
    price_annual_t: 'Plan anual: US$175.99 / €175.99',
    price_annual_p: 'Lo que cuestan 3 cafés latte al mes, más 1 mes gratis: unos 26.7% menos que pagar 12 meses del plan mensual (US$239.88).',
    price_import_t: 'Cuánto correo traemos al empezar',
    price_import_p: 'Plan mensual: los últimos 90 días de tu correo. Plan anual: los últimos 6 meses.',
    price_fx_t: '¿Por qué veo otra moneda?',
    price_fx_p: 'Te mostramos el precio convertido a la moneda de tu país, detectado por tu conexión, como referencia aproximada. El cobro real es en dólares (USD) en el continente americano y en euros (EUR) en la Unión Europea y el resto del mundo. Tu banco puede aplicar su propio tipo de cambio y comisiones. Los pagos los procesa nuestro procesador de pagos, que también calcula los impuestos.',
    levels_title: "Tres ritmos",
    levels_lede:
      "No cada mensaje merece un aviso. El sistema decide cuándo interrumpir y cuándo callar.",
    n1_badge: "N1 · Ahora",
    n1_title: "Interrumpe",
    n1_p: "Si pide acción ahora — un pago, un paquete, un acceso, la escuela — puede sonar en el celular.",
    n1_hint: "",
    n2_badge: "N2 · Cuando puedas",
    n2_title: "Resume",
    n2_p: "Agenda, contactos VIP y avisos que tú pediste. Entra en un resumen, no en un empujón.",
    n2_hint: "",
    n3_badge: "N3 · En silencio",
    n3_title: "Clasifica y guarda",
    n3_p: "Ofertas, redes y boletines masivos. Quedan archivados. Nunca ocupan la portada.",
    n3_hint: "",
    how_title: "Cómo se conecta",
    how_1_t: "Identidad",
    how_1_p:
      "Outlook y Hotmail se identifican en Microsoft. Gmail, en Google (la app aún no está verificada). Yahoo e iCloud usan una contraseña de app en app.donexto.com, no en este sitio. Con Gmail, Yahoo e iCloud llega el correo de verificación de Donexto.",
    how_2_t: "Lectura",
    how_2_p:
      "Outlook/Hotmail se autorizan en Microsoft (Mail.Read). Gmail, en Google (gmail.readonly). Yahoo e iCloud, por IMAP con contraseña de app (Yahoo mail-r aún pendiente). Solo lectura; Donexto no pide la contraseña de la cuenta.",
    how_3_t: "Consola",
    how_3_p:
      "Ves prioridad clasificada. El buzón original no se borra ni se reescribe.",
    console_title: "Consola",
    console_lede:
      "Tres prototipos del mismo tablero. Mismo criterio; distinto acento. El que entra a la app es el ejecutivo.",
    proto_a_k: "Prototipo A",
    proto_a_t: "Prioridad",
    proto_b_k: "Prototipo B · en la app",
    proto_b_t: "Ejecutivo",
    proto_c_k: "Prototipo C",
    proto_c_t: "Operación",
    market_title: "Por qué no otra bandeja",
    market_lede:
      "La mayor parte del volumen es oferta. Donexto es para el correo personal: sube lo que pide acción y calla el resto.",
    stat1_v: "N1 alto",
    stat1_l: "Aceptación de avisos útiles",
    stat2_v: ">60%",
    stat2_l: "Volumen = ofertas y boletines",
    stat3_v: "Móvil",
    stat3_l: "Ahí se abre el correo personal",
    market_note: "Hipótesis de producto, no claims publicitarios certificados.",
    wait_title: "Empieza con tu correo",
    wait_lede:
      "La app está en app.donexto.com. Escribimos desde support@donexto.com.",
    or_wait: "O déjanos un mensaje",
    label_name: "Nombre",
    label_email: "Correo",
    label_country: "País",
    label_message: "Mensaje",
    ph_name: "Alex",
    ph_email: "tu@correo.com",
    ph_message: "Cuéntanos en qué podemos ayudarte",
    opt_us: "Estados Unidos",
    opt_mx: "México",
    opt_other: "Otro",
    btn_join: "Enviar",
    btn_sending: "Enviando…",
    form_note: "Llega a support@donexto.com. No vendemos listas.",
    form_ok: "Listo. Recibimos tu mensaje.",
    form_err: "Escribe un correo válido.",
    form_msg_err: "Escribe un mensaje.",
    form_send_err: "No se pudo enviar. Escríbenos a",
    social_title: "Canal",
    foot_tag: "Do Next To…",
  },
  en: {
    nav_video: "Story",
    nav_levels: "Signal",
    nav_console: "Console",
    nav_how: "How",
    nav_app: "Open app",
    lang_label: "Language",
    kicker: "Attention on your email",
    hero_title: "Donexto",
    hero_tagline: "Do Next To… the next thing that actually matters.",
    hero_lede:
      "It reads Outlook, Hotmail, Gmail, Yahoo or iCloud and raises what needs action. Promotional noise stays off the cover. Not another inbox.",
    cta_app: "Enter Donexto",
    cta_video: "See the console",
    cta_app2: "Try the app",
    cta_app3: "Open the app",
    cta_mail: "support@donexto.com",
    trust_1: "Outlook and Hotmail: live with Microsoft",
    trust_2: "Yahoo and iCloud: app password, read-only",
    trust_3: "Gmail: OAuth on Google (app not verified yet)",
    video_title: "The signal, in 40 seconds",
    video_lede: "Say Do-NEX-to. Brand, standard, board.",
    video_caption: "Brand stills. Voiceover clip publishes when ready.",
    story_play: "Play",
    story_pause: "Pause",
    story_prev: "Back",
    story_next: "Next",
    story_vo_toggle: "Voiceover script",
    story_vo_full:
      "Donexto. Do Next To… Attention on personal email. What needs action rises; the offer waits. Outlook on Microsoft; Gmail on Google; Yahoo and iCloud with an app password. You confirm, authorize reading, and you see what to do next. app.donexto.com",
    scope_title: 'My spheres',
    scope_lede:
      'Donexto sorts your email into three spheres of your life. The app decides on its own where each notice belongs and learns when you correct it.',
    scope_1_t: 'Home',
    scope_1_p: "House, family, school, utilities, orders, and your family's health.",
    scope_2_t: 'Occupation',
    scope_2_p: 'Work, business, or profession: clients, meetings, invoices, and documents.',
    scope_3_t: 'Personal',
    scope_3_p: 'Just you: your purchases, subscriptions, trips, friends, and finances.',
    scope_areas:
      '13 areas: Money & finance · Shopping & orders · Subscriptions & services · Work & business · Home & family · Health & wellness · Bills & due dates · Travel & bookings · Security & accounts · Government & documents · Education · Agenda (events, tickets, concerts, conferences, games) · Social & communications. Areas are being rolled out in stages; early classification can be wrong and you can correct it.',
    price_title: 'Clear pricing',
    price_lede: '3-day free trial (coming soon). Then a monthly or annual plan.',
    price_plan_t: 'Monthly plan: US$19.99 / €19.99',
    price_plan_p: 'What 4 lattes cost a month (one a week, about US$26), discounted to US$19.99. Cancel anytime. When the trial ends nothing is charged unless you subscribe.',
    price_annual_t: 'Annual plan: US$175.99 / €175.99',
    price_annual_p: 'What 3 lattes cost a month, plus 1 month free: about 26.7% less than 12 months of the monthly plan (US$239.88).',
    price_import_t: 'How much email we bring in at the start',
    price_import_p: 'Monthly plan: the last 90 days of your email. Annual plan: the last 6 months.',
    price_fx_t: 'Why do I see another currency?',
    price_fx_p: "We show the price converted to your country's currency, detected from your connection, as an approximate reference. The actual charge is in US dollars (USD) in the Americas and in euros (EUR) in the European Union and the rest of the world. Your bank may apply its own exchange rate and fees. Payments are handled by our payment processor, which also calculates taxes.",
    levels_title: "Three tempos",
    levels_lede:
      "Not every message earns an alert. The system chooses when to interrupt and when to stay quiet.",
    n1_badge: "N1 · Now",
    n1_title: "Interrupts",
    n1_p: "If it needs action now — a payment, a package, a sign-in, school — it can reach the phone.",
    n1_hint: "",
    n2_badge: "N2 · When you can",
    n2_title: "Summarizes",
    n2_p: "Calendar, VIP contacts, and alerts you asked for. Digest—not a nudge.",
    n2_hint: "",
    n3_badge: "N3 · Silent",
    n3_title: "Files away",
    n3_p: "Offers, social, and bulk newsletters. Archived. Never on the cover.",
    n3_hint: "",
    how_title: "How it connects",
    how_1_t: "Identity",
    how_1_p:
      "Outlook and Hotmail identify you on Microsoft. Gmail on Google (the app is not verified yet). Yahoo and iCloud use an app password in app.donexto.com, not on this site. Gmail, Yahoo and iCloud still get Donexto’s verification email.",
    how_2_t: "Reading",
    how_2_p:
      "Outlook/Hotmail authorize on Microsoft (Mail.Read). Gmail on Google (gmail.readonly). Yahoo and iCloud over IMAP with an app password (Yahoo mail-r still pending). Read-only; Donexto does not ask for the account password.",
    how_3_t: "Console",
    how_3_p: "You see classified priority. The original mailbox is not deleted or rewritten.",
    console_title: "Console",
    console_lede:
      "Three prototypes of the same board. Same standard; different accent. The app ships the executive view.",
    proto_a_k: "Prototype A",
    proto_a_t: "Priority",
    proto_b_k: "Prototype B · in the app",
    proto_b_t: "Executive",
    proto_c_k: "Prototype C",
    proto_c_t: "Operations",
    market_title: "Why not another inbox",
    market_lede:
      "Most volume is offers. Donexto is for personal email: it raises what needs action and quiets the rest.",
    stat1_v: "High N1",
    stat1_l: "Acceptance of useful alerts",
    stat2_v: ">60%",
    stat2_l: "Volume = offers & newsletters",
    stat3_v: "Mobile",
    stat3_l: "Where personal email is opened",
    market_note: "Product hypotheses—not certified advertising claims.",
    wait_title: "Start with your email",
    wait_lede: "The app is at app.donexto.com. We write from support@donexto.com.",
    or_wait: "Or leave a message",
    label_name: "Name",
    label_email: "Email",
    label_country: "Country",
    label_message: "Message",
    ph_name: "Alex",
    ph_email: "you@email.com",
    ph_message: "Tell us how we can help",
    opt_us: "United States",
    opt_mx: "Mexico",
    opt_other: "Other",
    btn_join: "Send",
    btn_sending: "Sending…",
    form_note: "It goes to support@donexto.com. We don’t sell lists.",
    form_ok: "Sent. We received your message.",
    form_err: "Enter a valid email.",
    form_msg_err: "Write a message.",
    form_send_err: "Could not send. Email us at",
    social_title: "Channel",
    foot_tag: "Do Next To…",
  },
  fr: {
    nav_video: "Histoire",
    nav_levels: "Critère",
    nav_console: "Console",
    nav_how: "Comment",
    nav_app: "Ouvrir l’app",
    lang_label: "Langue",
    kicker: "Attention sur votre courrier",
    hero_title: "Donexto",
    hero_tagline: "Do Next To… la prochaine chose qui compte vraiment.",
    hero_lede:
      "Il lit Outlook, Hotmail, Gmail, Yahoo ou iCloud et fait remonter ce qui demande une action. Le bruit promotionnel reste hors couverture. Ce n’est pas une autre boîte.",
    cta_app: "Entrer dans Donexto",
    cta_video: "Voir la console",
    cta_app2: "Essayer l’app",
    cta_app3: "Ouvrir l’app",
    cta_mail: "support@donexto.com",
    trust_1: "Outlook et Hotmail : en ligne avec Microsoft",
    trust_2: "Yahoo et iCloud : mot de passe d’app, lecture seule",
    trust_3: "Gmail : OAuth chez Google (app pas encore vérifiée)",
    video_title: "Le critère, en 40 secondes",
    video_lede: "On dit Do-NEX-to. Marque, critère, tableau.",
    video_caption: "Images de marque. Le clip avec voix sera publié quand il sera prêt.",
    story_play: "Lecture",
    story_pause: "Pause",
    story_prev: "Précédent",
    story_next: "Suivant",
    story_vo_toggle: "Script (voix off)",
    story_vo_full:
      "Donexto. Do Next To… Attention sur votre courrier personnel. Ce qui demande une action monte ; l’offre attend. Outlook chez Microsoft ; Gmail chez Google ; Yahoo et iCloud avec mot de passe d’app. Vous confirmez, autorisez la lecture et voyez la suite. app.donexto.com",
    scope_title: 'Mes sphères',
    scope_lede:
      'Donexto range votre courrier dans trois sphères de votre vie. L’app décide seule où va chaque avis et apprend quand vous la corrigez.',
    scope_1_t: 'Foyer',
    scope_1_p: 'Maison, famille, école, services, commandes et santé des vôtres.',
    scope_2_t: 'Occupation',
    scope_2_p: 'Travail, entreprise ou profession : clients, réunions, factures et documents.',
    scope_3_t: 'Personnel',
    scope_3_p: 'Vous : vos achats, abonnements, voyages, amis et finances.',
    scope_areas:
      '13 domaines : Argent et finances · Achats et commandes · Abonnements et services · Travail et affaires · Foyer et famille · Santé et bien-être · Factures et échéances · Voyages et réservations · Sécurité et comptes · Administration et documents · Éducation · Agenda (événements, billets, concerts, conférences, matchs) · Social et communications. Les domaines arrivent par étapes ; au début, le classement peut se tromper et vous le corrigez.',
    price_title: 'Un prix clair',
    price_lede: 'Essai gratuit de 3 jours (bientôt). Ensuite, un abonnement mensuel ou annuel.',
    price_plan_t: 'Abonnement mensuel : 19,99 US$ / 19,99 €',
    price_plan_p: 'Le prix de 4 cafés latte par mois (un par semaine, environ 26 US$), réduit à 19,99. Résiliable à tout moment. À la fin de l’essai, rien n’est facturé sauf si vous vous abonnez.',
    price_annual_t: 'Abonnement annuel : 175,99 US$ / 175,99 €',
    price_annual_p: 'Le prix de 3 cafés latte par mois, plus 1 mois offert : environ 26,7 % de moins que 12 mois de l’abonnement mensuel (239,88 US$).',
    price_import_t: 'Combien de courrier nous importons au départ',
    price_import_p: 'Abonnement mensuel : les 90 derniers jours de votre courrier. Abonnement annuel : les 6 derniers mois.',
    price_fx_t: 'Pourquoi une autre devise ?',
    price_fx_p: 'Nous affichons le prix converti dans la devise de votre pays, détecté via votre connexion, à titre indicatif. Le paiement réel se fait en dollars (USD) sur le continent américain et en euros (EUR) dans l’Union européenne et le reste du monde. Votre banque peut appliquer son propre taux de change et ses frais. Les paiements sont traités par notre prestataire de paiement, qui calcule aussi les taxes.',
    levels_title: "Trois rythmes",
    levels_lede:
      "Chaque message ne mérite pas une alerte. Le système choisit quand interrompre et quand se taire.",
    n1_badge: "N1 · Maintenant",
    n1_title: "Interrompt",
    n1_p: "S’il faut agir maintenant — un paiement, un colis, un accès, l’école — cela peut sonner sur le téléphone.",
    n1_hint: "",
    n2_badge: "N2 · Quand vous pouvez",
    n2_title: "Résume",
    n2_p: "Agenda, contacts VIP et alertes que vous avez demandées. Un résumé, pas une poussée.",
    n2_hint: "",
    n3_badge: "N3 · En silence",
    n3_title: "Classe et range",
    n3_p: "Offres, réseaux et bulletins de masse. Archivés. Jamais en couverture.",
    n3_hint: "",
    how_title: "Comment ça se connecte",
    how_1_t: "Identité",
    how_1_p:
      "Outlook et Hotmail vous identifient chez Microsoft. Gmail chez Google (l’app n’est pas encore vérifiée). Yahoo et iCloud utilisent un mot de passe d’application sur app.donexto.com, pas sur ce site. Gmail, Yahoo et iCloud reçoivent quand même l’e-mail de vérification Donexto.",
    how_2_t: "Lecture",
    how_2_p:
      "Outlook/Hotmail s’autorisent chez Microsoft (Mail.Read). Gmail chez Google (gmail.readonly). Yahoo et iCloud en IMAP avec mot de passe d’app (mail-r Yahoo encore en attente). Lecture seule ; Donexto ne demande pas le mot de passe du compte.",
    how_3_t: "Console",
    how_3_p: "Vous voyez la priorité classée. La boîte d’origine n’est ni effacée ni réécrite.",
    console_title: "Console",
    console_lede:
      "Trois prototypes du même tableau. Même critère ; accent différent. L’app livre la vue exécutive.",
    proto_a_k: "Prototype A",
    proto_a_t: "Priorité",
    proto_b_k: "Prototype B · dans l’app",
    proto_b_t: "Exécutif",
    proto_c_k: "Prototype C",
    proto_c_t: "Opération",
    market_title: "Pourquoi pas une autre boîte",
    market_lede:
      "La plus grande partie du volume est de l’offre. Donexto est pour le courrier personnel : il fait monter ce qui demande une action et fait taire le reste.",
    stat1_v: "N1 élevé",
    stat1_l: "Acceptation des alertes utiles",
    stat2_v: ">60%",
    stat2_l: "Volume = offres et bulletins",
    stat3_v: "Mobile",
    stat3_l: "Là où le courrier personnel s’ouvre",
    market_note: "Hypothèses produit, pas de claims publicitaires certifiés.",
    wait_title: "Commencez avec votre e-mail",
    wait_lede: "L’app est sur app.donexto.com. Nous écrivons depuis support@donexto.com.",
    or_wait: "Ou laissez un message",
    label_name: "Nom",
    label_email: "E-mail",
    label_country: "Pays",
    label_message: "Message",
    ph_name: "Alex",
    ph_email: "vous@email.com",
    ph_message: "Dites-nous comment vous aider",
    opt_us: "États-Unis",
    opt_mx: "Mexique",
    opt_other: "Autre",
    btn_join: "Envoyer",
    btn_sending: "Envoi…",
    form_note: "Le message arrive à support@donexto.com. Nous ne vendons pas de listes.",
    form_ok: "Envoyé. Nous avons reçu votre message.",
    form_err: "Saisissez un e-mail valide.",
    form_msg_err: "Écrivez un message.",
    form_send_err: "Envoi impossible. Écrivez-nous à",
    social_title: "Canal",
    foot_tag: "Do Next To…",
  },
  it: {
    nav_video: "Storia",
    nav_levels: "Criterio",
    nav_console: "Console",
    nav_how: "Come",
    nav_app: "Apri app",
    lang_label: "Lingua",
    kicker: "Attenzione sulla tua posta",
    hero_title: "Donexto",
    hero_tagline: "Do Next To… la prossima cosa che conta davvero.",
    hero_lede:
      "Legge Outlook, Hotmail, Gmail, Yahoo o iCloud e porta in alto ciò che chiede azione. Il rumore promozionale resta fuori copertina. Non è un’altra casella.",
    cta_app: "Entra in Donexto",
    cta_video: "Vedi la console",
    cta_app2: "Prova l’app",
    cta_app3: "Apri l’app",
    cta_mail: "support@donexto.com",
    trust_1: "Outlook e Hotmail: attivi con Microsoft",
    trust_2: "Yahoo e iCloud: password per l’app, sola lettura",
    trust_3: "Gmail: OAuth su Google (app non ancora verificata)",
    video_title: "Il criterio, in 40 secondi",
    video_lede: "Si dice Do-NEX-to. Marca, criterio, cruscotto.",
    video_caption: "Immagini di marca. Il clip con voce si pubblica quando è pronto.",
    story_play: "Riproduci",
    story_pause: "Pausa",
    story_prev: "Indietro",
    story_next: "Avanti",
    story_vo_toggle: "Copione (voce)",
    story_vo_full:
      "Donexto. Do Next To… Attenzione sulla posta personale. Ciò che chiede azione sale; l’offerta aspetta. Outlook su Microsoft; Gmail su Google; Yahoo e iCloud con password per l’app. Confermi, autorizzi la lettura e vedi cosa fare. app.donexto.com",
    scope_title: 'Le mie sfere',
    scope_lede:
      'Donexto ordina la tua posta in tre sfere della tua vita. L’app decide da sola dove va ogni avviso e impara quando la correggi.',
    scope_1_t: 'Casa',
    scope_1_p: 'Casa, famiglia, scuola, servizi, ordini e salute dei tuoi.',
    scope_2_t: 'Occupazione',
    scope_2_p: 'Lavoro, attività o professione: clienti, riunioni, fatture e documenti.',
    scope_3_t: 'Personale',
    scope_3_p: 'Tu: i tuoi acquisti, abbonamenti, viaggi, amici e finanze.',
    scope_areas:
      '13 aree: Denaro e finanze · Acquisti e ordini · Abbonamenti e servizi · Lavoro e affari · Casa e famiglia · Salute e benessere · Bollette e scadenze · Viaggi e prenotazioni · Sicurezza e account · Pubblica amministrazione e documenti · Istruzione · Agenda (eventi, biglietti, concerti, conferenze, partite) · Social e comunicazioni. Le aree arrivano per fasi; all’inizio la classificazione può sbagliare e tu la correggi.',
    price_title: 'Prezzo chiaro',
    price_lede: 'Prova gratuita di 3 giorni (in arrivo). Poi un piano mensile o annuale.',
    price_plan_t: 'Piano mensile: US$19,99 / €19,99',
    price_plan_p: 'Quanto 4 caffè latte al mese (uno a settimana, circa US$26), scontato a 19,99. Disdici quando vuoi. Alla fine della prova non viene addebitato nulla, a meno che tu non ti abboni.',
    price_annual_t: 'Piano annuale: US$175,99 / €175,99',
    price_annual_p: 'Quanto 3 caffè latte al mese, più 1 mese gratis: circa il 26,7% in meno rispetto a 12 mesi del piano mensile (US$239,88).',
    price_import_t: 'Quanta posta importiamo all’inizio',
    price_import_p: 'Piano mensile: gli ultimi 90 giorni della tua posta. Piano annuale: gli ultimi 6 mesi.',
    price_fx_t: 'Perché vedo un’altra valuta?',
    price_fx_p: 'Mostriamo il prezzo convertito nella valuta del tuo paese, rilevato dalla tua connessione, come riferimento approssimativo. L’addebito reale è in dollari (USD) nelle Americhe e in euro (EUR) nell’Unione europea e nel resto del mondo. La tua banca può applicare il proprio cambio e commissioni. I pagamenti sono gestiti dal nostro processore di pagamento, che calcola anche le imposte.',
    levels_title: "Tre ritmi",
    levels_lede:
      "Non ogni messaggio merita un avviso. Il sistema sceglie quando interrompere e quando stare zitto.",
    n1_badge: "N1 · Ora",
    n1_title: "Interrompe",
    n1_p: "Se serve agire ora — un pagamento, un pacco, un accesso, la scuola — può suonare sul telefono.",
    n1_hint: "",
    n2_badge: "N2 · Quando puoi",
    n2_title: "Riassume",
    n2_p: "Agenda, contatti VIP e avvisi che hai chiesto. Un riepilogo, non una spinta.",
    n2_hint: "",
    n3_badge: "N3 · In silenzio",
    n3_title: "Classifica e archivia",
    n3_p: "Offerte, social e newsletter di massa. Archiviati. Mai in copertina.",
    n3_hint: "",
    how_title: "Come si collega",
    how_1_t: "Identità",
    how_1_p:
      "Outlook e Hotmail ti identificano su Microsoft. Gmail su Google (l’app non è ancora verificata). Yahoo e iCloud usano una password per l’app su app.donexto.com, non su questo sito. Gmail, Yahoo e iCloud ricevono comunque l’e-mail di verifica Donexto.",
    how_2_t: "Lettura",
    how_2_p:
      "Outlook/Hotmail si autorizzano su Microsoft (Mail.Read). Gmail su Google (gmail.readonly). Yahoo e iCloud via IMAP con password per l’app (mail-r Yahoo ancora in attesa). Sola lettura; Donexto non chiede la password dell’account.",
    how_3_t: "Console",
    how_3_p: "Vedi la priorità classificata. La casella originale non si cancella né si riscrive.",
    console_title: "Console",
    console_lede:
      "Tre prototipi dello stesso cruscotto. Stesso criterio; accento diverso. L’app spedisce la vista esecutiva.",
    proto_a_k: "Prototipo A",
    proto_a_t: "Priorità",
    proto_b_k: "Prototipo B · nell’app",
    proto_b_t: "Esecutivo",
    proto_c_k: "Prototipo C",
    proto_c_t: "Operazione",
    market_title: "Perché non un’altra casella",
    market_lede:
      "Gran parte del volume è offerta. Donexto è per la posta personale: alza ciò che chiede azione e zittisce il resto.",
    stat1_v: "N1 alto",
    stat1_l: "Accettazione di avvisi utili",
    stat2_v: ">60%",
    stat2_l: "Volume = offerte e newsletter",
    stat3_v: "Mobile",
    stat3_l: "Dove si apre la posta personale",
    market_note: "Ipotesi di prodotto, non claim pubblicitari certificati.",
    wait_title: "Inizia con la tua email",
    wait_lede: "L’app è su app.donexto.com. Scriviamo da support@donexto.com.",
    or_wait: "Oppure lascia un messaggio",
    label_name: "Nome",
    label_email: "Email",
    label_country: "Paese",
    label_message: "Messaggio",
    ph_name: "Alex",
    ph_email: "tu@email.com",
    ph_message: "Dicci come possiamo aiutarti",
    opt_us: "Stati Uniti",
    opt_mx: "Messico",
    opt_other: "Altro",
    btn_join: "Invia",
    btn_sending: "Invio…",
    form_note: "Arriva a support@donexto.com. Non vendiamo liste.",
    form_ok: "Inviato. Abbiamo ricevuto il messaggio.",
    form_err: "Inserisci un’email valida.",
    form_msg_err: "Scrivi un messaggio.",
    form_send_err: "Invio non riuscito. Scrivici a",
    social_title: "Canale",
    foot_tag: "Do Next To…",
  },
  pt: {
    nav_video: "História",
    nav_levels: "Critério",
    nav_console: "Consola",
    nav_how: "Como",
    nav_app: "Abrir app",
    lang_label: "Idioma",
    kicker: "Atenção sobre o seu correio",
    hero_title: "Donexto",
    hero_tagline: "Do Next To… o que segue e importa.",
    hero_lede:
      "Lê Outlook, Hotmail, Gmail, Yahoo ou iCloud e sobe o que pede ação. O ruído promocional fica fora da capa. Não é outra caixa.",
    cta_app: "Entrar no Donexto",
    cta_video: "Ver a consola",
    cta_app2: "Provar a app",
    cta_app3: "Abrir a app",
    cta_mail: "support@donexto.com",
    trust_1: "Outlook e Hotmail: ao vivo com a Microsoft",
    trust_2: "Yahoo e iCloud: palavra-passe de app, só leitura",
    trust_3: "Gmail: OAuth no Google (app ainda não verificada)",
    video_title: "O critério, em 40 segundos",
    video_lede: "Diz-se Do-NEX-to. Marca, critério e quadro.",
    video_caption: "Imagens de marca. O clipe com voz publica-se quando estiver pronto.",
    story_play: "Reproduzir",
    story_pause: "Pausar",
    story_prev: "Anterior",
    story_next: "Seguinte",
    story_vo_toggle: "Guião (voz off)",
    story_vo_full:
      "Donexto. Do Next To… Atenção sobre o correio pessoal. O que pede ação sobe; a oferta espera. Outlook na Microsoft; Gmail no Google; Yahoo e iCloud com palavra-passe de app. Confirma, autoriza a leitura e vê o que segue. app.donexto.com",
    scope_title: 'Minhas esferas',
    scope_lede:
      'O Donexto organiza o seu correio em três esferas da sua vida. A app decide sozinha onde fica cada aviso e aprende quando você a corrige.',
    scope_1_t: 'Casa',
    scope_1_p: 'Casa, família, escola, serviços, encomendas e saúde dos seus.',
    scope_2_t: 'Ocupação',
    scope_2_p: 'Trabalho, negócio ou profissão: clientes, reuniões, faturas e documentos.',
    scope_3_t: 'Pessoal',
    scope_3_p: 'Você: suas compras, assinaturas, viagens, amigos e finanças.',
    scope_areas:
      '13 áreas: Dinheiro e finanças · Compras e encomendas · Assinaturas e serviços · Trabalho e negócios · Casa e família · Saúde e bem-estar · Faturas e vencimentos · Viagens e reservas · Segurança e contas · Governo e documentos · Educação · Agenda (eventos, ingressos, shows, conferências, jogos) · Social e comunicações. As áreas chegam por etapas; no início a classificação pode errar e você corrige.',
    price_title: 'Preço claro',
    price_lede: 'Teste grátis de 3 dias (em breve). Depois, um plano mensal ou anual.',
    price_plan_t: 'Plano mensal: US$19,99 / €19,99',
    price_plan_p: 'O que custam 4 cafés com leite por mês (um por semana, cerca de US$26), com desconto para 19,99. Cancele quando quiser. Ao terminar o teste nada é cobrado, a menos que você assine.',
    price_annual_t: 'Plano anual: US$175,99 / €175,99',
    price_annual_p: 'O que custam 3 cafés com leite por mês, mais 1 mês grátis: cerca de 26,7% menos que 12 meses do plano mensal (US$239,88).',
    price_import_t: 'Quanto correio trazemos no início',
    price_import_p: 'Plano mensal: os últimos 90 dias do seu correio. Plano anual: os últimos 6 meses.',
    price_fx_t: 'Por que vejo outra moeda?',
    price_fx_p: 'Mostramos o preço convertido para a moeda do seu país, detectado pela sua conexão, como referência aproximada. A cobrança real é em dólares (USD) nas Américas e em euros (EUR) na União Europeia e no resto do mundo. Seu banco pode aplicar a própria taxa de câmbio e tarifas. Os pagamentos são feitos pelo nosso processador de pagamentos, que também calcula os impostos.',
    levels_title: "Três ritmos",
    levels_lede:
      "Nem cada mensagem merece um aviso. O sistema decide quando interromper e quando calar.",
    n1_badge: "N1 · Agora",
    n1_title: "Interrompe",
    n1_p: "Se pede ação agora — um pagamento, um pacote, um acesso, a escola — pode soar no telemóvel.",
    n1_hint: "",
    n2_badge: "N2 · Quando puder",
    n2_title: "Resume",
    n2_p: "Agenda, contactos VIP e avisos que pediu. Um resumo, não um empurrão.",
    n2_hint: "",
    n3_badge: "N3 · Em silêncio",
    n3_title: "Classifica e guarda",
    n3_p: "Ofertas, redes e boletins em massa. Arquivados. Nunca na capa.",
    n3_hint: "",
    how_title: "Como se liga",
    how_1_t: "Identidade",
    how_1_p:
      "Outlook e Hotmail identificam-no na Microsoft. Gmail no Google (a app ainda não está verificada). Yahoo e iCloud usam uma palavra-passe de app em app.donexto.com, não neste site. Gmail, Yahoo e iCloud recebem na mesma o e-mail de verificação do Donexto.",
    how_2_t: "Leitura",
    how_2_p:
      "Outlook/Hotmail autorizam-se na Microsoft (Mail.Read). Gmail no Google (gmail.readonly). Yahoo e iCloud por IMAP com palavra-passe de app (mail-r do Yahoo ainda pendente). Só leitura; o Donexto não pede a palavra-passe da conta.",
    how_3_t: "Consola",
    how_3_p: "Vê a prioridade classificada. A caixa original não se apaga nem se reescreve.",
    console_title: "Consola",
    console_lede:
      "Três protótipos do mesmo quadro. O mesmo critério; sotaque diferente. A app envia a vista executiva.",
    proto_a_k: "Protótipo A",
    proto_a_t: "Prioridade",
    proto_b_k: "Protótipo B · na app",
    proto_b_t: "Executivo",
    proto_c_k: "Protótipo C",
    proto_c_t: "Operação",
    market_title: "Por que não outra caixa",
    market_lede:
      "A maior parte do volume é oferta. O Donexto é para o correio pessoal: sobe o que pede ação e cala o resto.",
    stat1_v: "N1 alto",
    stat1_l: "Aceitação de avisos úteis",
    stat2_v: ">60%",
    stat2_l: "Volume = ofertas e boletins",
    stat3_v: "Telemóvel",
    stat3_l: "Onde se abre o correio pessoal",
    market_note: "Hipótese de produto, não claims publicitários certificados.",
    wait_title: "Comece com o seu correio",
    wait_lede: "A app está em app.donexto.com. Escrevemos de support@donexto.com.",
    or_wait: "Ou deixe uma mensagem",
    label_name: "Nome",
    label_email: "Correio",
    label_country: "País",
    label_message: "Mensagem",
    ph_name: "Alex",
    ph_email: "voce@email.com",
    ph_message: "Conte-nos como podemos ajudar",
    opt_us: "Estados Unidos",
    opt_mx: "México",
    opt_other: "Outro",
    btn_join: "Enviar",
    btn_sending: "A enviar…",
    form_note: "Chega a support@donexto.com. Não vendemos listas.",
    form_ok: "Enviado. Recebemos a sua mensagem.",
    form_err: "Escreva um correio válido.",
    form_msg_err: "Escreva uma mensagem.",
    form_send_err: "Não foi possível enviar. Escreva para",
    social_title: "Canal",
    foot_tag: "Do Next To…",
  },
};

const storyShots = {
  es: [
    {
      id: "marca",
      duration: 6,
      label: "01 · 0:00–0:06",
      chapter: "Marca",
      line: "Donexto. Do Next To… Atención sobre tu correo personal.",
      html: `<img class="vis-photo" src="./brand-youtube.webp" alt="" />`,
    },
    {
      id: "para-quien",
      duration: 8,
      label: "02 · 0:06–0:14",
      chapter: "Criterio",
      line: "Lo que pide acción. El resto espera.",
      html: `<img class="vis-photo wide" src="./brand-escritorio.webp" alt="" />`,
    },
    {
      id: "google",
      duration: 8,
      label: "03 · 0:14–0:22",
      chapter: "Acceso",
      line: "Outlook en Microsoft. Gmail en Google. Yahoo e iCloud con clave de app.",
      html: `
        <div class="vis-steps">
          <div class="vis-step"><span>1</span><strong>Outlook</strong><p style="margin:.35rem 0 0;color:var(--muted);font-size:.85rem">Microsoft</p></div>
          <div class="vis-step"><span>2</span><strong>Gmail</strong><p style="margin:.35rem 0 0;color:var(--muted);font-size:.85rem">Google</p></div>
          <div class="vis-step"><span>3</span><strong>Yahoo / iCloud</strong><p style="margin:.35rem 0 0;color:var(--muted);font-size:.85rem">clave de app</p></div>
        </div>`,
    },
    {
      id: "mismo-gmail",
      duration: 6,
      label: "04 · 0:22–0:28",
      chapter: "Cuenta",
      line: "El mismo correo es cuenta Donexto y buzón vigilado.",
      html: `
        <div class="vis-phone">
          <span class="vis-chip">tú@correo.com</span>
          <div class="vis-row good"><strong>Cuenta Donexto</strong><span class="tag">mismo</span></div>
          <div class="vis-row good"><strong>Buzón</strong><span class="tag">mismo</span></div>
        </div>`,
    },
    {
      id: "verificar",
      duration: 7,
      label: "05 · 0:28–0:35",
      chapter: "Lectura",
      line: "Confirmas el mail y autorizas la lectura. El buzón no se reescribe.",
      html: `
        <div class="vis-stack">
          <div class="vis-row"><strong>Correo de Donexto</strong><em>confirmar</em></div>
          <div class="vis-row good"><strong>Autorizas lectura</strong><span class="tag">OK</span></div>
        </div>`,
    },
    {
      id: "priorizar",
      duration: 5,
      label: "06 · 0:35–0:40",
      chapter: "Consola",
      line: "La consola muestra qué sigue. app.donexto.com",
      html: `
        <div class="vis-cta">
          <img class="vis-photo" src="./brand-youtube.webp" alt="" />
          <strong>app.donexto.com</strong>
          <span>Donexto · Do Next To…</span>
        </div>`,
    },
  ],
  en: [
    {
      id: "marca",
      duration: 6,
      label: "01 · 0:00–0:06",
      chapter: "Brand",
      line: "Donexto. Do Next To… Attention on personal email.",
      html: `<img class="vis-photo" src="./brand-youtube.webp" alt="" />`,
    },
    {
      id: "para-quien",
      duration: 8,
      label: "02 · 0:06–0:14",
      chapter: "Standard",
      line: "What needs action. Everything else waits.",
      html: `<img class="vis-photo wide" src="./brand-escritorio.webp" alt="" />`,
    },
    {
      id: "google",
      duration: 8,
      label: "03 · 0:14–0:22",
      chapter: "Access",
      line: "Outlook on Microsoft. Gmail on Google. Yahoo and iCloud with an app password.",
      html: `
        <div class="vis-steps">
          <div class="vis-step"><span>1</span><strong>Outlook</strong><p style="margin:.35rem 0 0;color:var(--muted);font-size:.85rem">Microsoft</p></div>
          <div class="vis-step"><span>2</span><strong>Gmail</strong><p style="margin:.35rem 0 0;color:var(--muted);font-size:.85rem">Google</p></div>
          <div class="vis-step"><span>3</span><strong>Yahoo / iCloud</strong><p style="margin:.35rem 0 0;color:var(--muted);font-size:.85rem">app password</p></div>
        </div>`,
    },
    {
      id: "mismo-gmail",
      duration: 6,
      label: "04 · 0:22–0:28",
      chapter: "Account",
      line: "The same address is Donexto account and watched mailbox.",
      html: `
        <div class="vis-phone">
          <span class="vis-chip">you@email.com</span>
          <div class="vis-row good"><strong>Donexto account</strong><span class="tag">same</span></div>
          <div class="vis-row good"><strong>Mailbox</strong><span class="tag">same</span></div>
        </div>`,
    },
    {
      id: "verificar",
      duration: 7,
      label: "05 · 0:28–0:35",
      chapter: "Reading",
      line: "You confirm the email and authorize reading. The mailbox is not rewritten.",
      html: `
        <div class="vis-stack">
          <div class="vis-row"><strong>Email from Donexto</strong><em>confirm</em></div>
          <div class="vis-row good"><strong>Authorize reading</strong><span class="tag">OK</span></div>
        </div>`,
    },
    {
      id: "priorizar",
      duration: 5,
      label: "06 · 0:35–0:40",
      chapter: "Console",
      line: "The console shows what to do next. app.donexto.com",
      html: `
        <div class="vis-cta">
          <img class="vis-photo" src="./brand-youtube.webp" alt="" />
          <strong>app.donexto.com</strong>
          <span>Donexto · Do Next To…</span>
        </div>`,
    },
  ],
};

const LANGUAGE_STORAGE_KEY = "donexto-language";
const APP_LANGUAGES = ["es", "en", "fr", "it", "pt"];

function isAppLanguage(value) {
  return APP_LANGUAGES.includes(value);
}

function readStoredLanguage() {
  try {
    const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    return isAppLanguage(stored) ? stored : null;
  } catch {
    return null;
  }
}

function writeStoredLanguage(next) {
  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, next);
  } catch {
    /* ignore */
  }
}

function languageFromBrowser() {
  const value = (navigator.language || "").toLowerCase();
  if (value.startsWith("es")) return "es";
  if (value.startsWith("en")) return "en";
  if (value.startsWith("fr")) return "fr";
  if (value.startsWith("it")) return "it";
  if (value.startsWith("pt")) return "pt";
  return "es";
}

let lang = readStoredLanguage() || languageFromBrowser();
let shotIndex = 0;
let playing = false;
let rafId = 0;
let shotStartedAt = 0;
let elapsedInShot = 0;

function shots() {
  return storyShots[lang] || storyShots.en;
}

function totalDuration() {
  return shots().reduce((s, x) => s + x.duration, 0);
}

function formatTime(sec) {
  const s = Math.max(0, Math.floor(sec));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${String(r).padStart(2, "0")}`;
}

function timeBeforeShot(i) {
  return shots()
    .slice(0, i)
    .reduce((s, x) => s + x.duration, 0);
}

function renderShot(i, preserveProgress) {
  const list = shots();
  const shot = list[Math.max(0, Math.min(i, list.length - 1))];
  shotIndex = list.indexOf(shot);

  const visual = document.getElementById("storyVisual");
  const line = document.getElementById("storyLine");
  const label = document.getElementById("storyShotLabel");
  if (visual) visual.innerHTML = shot.html;
  if (line) line.textContent = shot.line;
  if (label) label.textContent = shot.label;

  document.querySelectorAll("#storyChapters button").forEach((btn, idx) => {
    btn.setAttribute("aria-current", idx === shotIndex ? "true" : "false");
  });

  if (!preserveProgress) {
    elapsedInShot = 0;
    shotStartedAt = performance.now();
  }
  updateProgress();
}

function updateProgress() {
  const list = shots();
  const shot = list[shotIndex];
  const total = totalDuration();
  const abs = timeBeforeShot(shotIndex) + Math.min(elapsedInShot, shot.duration);
  const pct = (abs / total) * 100;
  const bar = document.getElementById("storyProgress");
  const time = document.getElementById("storyTime");
  if (bar) bar.style.width = `${pct}%`;
  if (time) time.textContent = `${formatTime(abs)} / ${formatTime(total)}`;
}

function tick(now) {
  if (!playing) return;
  const list = shots();
  const shot = list[shotIndex];
  elapsedInShot = (now - shotStartedAt) / 1000;
  updateProgress();

  if (elapsedInShot >= shot.duration) {
    if (shotIndex < list.length - 1) {
      shotIndex += 1;
      renderShot(shotIndex, false);
    } else {
      playing = false;
      syncPlayButton();
      elapsedInShot = shot.duration;
      updateProgress();
      return;
    }
  }
  rafId = requestAnimationFrame(tick);
}

function setPlaying(next) {
  playing = next;
  syncPlayButton();
  if (playing) {
    shotStartedAt = performance.now() - elapsedInShot * 1000;
    cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(tick);
  } else {
    cancelAnimationFrame(rafId);
  }
}

function syncPlayButton() {
  const btn = document.getElementById("storyPlay");
  const dict = strings[lang] || strings.es;
  if (!btn) return;
  btn.textContent = playing ? dict.story_pause : dict.story_play;
}

function buildChapters() {
  const ol = document.getElementById("storyChapters");
  if (!ol) return;
  ol.innerHTML = "";
  shots().forEach((shot, idx) => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = shot.chapter;
    btn.addEventListener("click", () => {
      shotIndex = idx;
      renderShot(shotIndex, false);
      if (playing) {
        shotStartedAt = performance.now();
      }
    });
    li.appendChild(btn);
    ol.appendChild(li);
  });
}

function applyLang() {
  const wasPlaying = playing;
  if (wasPlaying) setPlaying(false);

  writeStoredLanguage(lang);
  const dict = strings[lang] || strings.es;
  document.documentElement.lang = lang;

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (!key || dict[key] == null) return;
    el.textContent = dict[key];
  });

  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (key && dict[key] != null) el.setAttribute("placeholder", dict[key]);
  });

  const langSelect = document.getElementById("langSelect");
  if (langSelect && langSelect.value !== lang) {
    langSelect.value = lang;
  }

  document.querySelectorAll('a[href^="mailto"]').forEach((mailBtn) => {
    const isCta =
      mailBtn.classList.contains("ghost") ||
      mailBtn.getAttribute("data-i18n") === "cta_mail";
    if (isCta) {
      mailBtn.setAttribute(
        "href",
        lang === "es"
          ? "mailto:support@donexto.com?subject=Donexto%20contacto"
          : "mailto:support@donexto.com?subject=Donexto%20contact",
      );
    }
  });

  buildChapters();
  shotIndex = Math.min(shotIndex, shots().length - 1);
  renderShot(shotIndex, false);
  syncPlayButton();
}

document.getElementById("langSelect")?.addEventListener("change", (event) => {
  const next = event.target?.value;
  if (!isAppLanguage(next) || next === lang) {
    return;
  }
  lang = next;
  writeStoredLanguage(next);
  applyLang();
});

document.getElementById("year").textContent = String(new Date().getFullYear());

document.getElementById("storyPlay")?.addEventListener("click", () => {
  if (!playing && shotIndex === shots().length - 1 && elapsedInShot >= shots()[shotIndex].duration - 0.05) {
    shotIndex = 0;
    renderShot(0, false);
  }
  setPlaying(!playing);
});

document.getElementById("storyPrev")?.addEventListener("click", () => {
  shotIndex = Math.max(0, shotIndex - 1);
  renderShot(shotIndex, false);
  if (playing) shotStartedAt = performance.now();
});

document.getElementById("storyNext")?.addEventListener("click", () => {
  shotIndex = Math.min(shots().length - 1, shotIndex + 1);
  renderShot(shotIndex, false);
  if (playing) shotStartedAt = performance.now();
});

const CONTACT_API =
  "/api/hms/public/contact";

function paintFormStatus(status, tone) {
  status.hidden = false;
  if (tone === "ok") {
    status.style.background = "rgba(36, 200, 202, 0.2)";
    status.style.color = "#9fe8e4";
    return;
  }
  status.style.background = "rgba(140, 40, 28, 0.28)";
  status.style.color = "#ffb4a8";
}

function paintSendFailure(status, dict) {
  paintFormStatus(status, "err");
  status.replaceChildren();
  status.append(document.createTextNode(`${dict.form_send_err} `));
  const link = document.createElement("a");
  link.href = "mailto:support@donexto.com";
  link.textContent = "support@donexto.com";
  status.append(link);
}

document.getElementById("waitForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const status = document.getElementById("formStatus");
  const button = form.querySelector('button[type="submit"]');
  const dict = strings[lang] || strings.es;
  const data = new FormData(form);
  const name = String(data.get("name") || "").trim();
  const email = String(data.get("email") || "").trim().toLowerCase();
  const country = String(data.get("country") || "MX");
  const message = String(data.get("message") || "").trim();
  const website = String(data.get("website") || "");
  const turnstileToken = String(data.get("cf-turnstile-response") || "");

  if (!email.includes("@") || email.length < 5) {
    paintFormStatus(status, "err");
    status.replaceChildren(document.createTextNode(dict.form_err));
    return;
  }
  if (!message) {
    paintFormStatus(status, "err");
    status.replaceChildren(document.createTextNode(dict.form_msg_err));
    return;
  }

  if (button) {
    button.disabled = true;
    button.textContent = dict.btn_sending || dict.btn_join;
  }

  try {
    const response = await fetch(CONTACT_API, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        name,
        email,
        country,
        message,
        lang,
        website,
        turnstile_token: turnstileToken,
      }),
      signal: AbortSignal.timeout(15000),
    });
    if (window.turnstile) window.turnstile.reset();
    if (!response.ok) {
      paintSendFailure(status, dict);
      return;
    }
    paintFormStatus(status, "ok");
    status.replaceChildren(document.createTextNode(dict.form_ok));
    form.reset();
  } catch {
    paintSendFailure(status, dict);
  } finally {
    if (button) {
      const current = strings[lang] || strings.es;
      button.disabled = false;
      button.textContent = current.btn_join;
    }
  }
});

applyLang();
