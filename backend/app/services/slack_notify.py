"""Avisos best-effort a Slack (workspace Donexto) con chat.postMessage.

Nunca lanza excepciones ni bloquea la petición: se envía en un hilo daemon.
Sin ``SLACK_BOT_TOKEN`` no hace nada.
"""

from __future__ import annotations

import logging
import os
import threading

import httpx

logger = logging.getLogger(__name__)

CHANNEL_ALERTS = "#alertas"
CHANNEL_USERS = "#usuarios"
CHANNEL_ADMIN = "#admin"


def _post(channel: str, text: str) -> bool:
    token = os.getenv("SLACK_BOT_TOKEN", "").strip()
    if not token:
        return False
    try:
        response = httpx.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {token}"},
            json={"channel": channel, "text": ("<!channel> " + text)[:3500]},
            timeout=8,
        )
        ok = bool(response.json().get("ok"))
        if not ok:
            logger.warning("slack_post_not_ok channel=%s", channel)
        return ok
    except Exception as error:  # noqa: BLE001
        logger.warning("slack_post_failed type=%s", type(error).__name__)
        return False


def post_slack(channel: str, text: str) -> None:
    """Encola el mensaje; nunca falla."""
    if not os.getenv("SLACK_BOT_TOKEN", "").strip():
        return
    try:
        threading.Thread(target=_post, args=(channel, text), daemon=True).start()
    except Exception:  # noqa: BLE001
        pass
