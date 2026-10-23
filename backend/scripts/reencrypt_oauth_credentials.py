"""Re-cifrado versionado de oauth_credentials (NO se ejecuta en producción sin aprobación).

Por defecto es dry-run y solo imprime CONTEOS (nunca valores, ids completos ni hashes).

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
    active = ost._active_key_id()
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
            uq = client.table("oauth_credentials").update(update).eq("id", row["id"])
            for f in FIELDS:
                uq = uq.eq(f, row.get(f)) if row.get(f) else uq.is_(f, "null")
            if ost._rows_of(uq.execute()):
                stats["recifradas"] += 1
            else:
                stats["carrera_reintentar"] += 1
        if len(rows) < batch:
            break
    return {"llave_activa": active, "modo": "apply" if apply else "dry-run",
            "conteos": dict(stats), "versiones_campos": dict(versions), "ultimo_cursor_presente": cursor is not None}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--after")
    ap.add_argument("--batch", type=int, default=200)
    a = ap.parse_args()
    print(run(ost._get_supabase_client(), apply=a.apply, after=a.after, batch=a.batch))


if __name__ == "__main__":
    main()
