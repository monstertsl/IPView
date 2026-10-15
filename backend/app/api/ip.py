from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func, text, cast, String
from typing import List, Optional
import ipaddress
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.core.redis import RedisSession
from app.core.config import settings
from app.models.ip.ip_model import IPSubnet, IPRecord, IPEvent, IPStatus, IPEventType
from app.models.system.system_model import SystemConfig
from sqlalchemy.dialects.postgresql import INET, CIDR
from app.schemas.ip import (
    IPSubnetCreate, IPSubnetResponse,
    IPRecordResponse, IPHistoryResponse, IPBulkResponse, IPTooltipData,
    IPRemarkUpdate, IPRemarkBatchUpdate, IPRemarkBatchResponse
)

router = APIRouter(prefix="/api/ip", tags=["IP管理"])


def _iprecord_to_response(r: IPRecord) -> IPRecordResponse:
    return IPRecordResponse(
        id=str(r.id), ip_address=str(r.ip_address).split('/')[0],
        mac_address=r.mac_address, last_seen=r.last_seen,
        status=r.status, remark=r.remark,
        created_at=r.created_at, updated_at=r.updated_at,
    )


@router.get("/subnets", response_model=List[IPSubnetResponse])
async def list_subnets(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(IPSubnet).order_by(cast(IPSubnet.cidr, CIDR)))
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

    # Pre-populate IP records for this subnet (include all 0-255 addresses)
    network = ipaddress.ip_network(subnet.cidr, strict=False)
    batch = []
    for ip in network:
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
    await db.execute(delete(IPRecord).where(IPRecord.ip_address.op("<<=")(cast(s.cidr, CIDR))))
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

    # Get existing IPs in subnet from DB
    result = await db.execute(
        select(IPRecord)
        .where(IPRecord.ip_address.op("<<=")(cast(subnet.cidr, CIDR)))
        .order_by(IPRecord.ip_address)
    )
    db_records = result.scalars().all()
    db_map = {str(r.ip_address).split('/')[0]: r for r in db_records}

    # Build full address list for the subnet (0-255)
    network = ipaddress.ip_network(subnet.cidr, strict=False)
    all_records = []
    online = offline = unused = 0

    for host in network:
        ip_str = str(host)
        if ip_str in db_map:
            r = db_map[ip_str]
            all_records.append(_iprecord_to_response(r))
            if r.status == IPStatus.ONLINE:
                online += 1
            elif r.status == IPStatus.OFFLINE:
                offline += 1
            else:
                unused += 1
        else:
            all_records.append(IPRecordResponse(
                id="", ip_address=ip_str, mac_address=None,
                last_seen=None, status=None, created_at=None, updated_at=None,
            ))
            unused += 1

    return IPBulkResponse(
        subnet=subnet.cidr,
        total=len(all_records),
        online=online, offline=offline, unused=unused,
        records=all_records,
    )


@router.get("/search")
async def search_ip(
    q: str = Query(..., description="IP, MAC, or subnet CIDR"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    q = q.strip()
    # 1) Try exact IP address
    try:
        ipaddress.ip_address(q)
        result = await db.execute(select(IPRecord).where(IPRecord.ip_address == cast(q, INET)))
        record = result.scalar_one_or_none()
        if record:
            # Get MAC history for this IP (max 5, newest first)
            hist_result = await db.execute(
                select(IPEvent)
                .where(IPEvent.ip_address == cast(q, INET))
                .order_by(IPEvent.seen_at.desc())
                .limit(5)
            )
            events = hist_result.scalars().all()
            history = [
                {"mac_address": e.mac_address, "event_type": e.event_type.value if hasattr(e.event_type, 'value') else str(e.event_type), "seen_at": e.seen_at.isoformat() if e.seen_at else None}
                for e in events
            ]
            return {
                "type": "ip",
                "record": _iprecord_to_response(record),
                "history": history,
                "current_mac": record.mac_address,
            }
        # IP not found in DB（该地址还没被扫描到）→ 若它属于某个已知网段，
        # 仍然返回一条空记录，让前端能展示状态并直接添加备注。
        subnet_result = await db.execute(
            select(IPSubnet).where(cast(IPSubnet.cidr, CIDR).op(">>=")(cast(q, INET)))
        )
        owner = subnet_result.scalars().first()
        if owner:
            return {
                "type": "ip",
                "record": IPRecordResponse(
                    id="", ip_address=q, mac_address=None, last_seen=None,
                    status=IPStatus.UNUSED, remark=None,
                    created_at=None, updated_at=None,
                ),
                "history": [],
                "current_mac": None,
            }
        # IP not found in DB → fall through to subnet search
    except ValueError:
        pass

    # 2) Try MAC
    import re
    if re.match(r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$", q):
        result = await db.execute(
            select(IPRecord).where(func.upper(IPRecord.mac_address) == q.upper())
        )
        records = result.scalars().all()
        # Also find historical IPs that used this MAC (from ip_events)
        hist_result = await db.execute(
            select(IPEvent)
            .where(func.upper(IPEvent.mac_address) == q.upper())
            .order_by(IPEvent.seen_at.desc())
            .limit(5)
        )
        events = hist_result.scalars().all()
        history = [
            {"ip_address": str(e.ip_address), "event_type": e.event_type.value if hasattr(e.event_type, 'value') else str(e.event_type), "seen_at": e.seen_at.isoformat() if e.seen_at else None}
            for e in events
        ]
        # Current IP using this MAC — only the most recently seen record counts
        # as "current". When a device moves to a new IP, the old IPRecord row
        # may still carry the MAC for a while (until cleanup_days turns it
        # UNUSED and triggers IP_RELEASED). We pick the latest last_seen so the
        # UI reports the single IP the device actually uses right now.
        if records:
            latest = max(records, key=lambda r: r.last_seen or datetime.min)
            current_ips = [str(latest.ip_address).split('/')[0]]
        else:
            current_ips = []
        return {
            "type": "mac",
            "records": [_iprecord_to_response(r) for r in records],
            "history": history,
            "current_ips": current_ips,
        }

    # 3) Try exact CIDR match
    subnet_result = await db.execute(select(IPSubnet).where(IPSubnet.cidr == q))
    subnet = subnet_result.scalar_one_or_none()
    if subnet:
        return {"type": "subnet", "subnet_id": str(subnet.id), "cidr": subnet.cidr}

    # 4) Prefix match on the IP portion only (before '/')
    #    e.g. "10.10.0" matches "10.10.0.0/24"
    #    Only auto-jump if exactly ONE match, otherwise show list
    subnet_result = await db.execute(
        select(IPSubnet).where(func.split_part(IPSubnet.cidr, '/', 1).startswith(q)).order_by(cast(IPSubnet.cidr, CIDR))
    )
    prefix_matches = subnet_result.scalars().all()
    if len(prefix_matches) == 1:
        s = prefix_matches[0]
        return {"type": "subnet", "subnet_id": str(s.id), "cidr": s.cidr}
    elif len(prefix_matches) > 1:
        return {
            "type": "subnets",
            "subnets": [{"subnet_id": str(s.id), "cidr": s.cidr} for s in prefix_matches]
        }

    # 5) IP network containment (only for valid CIDR-like input containing '/', e.g. "10.10.0.0/16")
    if '/' in q:
        try:
            network = ipaddress.ip_network(q, strict=False)
            subnet_result = await db.execute(
                select(IPSubnet).where(cast(IPSubnet.cidr, CIDR).op(">>=")(cast(str(network), CIDR)))
            )
            subnet = subnet_result.scalar_one_or_none()
            if subnet:
                return {"type": "subnet", "subnet_id": str(subnet.id), "cidr": subnet.cidr}
        except ValueError:
            pass

    # 6) Fuzzy match on IP portion only (exclude subnet mask)
    #    e.g. "168" matches subnets whose IP part contains "168"
    subnet_result = await db.execute(
        select(IPSubnet).where(func.split_part(IPSubnet.cidr, '/', 1).contains(q)).order_by(cast(IPSubnet.cidr, CIDR))
    )
    fuzzy_subnets = subnet_result.scalars().all()
    if len(fuzzy_subnets) == 1:
        s = fuzzy_subnets[0]
        return {"type": "subnet", "subnet_id": str(s.id), "cidr": s.cidr}
    elif len(fuzzy_subnets) > 1:
        return {
            "type": "subnets",
            "subnets": [{"subnet_id": str(s.id), "cidr": s.cidr} for s in fuzzy_subnets]
        }

    return {"type": "not_found", "q": q}


@router.get("/ip/{ip_address}/tooltip", response_model=IPTooltipData)
async def get_ip_tooltip(ip_address: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    # Try cache first
    cached = await RedisSession.get_cached_ip_data(ip_address)
    if cached:
        return IPTooltipData(**cached)

    result = await db.execute(select(IPRecord).where(IPRecord.ip_address == cast(ip_address, INET)))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="IP not found")

    status_str = record.status.value if record.status else IPStatus.UNUSED.value

    # Get history (max 5, sorted desc)
    result = await db.execute(
        select(IPEvent)
        .where(IPEvent.ip_address == cast(ip_address, INET))
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
        remark=record.remark,
        history=history
    )

    await RedisSession.cache_ip_data(ip_address, data.model_dump(mode="json"))
    return data


async def _get_or_create_record(db: AsyncSession, ip_address: str) -> IPRecord:
    """按 IP 取记录，不存在则新建一条（备注是用户侧数据，可以脱离扫描先存在）"""
    result = await db.execute(select(IPRecord).where(IPRecord.ip_address == cast(ip_address, INET)))
    record = result.scalar_one_or_none()
    if record is None:
        record = IPRecord(ip_address=ip_address)
        db.add(record)
    return record


@router.put("/remark/{ip_address}", response_model=IPRecordResponse)
async def update_ip_remark(
    ip_address: str,
    body: IPRemarkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """设置/清除单个 IP 的备注"""
    try:
        ipaddress.ip_address(ip_address)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IP address")

    remark = (body.remark or "").strip() or None
    record = await _get_or_create_record(db, ip_address)
    record.remark = remark
    await db.commit()
    await db.refresh(record)
    # 备注变了，tooltip 缓存立即失效
    await RedisSession.delete(f"ip:data:{ip_address}")
    return _iprecord_to_response(record)


@router.post("/remark/batch", response_model=IPRemarkBatchResponse)
async def batch_update_ip_remark(
    body: IPRemarkBatchUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """批量设置/清除一组 IP 的备注（同一个值）"""
    remark = (body.remark or "").strip() or None

    targets: List[str] = []
    seen = set()
    for raw in body.ip_addresses:
        ip = str(raw).strip()
        if not ip or ip in seen:
            continue
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            continue
        seen.add(ip)
        targets.append(ip)

    if not targets:
        return IPRemarkBatchResponse(updated=0, records=[])

    # INET 列统一按去掉掩码的文本比较，兼容少数带 /xx 存储的历史数据
    ip_text = func.split_part(cast(IPRecord.ip_address, String), '/', 1)
    result = await db.execute(select(IPRecord).where(ip_text.in_(targets)))
    existing = {str(r.ip_address).split('/')[0]: r for r in result.scalars().all()}

    records: List[IPRecord] = []
    for ip in targets:
        record = existing.get(ip)
        if record is None:
            record = IPRecord(ip_address=ip)
            db.add(record)
        record.remark = remark
        records.append(record)

    await db.commit()
    for record in records:
        await db.refresh(record)

    for ip in targets:
        await RedisSession.delete(f"ip:data:{ip}")

    return IPRemarkBatchResponse(
        updated=len(records),
        records=[_iprecord_to_response(r) for r in records],
    )
