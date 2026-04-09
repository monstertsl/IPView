from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
import json

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.core.security import encrypt_data, decrypt_data, encrypt_json, decrypt_json
from app.models.switch.switch_model import Switch, SNMPVersion
from app.schemas.switch import SwitchCreate, SwitchUpdate, SwitchResponse

router = APIRouter(prefix="/api/switches", tags=["交换机管理"])


def _switch_to_response(s: Switch) -> SwitchResponse:
    snmp_v3 = None
    if s.snmp_v3_config_encrypted:
        cfg = json.loads(decrypt_data(s.snmp_v3_config_encrypted))
        snmp_v3 = cfg
    return SwitchResponse(
        id=str(s.id), ip=str(s.ip), mac=s.mac,
        snmp_version=s.snmp_version, community=s.community,
        snmp_v3_config=snmp_v3, location=s.location,
        description=s.description, is_active=s.is_active,
        created_at=s.created_at, updated_at=s.updated_at,
    )


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
    # Check duplicate IP - 使用 cast 将 INET 类型转换为文本进行比较
    from sqlalchemy import cast, Text
    result = await db.execute(select(Switch).where(cast(Switch.ip, Text) == body.ip))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Switch with this IP already exists")

    snmp_v3_enc = None
    if body.snmp_v3_config:
        snmp_v3_enc = encrypt_data(body.snmp_v3_config.model_dump_json())

    switch = Switch(
        ip=body.ip, mac=body.mac,
        snmp_version=body.snmp_version, community=body.community,
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
    if body.community is not None:
        s.community = body.community
    if body.snmp_v3_config is not None:
        s.snmp_v3_config_encrypted = encrypt_data(body.snmp_v3_config.model_dump_json())
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
async def test_switch_connection(body: SwitchCreate, current_user=Depends(require_role("admin"))):
    """Test SNMP connection to a switch using OID .1.3.6.1.2.1.1.1.0 (sysDescr)."""
    from app.services.snmp import SNMPScanner
    from app.core.config import settings

    snmp_config = None
    if body.snmp_v3_config:
        snmp_config = body.snmp_v3_config.model_dump()

    scanner = SNMPScanner(
        host=body.ip,
        snmp_version=body.snmp_version.value if hasattr(body.snmp_version, 'value') else body.snmp_version,
        community=body.community,
        snmp_v3_config=snmp_config,
        timeout=settings.SNMP_TIMEOUT,
        retry=settings.SNMP_RETRY,
    )

    try:
        sys_descr = await scanner.get_sys_descr()
        return {"success": True, "message": sys_descr}
    except Exception as e:
        return {"success": False, "message": str(e)}
