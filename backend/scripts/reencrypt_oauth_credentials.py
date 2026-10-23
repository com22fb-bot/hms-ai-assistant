"""Re-cifrado versionado de oauth_credentials (NO se ejecuta en producción sin aprobación).

Por defecto es dry-run y solo imprime CONTEOS y el último cursor (uuid) para reanudar; nunca valores ni hashes.
Un error de configuración (falta OAUTH_ENCRYPTION_KEY, llavero inválido) aborta antes de escribir.

    python -m scripts.reencrypt_oauth_credentials            # auditoría, solo conteos
    python -m scripts.reencrypt_oauth_credentials --apply    # re-cifra (requiere aprobación)
    python -m scripts.reencrypt_oauth_credentials --apply --after <uuid>   # reanudar

Propiedades:
- Idempotente: filas ya cifradas con la llave activa no se tocan.
- Reanudable: recorre por id ascendente en lotes; imprime el último id procesado.
- Concurrencia: el UPDATE exige que access_token/refresh_token sigan iguales a lo leído
  (optimista); si cambió entre lectura y escritura, la fila se cuenta como "carrera" y se
  reintenta en la siguiente corrida.
- Filas indescifrables: no se modifican; solo se cuentan.
"""
from __future__ import annotations

import argparse
from collections import Counter
from typing import Any

from app.services import oauth_storage as ost

FIELDS = ("access_token", "refresh_token")


def run(client: Any, *, apply: bool = False, after: str | None = None, batch: int = 200) -> dict[str, Any]:
    stats: Counter = Counter()
    versions: Counter = Counter()
    active = ost._active_key_id()      # valida llavero y llave activa
    ost._get_encryption_secret()       # la llave legado debe existir (filas sin prefijo)
    cursor = after
    while True:
        q = client.table("oauth_credentials").select("id,access_token,refresh_token").order("id")
        if cursor:
            q = q.gt("id", cursor)
        rows = ost._rows_of(q.limit(batch).execute())
        if not rows:
            break
        for row in rows:
            stats["filas"] += 1
            cursor = row["id"]
            update: dict[str, Any] = {}
            bad = False
            for f in FIELDS:
                v = row.get(f)
                if v:
                    versions[ost.key_version_of(v)] += 1
                try:
                    ost._decrypt(v)  # verifica también filas ya en la llave activa
                    new, changed = ost.reencrypt_value(v)
                except ost.OAuthCredentialError:
                    bad = True
                    break
                if changed:
                    update[f] = new
            if bad:
                stats["indescifrables"] += 1
                continue
            if not update:
                stats["ya_en_llave_activa"] += 1
                continue
            stats["por_recifrar"] += 1
            if not apply:
                continue
            # returning=representation (default de postgrest-py): PostgREST devuelve las filas
            # actualizadas; vacío = ninguna fila cumplió el filtro optimista.
            uq = client.table("oauth_credentials").update(update, returning="representation").eq("id", row["id"])
            for f in FIELDS:
                uq = uq.eq(f, row.get(f)) if row.get(f) else uq.is_(f, "null")
            if ost._rows_of(uq.execute()):
                stats["recifradas"] += 1
                continue
            # Vacío no se asume como carrera: se relee para clasificar.
            now = ost._rows_of(client.table("oauth_credentials").select("id,access_token,refresh_token")
                               .eq("id", row["id"]).limit(1).execute())
            if not now:
                stats["eliminada_durante_proceso"] += 1
            elif any(now[0].get(f) != row.get(f) for f in FIELDS):
                stats["carrera_reintentar"] += 1
            else:
                stats["update_sin_confirmar"] += 1
        if len(rows) < batch:
            break
    return {"llave_activa": active, "modo": "apply" if apply else "dry-run",
            "conteos": dict(stats), "versiones_campos": dict(versions), "ultimo_cursor": cursor}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--after")
    ap.add_argument("--batch", type=int, default=200)
    a = ap.parse_args()
    print(run(ost._get_supabase_client(), apply=a.apply, after=a.after, batch=a.batch))


if __name__ == "__main__":
    main()
