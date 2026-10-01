from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.preferences_service import load_preferences, store_preferences


router = APIRouter(prefix="/preferences", tags=["Preferences"])


class PreferencesBody(BaseModel):
    preferences: dict[str, Any]


@router.get("")
def read_preferences() -> dict[str, Any]:
    return {"status": "ok", "preferences": load_preferences()}


@router.put("")
def write_preferences(body: PreferencesBody) -> dict[str, Any]:
    return {"status": "ok", "preferences": store_preferences(body.preferences)}
