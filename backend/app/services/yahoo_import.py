"""Importación guiada de Yahoo IMAP (mismos 6 meses + clasificación que Gmail)."""

from __future__ import annotations

import email
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
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
from app.services.oauth_storage import OAuthStorage
from app.services.yahoo_imap import (
    YahooImapError,
    _decode_header_value,
    _open_yahoo_client,
    classify_yahoo_folder,
    decode_yahoo_ref,
    encode_yahoo_ref,
    extract_rfc822_bodies,
    imap_search_date,
    normalize_yahoo_address,
    normalize_yahoo_app_password,
    parse_list_mailbox_name,
)


def is_yahoo_provider(account: dict[str, Any] | None) -> bool:
    provider = str((account or {}).get("provider") or "").strip().lower()
    return provider in {"yahoo", "imap"}


YAHOO_IMPORT_TIMEOUT = 120
YAHOO_PAGE_SIZE = 25


def _quoted_mailbox(name: str) -> str:
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _history_window(
    cutoff_at: datetime | None = None,
) -> tuple[datetime, datetime]:
    current = cutoff_at or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    start = current - timedelta(days=INITIAL_HISTORY_DAYS)
    return start, current


def _list_folder_names(client: Any) -> list[str]:
    status, data = client.list()
    if status != "OK" or not data:
        return ["INBOX"]

    names: list[str] = []
    for row in data:
        name = parse_list_mailbox_name(row)
        if name:
            names.append(name)
    return names or ["INBOX"]


def _uid_search(client: Any, *criteria: str) -> list[str]:
    status, data = client.uid("SEARCH", None, *criteria)
    if status != "OK" or not data or not data[0]:
        return []
    raw = data[0]
    text = raw.decode("ascii", errors="ignore") if isinstance(raw, bytes) else str(raw)
    return [item for item in text.split() if item]


def _select_folder(client: Any, folder: str) -> None:
    status, _ = client.select(_quoted_mailbox(folder), readonly=True)
    if status != "OK":
        status, _ = client.select(folder, readonly=True)
    if status != "OK":
        raise YahooImapError(f"No fue posible abrir la carpeta {folder}.")


def _folder_uids_since(client: Any, folder: str, since: datetime) -> list[str]:
    _select_folder(client, folder)
    return _uid_search(client, "SINCE", imap_search_date(since))


def _collect_refs(
    client: Any,
    *,
    since: datetime,
    roles: set[str],
) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {role: [] for role in roles}
    grouped.setdefault("other", [])

    for folder in _list_folder_names(client):
        role = classify_yahoo_folder(folder)
        if role not in roles:
            continue
        try:
            uids = _folder_uids_since(client, folder, since)
        except YahooImapError:
            continue
        except Exception:
            continue
        for uid in uids:
            grouped.setdefault(role, []).append(encode_yahoo_ref(folder, uid))
    return grouped


def yahoo_initial_snapshot(
    address: str,
    app_password: str,
    *,
    cutoff_at: datetime | None = None,
) -> dict[str, Any]:
    address = normalize_yahoo_address(address)
    app_password = normalize_yahoo_app_password(app_password)
    start, current = _history_window(cutoff_at)

    client = _open_yahoo_client(
        address,
        app_password,
        timeout=YAHOO_IMPORT_TIMEOUT,
    )
    try:
        grouped = _collect_refs(
            client,
            since=start,
            roles={"inbox", "sent", "draft", "spam", "trash"},
        )
        eligible = grouped.get("inbox", []) + grouped.get("sent", [])
        unread = 0
        inbox_folders = {
            decode_yahoo_ref(ref)[0] for ref in grouped.get("inbox", [])
        } or {"INBOX"}
        for folder in inbox_folders:
            try:
                _select_folder(client, folder)
                unread += len(
                    _uid_search(
                        client,
                        "SINCE",
                        imap_search_date(start),
                        "UNSEEN",
                    )
                )
            except Exception:
                continue
    finally:
        try:
            client.logout()
        except Exception:
            pass

    unique_eligible = list(dict.fromkeys(eligible))
    return {
        "query": (
            f"yahoo:since:{imap_search_date(start)} "
            f"until:{imap_search_date(current)}"
        ),
        "eligible_messages": len(unique_eligible),
        "yahoo_refs": unique_eligible,
        "snapshot_at_utc": current.isoformat(),
        "period_start_utc": start.isoformat(),
        "period_end_utc": current.isoformat(),
        "period_start_local": start.astimezone(LOCAL_TIMEZONE).isoformat(),
        "period_end_local": current.astimezone(LOCAL_TIMEZONE).isoformat(),
        "timezone": "America/Chihuahua",
        "history_days": INITIAL_HISTORY_DAYS,
        "breakdown": {
            "received": len(grouped.get("inbox", [])),
            "sent": len(grouped.get("sent", [])),
            "unread": unread,
        },
        "excluded": {
            "drafts": len(grouped.get("draft", [])),
            "spam": len(grouped.get("spam", [])),
            "trash": len(grouped.get("trash", [])),
        },
    }


def yahoo_inventory(address: str, app_password: str) -> dict[str, Any]:
    snapshot = yahoo_initial_snapshot(address, app_password)
    snapshot.pop("yahoo_refs", None)
    breakdown = snapshot.pop("breakdown")
    excluded = snapshot.pop("excluded")
    return {
        "status": "ok",
        "mode": "initial_six_month_inventory",
        "email": normalize_yahoo_address(address),
        "provider": "yahoo",
        "provider_label": "Yahoo",
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


def yahoo_incremental_refs(
    address: str,
    app_password: str,
    *,
    since: datetime,
) -> list[str]:
    address = normalize_yahoo_address(address)
    app_password = normalize_yahoo_app_password(app_password)
    client = _open_yahoo_client(
        address,
        app_password,
        timeout=YAHOO_IMPORT_TIMEOUT,
    )
    try:
        grouped = _collect_refs(
            client,
            since=since,
            roles={"inbox", "sent"},
        )
        return list(dict.fromkeys(grouped.get("inbox", []) + grouped.get("sent", [])))
    finally:
        try:
            client.logout()
        except Exception:
            pass


def _flags_from_fetch(meta: bytes | str) -> str:
    if isinstance(meta, bytes):
        return meta.decode("utf-8", errors="ignore")
    return str(meta)


def _fetch_uid_message(client: Any, uid: str) -> tuple[email.message.Message, str]:
    status, fetched = client.uid("FETCH", uid, "(FLAGS BODY.PEEK[])")
    if status != "OK" or not fetched:
        raise YahooImapError(f"Yahoo no devolvió el mensaje {uid}.")

    raw_bytes = b""
    flags_text = ""
    for part in fetched:
        if isinstance(part, tuple) and len(part) >= 2:
            flags_text += _flags_from_fetch(part[0])
            payload = part[1]
            if isinstance(payload, bytes) and payload:
                raw_bytes = payload
        elif isinstance(part, bytes):
            flags_text += _flags_from_fetch(part)

    if not raw_bytes:
        raise YahooImapError(f"Yahoo devolvió un mensaje vacío ({uid}).")
    return email.message_from_bytes(raw_bytes), flags_text


def _external_thread_id(parsed: email.message.Message, fallback: str) -> str:
    in_reply = _decode_header_value(parsed.get("In-Reply-To")).strip()
    message_id = _decode_header_value(parsed.get("Message-ID")).strip()
    references = _decode_header_value(parsed.get("References")).strip()
    for candidate in (in_reply, message_id, references.split()[0] if references else ""):
        cleaned = candidate.strip("<> \t")
        if cleaned:
            return cleaned[:500]
    return fallback


def sync_yahoo_page(
    *,
    account: dict[str, Any],
    app_password: str,
    refs: list[str],
    offset: int,
    batch_size: int = YAHOO_PAGE_SIZE,
) -> dict[str, Any]:
    account_id = str(account["id"])
    address = normalize_yahoo_address(str(account.get("email") or ""))
    app_password = normalize_yahoo_app_password(app_password)
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
        f"yahoo:{folder}:{uid}"
        for folder, uid in (decode_yahoo_ref(ref) for ref in page_refs)
    ]
    existing_ids = _existing_message_ids(
        client=client_db,
        account_id=account_id,
        external_ids=external_ids,
    )
    duplicates = len(existing_ids)

    imap_client = _open_yahoo_client(
        address,
        app_password,
        timeout=YAHOO_IMPORT_TIMEOUT,
    )
    selected_folder: str | None = None
    try:
        for ref in page_refs:
            folder, uid = decode_yahoo_ref(ref)
            external_message_id = f"yahoo:{folder}:{uid}"
            if external_message_id in existing_ids:
                continue
            try:
                if selected_folder != folder:
                    _select_folder(imap_client, folder)
                    selected_folder = folder
                parsed, flags_text = _fetch_uid_message(imap_client, uid)
                body_text, body_html, has_attachments = extract_rfc822_bodies(
                    parsed
                )
                subject = _decode_header_value(parsed.get("Subject")) or "(Sin asunto)"
                from_raw = _decode_header_value(parsed.get("From"))
                to_raw = _decode_header_value(parsed.get("To"))
                cc_raw = _decode_header_value(parsed.get("Cc"))
                bcc_raw = _decode_header_value(parsed.get("Bcc"))
                date_raw = parsed.get("Date")
                received_at = None
                if date_raw:
                    try:
                        parsed_date = parsedate_to_datetime(date_raw)
                        if parsed_date.tzinfo is None:
                            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                        received_at = parsed_date.astimezone(timezone.utc)
                    except Exception:
                        received_at = None
                received_at_iso = _to_iso(received_at or _utc_now())
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
                folder_role = classify_yahoo_folder(folder)
                labels = ["YAHOO", folder_role.upper()]
                is_unread = "\\Seen" not in flags_text
                direction = "outbound" if folder_role == "sent" else "inbound"
                snippet = re.sub(
                    r"\s+",
                    " ",
                    (body_text or subject or "")[:280],
                ).strip()
                if not body_text:
                    body_text = snippet
                thread = _get_or_create_thread(
                    client=client_db,
                    account_id=account_id,
                    external_thread_id=_external_thread_id(
                        parsed,
                        external_message_id,
                    ),
                    subject=subject,
                    participants=participants,
                    last_message_at=received_at_iso or _to_iso(_utc_now()) or "",
                    provider="yahoo",
                )
                insert_response = (
                    client_db.table("communication_messages")
                    .insert(
                        {
                            "thread_id": str(thread["id"]),
                            "account_id": account_id,
                            "provider": "yahoo",
                            "external_message_id": external_message_id,
                            "sender": sender,
                            "recipients": recipients,
                            "cc": cc,
                            "bcc": bcc,
                            "subject": subject,
                            "body_text": body_text,
                            "body_html": body_html,
                            "received_at": received_at_iso,
                            "has_attachments": has_attachments,
                            "labels": labels,
                            "is_unread": is_unread,
                            "snippet": snippet,
                            "direction": direction,
                            "internet_message_id": (
                                _decode_header_value(parsed.get("Message-ID")).strip()
                                or None
                            ),
                            "in_reply_to": (
                                _decode_header_value(parsed.get("In-Reply-To")).strip()
                                or None
                            ),
                            "references_header": [
                                item.strip()
                                for item in _decode_header_value(
                                    parsed.get("References")
                                ).split()
                                if item.strip()
                            ],
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
                        "Supabase no confirmó la creación del mensaje Yahoo."
                    )
                inserted += 1
                inserted_message_ids.append(str(created_row["id"]))
            except Exception as error:
                error_text = str(error).lower()
                if (
                    "duplicate key" in error_text
                    or "unique constraint" in error_text
                    or "23505" in error_text
                ):
                    duplicates += 1
                    continue
                errors += 1
                if len(error_details) < 20:
                    error_details.append(
                        {
                            "message_id": external_message_id,
                            "error": str(error),
                        }
                    )
    finally:
        try:
            imap_client.logout()
        except Exception:
            pass

    completed_at = _utc_now()
    return {
        "status": "ok" if errors == 0 else "partial",
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
