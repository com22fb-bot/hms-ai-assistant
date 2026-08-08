from __future__ import annotations

import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


# scripts/ -> repo root (parents[1]); parents[2] would target the parent of the repo
repo = Path(__file__).resolve().parents[1]
secret_dir = repo / ".hms-secrets"
secret_dir.mkdir(parents=True, exist_ok=True)
private_path = secret_dir / "vapid_private.pem"
env_path = secret_dir / "push.env"

if private_path.exists() and env_path.exists():
    print("VAPID_KEYS=EXISTING")
    raise SystemExit(0)

private_key = ec.generate_private_key(ec.SECP256R1())
private_path.write_bytes(
    private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
)
public_numbers = private_key.public_key().public_numbers()
public_bytes = (
    b"\x04"
    + public_numbers.x.to_bytes(32, "big")
    + public_numbers.y.to_bytes(32, "big")
)
public_key = base64.urlsafe_b64encode(public_bytes).rstrip(b"=").decode("ascii")
subject = os.getenv("HMS_VAPID_SUBJECT", "mailto:hmcelinfo@gmail.com")
env_path.write_text(
    "\n".join(
        [
            f"HMS_VAPID_PUBLIC_KEY={public_key}",
            f"HMS_VAPID_PRIVATE_KEY_PATH={private_path}",
            f"HMS_VAPID_SUBJECT={subject}",
            "HMS_AUTO_SYNC_ENABLED=true",
            "HMS_AUTO_SYNC_INTERVAL_SECONDS=120",
            "",
        ]
    ),
    encoding="utf-8",
)
os.chmod(private_path, 0o600)
os.chmod(env_path, 0o600)
print("VAPID_KEYS=CREATED")
print(f"VAPID_PUBLIC_KEY={public_key}")
