from datetime import datetime
from sqlalchemy import select, cast, delete
from sqlalchemy.dialects.postgresql import INET, CIDR
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import ipaddress

from app.tasks.celery_config import celery
from app.core.config import settings
from app.core.security import decrypt_data
from app.models.scan.scan_model import ScanTask, TaskStatus
from app.models.scan.scan_subnet_model import ScanSubnet
from app.models.switch.switch_model import Switch
from app.models.ip.ip_model import IPRecord, IPEvent, IPEventType, IPStatus, IPSubnet
from app.models.system.system_model import SystemConfig
from app.services.snmp import SNMPScanner


def is_ip_in_subnets(ip_str: str, subnets: list) -> bool:
    """检查IP是否在任一配置的网段内"""
    if not subnets:
        # 如果没有配置任何网段，则允许所有IP入库
        return True
    
    try:
        ip = ipaddress.ip_address(ip_str)
        for subnet in subnets:
            try:
                network = ipaddress.ip_network(subnet.cidr, strict=False)
                if ip in network:
                    return True
            except ValueError:
                continue
        return False
    except ValueError:
        return False


def _compute_status(last_seen: datetime, online_days: int, cleanup_days: int) -> IPStatus:
    """Compute IP status based on last_seen timestamp."""
    now = datetime.utcnow()
    delta = (now - last_seen).days
    if delta <= online_days:
        return IPStatus.ONLINE
    elif delta <= cleanup_days:
        return IPStatus.OFFLINE
    else:
        return IPStatus.UNUSED


@celery.task(bind=True)
def run_scan_task(self, task_id: str):
    """Main SNMP scan task — fetches ARP table from all active switches."""

    async def _run():
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with session_maker() as db:
            # Get task
            result = await db.execute(select(ScanTask).where(ScanTask.id == task_id))
            task: ScanTask = result.scalar_one_or_none()
            if not task:
                return

            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            await db.commit()

            try:
                # Load system config for status thresholds
                cfg_result = await db.execute(select(SystemConfig).limit(1))
                cfg = cfg_result.scalar_one_or_none()
                online_days = cfg.online_days if cfg else settings.ONLINE_DAYS
                cleanup_days = cfg.cleanup_days if cfg else settings.CLEANUP_DAYS

                # Get active subnets for filtering
                subnet_result = await db.execute(select(ScanSubnet).where(ScanSubnet.is_active == True))
                active_subnets = subnet_result.scalars().all()

                # Get active switches
                result = await db.execute(select(Switch).where(Switch.is_active == True))
                switches = result.scalars().all()

                total_ips = 0
                updated_ips = 0
                filtered_ips = 0
                error_messages = []

                for switch in switches:
                    try:
                        # Decrypt SNMP v3 config if needed
                        snmp_config = None
                        if switch.snmp_v3_config_encrypted:
                            snmp_config = __import__("json").loads(decrypt_data(switch.snmp_v3_config_encrypted))

                        scanner = SNMPScanner(
                            host=str(switch.ip),
                            snmp_version=switch.snmp_version.value,
                            community=switch.community,
                            snmp_v3_config=snmp_config,
                            timeout=settings.SNMP_TIMEOUT,
                            retry=settings.SNMP_RETRY,
                        )

                        arp_table = await scanner.get_arp_table()
                        total_ips += len(arp_table)

                        # Batch upsert IP records
                        now = datetime.utcnow()
                        for ip_str, mac in arp_table.items():
                            # Check if IP is in allowed subnets
                            if not is_ip_in_subnets(ip_str, active_subnets):
                                filtered_ips += 1
                                continue
                            
                            result = await db.execute(select(IPRecord).where(IPRecord.ip_address == cast(ip_str, INET)))
                            record = result.scalar_one_or_none()
                            new_status = _compute_status(now, online_days, cleanup_days)

                            if record:
                                # Check MAC change
                                if record.mac_address and record.mac_address.upper() != mac.upper():
                                    event = IPEvent(
                                        ip_address=ip_str,
                                        mac_address=mac.upper(),
                                        event_type=IPEventType.MAC_CHANGED,
                                        seen_at=now,
                                    )
                                    db.add(event)
                                record.mac_address = mac.upper()
                                record.last_seen = now
                                record.status = new_status
                                updated_ips += 1
                            else:
                                record = IPRecord(
                                    ip_address=ip_str,
                                    mac_address=mac.upper(),
                                    last_seen=now,
                                    status=new_status,
                                )
                                db.add(record)
                                event = IPEvent(
                                    ip_address=ip_str,
                                    mac_address=mac.upper(),
                                    event_type=IPEventType.NEW,
                                    seen_at=now,
                                )
                                db.add(event)
                                updated_ips += 1

                        await db.commit()

                    except Exception as e:
                        await db.rollback()
                        error_messages.append(f"Switch {switch.ip}: {str(e)}")

                # Auto-create /24 subnets for discovered IPs (only matching scan_subnets)
                try:
                    all_ips_result = await db.execute(select(IPRecord.ip_address))
                    all_ips = all_ips_result.scalars().all()
                    discovered_cidrs = set()
                    for ip_val in all_ips:
                        try:
                            ip_str = str(ip_val).split('/')[0]
                            if active_subnets and not is_ip_in_subnets(ip_str, active_subnets):
                                continue
                            net = ipaddress.ip_network(f"{ip_str}/24", strict=False)
                            discovered_cidrs.add(str(net))
                        except ValueError:
                            continue

                    existing_result = await db.execute(select(IPSubnet))
                    existing_subnets = existing_result.scalars().all()
                    existing_cidrs = {s.cidr for s in existing_subnets}

                    for cidr in discovered_cidrs - existing_cidrs:
                        db.add(IPSubnet(cidr=cidr, description="自动发现"))

                    if active_subnets:
                        for s in existing_subnets:
                            if s.description == "自动发现" and s.cidr not in discovered_cidrs:
                                await db.execute(
                                    delete(IPRecord).where(
                                        IPRecord.ip_address.op("<<=")(cast(s.cidr, CIDR))
                                    )
                                )
                                await db.execute(
                                    delete(IPSubnet).where(IPSubnet.id == s.id)
                                )

                    await db.commit()
                except Exception:
                    await db.rollback()

                # Finalize task
                success_count = len(switches) - len(error_messages)
                if not error_messages:
                    task.status = TaskStatus.SUCCESS
                elif success_count > 0:
                    task.status = TaskStatus.PARTIAL
                else:
                    task.status = TaskStatus.FAILED
                task.finished_at = datetime.utcnow()
                task.duration = int((task.finished_at - task.started_at).total_seconds())
                task.total_ips = total_ips
                task.updated_ips = updated_ips
                parts = []
                if success_count > 0:
                    parts.append(f"{success_count} 台交换机扫描成功，共 {total_ips} 个 IP，更新 {updated_ips} 个")
                if error_messages:
                    parts.append(f"{len(error_messages)} 台失败: " + "; ".join(error_messages))
                task.error_message = "，".join(parts) if parts else None
                await db.commit()

            except Exception as e:
                # Ensure task is marked as FAILED on any uncaught exception
                await db.rollback()
                try:
                    task.status = TaskStatus.FAILED
                    task.finished_at = datetime.utcnow()
                    if task.started_at:
                        task.duration = int((task.finished_at - task.started_at).total_seconds())
                    task.error_message = f"扫描异常: {str(e)}"
                    await db.commit()
                except Exception:
                    pass

    import asyncio
    asyncio.run(_run())
