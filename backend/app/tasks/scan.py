from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import uuid

from app.tasks.celery_config import celery
from app.core.config import settings
from app.core.security import decrypt_data
from app.core.database import async_session_maker
from app.models.scan.scan_model import ScanTask, ScanLog, TaskStatus
from app.models.switch.switch_model import Switch
from app.models.ip.ip_model import IPRecord, IPEvent, IPEventType, IPStatus
from app.services.snmp import SNMPScanner


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
            task.started_at = datetime.now(timezone.utc)
            await db.commit()

            # Get active switches
            result = await db.execute(select(Switch).where(Switch.is_active == True))
            switches = result.scalars().all()

            total_ips = 0
            updated_ips = 0
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

                    arp_table = scanner.get_arp_table()
                    total_ips += len(arp_table)

                    # Batch upsert IP records
                    now = datetime.now(timezone.utc)
                    for ip_str, mac in arp_table.items():
                        result = await db.execute(select(IPRecord).where(IPRecord.ip_address == ip_str))
                        record = result.scalar_one_or_none()

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
                            updated_ips += 1
                        else:
                            record = IPRecord(
                                ip_address=ip_str,
                                mac_address=mac.upper(),
                                last_seen=now,
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

                    scan_log = ScanLog(
                        task_id=uuid.UUID(task_id),
                        status="SUCCESS",
                        message=f"Switch {switch.ip}: {len(arp_table)} IPs",
                    )
                    db.add(scan_log)
                    await db.commit()

                except Exception as e:
                    error_messages.append(f"Switch {switch.ip}: {str(e)}")
                    scan_log = ScanLog(
                        task_id=uuid.UUID(task_id),
                        status="FAILED",
                        message=f"Switch {switch.ip}: {str(e)}",
                    )
                    db.add(scan_log)
                    await db.commit()

            # Finalize task
            task.status = TaskStatus.SUCCESS if not error_messages else TaskStatus.FAILED
            task.finished_at = datetime.now(timezone.utc)
            task.duration = int((task.finished_at - task.started_at).total_seconds())
            task.total_ips = total_ips
            task.updated_ips = updated_ips
            if error_messages:
                task.error_message = "; ".join(error_messages)
            await db.commit()

    import asyncio
    asyncio.run(_run())
