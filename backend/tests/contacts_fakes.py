"""FakeSupabase con las claves únicas de las tablas CONTACTS_V1 (F1). Solo pruebas."""
from __future__ import annotations

from tests.fake_supabase import FakeSupabase, UniqueViolation

_UNIQUE_KEYS = {
    "message_participants": [("message_id", "role", "position"), ("message_id", "role", "address_norm")],
    "contact_addresses": [("workspace_id", "address_norm")],
    "own_address_aliases": [("workspace_id", "address_norm")],
}


class ContactsFakeSupabase(FakeSupabase):
    def _check_unique(self, table, row, rows):
        super()._check_unique(table, row, rows)
        for key in _UNIQUE_KEYS.get(table, []):
            if any(row.get(col) is None for col in key):
                continue  # índice parcial: address_norm nulo no participa
            for other in rows:
                if other is row or other.get("id") == row.get("id"):
                    continue
                if all(str(other.get(c)) == str(row.get(c)) for c in key):
                    raise UniqueViolation(f"duplicate key value violates unique constraint {table}{key} (23505)")

    def writes(self, table: str | None = None):
        return [c for c in self.calls if c[1] in ("insert", "update", "delete") and (table is None or c[0] == table)]
