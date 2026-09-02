"""Stripe Test Checkout para Plan Normal $19.99/mes. Sin Live."""

from __future__ import annotations

import os
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

STRIPE_API = "https://api.stripe.com/v1/checkout/sessions"
PLAN_CODE = "normal"
PLAN_AMOUNT_LABEL = "$19.99"
PLAN_INTERVAL = "mes"


def stripe_secret_key() -> str:
    return os.getenv("STRIPE_SECRET_KEY", "").strip()


def stripe_price_id() -> str:
    return (
        os.getenv("STRIPE_PRICE_NORMAL_MONTHLY", "").strip()
        or os.getenv("STRIPE_PRICE_ID", "").strip()
    )


def stripe_success_url() -> str:
    return os.getenv(
        "STRIPE_SUCCESS_URL",
        "https://app.donexto.com/?donexto=billing_ok",
    ).strip()


def stripe_cancel_url() -> str:
    return os.getenv(
        "STRIPE_CANCEL_URL",
        "https://app.donexto.com/?donexto=billing_cancel",
    ).strip()


def missing_stripe_message() -> str:
    if not stripe_secret_key():
        return "falta STRIPE_SECRET_KEY en Railway"
    if stripe_secret_key().startswith("sk_live_"):
        return (
            "Stripe Live no está habilitado. En Railway usa una clave "
            "sk_test_ (Test Mode)."
        )
    if not stripe_price_id():
        return "falta STRIPE_PRICE_NORMAL_MONTHLY en Railway"
    return ""


def plan_payload() -> dict[str, object]:
    missing = missing_stripe_message()
    return {
        "status": "ok" if not missing else "not_configured",
        "plan_code": PLAN_CODE,
        "plan_name": "Plan Normal",
        "amount_label": PLAN_AMOUNT_LABEL,
        "interval": PLAN_INTERVAL,
        "test_mode": True,
        "checkout_ready": not missing,
        "message": missing
        or "Checkout de Stripe Test listo para Plan Normal $19.99/mes.",
    }


def create_checkout_session(*, customer_email: str, client_reference_id: str) -> dict[str, object]:
    missing = missing_stripe_message()
    if missing:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "stripe_not_configured",
                "message": missing,
            },
        )

    body = {
        "mode": "subscription",
        "success_url": stripe_success_url(),
        "cancel_url": stripe_cancel_url(),
        "client_reference_id": client_reference_id,
        "customer_email": customer_email,
        "line_items[0][price]": stripe_price_id(),
        "line_items[0][quantity]": "1",
        "allow_promotion_codes": "true",
        "metadata[plan_code]": PLAN_CODE,
        "metadata[app]": "donexto",
    }
    try:
        response = httpx.post(
            STRIPE_API,
            content=urlencode(body),
            headers={
                "Authorization": f"Bearer {stripe_secret_key()}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=18.0,
        )
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "stripe_unreachable",
                "message": "No fue posible hablar con Stripe Test.",
                "technical_detail": str(error),
            },
        ) from error

    payload = response.json() if response.content else {}
    if response.status_code >= 400:
        stripe_message = ""
        if isinstance(payload, dict):
            err = payload.get("error")
            if isinstance(err, dict):
                stripe_message = str(err.get("message") or "")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "stripe_error",
                "message": stripe_message
                or "Stripe Test rechazó el Checkout. Revisa STRIPE_PRICE_NORMAL_MONTHLY.",
            },
        )

    checkout_url = payload.get("url") if isinstance(payload, dict) else None
    if not checkout_url:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "stripe_error",
                "message": "Stripe Test no devolvió una URL de Checkout.",
            },
        )
    return {
        "status": "ok",
        "checkout_url": checkout_url,
        "session_id": payload.get("id"),
        "test_mode": True,
        "plan_code": PLAN_CODE,
    }
