"""Explicit mailbox proof, independent of OAuth and legacy verification flags."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import smtplib
import ssl
import time
from email.message import EmailMessage
from urllib.parse import urlencode

from fastapi import HTTPException
from app.database.supabase import get_supabase_client

KEY = "mailbox_email_verification_v1"
PENDING = "mailbox_email_challenge_v1"


def verified(metadata: dict, email: str) -> bool:
    proof = metadata.get(KEY)
    return bool(email and isinstance(proof, dict)
                and proof.get("email") == email.strip().lower()
                and proof.get("method") == "email_link"
                and proof.get("verified_at"))


def mailbox_email(context) -> str:
    email = context.user.email.strip().lower()
    account = context.google_account or {}
    target = str(account.get("email") or email).strip().lower()
    if target != email:
        raise HTTPException(409, detail={"message": "Inicia sesión con el mismo correo que deseas monitorear."})
    return target


def context_verified(context) -> bool:
    return verified(context.user.raw_app_metadata, mailbox_email(context))


def _admin_user(user_id: str):
    client = get_supabase_client()
    response = client.auth.admin.get_user_by_id(user_id)
    user = response.get("user") if isinstance(response, dict) else response.user
    email = user.get("email") if isinstance(user, dict) else user.email
    meta = user.get("app_metadata") if isinstance(user, dict) else user.app_metadata
    return client, str(email or "").strip().lower(), dict(meta or {})


def send_link(email: str, token: str) -> None:
    # Dedicated transactional SMTP. Never fall back to a public form service.
    host = os.getenv("DONEXTO_SMTP_HOST", "").strip()
    sender = os.getenv("DONEXTO_SMTP_FROM", "").strip()
    if not host or not sender:
        raise HTTPException(503, detail={"message": "El envío de verificación aún no está disponible. Inténtalo más tarde."})
    port = int(os.getenv("DONEXTO_SMTP_PORT", "587"))
    message = EmailMessage()
    message["Subject"] = "Verifica tu correo para entrar a Donexto"
    message["From"] = sender
    message["To"] = email
    # Fragment keeps the bearer proof out of proxy request URLs and referrers.
    link = "https://app.donexto.com/#" + urlencode({"donexto_verification": token})
    message.set_content(f"Para verificar {email} y acceder a Donexto, abre este enlace:\n\n{link}\n\nCaduca en 30 minutos. Inicia sesión con ese mismo correo si se solicita.\nSi no lo solicitaste, ignora este mensaje.")
    tls = ssl.create_default_context()
    factory = smtplib.SMTP_SSL if port == 465 else smtplib.SMTP
    kwargs = {"context": tls} if port == 465 else {}
    with factory(host, port, timeout=15, **kwargs) as smtp:
        if port != 465:
            smtp.ehlo()
            smtp.starttls(context=tls)
            smtp.ehlo()
        user = os.getenv("DONEXTO_SMTP_USER", "")
        if user:
            smtp.login(user, os.getenv("DONEXTO_SMTP_PASSWORD", ""))
        smtp.send_message(message)


def request_verification(context) -> dict:
    email = mailbox_email(context)
    client, current_email, meta = _admin_user(context.user.id)
    if current_email != email:
        raise HTTPException(409, detail={"message": "La cuenta cambió. Vuelve a iniciar sesión."})
    if verified(meta, email):
        return {"status": "verified"}
    now = int(time.time())
    pending = meta.get(PENDING) or {}
    if isinstance(pending, dict) and now - int(pending.get("sent_at", 0)) < 60:
        raise HTTPException(429, detail={"message": "Espera un minuto antes de solicitar otro enlace."})
    token = secrets.token_urlsafe(32)
    challenge = {"hash": hashlib.sha256(token.encode()).hexdigest(), "email": email,
                 "sent_at": now, "expires_at": now + 1800}
    client.auth.admin.update_user_by_id(context.user.id, {"app_metadata": {**meta, PENDING: challenge}})
    try:
        send_link(email, token)
    except Exception as error:
        # Fail closed; allow retry after cooldown. Never expose SMTP details.
        raise HTTPException(503, detail={"message": "No se pudo enviar la verificación. Espera un minuto y vuelve a intentarlo."}) from error
    return {"status": "sent", "email": email}


def confirm_verification(context, token: str) -> dict:
    email = mailbox_email(context)
    client, current_email, meta = _admin_user(context.user.id)
    pending = meta.get(PENDING)
    valid = (current_email == email and isinstance(pending, dict)
             and pending.get("email") == email
             and int(pending.get("expires_at", 0)) > time.time()
             and hmac.compare_digest(str(pending.get("hash", "")), hashlib.sha256(token.encode()).hexdigest()))
    if not valid:
        raise HTTPException(400, detail={"message": "El enlace es inválido, expiró o ya fue utilizado. Solicita otro enlace."})
    proof = {"email": email, "method": "email_link", "verified_at": int(time.time())}
    client.auth.admin.update_user_by_id(context.user.id, {"app_metadata": {**meta, PENDING: None, KEY: proof}})
    return {"status": "ok", "donexto_verified": True}
