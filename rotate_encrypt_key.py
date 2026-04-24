"""Rotate / verify ENCRYPT_KEY for IPView.

Two independent modes controlled by the MODE env var:

  MODE=verify  (default if NEW_ENCRYPT_KEY is not set)
      Read-only. Decrypts every encrypted field with OLD_ENCRYPT_KEY and reports
      how many rows are readable. No new key required, no writes.

  MODE=rotate  (default if NEW_ENCRYPT_KEY is set)
      Decrypt with OLD_ENCRYPT_KEY, re-encrypt with NEW_ENCRYPT_KEY, write back.
      Aborts without any write if any row fails to decrypt with the old key.

Fields covered:
- users.totp_secret_encrypted
- switches.community_encrypted
- switches.snmp_v3_config_encrypted

Usage (one-liner, from host; script stays on host, streamed via stdin):

    # 1) Verify old key only (no writes, no new key required)
    docker exec -i -e PYTHONPATH=/app \
      -e OLD_ENCRYPT_KEY='<current-encrypt-key>' \
      -e MODE=verify \
      ipview-backend-1 python - < /root/IPView/rotate_encrypt_key.py

    # 2) Rotate (after stopping celery to avoid concurrent SNMP decrypt)
    docker compose stop celery celery-beat
    docker exec -i -e PYTHONPATH=/app \
      -e OLD_ENCRYPT_KEY='<current-encrypt-key>' \
      -e NEW_ENCRYPT_KEY='<new-encrypt-key>' \
      -e MODE=rotate \
      ipview-backend-1 python - < /root/IPView/rotate_encrypt_key.py

    # 3) Update docker-compose.yml (x-backend-env anchor) with the new key,
    #    then restart services.
    docker compose up -d backend celery celery-beat

Safety:
- Verify mode never writes; pure read + decrypt check.
- Rotate mode runs inside a single transaction; any failed decrypt aborts
  the whole batch so partial data is never written.
- Idempotent: re-running rotate is safe (rows already using the new key are
  detected and skipped).
"""
from __future__ import annotations

import asyncio
import base64
import os
import sys
from typing import Iterable

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import text

# NOTE: runs inside the backend container where `app` is importable.
from app.core.database import engine


# Tables to process: (table, primary_key, encrypted_column)
TARGETS: Iterable[tuple[str, str, str]] = (
    ("users", "id", "totp_secret_encrypted"),
    ("switches", "id", "community_encrypted"),
    ("switches", "id", "snmp_v3_config_encrypted"),
)


def _build_fernet(key: str) -> Fernet:
    """Mirror app.core.security._get_fernet but with an arbitrary key."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"ipview-salt-v1",
        iterations=100000,
    )
    derived = base64.urlsafe_b64encode(kdf.derive(key.encode()))
    return Fernet(derived)


def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        print(f"[rotate] ERROR: {name} env var is required", file=sys.stderr)
        sys.exit(2)
    return val


def _resolve_mode() -> str:
    """Determine verify vs rotate. Explicit MODE wins; otherwise infer from env."""
    explicit = os.environ.get("MODE", "").strip().lower()
    if explicit in {"verify", "rotate"}:
        return explicit
    if explicit:
        print(f"[rotate] ERROR: unknown MODE '{explicit}', expected 'verify' or 'rotate'", file=sys.stderr)
        sys.exit(2)
    # Infer: has NEW_ENCRYPT_KEY -> rotate, otherwise verify.
    return "rotate" if os.environ.get("NEW_ENCRYPT_KEY") else "verify"


async def _verify_table(conn, table: str, pk: str, column: str, fernet_old: Fernet) -> dict:
    rows = (await conn.execute(
        text(f"SELECT {pk}, {column} FROM {table} WHERE {column} IS NOT NULL AND {column} <> ''")
    )).fetchall()

    ok = 0
    failed = 0
    for row in rows:
        try:
            fernet_old.decrypt(row[1].encode())
            ok += 1
        except InvalidToken:
            failed += 1
            print(f"[verify] FAILED to decrypt {table}.{column} (id={row[0]})", file=sys.stderr)

    return {"table": table, "column": column, "total": len(rows), "ok": ok, "failed": failed}


async def _rotate_table(
    conn,
    table: str,
    pk: str,
    column: str,
    fernet_old: Fernet,
    fernet_new: Fernet,
) -> dict:
    rows = (await conn.execute(
        text(f"SELECT {pk}, {column} FROM {table} WHERE {column} IS NOT NULL AND {column} <> ''")
    )).fetchall()

    ok_old = 0
    already_new = 0
    failed = 0
    updates: list[tuple[str, str]] = []  # (new_cipher, pk_value)

    for row in rows:
        pk_val = row[0]
        cipher = row[1]

        # Already encrypted with the new key — skip (idempotent re-runs).
        try:
            fernet_new.decrypt(cipher.encode())
            already_new += 1
            continue
        except InvalidToken:
            pass

        # Try old key.
        try:
            plain = fernet_old.decrypt(cipher.encode()).decode()
        except InvalidToken:
            failed += 1
            print(f"[rotate] FAILED to decrypt {table}.{column} (id={pk_val}) with OLD key", file=sys.stderr)
            continue

        ok_old += 1
        new_cipher = fernet_new.encrypt(plain.encode()).decode()
        updates.append((new_cipher, pk_val))

    if failed:
        raise RuntimeError(
            f"{failed} row(s) in {table}.{column} could not be decrypted with OLD key. "
            "Aborting without writing any changes."
        )

    if updates:
        await conn.execute(
            text(f"UPDATE {table} SET {column} = :new_cipher WHERE {pk} = :pk_val"),
            [{"new_cipher": c, "pk_val": pk} for c, pk in updates],
        )

    return {
        "table": table,
        "column": column,
        "total": len(rows),
        "rotated": len(updates),
        "already_new": already_new,
    }


async def _run_verify() -> int:
    old_key = _require_env("OLD_ENCRYPT_KEY")
    fernet_old = _build_fernet(old_key)

    async with engine.connect() as conn:
        summary = []
        for table, pk, column in TARGETS:
            summary.append(await _verify_table(conn, table, pk, column, fernet_old))

    print("[verify] mode = verify (read-only)")
    print("[verify] summary:")
    any_failed = False
    for r in summary:
        print(
            f"  - {r['table']}.{r['column']}: total={r['total']} ok={r['ok']} failed={r['failed']}"
        )
        if r["failed"]:
            any_failed = True
    print("[verify] done." if not any_failed else "[verify] done WITH FAILURES.")
    return 1 if any_failed else 0


async def _run_rotate() -> int:
    old_key = _require_env("OLD_ENCRYPT_KEY")
    new_key = _require_env("NEW_ENCRYPT_KEY")

    if old_key == new_key:
        print("[rotate] OLD_ENCRYPT_KEY equals NEW_ENCRYPT_KEY; nothing to do.")
        return 0

    fernet_old = _build_fernet(old_key)
    fernet_new = _build_fernet(new_key)

    async with engine.begin() as conn:
        summary = []
        for table, pk, column in TARGETS:
            summary.append(
                await _rotate_table(conn, table, pk, column, fernet_old, fernet_new)
            )

    print("[rotate] mode = rotate (writes committed)")
    print("[rotate] summary:")
    for r in summary:
        print(
            f"  - {r['table']}.{r['column']}: total={r['total']} "
            f"rotated={r['rotated']} already_new={r['already_new']}"
        )
    print("[rotate] done.")
    return 0


async def _main() -> int:
    mode = _resolve_mode()
    if mode == "verify":
        return await _run_verify()
    return await _run_rotate()


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
