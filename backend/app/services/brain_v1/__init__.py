"""Cerebro v1 (Etapa 1): reglas deterministas detrás de BRAIN_V1_ENABLED.

Con la bandera apagada (predeterminado) nada de este paquete cambia el
comportamiento actual: el clasificador, el motor de casos, skip_message y los
importadores Graph/IMAP siguen exactamente igual que en main b8cfc7d.
"""
from __future__ import annotations

import os


def brain_v1_enabled() -> bool:
    return os.getenv("BRAIN_V1_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
