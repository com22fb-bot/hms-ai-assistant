from __future__ import annotations

from fastapi import APIRouter

from app.security.identity import require_request_context
from app.services.stripe_checkout import create_checkout_session, plan_payload


router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/plan")
def billing_plan() -> dict[str, object]:
    require_request_context()
    return plan_payload()


@router.post("/checkout")
def billing_checkout() -> dict[str, object]:
    context = require_request_context()
    email = (context.user.email or "").strip().lower()
    return create_checkout_session(
        customer_email=email,
        client_reference_id=context.user.id,
    )
