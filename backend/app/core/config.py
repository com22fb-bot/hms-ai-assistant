from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


load_dotenv()


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


@dataclass(frozen=True)
class Settings:
    app_name: str = "HMS AI Assistant API"
    app_description: str = (
        "Backend para conectar cuentas de Google "
        "y consultar correos de Gmail."
    )
    app_version: str = "0.4.0"

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

    google_scopes: list[str] = field(
        default_factory=lambda: [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/gmail.readonly",
        ]
    )


settings = Settings()