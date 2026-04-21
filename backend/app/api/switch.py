from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import json

from app.core.database import get_db
from app.core.auth import require_role
from app.core.security import encrypt_data, decrypt_data
from app.models.switch.switch_model import Switch, SNMPVersion
from app.schemas.switch import (
    SwitchCreate, SwitchUpdate, SwitchResponse,
    SNMPv3ConfigResponse, MASKED_PASSWORD,
)

router = APIRouter(prefix="/api/switches", tags=["交换机管理"])


def _decrypt_community(enc: str | None) -> str | None:
    if not enc:
        return None
    try:
        return decrypt_data(enc)
    except Exception:
        return None


def _switch_to_response(s: Switch) -> SwitchResponse:
    """Build a SwitchResponse with all sensitive fields masked."""
    # SNMPv3
    snmp_v3_resp = None
    if s.snmp_v3_config_encrypted:
        try:
            cfg = json.loads(decrypt_data(s.snmp_v3_config_encrypted))
        except Exception:
            cfg = {}
        snmp_v3_resp = SNMPv3ConfigResponse(
            username=cfg.get("username", ""),
            auth_protocol=cfg.get("auth_protocol", "SHA"),
            priv_protocol=cfg.get("priv_protocol", "AES"),
            auth_password=MASKED_PASSWORD,
            priv_password=MASKED_PASSWORD,
            auth_password_set=bool(cfg.get("auth_password")),
            priv_password_set=bool(cfg.get("priv_password")),
        )

    has_community = bool(s.community_encrypted)
    return SwitchResponse(
        id=str(s.id), ip=str(s.ip), mac=s.mac,
        snmp_version=s.snmp_version,
        community=MASKED_PASSWORD if has_community else None,
        community_set=has_community,
        snmp_v3_config=snmp_v3_resp, location=s.location,
        description=s.description, is_active=s.is_active,
        created_at=s.created_at, updated_at=s.updated_at,
    )


def _merge_snmp_v3(existing_encrypted: str | None, incoming) -> str:
    """Merge incoming SNMPv3 update with stored config.

    - Fields not provided (None) are kept.
    - Password fields equal to ``******`` are treated as "unchanged" so the UI can render a
      placeholder without the user having to re-enter the password.
    """
    existing = {}
    if existing_encrypted:
        try:
            existing = json.loads(decrypt_data(existing_encrypted))
        except Exception:
            existing = {}

    merged = dict(existing)
    if incoming is None:
        return encrypt_data(json.dumps(merged))

    data = incoming.model_dump(exclude_unset=True) if hasattr(incoming, "model_dump") else dict(incoming)
    for key in ("username", "auth_protocol", "priv_protocol"):
        if key in data and data[key] is not None:
            merged[key] = data[key]
    for key in ("auth_password", "priv_password"):
        if key in data and data[key] is not None and data[key] != MASKED_PASSWORD:
            merged[key] = data[key]

    required = {"username", "auth_protocol", "auth_password", "priv_protocol", "priv_password"}
    missing = [k for k in required if not merged.get(k)]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SNMPv3 config incomplete: missing {', '.join(missing)}",
        )

    return encrypt_data(json.dumps(merged))


def _merge_community(existing_encrypted: str | None, incoming: str | None) -> str | None:
    """Return the new community_encrypted value for a PATCH.

    - ``incoming is None``: caller did not send anything → keep existing.
    - ``incoming == "******"``: UI placeholder → keep existing.
    - Otherwise: encrypt and replace (empty string clears the field).
    """
    if incoming is None:
        return existing_encrypted
    if incoming == MASKED_PASSWORD:
        return existing_encrypted
    if incoming == "":
        return None
    return encrypt_data(incoming)


@router.get("", response_model=List[SwitchResponse])
async def list_switches(db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
    result = await db.execute(select(Switch).order_by(Switch.created_at.desc()))
    switches = result.scalars().all()
    return [_switch_to_response(s) for s in switches]


@router.get("/{switch_id}", response_model=SwitchResponse)
async def get_switch(switch_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
    result = await db.execute(select(Switch).where(Switch.id == switch_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Switch not found")
    return _switch_to_response(s)


@router.post("", response_model=SwitchResponse, status_code=status.HTTP_201_CREATED)
async def create_switch(body: SwitchCreate, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
    from sqlalchemy import cast, Text
    result = await db.execute(select(Switch).where(cast(Switch.ip, Text) == body.ip))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Switch with this IP already exists")

    snmp_v3_enc = None
    if body.snmp_v3_config:
        snmp_v3_enc = encrypt_data(body.snmp_v3_config.model_dump_json())

    community_enc = encrypt_data(body.community) if body.community else None

    switch = Switch(
        ip=body.ip, mac=body.mac,
        snmp_version=body.snmp_version,
        community_encrypted=community_enc,
        snmp_v3_config_encrypted=snmp_v3_enc,
        location=body.location, description=body.description,
    )
    db.add(switch)
    await db.commit()
    await db.refresh(switch)
    return _switch_to_response(switch)


@router.patch("/{switch_id}", response_model=SwitchResponse)
async def update_switch(switch_id: str, body: SwitchUpdate, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
    result = await db.execute(select(Switch).where(Switch.id == switch_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Switch not found")

    if body.mac is not None:
        s.mac = body.mac
    if body.snmp_version is not None:
        s.snmp_version = body.snmp_version
    s.community_encrypted = _merge_community(s.community_encrypted, body.community)
    if body.snmp_v3_config is not None:
        s.snmp_v3_config_encrypted = _merge_snmp_v3(s.snmp_v3_config_encrypted, body.snmp_v3_config)
    if body.location is not None:
        s.location = body.location
    if body.description is not None:
        s.description = body.description
    if body.is_active is not None:
        s.is_active = body.is_active

    await db.commit()
    await db.refresh(s)
    return _switch_to_response(s)


@router.delete("/{switch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_switch(switch_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
    result = await db.execute(select(Switch).where(Switch.id == switch_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Switch not found")
    await db.delete(s)
    await db.commit()


@router.post("/test")
async def test_switch_connection(
    body: SwitchCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Test SNMP connection to a switch using OID .1.3.6.1.2.1.1.1.0 (sysDescr).

    When the caller sends a masked community / SNMPv3 password (``******``) we look up the stored
    values for an existing switch with the same IP so admins can click "test" without retyping.
    """
    from app.services.snmp import SNMPScanner
    from app.core.config import settings
    from sqlalchemy import cast, Text

    community_value = body.community
    snmp_v3_dict = body.snmp_v3_config.model_dump() if body.snmp_v3_config else None

    needs_stored = (
        (community_value == MASKED_PASSWORD)
        or (snmp_v3_dict and (
            snmp_v3_dict.get("auth_password") == MASKED_PASSWORD
            or snmp_v3_dict.get("priv_password") == MASKED_PASSWORD
        ))
    )
    if needs_stored:
        existing_res = await db.execute(select(Switch).where(cast(Switch.ip, Text) == body.ip))
        existing = existing_res.scalar_one_or_none()
        if existing:
            if community_value == MASKED_PASSWORD:
                community_value = _decrypt_community(existing.community_encrypted)
            if snmp_v3_dict and existing.snmp_v3_config_encrypted:
                try:
                    stored_v3 = json.loads(decrypt_data(existing.snmp_v3_config_encrypted))
                except Exception:
                    stored_v3 = {}
                if snmp_v3_dict.get("auth_password") == MASKED_PASSWORD:
                    snmp_v3_dict["auth_password"] = stored_v3.get("auth_password", "")
                if snmp_v3_dict.get("priv_password") == MASKED_PASSWORD:
                    snmp_v3_dict["priv_password"] = stored_v3.get("priv_password", "")

    scanner = SNMPScanner(
        host=body.ip,
        snmp_version=body.snmp_version.value if hasattr(body.snmp_version, "value") else body.snmp_version,
        community=community_value,
        snmp_v3_config=snmp_v3_dict,
        timeout=settings.SNMP_TIMEOUT,
        retry=settings.SNMP_RETRY,
    )

    try:
        sys_descr = await scanner.get_sys_descr()
        return {"success": True, "message": sys_descr}
    except Exception as e:
        return {"success": False, "message": str(e)}
