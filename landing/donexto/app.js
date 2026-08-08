const strings = {
  en: {
    nav_cta: "Join waitlist",
    kicker: "Email intelligence · US & Mexico",
    hero_title: "What needs attention<br />in your email.",
    hero_lede:
      "Not another inbox. A dashboard for replies waiting on you, money moves, deadlines—and quiet silence for social and promotions.",
    cta_primary: "Join the waitlist",
    cta_mail: "hello@donexto.com",
    trust_1: "Web + phone + tablet · PWA-ready",
    trust_2: "Start with Gmail · more providers next",
    trust_3: "Built for real people, not mail clutter",
    how_title: "One job",
    how_1_t: "See priorities",
    how_1_p: "Who is waiting, what is due, what can wait until next week.",
    how_2_t: "Track money signals",
    how_2_p: "Banks, charges, failed payments, invoices that need a decision.",
    how_3_t: "Mute the noise",
    how_3_p: "Social and promotions stay classified—never the front page.",
    wait_title: "Get early access",
    wait_lede:
      "Stage one: limited seats while we stabilize for the first subscribers. Leave your email—we write from hello@donexto.com.",
    label_name: "Name",
    label_email: "Email",
    label_country: "Country",
    ph_name: "Alex",
    ph_email: "you@company.com",
    opt_us: "United States",
    opt_mx: "Mexico",
    opt_other: "Other",
    btn_join: "Request access",
    form_note:
      "Opens your email app to message hello@donexto.com. No spam list sold. Ever.",
    form_ok: "Almost done—send the email that just opened to join the waitlist.",
    form_err: "Please enter a valid email.",
    social_title: "Follow the build",
    foot_tag: "Priorities from your email.",
  },
  es: {
    nav_cta: "Lista de espera",
    kicker: "Inteligencia de correo · EE. UU. y México",
    hero_title: "Lo que requiere tu atención<br />en el correo.",
    hero_lede:
      "No es otra bandeja. Un panel de quién espera respuesta, movimientos de dinero, plazos—y silencio para social y promociones.",
    cta_primary: "Unirme a la lista",
    cta_mail: "hola@donexto.com",
    trust_1: "Web + móvil + tablet · listo para PWA",
    trust_2: "Empezamos con Gmail · más proveedores después",
    trust_3: "Hecho para personas, no para el caos del inbox",
    how_title: "Un solo trabajo",
    how_1_t: "Ver prioridades",
    how_1_p: "Quién espera, qué vence, qué puede esperar a la próxima semana.",
    how_2_t: "Señales de dinero",
    how_2_p: "Bancos, cargos, pagos fallidos, facturas que piden una decisión.",
    how_3_t: "Silenciar el ruido",
    how_3_p: "Social y promociones clasificados—nunca en la portada.",
    wait_title: "Acceso anticipado",
    wait_lede:
      "Etapa uno: cupos limitados mientras estabilizamos a los primeros suscriptores. Déjanos tu correo—escribimos desde hola@donexto.com.",
    label_name: "Nombre",
    label_email: "Correo",
    label_country: "País",
    ph_name: "Alex",
    ph_email: "tu@empresa.com",
    opt_us: "Estados Unidos",
    opt_mx: "México",
    opt_other: "Otro",
    btn_join: "Pedir acceso",
    form_note:
      "Abre tu app de correo hacia hola@donexto.com. No vendemos listas. Nunca.",
    form_ok: "Casi listo—envía el correo que se abrió para entrar a la lista.",
    form_err: "Escribe un correo válido.",
    social_title: "Sigue el avance",
    foot_tag: "Prioridades desde tu correo.",
  },
};

let lang = "en";

function applyLang() {
  const dict = strings[lang];
  document.documentElement.lang = lang === "es" ? "es" : "en";

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (!key || dict[key] == null) return;
    if (key === "hero_title") {
      el.innerHTML = dict[key];
    } else {
      el.textContent = dict[key];
    }
  });

  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (key && dict[key] != null) el.setAttribute("placeholder", dict[key]);
  });

  const toggle = document.getElementById("langToggle");
  if (toggle) toggle.textContent = lang === "en" ? "ES" : "EN";

  const mailBtn = document.querySelector('a.btn.ghost[href^="mailto"]');
  if (mailBtn) {
    mailBtn.setAttribute(
      "href",
      lang === "es" ? "mailto:hola@donexto.com" : "mailto:hello@donexto.com",
    );
  }
}

document.getElementById("langToggle")?.addEventListener("click", () => {
  lang = lang === "en" ? "es" : "en";
  applyLang();
});

document.getElementById("year").textContent = String(new Date().getFullYear());

document.getElementById("waitForm")?.addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const status = document.getElementById("formStatus");
  const dict = strings[lang];
  const data = new FormData(form);
  const name = String(data.get("name") || "").trim();
  const email = String(data.get("email") || "").trim().toLowerCase();
  const country = String(data.get("country") || "US");

  if (!email.includes("@") || email.length < 5) {
    status.hidden = false;
    status.textContent = dict.form_err;
    status.style.background = "rgba(140, 40, 28, 0.28)";
    status.style.color = "#ffb4a8";
    return;
  }

  const to = lang === "es" ? "hola@donexto.com" : "hello@donexto.com";
  const subject = encodeURIComponent("Donexto waitlist");
  const body = encodeURIComponent(
    [
      "Donexto waitlist request",
      "",
      `Name: ${name || "(not provided)"}`,
      `Email: ${email}`,
      `Country: ${country}`,
      `Lang: ${lang}`,
      `Source: donexto.com landing`,
    ].join("\n"),
  );

  status.hidden = false;
  status.textContent = dict.form_ok;
  status.style.background = "rgba(30, 90, 55, 0.28)";
  status.style.color = "#9fe0b4";

  window.location.href = `mailto:${to}?subject=${subject}&body=${body}`;
});

applyLang();
