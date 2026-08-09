from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field

from dotenv import load_dotenv


load_dotenv()
HMS_PUSH_ENV_PATH = Path(__file__).resolve().parents[3] / '.hms-secrets' / 'push.env'
if HMS_PUSH_ENV_PATH.exists():
    load_dotenv(HMS_PUSH_ENV_PATH, override=False)


def get_environment_variable(
    name: str,
    default: str = "",
) -> str:
    """Obtiene una variable de entorno eliminando espacios externos."""
    return os.getenv(name, default).strip()


def get_list_environment_variable(
    name: str,
    default: str = "",
) -> list[str]:
    """Convierte una variable separada por comas en una lista limpia."""
    return [
        value.strip()
        for value in os.getenv(name, default).split(",")
        if value.strip()
    ]


def get_boolean_environment_variable(
    name: str,
    default: bool = False,
) -> bool:
    """Obtiene una bandera booleana con validación estricta."""
    raw_value = os.getenv(name)

    if raw_value is None or not raw_value.strip():
        return default

    normalized = raw_value.strip().lower()

    if normalized in {"1", "true", "yes", "on"}:
        return True

    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(
        f"{name} debe ser true/false, 1/0, yes/no u on/off."
    )


@dataclass(frozen=True)
class Settings:
    app_name: str = "Donexto API"
    app_description: str = (
        "Donexto — lo que requiere atención en tu correo. "
        "Buzones Gmail y Yahoo, prioridades y operaciones."
    )
    app_version: str = "0.4.4"

    supabase_url: str = field(
        default_factory=lambda: get_environment_variable(
            "SUPABASE_URL"
        )
    )
    supabase_secret_key: str = field(
        default_factory=lambda: get_environment_variable(
            "SUPABASE_SECRET_KEY"
        )
    )

    google_client_id: str = field(
        default_factory=lambda: get_environment_variable(
            "GOOGLE_CLIENT_ID"
        )
    )
    google_client_secret: str = field(
        default_factory=lambda: get_environment_variable(
            "GOOGLE_CLIENT_SECRET"
        )
    )
    google_redirect_uri: str = field(
        default_factory=lambda: get_environment_variable(
            "GOOGLE_REDIRECT_URI"
        )
    )

    frontend_origins: list[str] = field(
        default_factory=lambda: get_list_environment_variable(
            "FRONTEND_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        )
    )

    data_mutations_enabled: bool = field(
        default_factory=lambda: get_boolean_environment_variable(
            "HMS_DATA_MUTATIONS_ENABLED",
            False,
        )
    )

    google_scopes: list[str] = field(
        default_factory=lambda: [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/gmail.readonly",
        ]
    )


settings = Settings()