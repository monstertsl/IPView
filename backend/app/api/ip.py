from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func, text
from typing import List, Optional
import ipaddress
from datetime import datetime, timezone, timedelta

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.core.redis import RedisSession
from app.core.config import settings
from app.models.ip.ip_model import IPSubnet, IPRecord, IPEvent, IPStatus, IPEventType
from app.models.system.system_model import SystemConfig
from app.schemas.ip import (
    IPSubnetCreate, IPSubnetResponse,
    IPRecordResponse, IPHistoryResponse, IPBulkResponse, IPTooltipData
)

router = APIRouter(prefix="/api/ip", tags=["IP管理"])


async def _get_status(last_seen: Optional[datetime], db: AsyncSession) -> IPStatus:
    if not last_seen:
        return IPStatus.UNUSED
    result = await db.execute(select(SystemConfig).limit(1))
    cfg = result.scalar_one_or_none()
    if not cfg:
        cfg_dict = {
            "online_days": settings.ONLINE_DAYS,
            "offline_days": settings.OFFLINE_DAYS,
            "cleanup_days": settings.CLEANUP_DAYS,
        }
    else:
        cfg_dict = {
            "online_days": cfg.online_days,
            "offline_days": cfg.offline_days,
            "cleanup_days": cfg.cleanup_days,
        }
    now = datetime.now(timezone.utc)
    delta = (now - last_seen.replace(tzinfo=timezone.utc)).days
    if delta <= cfg_dict["online_days"]:
        return IPStatus.ONLINE
    elif delta <= cfg_dict["offline_days"]:
        return IPStatus.OFFLINE
    else:
        return IPStatus.UNUSED


def _iprecord_to_response(r: IPRecord) -> IPRecordResponse:
    return IPRecordResponse(
        id=str(r.id), ip_address=str(r.ip_address),
        mac_address=r.mac_address, last_seen=r.last_seen,
        status=r.status, created_at=r.created_at, updated_at=r.updated_at,
    )


@router.get("/subnets", response_model=List[IPSubnetResponse])
async def list_subnets(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(IPSubnet).order_by(IPSubnet.cidr))
    subnets = result.scalars().all()
    return [IPSubnetResponse(
        id=str(s.id), cidr=s.cidr,
        description=s.description, created_at=s.created_at
    ) for s in subnets]


@router.post("/subnets", response_model=IPSubnetResponse, status_code=201)
async def create_subnet(body: IPSubnetCreate, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
    result = await db.execute(select(IPSubnet).where(IPSubnet.cidr == body.cidr))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Subnet already exists")
    subnet = IPSubnet(cidr=body.cidr, description=body.description)
    db.add(subnet)
    await db.commit()
    await db.refresh(subnet)

    # Pre-populate IP records for this subnet
    network = ipaddress.ip_network(subnet.cidr, strict=False)
    batch = []
    for ip in network.hosts():
        batch.append(IPRecord(ip_address=str(ip)))
    if batch:
        db.add_all(batch)
        await db.commit()

    return IPSubnetResponse(id=str(subnet.id), cidr=subnet.cidr, description=subnet.description, created_at=subnet.created_at)


@router.delete("/subnets/{subnet_id}", status_code=204)
async def delete_subnet(subnet_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
    result = await db.execute(select(IPSubnet).where(IPSubnet.id == subnet_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Subnet not found")
    # Delete IP records first
    await db.execute(delete(IPRecord).where(IPRecord.ip_address.op("<<=")(s.cidr)))
    await db.execute(delete(IPSubnet).where(IPSubnet.id == subnet_id))
    await db.commit()


@router.get("/subnets/{subnet_id}/ips", response_model=IPBulkResponse)
async def get_subnet_ips(
    subnet_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    result = await db.execute(select(IPSubnet).where(IPSubnet.id == subnet_id))
    subnet = result.scalar_one_or_none()
    if not subnet:
        raise HTTPException(status_code=404, detail="Subnet not found")

    # Get all IPs in subnet
    result = await db.execute(
        select(IPRecord)
        .where(IPRecord.ip_address.op("<<=")(subnet.cidr))
        .order_by(IPRecord.ip_address)
    )
    records = result.scalars().all()

    online = offline = unused = 0
    for r in records:
        if r.status == IPStatus.ONLINE:
            online += 1
        elif r.status == IPStatus.OFFLINE:
            offline += 1
        else:
            unused += 1

    return IPBulkResponse(
        subnet=subnet.cidr,
        total=len(records),
        online=online, offline=offline, unused=unused,
        records=[_iprecord_to_response(r) for r in records]
    )


@router.get("/search")
async def search_ip(
    q: str = Query(..., description="IP, MAC, or subnet CIDR"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    q = q.strip()
    # Try IP first
    try:
        ipaddress.ip_address(q)
        result = await db.execute(select(IPRecord).where(IPRecord.ip_address == q))
        record = result.scalar_one_or_none()
        if record:
            return {"type": "ip", "record": _iprecord_to_response(record)}
    except ValueError:
        pass

    # Try MAC
    import re
    if re.match(r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$", q):
        result = await db.execute(
            select(IPRecord).where(func.upper(IPRecord.mac_address) == q.upper())
        )
        records = result.scalars().all()
        if records:
            return {"type": "mac", "records": [_iprecord_to_response(r) for r in records]}

    # Try subnet
    try:
        network = ipaddress.ip_network(q, strict=False)
        result = await db.execute(
            select(IPRecord)
            .where(IPRecord.ip_address.op("<<=")(str(network)))
            .order_by(IPRecord.ip_address)
        )
        records = result.scalars().all()
        if records:
            return {"type": "subnet", "cidr": str(network), "records": [_iprecord_to_response(r) for r in records]}
    except ValueError:
        pass

    return {"type": "not_found", "q": q}


@router.get("/ip/{ip_address}/tooltip", response_model=IPTooltipData)
async def get_ip_tooltip(ip_address: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    # Try cache first
    cached = await RedisSession.get_cached_ip_data(ip_address)
    if cached:
        return IPTooltipData(**cached)

    result = await db.execute(select(IPRecord).where(IPRecord.ip_address == ip_address))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="IP not found")

    status_str = record.status.value if record.status else IPStatus.UNUSED.value

    # Get history (max 5, sorted desc)
    result = await db.execute(
        select(IPEvent)
        .where(IPEvent.ip_address == ip_address)
        .order_by(IPEvent.seen_at.desc())
        .limit(5)
    )
    events = result.scalars().all()

    history = [
        IPHistoryResponse(
            id=str(e.id), ip_address=str(e.ip_address),
            mac_address=e.mac_address, event_type=e.event_type, seen_at=e.seen_at
        ) for e in events
    ]

    data = IPTooltipData(
        ip_address=str(record.ip_address),
        status=status_str,
        current_mac=record.mac_address,
        last_seen=record.last_seen,
        history=history
    )

    await RedisSession.cache_ip_data(ip_address, data.model_dump(mode="json"))
    return data
