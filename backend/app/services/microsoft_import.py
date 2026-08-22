"""Importación guiada de Outlook / Hotmail / Microsoft 365 vía Graph."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.gmail_full_sync import _existing_message_ids
from app.services.gmail_import_inventory import INITIAL_HISTORY_DAYS, LOCAL_TIMEZONE
from app.services.gmail_sync import (
    _format_sender,
    _get_or_create_thread,
    _parse_addresses,
    _to_iso,
    _utc_now,
)
from app.services.microsoft_oauth import (
    MicrosoftOAuthError,
    graph_get,
    refresh_microsoft_tokens,
)
from app.services.oauth_storage import OAuthStorage


MICROSOFT_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
MICROSOFT_PAGE_SIZE = 25
MICROSOFT_SELECT = (
    "id,subject,from,toRecipients,ccRecipients,bccRecipients,"
    "receivedDateTime,isRead,body,bodyPreview,conversationId,"
    "internetMessageId,hasAttachments"
)


class MicrosoftImportError(RuntimeError):
    """Fallo al leer el buzón Outlook en Graph."""


def is_microsoft_provider(account: dict[str, Any] | None) -> bool:
    provider = str((account or {}).get("provider") or "").strip().lower()
    return provider in {"microsoft", "outlook", "hotmail"}


def encode_microsoft_ref(folder: str, message_id: str) -> str:
    return f"{folder}|{message_id}"


def decode_microsoft_ref(ref: str) -> tuple[str, str]:
    folder, separator, message_id = (ref or "").partition("|")
    if not separator or not folder or not message_id:
        raise MicrosoftImportError("Referencia de Outlook inválida.")
    return folder, message_id


def graph_address(entry: dict[str, Any] | None) -> str:
    payload = (entry or {}).get("emailAddress") or {}
    name = str(payload.get("name") or "").strip()
    address = str(payload.get("address") or "").strip()
    if name and address:
        return f"{name} <{address}>"
    return address or name


def graph_address_list(entries: Any) -> str:
    if not isinstance(entries, list):
        return ""
    return ", ".join(
        item
        for item in (graph_address(entry) for entry in entries if isinstance(entry, dict))
        if item
    )


def _history_window(
    cutoff_at: datetime | None = None,
) -> tuple[datetime, datetime]:
    current = cutoff_at or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    start = current - timedelta(days=INITIAL_HISTORY_DAYS)
    return start, current


def _graph_since(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_microsoft_access_token(account: dict[str, Any]) -> str:
    storage = OAuthStorage()
    stored = storage.get_credentials(str(account["id"])) or {}
    access = str(stored.get("access_token") or "")
    refresh = str(stored.get("refresh_token") or "")
    if not access and not refresh:
        raise MicrosoftImportError(
            "Vuelve a firmar en el sitio de Microsoft para autorizar el buzón."
        )
    expires_at = stored.get("expires_at")
    soon = False
    if expires_at:
        try:
            parsed = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            soon = parsed <= datetime.now(timezone.utc) + timedelta(minutes=3)
        except ValueError:
            soon = False
    if access and not soon:
        return access
    if not refresh:
        if access:
            return access
        raise MicrosoftImportError(
            "Vuelve a firmar en el sitio de Microsoft para autorizar el buzón."
        )
    payload = refresh_microsoft_tokens(refresh)
    new_access = str(payload.get("access_token") or "")
    new_refresh = str(payload.get("refresh_token") or "") or refresh
    expires_in = payload.get("expires_in")
    new_expires = None
    if expires_in:
        try:
            new_expires = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        except (TypeError, ValueError):
            new_expires = None
    raw_scope = str(payload.get("scope") or "")
    scopes = [part for part in raw_scope.replace(",", " ").split() if part]
    storage.save_credentials(
        account_id=str(account["id"]),
        access_token=new_access,
        refresh_token=new_refresh,
        expires_at=new_expires,
        token_uri="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        scopes=scopes or list(stored.get("scopes") or []),
        metadata=dict(stored.get("metadata") or {}),
    )
    return new_access


def _graph_get_with_refresh(
    account: dict[str, Any],
    url: str,
    *,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    token = ensure_microsoft_access_token(account)
    try:
        return graph_get(token, url, params=params)
    except MicrosoftOAuthError as error:
        if "graph_http_401" not in str(error):
            raise MicrosoftImportError(str(error)) from error
        stored = OAuthStorage().get_credentials(str(account["id"])) or {}
        refresh = str(stored.get("refresh_token") or "")
        if not refresh:
            raise MicrosoftImportError(
                "Vuelve a firmar en el sitio de Microsoft para autorizar el buzón."
            ) from error
        payload = refresh_microsoft_tokens(refresh)
        new_access = str(payload.get("access_token") or "")
        OAuthStorage().save_credentials(
            account_id=str(account["id"]),
            access_token=new_access,
            refresh_token=str(payload.get("refresh_token") or "") or refresh,
            token_uri="https://login.microsoftonline.com/common/oauth2/v2.0/token",
            scopes=list(stored.get("scopes") or []),
            metadata=dict(stored.get("metadata") or {}),
        )
        try:
            return graph_get(new_access, url, params=params)
        except MicrosoftOAuthError as retry_error:
            raise MicrosoftImportError(str(retry_error)) from retry_error


def _list_folder_ids(
    account: dict[str, Any],
    folder: str,
    since: datetime,
) -> list[str]:
    ids: list[str] = []
    url = f"{MICROSOFT_GRAPH_BASE}/me/mailFolders/{folder}/messages"
    params = {
        "$select": "id",
        "$top": "100",
        "$filter": f"receivedDateTime ge {_graph_since(since)}",
        "$orderby": "receivedDateTime desc",
    }
    while url:
        payload = _graph_get_with_refresh(
            account,
            url,
            params=params if "mailFolders" in url and "$skiptoken" not in url.lower() else None,
        )
        params = None
        for row in payload.get("value") or []:
            if isinstance(row, dict) and row.get("id"):
                ids.append(str(row["id"]))
        url = str(payload.get("@odata.nextLink") or "")
    return ids


def microsoft_initial_snapshot(
    account: dict[str, Any],
    *,
    cutoff_at: datetime | None = None,
) -> dict[str, Any]:
    start, current = _history_window(cutoff_at)
    inbox_ids = _list_folder_ids(account, "inbox", start)
    sent_ids = _list_folder_ids(account, "sentitems", start)
    try:
        drafts = len(_list_folder_ids(account, "drafts", start))
    except MicrosoftImportError:
        drafts = 0
    try:
        spam = len(_list_folder_ids(account, "junkemail", start))
    except MicrosoftImportError:
        spam = 0
    try:
        trash = len(_list_folder_ids(account, "deleteditems", start))
    except MicrosoftImportError:
        trash = 0

    unread = 0
    try:
        payload = _graph_get_with_refresh(
            account,
            f"{MICROSOFT_GRAPH_BASE}/me/mailFolders/inbox/messages",
            params={
                "$select": "id",
                "$top": "1",
                "$count": "true",
                "$filter": (
                    f"receivedDateTime ge {_graph_since(start)} and isRead eq false"
                ),
            },
        )
        unread = int(payload.get("@odata.count") or 0)
    except (MicrosoftImportError, TypeError, ValueError):
        unread = 0

    refs = [
        encode_microsoft_ref("inbox", item) for item in inbox_ids
    ] + [
        encode_microsoft_ref("sent", item) for item in sent_ids
    ]
    unique_eligible = list(dict.fromkeys(refs))
    return {
        "query": (
            f"microsoft:since:{start.date().isoformat()} "
            f"until:{current.date().isoformat()}"
        ),
        "eligible_messages": len(unique_eligible),
        "microsoft_refs": unique_eligible,
        "snapshot_at_utc": current.isoformat(),
        "period_start_utc": start.isoformat(),
        "period_end_utc": current.isoformat(),
        "period_start_local": start.astimezone(LOCAL_TIMEZONE).isoformat(),
        "period_end_local": current.astimezone(LOCAL_TIMEZONE).isoformat(),
        "timezone": "America/Chihuahua",
        "history_days": INITIAL_HISTORY_DAYS,
        "breakdown": {
            "received": len(inbox_ids),
            "sent": len(sent_ids),
            "unread": unread,
        },
        "excluded": {
            "drafts": drafts,
            "spam": spam,
            "trash": trash,
        },
    }


def microsoft_inventory(account: dict[str, Any]) -> dict[str, Any]:
    snapshot = microsoft_initial_snapshot(account)
    snapshot.pop("microsoft_refs", None)
    breakdown = snapshot.pop("breakdown")
    excluded = snapshot.pop("excluded")
    email = str(account.get("email") or "").strip().lower()
    return {
        "status": "ok",
        "mode": "initial_six_month_inventory",
        "email": email,
        "provider": "microsoft",
        "provider_label": "Outlook",
        "profile_messages_total": (
            snapshot["eligible_messages"]
            + excluded["drafts"]
            + excluded["spam"]
            + excluded["trash"]
        ),
        "profile_threads_total": snapshot["eligible_messages"],
        **snapshot,
        "breakdown": [
            {"key": "received", "count": breakdown["received"]},
            {"key": "sent", "count": breakdown["sent"]},
            {"key": "unread", "count": breakdown["unread"]},
        ],
        "excluded": excluded,
        "notice": (
            "Donexto importará los mensajes elegibles de los últimos seis "
            "meses. Spam, Papelera y Borradores quedan excluidos. "
            "El buzón original no se modifica."
        ),
    }


def microsoft_incremental_refs(
    account: dict[str, Any],
    *,
    since: datetime,
) -> list[str]:
    inbox_ids = _list_folder_ids(account, "inbox", since)
    sent_ids = _list_folder_ids(account, "sentitems", since)
    return list(
        dict.fromkeys(
            [encode_microsoft_ref("inbox", item) for item in inbox_ids]
            + [encode_microsoft_ref("sent", item) for item in sent_ids]
        )
    )


def _body_parts(payload: dict[str, Any]) -> tuple[str, str]:
    body = payload.get("body") or {}
    content = str(body.get("content") or "")
    content_type = str(body.get("contentType") or "").lower()
    preview = str(payload.get("bodyPreview") or "")
    if content_type == "html":
        text = re.sub(r"<[^>]+>", " ", content)
        text = re.sub(r"\s+", " ", text).strip() or preview
        return text, content
    text = re.sub(r"\s+", " ", content or preview).strip()
    return text, ""


def sync_microsoft_page(
    *,
    account: dict[str, Any],
    refs: list[str],
    offset: int,
    batch_size: int = MICROSOFT_PAGE_SIZE,
) -> dict[str, Any]:
    account_id = str(account["id"])
    address = str(account.get("email") or "").strip().lower()
    safe_batch = min(max(int(batch_size), 1), 50)
    started_at = _utc_now()
    page_refs = refs[offset : offset + safe_batch]
    next_offset = offset + len(page_refs)
    has_more = next_offset < len(refs)

    storage = OAuthStorage()
    client_db = storage.client
    inserted = 0
    duplicates = 0
    errors = 0
    inserted_message_ids: list[str] = []
    error_details: list[dict[str, str]] = []

    if not page_refs:
        completed_at = _utc_now()
        return {
            "status": "ok",
            "connected": True,
            "account_id": account_id,
            "email": address,
            "batch_size": safe_batch,
            "page_found": 0,
            "inserted": 0,
            "inserted_message_ids": [],
            "duplicates": 0,
            "errors": 0,
            "error_details": [],
            "next_page_token": None,
            "has_more": False,
            "started_at": _to_iso(started_at),
            "completed_at": _to_iso(completed_at),
        }

    external_ids = [
        f"microsoft:{folder}:{message_id}"
        for folder, message_id in (decode_microsoft_ref(ref) for ref in page_refs)
    ]
    existing_ids = _existing_message_ids(
        client=client_db,
        account_id=account_id,
        external_ids=external_ids,
    )
    duplicates = len(existing_ids)

    for ref in page_refs:
        folder, message_id = decode_microsoft_ref(ref)
        external_message_id = f"microsoft:{folder}:{message_id}"
        if external_message_id in existing_ids:
            continue
        try:
            payload = _graph_get_with_refresh(
                account,
                f"{MICROSOFT_GRAPH_BASE}/me/messages/{message_id}",
                params={"$select": MICROSOFT_SELECT},
            )
            subject = str(payload.get("subject") or "(Sin asunto)")
            from_raw = graph_address(payload.get("from") if isinstance(payload.get("from"), dict) else {})
            to_raw = graph_address_list(payload.get("toRecipients"))
            cc_raw = graph_address_list(payload.get("ccRecipients"))
            bcc_raw = graph_address_list(payload.get("bccRecipients"))
            received_raw = payload.get("receivedDateTime")
            received_at_iso = None
            if received_raw:
                try:
                    parsed = datetime.fromisoformat(
                        str(received_raw).replace("Z", "+00:00")
                    )
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    received_at_iso = _to_iso(parsed.astimezone(timezone.utc))
                except ValueError:
                    received_at_iso = _to_iso(_utc_now())
            else:
                received_at_iso = _to_iso(_utc_now())
            sender = _format_sender(from_raw)
            recipients = _parse_addresses(to_raw)
            cc = _parse_addresses(cc_raw)
            bcc = _parse_addresses(bcc_raw)
            participant_values: list[str] = []
            if sender:
                participant_values.append(sender)
            for item in recipients + cc + bcc:
                formatted = item.get("email") or item.get("name")
                if formatted:
                    participant_values.append(formatted)
            participants = ", ".join(dict.fromkeys(participant_values))
            body_text, body_html = _body_parts(payload)
            snippet = re.sub(
                r"\s+",
                " ",
                (body_text or subject or "")[:280],
            ).strip()
            if not body_text:
                body_text = snippet
            labels = ["MICROSOFT", folder.upper()]
            direction = "outbound" if folder == "sent" else "inbound"
            conversation = str(payload.get("conversationId") or external_message_id)
            thread = _get_or_create_thread(
                client=client_db,
                account_id=account_id,
                external_thread_id=conversation[:500],
                subject=subject,
                participants=participants,
                last_message_at=received_at_iso or _to_iso(_utc_now()) or "",
                provider="microsoft",
            )
            insert_response = (
                client_db.table("communication_messages")
                .insert(
                    {
                        "thread_id": str(thread["id"]),
                        "account_id": account_id,
                        "provider": "microsoft",
                        "external_message_id": external_message_id,
                        "sender": sender,
                        "recipients": recipients,
                        "cc": cc,
                        "bcc": bcc,
                        "subject": subject,
                        "body_text": body_text,
                        "body_html": body_html,
                        "received_at": received_at_iso,
                        "has_attachments": bool(payload.get("hasAttachments")),
                        "labels": labels,
                        "is_unread": not bool(payload.get("isRead")),
                        "snippet": snippet,
                        "direction": direction,
                        "internet_message_id": (
                            str(payload.get("internetMessageId") or "").strip()
                            or None
                        ),
                        "in_reply_to": None,
                        "references_header": [],
                        "case_processed": False,
                        "ai_processed": False,
                    }
                )
                .execute()
            )
            created = getattr(insert_response, "data", None)
            created_row = None
            if isinstance(created, list) and created:
                created_row = created[0]
            elif isinstance(created, dict):
                created_row = created
            if not created_row:
                raise RuntimeError(
                    "Supabase no confirmó la creación del mensaje Outlook."
                )
            inserted += 1
            inserted_message_ids.append(str(created_row["id"]))
        except Exception as error:
            errors += 1
            error_details.append(
                {
                    "ref": ref,
                    "error": str(error)[:240],
                }
            )

    completed_at = _utc_now()
    return {
        "status": "ok",
        "connected": True,
        "account_id": account_id,
        "email": address,
        "batch_size": safe_batch,
        "page_found": len(page_refs),
        "inserted": inserted,
        "inserted_message_ids": inserted_message_ids,
        "duplicates": duplicates,
        "errors": errors,
        "error_details": error_details,
        "next_page_token": str(next_offset) if has_more else None,
        "has_more": has_more,
        "started_at": _to_iso(started_at),
        "completed_at": _to_iso(completed_at),
    }
