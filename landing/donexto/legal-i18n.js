/* Idioma de los textos legales: mismo almacenamiento que la home (donexto-language).
   El español vive en el HTML; EN/FR/IT/PT se cargan desde ./legal/<pagina>.<idioma>.html */
(function () {
  "use strict";
  var KEY = "donexto-language";
  var LANGS = ["es", "en", "fr", "it", "pt"];
  var LABELS = { es: "Español", en: "English", fr: "Français", it: "Italiano", pt: "Português" };
  var NAV = {
    es: { privacidad: "Privacidad", cookies: "Cookies", terminos: "Términos", app: "Abrir app", lang: "Idioma" },
    en: { privacidad: "Privacy", cookies: "Cookies", terminos: "Terms", app: "Open app", lang: "Language" },
    fr: { privacidad: "Confidentialité", cookies: "Cookies", terminos: "Conditions", app: "Ouvrir l’app", lang: "Langue" },
    it: { privacidad: "Privacy", cookies: "Cookie", terminos: "Termini", app: "Apri l’app", lang: "Lingua" },
    pt: { privacidad: "Privacidade", cookies: "Cookies", terminos: "Termos", app: "Abrir app", lang: "Idioma" }
  };
  var TITLES = {
    terminos: { es: null, en: "Terms of Service · Donexto", fr: "Conditions d’utilisation · Donexto", it: "Termini di servizio · Donexto", pt: "Termos de Serviço · Donexto" },
    privacidad: { es: null, en: "Privacy Policy · Donexto", fr: "Politique de confidentialité · Donexto", it: "Informativa sulla privacy · Donexto", pt: "Política de Privacidade · Donexto" },
    cookies: { es: null, en: "Cookie Policy · Donexto", fr: "Politique relative aux cookies · Donexto", it: "Cookie Policy · Donexto", pt: "Política de Cookies · Donexto" }
  };

  var match = /(terminos|privacidad|cookies)(\.html)?\/?$/.exec(window.location.pathname);
  if (!match) return;
  var page = match[1];
  var main = document.querySelector("main");
  if (!main) return;
  var spanish = main.innerHTML;
  var spanishTitle = document.title;

  function stored() {
    try { var v = window.localStorage.getItem(KEY); return LANGS.indexOf(v) >= 0 ? v : null; } catch (e) { return null; }
  }
  function store(v) { try { window.localStorage.setItem(KEY, v); } catch (e) { /* ignore */ } }
  function fromBrowser() {
    var v = (navigator.language || "").slice(0, 2).toLowerCase();
    return LANGS.indexOf(v) >= 0 ? v : "es";
  }
  function initial() {
    var q = new URLSearchParams(window.location.search).get("lang");
    if (q && LANGS.indexOf(q) >= 0) { store(q); return q; }
    return stored() || fromBrowser();
  }

  function navText(lang) {
    var t = NAV[lang] || NAV.es;
    document.querySelectorAll(".top-nav a").forEach(function (a) {
      var href = a.getAttribute("href") || "";
      if (href.indexOf("privacidad") >= 0) a.textContent = t.privacidad;
      else if (href.indexOf("cookies") >= 0) a.textContent = t.cookies;
      else if (href.indexOf("terminos") >= 0) a.textContent = t.terminos;
      else if (href.indexOf("app.donexto.com") >= 0) a.textContent = t.app;
    });
    var sel = document.getElementById("legal-lang");
    if (sel) { sel.value = lang; sel.setAttribute("aria-label", t.lang); }
  }

  function apply(lang) {
    document.documentElement.lang = lang === "es" ? "es-MX" : lang;
    navText(lang);
    if (lang === "es") {
      main.innerHTML = spanish;
      document.title = spanishTitle;
      return;
    }
    fetch("./legal/" + page + "." + lang + ".html", { credentials: "same-origin" })
      .then(function (r) { if (!r.ok) throw new Error(String(r.status)); return r.text(); })
      .then(function (html) {
        main.innerHTML = html;
        document.title = (TITLES[page] && TITLES[page][lang]) || spanishTitle;
        if (window.location.hash) {
          var el = document.getElementById(window.location.hash.slice(1));
          if (el) el.scrollIntoView();
        }
      })
      .catch(function () { main.innerHTML = spanish; document.title = spanishTitle; });
  }

  var nav = document.querySelector(".top-nav");
  if (nav) {
    var sel = document.createElement("select");
    sel.id = "legal-lang";
    sel.className = "nav-link subtle legal-lang";
    LANGS.forEach(function (l) {
      var o = document.createElement("option");
      o.value = l; o.textContent = LABELS[l];
      sel.appendChild(o);
    });
    sel.addEventListener("change", function () { store(sel.value); apply(sel.value); });
    nav.insertBefore(sel, nav.firstChild);
  }
  apply(initial());
})();
