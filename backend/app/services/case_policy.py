"""Which emails become a case, and which case they join (rule-based, no AI).

``decide`` reads one stored message and answers three questions:

1. **Is it noise?** Promotions are caught by *content* (insight kind
   ``promo``, marketing sub-domain / local part, or unsubscribe footer)
   before they can fall into "review".
2. **Does it create a case?** Only the event types listed in
   ``CASE_KINDS``. Everything in ``NEVER_CASE`` stays a notice
   (codes, links, receipts, transfers, statements without an amount,
   terms updates, generic sign-in alerts, promos).
3. **Which case?** A deterministic ``group_key`` built from the sender
   and stable facts (merchant, card ending, order reference), so 58
   "Rechazo por saldo insuficiente" emails become one case per merchant,
   not 58 cases and not one giant case.

Pure function: no network, no database, no writes. Same input → same
output. The import path (``safe_case_classifier``) applies the decision.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.services.classification_catalog import identify_sender, is_marketing_local_part
from app.services.mail_insights import (
    _PERSONAL_DOMAINS,
    _RULES,
    LANGS,
    _is_marketing_domain,
    _sender_parts,
    build_insight,
    fold,
)
from app.utils.mail_clean import clean_subject, strip_subject_prefix

POLICY_VERSION = "case-policy-v1"
USER_TZ = ZoneInfo("America/Mexico_City")

# ------------------------------------------------------------ the list

#: Event types that create (or join) a case. Anything else never creates one.
CASE_KINDS: dict[str, str] = {
    "payment_declined": "Cobro rechazado (tarjeta o suscripción): un caso por comercio.",
    "bill_due": "Recibo o adeudo con monto o fecha límite (luz, teléfono, ISSSTE FOPI): un caso por proveedor.",
    "debt_overdue": "Crédito o tarjeta vencida: un caso crítico por acreedor.",
    "debt_offer": "Oferta de liquidación de cobranza: un caso por acreedor, con precaución.",
    "card_failed": "Tarjeta que no se pudo entregar o fue devuelta.",
    "order_in_transit": "Pedido en camino: un caso por pedido; la entrega lo cierra.",
    "security_change": "Cambio sensible de seguridad (contraseña de app, 2 pasos, app nueva con acceso).",
    "job_interview": "Empleo: invitación a entrevista o reclutador que respondió tu CV.",
    "gov_human": "Trámite de gobierno escrito por una persona (no boletín).",
    "reply_to_you": "Una persona respondió a algo que tú enviaste.",
}

#: Insight kinds that never create a case on their own.
NEVER_CASE = frozenset(
    {
        "promo",
        "verification_code",
        "magic_link",
        "receipt",
        "transfer_received",
        "transfer_sent",
        "statement",
        "terms_update",
        "order_placed",
        "order_delivered",
        "security_alert",
        "card_status",
    }
)

#: Grouped kinds ignore subject matching (all Banco Azteca declines share one subject).
GROUPED_KINDS = frozenset(
    {"payment_declined", "bill_due", "debt_overdue", "debt_offer", "card_failed", "order_in_transit", "security_change", "job_interview"}
)

PRIORITY_RISK = {"critical": 90, "high": 70, "normal": 45, "low": 20}

# ------------------------------------------------------------ helpers

_UNSUBSCRIBE = re.compile(
    r"unsubscribe|darte de baja|dar(?:se)? de baja|date de baja|cancelar (?:tu |la )?suscripci|desuscrib|anular (?:la )?suscripci"
    r"|no (?:deseas|quieres) recibir|preferencias de (?:correo|comunicaci)|email preferences|manage (?:your )?preferences"
    r"|ver (?:este correo |el correo )?en (?:tu |el )?navegador|view (?:this email )?in (?:your )?browser|desinscri|disiscri"
)
_RECEIPT_CUE = re.compile(
    r"pago recibido|gracias por tu pago|hemos recibido tu pago|pago (?:aplicado|exitoso|realizado con exito)|comprobante de pago|recibo de pago"
    r"|payment received|thank you for your payment|ya fue pagad|tu pago fue"
)
_SENSITIVE_SECURITY = re.compile(
    r"contrasena de aplicacion|app password|verificacion en dos pasos.{0,40}(?:desactiv|cambi|apag)|(?:2-step|two-step).{0,40}(?:off|changed|disabled)"
    r"|se cambio (?:la|tu) contrasena|tu contrasena (?:se cambio|fue cambiada)|password (?:was |has been )?changed"
    r"|(?:nueva|una) (?:aplicacion|app) (?:tiene acceso|conectada|se conecto)|has access to your|ahora tiene acceso|now has access"
    r"|se agrego (?:un|una) (?:telefono|correo) de recuperacion|recovery (?:email|phone) (?:was )?changed"
)
_INTERVIEW = re.compile(r"entrevista|interview")
_REPLY_SUBJECT = re.compile(r"^(?:re|rv|aw)\s*:", re.IGNORECASE)
_HUMAN_BLOCK = re.compile(
    r"no-?reply|noreply|no_reply|do-?not-?reply|notificacion|notification|alert|aviso|mailer|newsletter|boletin|info@|news|marketing|soporte@|support@"
)
_COLLECTION_TEXT = re.compile(r"extrajudicial|despacho de cobranza|cobranza especializada|agencia de cobranza")
_PROMO_SUBJECT = dict(_RULES)["promo"]
_FAILED_CARD = re.compile(r"no (?:fue posible|pudimos|se pudo) entregar|devuelta|regres\w* a (?:la )?mensajer")
_HOLDER = re.compile(r"(?:^|\n)\s*(?:nombre|titular|a nombre de)\s*:\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ .'-]{3,60})", re.IGNORECASE)
_CREDITORS = (
    ("bbva", "BBVA"),
    ("banamex", "Banamex"),
    ("citibanamex", "Banamex"),
    ("santander", "Santander"),
    ("banco azteca", "Banco Azteca"),
    ("bancoppel", "BanCoppel"),
    ("coppel", "Coppel"),
    ("banorte", "Banorte"),
    ("hsbc", "HSBC"),
    ("scotiabank", "Scotiabank"),
    ("nu mexico", "Nu"),
    ("mercado pago", "Mercado Pago"),
    ("liverpool", "Liverpool"),
    ("elektra", "Elektra"),
)

# merchant text (folded) → (key, label). First match wins: put "youtube" before "google".
_MERCHANT_ALIASES: tuple[tuple[str, str, str], ...] = (
    ("youtube", "youtube-premium", "YouTube Premium"),
    ("google one", "google-one", "Google One"),
    ("googleone", "google-one", "Google One"),
    ("google play", "google-play", "Google Play"),
    ("google cloud", "google-cloud", "Google Cloud"),
    ("cursor", "cursor", "Cursor"),
    ("github", "github", "GitHub"),
    ("uber eats", "uber-eats", "Uber Eats"),
    ("uber", "uber", "Uber"),
    ("emergent", "emergent", "Emergent"),
    ("netflix", "netflix", "Netflix"),
    ("spotify", "spotify", "Spotify"),
    ("icloud", "apple", "Apple"),
    ("apple", "apple", "Apple"),
    ("prime video", "amazon-prime", "Amazon Prime"),
    ("amazon prime", "amazon-prime", "Amazon Prime"),
    ("amazon", "amazon", "Amazon"),
    ("openai", "openai", "OpenAI"),
    ("chatgpt", "openai", "OpenAI"),
    ("anthropic", "anthropic", "Anthropic"),
    ("disney", "disney-plus", "Disney+"),
    ("hbo", "max", "Max"),
    ("microsoft", "microsoft", "Microsoft"),
    ("xbox", "microsoft", "Microsoft"),
    ("adobe", "adobe", "Adobe"),
    ("canva", "canva", "Canva"),
    ("figma", "figma", "Figma"),
    ("notion", "notion", "Notion"),
    ("dropbox", "dropbox", "Dropbox"),
    ("ccleaner", "ccleaner", "CCleaner"),
    ("didi", "didi", "DiDi"),
    ("rappi", "rappi", "Rappi"),
    ("railway", "railway", "Railway"),
    ("vercel", "vercel", "Vercel"),
    ("supabase", "supabase", "Supabase"),
)
_MERCHANT_NOISE = re.compile(r"^(?:dlo|pp|paypal|sq|mp|merpago|conekta|stripe|www|com|mx|inc|llc|ltd|sa|de|cv)$")


def slug(value: str | None) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", fold(value or "")).strip("-")
    return text[:48] or "x"


def merchant_key(merchant: str | None) -> tuple[str, str]:
    """``("youtube-premium", "YouTube Premium")`` for "Google Youtubepremium 650-2530"."""
    folded = fold(merchant or "")
    for needle, key, label in _MERCHANT_ALIASES:
        if needle in folded:
            return key, label
    words = [
        word
        for word in re.findall(r"[a-z][a-z&]+", re.sub(r"\+?\d[\d\s-]{3,}", " ", folded))
        if not _MERCHANT_NOISE.match(word)
    ]
    if not words:
        return "comercio", (merchant or "").strip() or "—"
    key = "-".join(words[:2])
    label = " ".join(word.capitalize() for word in words[:2])
    return key, label


def parse_due_date(raw: str | None) -> str | None:
    """Due date text → ISO UTC instant at 23:59 America/Mexico_City that day."""
    if not raw:
        return None
    text = fold(raw).strip()
    months = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
        "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
        "oct": 10, "nov": 11, "dec": 12, "ene": 1, "abr": 4, "ago": 8, "dic": 12,
        "january": 1, "february": 2, "march": 3, "april": 4, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }
    year = month = day = None
    if match := re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text):
        year, month, day = int(match[1]), int(match[2]), int(match[3])
    elif match := re.fullmatch(r"(\d{1,2})/(\d{1,2}|[a-z]{3,4})/(\d{2,4})", text):
        day = int(match[1])
        month = int(match[2]) if match[2].isdigit() else months.get(match[2])
        year = int(match[3]) + (2000 if len(match[3]) == 2 else 0)
    elif match := re.fullmatch(r"(\d{1,2}) de ([a-z]+)(?: de(?:l)? (\d{4}))?", text):
        day, month = int(match[1]), months.get(match[2])
        year = int(match[3]) if match[3] else None
    elif match := re.fullmatch(r"([a-z]+)\.? (\d{1,2})(?:, (\d{4}))?", text):
        month, day = months.get(match[1]), int(match[2])
        year = int(match[3]) if match[3] else None
    elif match := re.fullmatch(r"(\d{1,2}) ([a-z]+) (\d{4})", text):
        day, month, year = int(match[1]), months.get(match[2]), int(match[3])
    if not (year and month and day):
        return None
    try:
        local = datetime.combine(datetime(year, month, day).date(), time(23, 59), tzinfo=USER_TZ)
    except ValueError:
        return None
    return local.astimezone(timezone.utc).isoformat()


def _i18n(es: str, en: str, fr: str, it: str, pt: str) -> dict[str, str]:
    return dict(zip(LANGS, (es, en, fr, it, pt)))


CAUTION_DEBT = _i18n(
    "Verifica con tu banco antes de pagar. Usa solo el teléfono o la app oficial del banco; no pagues a cuentas o WhatsApp que te den en el correo.",
    "Check with your bank before paying. Use only the bank's official phone or app; don't pay accounts or WhatsApp numbers given in the email.",
    "Vérifiez auprès de votre banque avant de payer. Utilisez uniquement le téléphone ou l'appli officielle ; ne payez pas les comptes ou numéros WhatsApp indiqués dans l'e-mail.",
    "Verifica con la tua banca prima di pagare. Usa solo il telefono o l'app ufficiale; non pagare conti o numeri WhatsApp indicati nell'email.",
    "Verifique com seu banco antes de pagar. Use só o telefone ou o app oficial do banco; não pague contas ou WhatsApp informados no e-mail.",
)


def _next_step(kind: str, v: dict[str, str]) -> dict[str, str]:
    merchant = v.get("merchant") or ""
    brand = v.get("brand") or ""
    amount = v.get("amount") or ""
    if kind == "payment_declined":
        return _i18n(
            f"Revisa tu saldo o cambia la tarjeta de {merchant}; si ya no lo usas, cancela la suscripción.",
            f"Check your balance or update the card for {merchant}; if you no longer use it, cancel the subscription.",
            f"Vérifiez votre solde ou changez la carte pour {merchant} ; sinon, résiliez l'abonnement.",
            f"Controlla il saldo o cambia la carta per {merchant}; se non lo usi più, annulla l'abbonamento.",
            f"Confira seu saldo ou troque o cartão de {merchant}; se não usa mais, cancele a assinatura.",
        )
    if kind == "bill_due":
        due = f" ({amount})" if amount else ""
        return _i18n(
            f"Paga el recibo de {brand}{due} antes de la fecha límite o confirma que ya está pagado.",
            f"Pay the {brand} bill{due} before the due date, or confirm it is already paid.",
            f"Payez la facture {brand}{due} avant l'échéance, ou confirmez qu'elle est déjà réglée.",
            f"Paga la bolletta {brand}{due} entro la scadenza, o conferma che è già pagata.",
            f"Pague a conta de {brand}{due} até o vencimento ou confirme que já está paga.",
        )
    if kind == "debt_overdue":
        return _i18n(
            f"Comunícate con {brand} por su canal oficial para ponerte al corriente.",
            f"Contact {brand} through its official channel to bring the account up to date.",
            f"Contactez {brand} par son canal officiel pour régulariser le compte.",
            f"Contatta {brand} tramite il canale ufficiale per regolarizzare il conto.",
            f"Fale com {brand} pelo canal oficial para regularizar a conta.",
        )
    if kind == "debt_offer":
        return _i18n(
            "Si te interesa la oferta, confírmala primero con tu banco por su canal oficial.",
            "If you want the offer, confirm it with your bank through its official channel first.",
            "Si l'offre vous intéresse, confirmez-la d'abord auprès de votre banque.",
            "Se ti interessa l'offerta, confermala prima con la tua banca.",
            "Se tiver interesse na oferta, confirme primeiro com seu banco pelo canal oficial.",
        )
    if kind == "card_failed":
        return _i18n(
            f"Llama a {brand} para reprogramar la entrega de tu tarjeta.",
            f"Call {brand} to reschedule your card delivery.",
            f"Appelez {brand} pour reprogrammer la livraison de votre carte.",
            f"Chiama {brand} per riprogrammare la consegna della carta.",
            f"Ligue para {brand} para reagendar a entrega do cartão.",
        )
    if kind == "order_in_transit":
        return _i18n(
            "Sigue el envío; el caso se cierra solo cuando llegue.",
            "Track the delivery; the case closes on its own when it arrives.",
            "Suivez la livraison ; le dossier se ferme tout seul à l'arrivée.",
            "Segui la spedizione; il caso si chiude da solo alla consegna.",
            "Acompanhe a entrega; o caso fecha sozinho quando chegar.",
        )
    if kind == "security_change":
        return _i18n(
            f"Si no fuiste tú, cambia tu contraseña de {brand} y revisa los accesos de tu cuenta.",
            f"If it wasn't you, change your {brand} password and review your account access.",
            f"Si ce n'était pas vous, changez votre mot de passe {brand} et vérifiez les accès.",
            f"Se non sei stato tu, cambia la password di {brand} e controlla gli accessi.",
            f"Se não foi você, troque a senha de {brand} e revise os acessos da conta.",
        )
    if kind == "job_interview":
        return _i18n(
            "Responde o agenda la entrevista antes de que venza.",
            "Reply or schedule the interview before it expires.",
            "Répondez ou planifiez l'entretien avant son expiration.",
            "Rispondi o fissa il colloquio prima della scadenza.",
            "Responda ou agende a entrevista antes que vença.",
        )
    if kind == "gov_human":
        return _i18n(
            "Revisa el trámite y responde si te piden algo.",
            "Review the procedure and reply if they ask for something.",
            "Consultez la démarche et répondez si on vous demande quelque chose.",
            "Controlla la pratica e rispondi se ti chiedono qualcosa.",
            "Revise o trâmite e responda se pedirem algo.",
        )
    return _i18n(
        "Lee la respuesta y contesta si hace falta.",
        "Read the reply and answer if needed.",
        "Lisez la réponse et répondez si nécessaire.",
        "Leggi la risposta e rispondi se serve.",
        "Leia a resposta e responda se precisar.",
    )


def _title(kind: str, v: dict[str, str], topic: str) -> dict[str, str]:
    brand, merchant = v.get("brand") or "", v.get("merchant") or ""
    card = f" ****{v['card']}" if v.get("card") else ""
    by = f" ({brand})" if brand else ""
    table = {
        "payment_declined": (f"Cobro rechazado: {merchant}{by}", f"Declined charge: {merchant}{by}", f"Prélèvement refusé : {merchant}{by}", f"Addebito rifiutato: {merchant}{by}", f"Cobrança recusada: {merchant}{by}"),
        "bill_due": (f"Recibo por pagar: {brand}", f"Bill to pay: {brand}", f"Facture à payer : {brand}", f"Bolletta da pagare: {brand}", f"Conta a pagar: {brand}"),
        "debt_overdue": (f"Pago vencido: {brand}", f"Overdue payment: {brand}", f"Paiement en retard : {brand}", f"Pagamento scaduto: {brand}", f"Pagamento vencido: {brand}"),
        "debt_offer": (f"Oferta de cobranza: {brand}", f"Debt collection offer: {brand}", f"Offre de recouvrement : {brand}", f"Offerta di recupero crediti: {brand}", f"Oferta de cobrança: {brand}"),
        "card_failed": (f"Tarjeta no entregada: {brand}{card}", f"Card not delivered: {brand}{card}", f"Carte non livrée : {brand}{card}", f"Carta non consegnata: {brand}{card}", f"Cartão não entregue: {brand}{card}"),
        "order_in_transit": (f"Pedido en camino: {brand}", f"Order on its way: {brand}", f"Commande en route : {brand}", f"Ordine in arrivo: {brand}", f"Pedido a caminho: {brand}"),
        "security_change": (f"Cambio de seguridad: {brand}", f"Security change: {brand}", f"Changement de sécurité : {brand}", f"Modifica di sicurezza: {brand}", f"Alteração de segurança: {brand}"),
        "job_interview": (f"Empleo: {brand}", f"Job: {brand}", f"Emploi : {brand}", f"Lavoro: {brand}", f"Emprego: {brand}"),
    }
    values = table.get(kind)
    if not values:
        return dict.fromkeys(LANGS, topic)
    return dict(zip(LANGS, values))


# ------------------------------------------------------------ decision

@dataclass(frozen=True)
class CaseDecision:
    category: str | None
    score: int
    reason: str
    create_case: bool = False
    link_only: bool = False
    forbid_case: bool = False
    kind: str | None = None
    insight_kind: str | None = None
    group_key: str | None = None
    title: str | None = None
    priority: str = "normal"
    due_at: str | None = None
    resolves_case: bool = False
    summary: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def actionable(self) -> bool:
        return self.create_case

    @property
    def risk_score(self) -> int:
        return PRIORITY_RISK.get(self.priority, 45)


def is_promo_by_content(message: dict[str, Any], insight: dict[str, Any] | None = None) -> bool:
    """Promotions by what the email says and how it is sent, not Gmail labels."""
    insight = insight if insight is not None else build_insight(message)
    kind = str(insight.get("kind") or "")
    if kind == "promo":
        return True
    if kind not in {"unknown", "job"}:
        return False
    sender = str(message.get("sender") or "")
    _, address, domain = _sender_parts(sender)
    if domain.endswith(".gob.mx") or domain.endswith(".gov"):
        return False
    if _is_marketing_domain(domain) or is_marketing_local_part(sender):
        return True
    if domain in _PERSONAL_DOMAINS:
        return False
    raw = fold(f"{message.get('body_text') or ''}\n{(message.get('body_html') or '')[-30000:]}")
    return bool(_UNSUBSCRIBE.search(raw))


def _is_human_sender(sender: str) -> bool:
    _, address, _ = _sender_parts(sender)
    return bool(address) and not _HUMAN_BLOCK.search(address)


def _creditor(text: str, fallback: str) -> str:
    folded = fold(text)
    for needle, label in _CREDITORS:
        if needle in folded:
            return label
    return fallback


def _holder_note(text: str, owner_names: tuple[str, ...]) -> dict[str, str] | None:
    found = _HOLDER.search(text)
    if not found:
        return None
    holder = re.sub(r"\s+", " ", found.group(1)).strip(" .")
    holder_tokens = {token for token in re.findall(r"[a-z]{3,}", fold(holder))}
    owner_tokens = {token for name in owner_names for token in re.findall(r"[a-z]{3,}", fold(name))}
    if holder_tokens and owner_tokens and holder_tokens & owner_tokens:
        return None
    return _i18n(
        f"El recibo está a nombre de {holder}.",
        f"The bill is in the name of {holder}.",
        f"La facture est au nom de {holder}.",
        f"La bolletta è intestata a {holder}.",
        f"A conta está em nome de {holder}.",
    )


def decide(
    message: dict[str, Any],
    *,
    owner_names: tuple[str, ...] = (),
    user_sent_subject: bool = False,
    insight: dict[str, Any] | None = None,
) -> CaseDecision:
    """Decide what one inbound/outbound stored message means for cases."""
    insight = insight if insight is not None else build_insight(message)
    ikind = str(insight.get("kind") or "unknown")
    facts = insight.get("facts") or {}
    sender = str(message.get("sender") or "")
    subject = clean_subject(message.get("subject"))
    topic = strip_subject_prefix(subject) or subject or "(Sin asunto)"
    identity = identify_sender(sender) or {}
    vertical = str(identity.get("vertical") or "")
    brand = str(facts.get("brand") or identity.get("name") or "")
    if vertical == "debt_collection" and identity.get("name"):
        brand = str(identity["name"])
    head = fold(f"{subject}\n{insight.get('preview') or ''}\n{' '.join(insight.get('excerpts') or [])}")
    body_text = str(message.get("body_text") or "")
    full = fold(f"{subject}\n{body_text[:4000]}")
    _, address, domain = _sender_parts(sender)
    labels = {str(item).upper() for item in (message.get("labels") or [])}
    outbound = "SENT" in labels and "INBOX" not in labels

    base_meta: dict[str, Any] = {"policy_version": POLICY_VERSION, "insight_kind": ikind}

    def case(kind: str, group_key: str | None, priority: str, reason: str, **extra: Any) -> CaseDecision:
        values = {
            "brand": brand,
            "merchant": extra.pop("merchant_label", "") or facts.get("merchant") or "",
            "amount": facts.get("amount") or "",
            "card": facts.get("card_last4") or "",
        }
        titles = _title(kind, values, topic)
        meta = {
            **base_meta,
            "kind": kind,
            "group_key": group_key,
            "title": titles,
            "next_step": _next_step(kind, values),
            "merchant_label": values["merchant"] or None,
            "last_amount": facts.get("amount"),
            **extra.pop("meta", {}),
        }
        return CaseDecision(
            category="action_required",
            score=extra.pop("score", 90),
            reason=reason,
            create_case=True,
            kind=kind,
            insight_kind=ikind,
            group_key=group_key,
            title=titles["es"],
            priority=priority,
            due_at=parse_due_date(facts.get("due_date")),
            summary=((insight.get("main_idea") or {}).get("es") or None),
            metadata={key: value for key, value in meta.items() if value is not None},
        )

    if outbound:
        return CaseDecision(category=None, score=0, reason="", insight_kind=ikind)

    collection_sender = vertical == "debt_collection"
    # "La oferta vence el 5 de octubre" is advertising, not a bill.
    promo_subject = bool(_PROMO_SUBJECT.search(fold(subject)))
    if promo_subject and ikind in {"bill_due", "order_shipped", "job", "security_alert", "statement"}:
        return CaseDecision(
            category="promotional", score=5, reason=f"Publicidad detectada por contenido ({brand or domain}).",
            forbid_case=True, insight_kind=ikind, metadata=base_meta,
        )

    # --- 1. kinds that create a grouped case -------------------------------
    if ikind == "payment_declined":
        key, label = merchant_key(facts.get("merchant") or (topic if vertical == "payment_processor" else None))
        return case(
            "payment_declined",
            f"declined:{slug(brand)}:{key}",
            "high",
            f"Cobro rechazado de {label} ({brand}); se agrupa por comercio.",
            merchant_label=label,
        )

    if ikind in {"debt_offer", "debt_overdue"} or (collection_sender and ikind in {"unknown", "bill_due", "personal"}):
        creditor = _creditor(full, brand if not collection_sender else "")
        if ikind == "debt_offer" or collection_sender:
            label = creditor or brand
            key = f"debt-offer:{slug(creditor or domain or brand)}"
            meta = {"caution": CAUTION_DEBT, "creditor": creditor or None, "collector": brand if collection_sender else None}
            return case(
                "debt_offer",
                key,
                "normal",
                f"Cobranza u oferta de liquidación ({label}); verifica con tu banco antes de pagar.",
                meta=meta,
                score=80,
            )
        meta = {"caution": CAUTION_DEBT} if ("cobranza" in address or _COLLECTION_TEXT.search(full)) else {}
        card = facts.get("card_last4")
        return case(
            "debt_overdue",
            f"debt:{slug(brand)}" + (f":{card}" if card else ""),
            "critical",
            f"Pago vencido con {brand}.",
            meta=meta,
            score=95,
        )

    if ikind == "bill_due" and not _RECEIPT_CUE.search(full):
        if facts.get("amount") or facts.get("due_date") or vertical in {"utility", "government"}:
            meta: dict[str, Any] = {}
            holder = _holder_note(_clean_text(message), owner_names)
            if holder:
                meta["account_holder"] = holder
            return case("bill_due", f"bill:{slug(brand)}", "high", f"Recibo o adeudo por pagar de {brand}.", meta=meta)

    if ikind == "statement" and vertical == "utility" and facts.get("amount") and facts.get("due_date"):
        return case("bill_due", f"bill:{slug(brand)}", "high", f"Estado de cuenta con monto y fecha límite de {brand}.")

    if ikind == "card_status":
        card = facts.get("card_last4") or "tarjeta"
        group = f"card:{slug(brand)}:{card}"
        if _FAILED_CARD.search(full) or _FAILED_CARD.search(head):
            return case("card_failed", group, "high", f"{brand} no pudo entregar tu tarjeta.")
        return CaseDecision(
            category="notice", score=70, reason=f"Aviso de tarjeta de {brand}.", link_only=True,
            kind="card_failed", insight_kind=ikind, group_key=group, metadata=base_meta,
        )

    if ikind == "order_shipped":
        ref = facts.get("reference") or "compra"
        return case("order_in_transit", f"order:{slug(brand)}:{slug(ref)}", "low", f"Pedido en camino de {brand}.", score=75)

    if ikind == "order_delivered":
        ref = facts.get("reference") or "compra"
        return CaseDecision(
            category="notice", score=70, reason=f"Pedido entregado ({brand}).", link_only=True, resolves_case=True,
            kind="order_in_transit", insight_kind=ikind, group_key=f"order:{slug(brand)}:{slug(ref)}", metadata=base_meta,
        )

    if ikind == "security_alert" and _SENSITIVE_SECURITY.search(full):
        return case("security_change", f"security:{slug(brand)}", "high", f"Cambio sensible de seguridad en {brand}.", score=85)

    if ikind == "job":
        interview = bool(_INTERVIEW.search(fold(subject))) and not is_marketing_local_part(sender)
        recruiter_reply = bool(_REPLY_SUBJECT.match(subject)) and _is_human_sender(sender)
        if interview or recruiter_reply:
            return case("job_interview", f"job:{slug(brand or domain)}", "normal", f"Empleo: {brand} te escribió sobre una entrevista o tu CV.", score=80)

    # --- 2. promotions by content, before anything can land in "review" -----
    if is_promo_by_content(message, insight):
        return CaseDecision(
            category="promotional", score=5, reason=f"Publicidad detectada por contenido ({brand or domain}).",
            forbid_case=True, insight_kind=ikind, metadata=base_meta,
        )

    # --- 3. human threads: government procedure or reply to what you sent ---
    if ikind == "gov_procedure" and _is_human_sender(sender):
        return case("gov_human", None, "normal", f"Trámite de gobierno con {brand}.", score=80)
    if (ikind in {"personal", "unknown", "job"}) and user_sent_subject and _REPLY_SUBJECT.match(subject) and _is_human_sender(sender):
        return case("reply_to_you", None, "normal", f"{brand or address} respondió a un correo que enviaste.", score=80)

    # --- 4. never a case ----------------------------------------------------
    if ikind in NEVER_CASE or ikind == "bill_due":
        return CaseDecision(category=None, score=0, reason="", forbid_case=True, insight_kind=ikind, metadata=base_meta)

    return CaseDecision(category=None, score=0, reason="", insight_kind=ikind, metadata=base_meta)


def _clean_text(message: dict[str, Any]) -> str:
    from app.utils.mail_clean import clean_email

    try:
        return clean_email(message.get("body_text") or message.get("snippet"), message.get("body_html"), message.get("subject")).text[:4000]
    except Exception:  # pragma: no cover - defensive
        return str(message.get("body_text") or "")[:4000]


# ------------------------------------------------------------ grouped view

_MONTHS = {
    "es": ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"),
    "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
    "fr": ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."),
    "it": ("gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"),
    "pt": ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"),
}


def local_day(value: str | None, lang: str) -> str | None:
    """'2026-10-03T03:10:00Z' → '2 oct' in America/Mexico_City."""
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    local = moment.astimezone(USER_TZ)
    month = _MONTHS.get(lang, _MONTHS["es"])[local.month - 1]
    return f"{month} {local.day}" if lang == "en" else f"{local.day} {month}"


def grouped_main_idea(main_idea: dict[str, str], metadata: dict[str, Any], facts: dict[str, Any]) -> dict[str, str]:
    """Add "N times, last on <day>" to a grouped case's main idea (5 languages)."""
    count = int(metadata.get("occurrences") or 1)
    if count <= 1:
        return main_idea
    kind = metadata.get("kind")
    out: dict[str, str] = {}
    for lang in LANGS:
        day = local_day(metadata.get("last_seen_at"), lang) or "—"
        if kind == "payment_declined":
            brand = facts.get("brand") or ""
            merchant = metadata.get("merchant_label") or facts.get("merchant") or ""
            amount = facts.get("amount")
            amt = {"es": f" ({amount})", "en": f" ({amount})", "fr": f" ({amount})", "it": f" ({amount})", "pt": f" ({amount})"}[lang] if amount else ""
            out[lang] = {
                "es": f"{brand} rechazó {count} veces el cobro de {merchant}{amt}; último intento {day}.",
                "en": f"{brand} declined the {merchant} charge {count} times{amt}; last attempt {day}.",
                "fr": f"{brand} a refusé {count} fois le prélèvement de {merchant}{amt} ; dernière tentative le {day}.",
                "it": f"{brand} ha rifiutato {count} volte l’addebito di {merchant}{amt}; ultimo tentativo il {day}.",
                "pt": f"{brand} recusou {count} vezes a cobrança de {merchant}{amt}; última tentativa em {day}.",
            }[lang]
            continue
        suffix = {
            "es": f" ({count} avisos; el último el {day}).",
            "en": f" ({count} notices; latest on {day}).",
            "fr": f" ({count} avis ; le dernier le {day}).",
            "it": f" ({count} avvisi; l’ultimo il {day}).",
            "pt": f" ({count} avisos; o último em {day}).",
        }[lang]
        base = (main_idea.get(lang) or main_idea.get("es") or "").rstrip(" .")
        out[lang] = base + suffix
    return out
