"""
Análisis inteligente de correos.

HMS AI Assistant
Sprint 3.2

Proveedores disponibles:

- mock: análisis local y gratuito basado en reglas.
- openai: análisis mediante la API de OpenAI.

La selección se realiza con:

    AI_PROVIDER=mock
    AI_PROVIDER=openai
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.database.supabase import get_supabase_client


ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {
            "type": "string",
        },
        "sentiment": {
            "type": "string",
            "enum": [
                "positive",
                "neutral",
                "negative",
                "urgent",
            ],
        },
        "priority": {
            "type": "string",
            "enum": [
                "low",
                "normal",
                "high",
                "critical",
            ],
        },
        "category": {
            "type": "string",
            "enum": [
                "general",
                "request",
                "payment",
                "invoice",
                "meeting",
                "complaint",
                "legal",
                "human_resources",
                "sales",
                "security",
                "notification",
                "spam",
            ],
        },
        "requires_reply": {
            "type": "boolean",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
        },
        "deadline": {
            "type": [
                "string",
                "null",
            ],
        },
        "entities": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "people": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },
                "companies": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },
                "amounts": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },
                "dates": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },
                "topics": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },
            },
            "required": [
                "people",
                "companies",
                "amounts",
                "dates",
                "topics",
            ],
        },
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {
                        "type": "string",
                    },
                    "description": {
                        "type": "string",
                    },
                    "priority": {
                        "type": "string",
                        "enum": [
                            "low",
                            "normal",
                            "high",
                            "critical",
                        ],
                    },
                    "due_date": {
                        "type": [
                            "string",
                            "null",
                        ],
                    },
                },
                "required": [
                    "title",
                    "description",
                    "priority",
                    "due_date",
                ],
            },
        },
    },
    "required": [
        "summary",
        "sentiment",
        "priority",
        "category",
        "requires_reply",
        "confidence",
        "deadline",
        "entities",
        "tasks",
    ],
}


SYSTEM_INSTRUCTIONS = """
Eres el motor de clasificación de correos de HMS AI Assistant.

Analiza cada mensaje como un asistente ejecutivo y administrativo.

Debes:

1. Resumir objetivamente el correo.
2. Determinar su categoría.
3. Evaluar prioridad y urgencia.
4. Detectar si requiere respuesta.
5. Detectar solicitudes, compromisos y tareas concretas.
6. Detectar pagos, facturas, importes y fechas límite.
7. Extraer personas, empresas, fechas, montos y temas.
8. No inventar información.
9. No crear tareas para mensajes meramente informativos.
10. Usar null cuando no exista una fecha límite verificable.

El correo puede estar en español o inglés.
Devuelve el análisis en español.
""".strip()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: datetime | str | None) -> str | None:
    if value is None or value == "":
        return None

    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError:
            return None
    else:
        parsed = value

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc).isoformat()


def _first_row(response: Any) -> dict[str, Any] | None:
    data = getattr(response, "data", None)

    if not data:
        return None

    if isinstance(data, list):
        return data[0] if data else None

    if isinstance(data, dict):
        return data

    return None


def _message_text(message: dict[str, Any]) -> str:
    subject = str(
        message.get("subject") or ""
    ).strip()

    body = str(
        message.get("body_text")
        or message.get("body_html")
        or ""
    ).strip()

    return f"{subject}\n\n{body}".strip()


def _contains_any(
    text: str,
    terms: tuple[str, ...],
) -> bool:
    normalized = text.lower()

    return any(
        term in normalized
        for term in terms
    )


def _extract_amounts(text: str) -> list[str]:
    patterns = (
        r"(?:MXN|USD|EUR|\$|€)\s?"
        r"\d[\d,]*(?:\.\d{1,2})?",
        r"\d[\d,]*(?:\.\d{1,2})?\s?"
        r"(?:pesos|dólares|dollars|usd|mxn|eur)",
    )

    found: list[str] = []

    for pattern in patterns:
        found.extend(
            re.findall(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
        )

    return list(
        dict.fromkeys(
            value.strip()
            for value in found
            if value.strip()
        )
    )


def _extract_dates(text: str) -> list[str]:
    patterns = (
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",
        r"\b\d{1,2}-\d{1,2}-\d{4}\b",
    )

    found: list[str] = []

    for pattern in patterns:
        found.extend(
            re.findall(
                pattern,
                text,
            )
        )

    return list(
        dict.fromkeys(found)
    )


def _detect_category(text: str) -> str:
    rules: tuple[
        tuple[str, tuple[str, ...]],
        ...
    ] = (
        (
            "security",
            (
                "alerta de seguridad",
                "security alert",
                "contraseña",
                "password",
                "inicio de sesión",
                "recovery phone",
                "teléfono de recuperación",
                "actividad sospechosa",
                "suspicious activity",
                "verificación de cuenta",
            ),
        ),
        (
            "payment",
            (
                "pago",
                "payment",
                "transferencia",
                "depósito",
                "deposit",
                "cobro",
                "saldo pendiente",
            ),
        ),
        (
            "invoice",
            (
                "factura",
                "invoice",
                "comprobante fiscal",
                "cfdi",
            ),
        ),
        (
            "meeting",
            (
                "reunión",
                "meeting",
                "videollamada",
                "zoom",
                "teams",
                "calendar",
                "calendario",
            ),
        ),
        (
            "complaint",
            (
                "queja",
                "complaint",
                "inconformidad",
                "reclamo",
                "molesto",
                "disconformidad",
            ),
        ),
        (
            "legal",
            (
                "contrato",
                "legal",
                "demanda",
                "convenio",
                "abogado",
                "tribunal",
            ),
        ),
        (
            "human_resources",
            (
                "recursos humanos",
                "nómina",
                "vacaciones",
                "incapacidad",
                "empleado",
                "contratación",
            ),
        ),
        (
            "sales",
            (
                "cotización",
                "quotation",
                "propuesta comercial",
                "venta",
                "cliente potencial",
            ),
        ),
        (
            "spam",
            (
                "unsubscribe",
                "cancelar suscripción",
                "promoción",
                "oferta exclusiva",
                "newsletter",
                "boletín",
            ),
        ),
        (
            "request",
            (
                "por favor",
                "favor de",
                "se solicita",
                "solicitamos",
                "please send",
                "please confirm",
                "necesitamos",
                "requerimos",
                "quedo atento",
                "quedamos atentos",
            ),
        ),
        (
            "notification",
            (
                "notificación",
                "notification",
                "aviso",
                "informamos",
            ),
        ),
    )

    for category, keywords in rules:
        if _contains_any(text, keywords):
            return category

    return "general"


def _detect_priority(
    text: str,
    category: str,
) -> str:
    if _contains_any(
        text,
        (
            "crítico",
            "critical",
            "inmediatamente",
            "immediately",
            "emergencia",
            "fraude",
            "cuenta comprometida",
        ),
    ):
        return "critical"

    if _contains_any(
        text,
        (
            "urgente",
            "urgent",
            "hoy",
            "today",
            "vence",
            "vencimiento",
            "atención inmediata",
            "acción requerida",
            "action required",
        ),
    ):
        return "high"

    if category in {
        "security",
        "payment",
        "legal",
        "complaint",
    }:
        return "high"

    if category in {
        "spam",
        "notification",
    }:
        return "low"

    return "normal"


def _detect_requires_reply(
    text: str,
    category: str,
) -> bool:
    if "?" in text:
        return True

    if _contains_any(
        text,
        (
            "favor de confirmar",
            "por favor confirme",
            "please confirm",
            "quedo atento",
            "quedamos atentos",
            "esperamos su respuesta",
            "se solicita respuesta",
            "puede enviar",
            "podría enviar",
            "necesitamos que",
            "requerimos que",
        ),
    ):
        return True

    return category in {
        "request",
        "complaint",
        "sales",
    }


def _detect_sentiment(
    text: str,
    priority: str,
    category: str,
) -> str:
    if priority in {
        "critical",
        "high",
    } and category in {
        "security",
        "complaint",
        "payment",
        "legal",
    }:
        return "urgent"

    if _contains_any(
        text,
        (
            "gracias",
            "thank you",
            "excelente",
            "felicidades",
            "aprobado",
        ),
    ):
        return "positive"

    if _contains_any(
        text,
        (
            "error",
            "problema",
            "incumplimiento",
            "rechazado",
            "molesto",
            "queja",
        ),
    ):
        return "negative"

    return "neutral"


def _build_summary(
    message: dict[str, Any],
    category: str,
) -> str:
    subject = str(
        message.get("subject")
        or "(Sin asunto)"
    ).strip()

    sender = str(
        message.get("sender")
        or "remitente no identificado"
    ).strip()

    descriptions = {
        "security": (
            "Se recibió una alerta relacionada con la "
            "seguridad o configuración de una cuenta."
        ),
        "payment": (
            "El correo contiene información o una solicitud "
            "relacionada con un pago."
        ),
        "invoice": (
            "El mensaje trata sobre una factura o documento fiscal."
        ),
        "meeting": (
            "El correo está relacionado con una reunión o cita."
        ),
        "complaint": (
            "El remitente expresa una inconformidad o reclamación."
        ),
        "legal": (
            "El mensaje contiene un asunto de naturaleza legal."
        ),
        "human_resources": (
            "El correo está relacionado con personal o recursos humanos."
        ),
        "sales": (
            "El mensaje corresponde a una oportunidad o gestión comercial."
        ),
        "request": (
            "El remitente presenta una solicitud que debe revisarse."
        ),
        "notification": (
            "Se recibió un aviso informativo."
        ),
        "spam": (
            "El mensaje parece promocional o de baja relevancia."
        ),
        "general": (
            "Se recibió un correo de carácter general."
        ),
    }

    description = descriptions.get(
        category,
        descriptions["general"],
    )

    return (
        f'{description} Asunto: "{subject}". '
        f"Remitente: {sender}."
    )


def _build_tasks(
    message: dict[str, Any],
    text: str,
    category: str,
    priority: str,
    requires_reply: bool,
) -> list[dict[str, Any]]:
    subject = str(
        message.get("subject")
        or "(Sin asunto)"
    ).strip()

    tasks: list[dict[str, Any]] = []

    if category == "security":
        tasks.append(
            {
                "title": (
                    "Revisar actividad de seguridad de la cuenta"
                ),
                "description": (
                    f'Revisar el correo "{subject}" y confirmar '
                    "que el cambio o la actividad fueron autorizados."
                ),
                "priority": priority,
                "due_date": None,
            }
        )

    elif category == "payment":
        tasks.append(
            {
                "title": (
                    "Revisar solicitud o situación de pago"
                ),
                "description": (
                    f'Revisar el correo "{subject}", validar el '
                    "importe y determinar la acción correspondiente."
                ),
                "priority": priority,
                "due_date": None,
            }
        )

    elif category == "invoice":
        tasks.append(
            {
                "title": (
                    "Revisar factura o documento fiscal"
                ),
                "description": (
                    f'Validar la información contenida en "{subject}".'
                ),
                "priority": priority,
                "due_date": None,
            }
        )

    elif category == "meeting":
        tasks.append(
            {
                "title": (
                    "Revisar y confirmar reunión"
                ),
                "description": (
                    f'Revisar los datos de la reunión indicada en "{subject}".'
                ),
                "priority": priority,
                "due_date": None,
            }
        )

    elif category in {
        "request",
        "complaint",
        "legal",
        "human_resources",
        "sales",
    }:
        tasks.append(
            {
                "title": (
                    f"Atender correo: {subject}"
                ),
                "description": (
                    "Revisar la solicitud y realizar la acción "
                    "correspondiente."
                ),
                "priority": priority,
                "due_date": None,
            }
        )

    elif requires_reply:
        tasks.append(
            {
                "title": (
                    f"Responder correo: {subject}"
                ),
                "description": (
                    "Preparar y enviar una respuesta al remitente."
                ),
                "priority": priority,
                "due_date": None,
            }
        )

    return tasks


def analyze_message_with_mock(
    message: dict[str, Any],
) -> dict[str, Any]:
    text = _message_text(message)
    category = _detect_category(text)

    priority = _detect_priority(
        text=text,
        category=category,
    )

    requires_reply = _detect_requires_reply(
        text=text,
        category=category,
    )

    sentiment = _detect_sentiment(
        text=text,
        priority=priority,
        category=category,
    )

    amounts = _extract_amounts(text)
    dates = _extract_dates(text)

    return {
        "summary": _build_summary(
            message=message,
            category=category,
        ),
        "sentiment": sentiment,
        "priority": priority,
        "category": category,
        "requires_reply": requires_reply,
        "confidence": 0.75,
        "deadline": None,
        "entities": {
            "people": [],
            "companies": [],
            "amounts": amounts,
            "dates": dates,
            "topics": [category],
        },
        "tasks": _build_tasks(
            message=message,
            text=text,
            category=category,
            priority=priority,
            requires_reply=requires_reply,
        ),
    }


def _build_email_input(
    message: dict[str, Any],
) -> str:
    body = str(
        message.get("body_text")
        or message.get("body_html")
        or ""
    ).strip()[:30000]

    return f"""
Analiza el siguiente correo.

Remitente:
{message.get("sender") or ""}

Destinatarios:
{json.dumps(message.get("recipients") or [], ensure_ascii=False)}

Fecha:
{message.get("received_at") or ""}

Asunto:
{message.get("subject") or "(Sin asunto)"}

Contenido:
{body}
""".strip()


def analyze_message_with_openai(
    message: dict[str, Any],
) -> dict[str, Any]:
    api_key = os.getenv(
        "OPENAI_API_KEY",
        "",
    ).strip()

    model = os.getenv(
        "OPENAI_MODEL",
        "gpt-5-mini",
    ).strip()

    if not api_key:
        raise RuntimeError(
            "Falta OPENAI_API_KEY en backend/.env."
        )

    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError(
            "El paquete openai no está instalado."
        ) from error

    client = OpenAI(
        api_key=api_key,
    )

    response = client.responses.create(
        model=model,
        instructions=SYSTEM_INSTRUCTIONS,
        input=_build_email_input(message),
        store=False,
        text={
            "format": {
                "type": "json_schema",
                "name": "email_analysis",
                "strict": True,
                "schema": ANALYSIS_SCHEMA,
            }
        },
    )

    raw_output = response.output_text

    if not raw_output:
        raise RuntimeError(
            "OpenAI no devolvió contenido."
        )

    result = json.loads(raw_output)

    if not isinstance(result, dict):
        raise RuntimeError(
            "OpenAI devolvió un formato inválido."
        )

    return result


def analyze_message(
    message: dict[str, Any],
) -> dict[str, Any]:
    provider = os.getenv(
        "AI_PROVIDER",
        "mock",
    ).strip().lower()

    if provider in {
        "mock",
        "local",
        "rules",
    }:
        return analyze_message_with_mock(
            message
        )

    if provider == "openai":
        return analyze_message_with_openai(
            message
        )

    raise RuntimeError(
        f"Proveedor de IA no compatible: {provider}."
    )


def _get_pending_messages(
    client: Any,
    limit: int,
) -> list[dict[str, Any]]:
    response = (
        client.table("communication_messages")
        .select(
            "id,thread_id,account_id,provider,"
            "external_message_id,sender,recipients,"
            "subject,body_text,body_html,received_at,"
            "ai_processed"
        )
        .eq("ai_processed", False)
        .order("received_at", desc=False)
        .limit(limit)
        .execute()
    )

    data = getattr(response, "data", None)

    return data if isinstance(data, list) else []


def _get_workspace_id(
    client: Any,
    account_id: str,
) -> str:
    response = (
        client.table("communication_accounts")
        .select("workspace_id")
        .eq("id", account_id)
        .limit(1)
        .execute()
    )

    account = _first_row(response)

    if not account or not account.get("workspace_id"):
        raise RuntimeError(
            "No fue posible identificar el workspace."
        )

    return str(account["workspace_id"])


def _save_analysis(
    client: Any,
    message_id: str,
    analysis: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "message_id": message_id,
        "summary": analysis["summary"],
        "sentiment": analysis["sentiment"],
        "priority": analysis["priority"],
        "category": analysis["category"],
        "requires_reply": analysis["requires_reply"],
        "confidence": round(
            float(analysis["confidence"]),
            2,
        ),
        "entities": analysis["entities"],
        "deadline": _to_iso(
            analysis.get("deadline")
        ),
    }

    existing_response = (
        client.table("ai_analysis")
        .select("id")
        .eq("message_id", message_id)
        .limit(1)
        .execute()
    )

    existing = _first_row(
        existing_response
    )

    if existing:
        response = (
            client.table("ai_analysis")
            .update(payload)
            .eq("message_id", message_id)
            .execute()
        )
    else:
        response = (
            client.table("ai_analysis")
            .insert(payload)
            .execute()
        )

    saved = _first_row(response)

    if not saved:
        raise RuntimeError(
            "Supabase no confirmó el análisis."
        )

    return saved


def _replace_generated_tasks(
    client: Any,
    workspace_id: str,
    message_id: str,
    tasks: list[dict[str, Any]],
) -> int:
    """
    Reemplaza las tareas generadas por IA para un mensaje.

    Las tareas se almacenan en communication_tasks, que pertenece
    al modelo actual de comunicación y no depende del user_id
    obligatorio de la tabla tasks anterior.
    """

    (
        client.table("communication_tasks")
        .delete()
        .eq("message_id", message_id)
        .eq("detected_by_ai", True)
        .execute()
    )

    priority_map = {
        "low": "LOW",
        "normal": "MEDIUM",
        "medium": "MEDIUM",
        "high": "HIGH",
        "critical": "CRITICAL",
    }

    rows: list[dict[str, Any]] = []

    for task in tasks:
        title = str(
            task.get("title") or ""
        ).strip()

        if not title:
            continue

        raw_priority = str(
            task.get("priority") or "normal"
        ).strip().lower()

        rows.append(
            {
                "workspace_id": workspace_id,
                "message_id": message_id,
                "title": title,
                "description": str(
                    task.get("description") or ""
                ).strip(),
                "status": "OPEN",
                "priority": priority_map.get(
                    raw_priority,
                    "MEDIUM",
                ),
                "due_at": _to_iso(
                    task.get("due_date")
                ),
                "assigned_to": None,
                "detected_by_ai": True,
            }
        )

    if not rows:
        return 0

    response = (
        client.table("communication_tasks")
        .insert(rows)
        .execute()
    )

    data = getattr(response, "data", None)

    if not isinstance(data, list):
        raise RuntimeError(
            "Supabase no confirmó las tareas de comunicación."
        )

    return len(data)


def analyze_pending_messages(
    limit: int = 20,
) -> dict[str, Any]:
    safe_limit = min(
        max(limit, 1),
        100,
    )

    provider = os.getenv(
        "AI_PROVIDER",
        "mock",
    ).strip().lower()

    client = get_supabase_client()

    pending_messages = _get_pending_messages(
        client=client,
        limit=safe_limit,
    )

    analyzed = 0
    tasks_created = 0
    errors = 0
    error_details: list[dict[str, str]] = []

    started_at = _utc_now()

    for message in pending_messages:
        message_id = str(
            message.get("id") or ""
        )

        try:
            if not message_id:
                raise RuntimeError(
                    "El mensaje no tiene ID."
                )

            account_id = str(
                message.get("account_id") or ""
            )

            if not account_id:
                raise RuntimeError(
                    "El mensaje no tiene account_id."
                )

            workspace_id = _get_workspace_id(
                client=client,
                account_id=account_id,
            )

            analysis = analyze_message(
                message
            )

            _save_analysis(
                client=client,
                message_id=message_id,
                analysis=analysis,
            )

            created_tasks = _replace_generated_tasks(
                client=client,
                workspace_id=workspace_id,
                message_id=message_id,
                tasks=analysis.get("tasks") or [],
            )

            update_response = (
                client.table("communication_messages")
                .update(
                    {
                        "ai_processed": True,
                    }
                )
                .eq("id", message_id)
                .execute()
            )

            if not getattr(
                update_response,
                "data",
                None,
            ):
                raise RuntimeError(
                    "Supabase no confirmó ai_processed."
                )

            analyzed += 1
            tasks_created += created_tasks

        except Exception as error:
            errors += 1

            if len(error_details) < 20:
                error_details.append(
                    {
                        "message_id": message_id,
                        "error": str(error),
                    }
                )

    completed_at = _utc_now()

    return {
        "status": (
            "ok"
            if errors == 0
            else "partial"
        ),
        "ai_provider": provider,
        "requested_limit": safe_limit,
        "pending_found": len(pending_messages),
        "analyzed": analyzed,
        "tasks_created": tasks_created,
        "errors": errors,
        "error_details": error_details,
        "started_at": _to_iso(started_at),
        "completed_at": _to_iso(completed_at),
    }
