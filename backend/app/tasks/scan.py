import logging
from datetime import datetime, timedelta
from sqlalchemy import select, cast, delete, update, func, Integer
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

logger = logging.getLogger(__name__)


def is_ip_in_subnets(ip_str: str, subnet_cidrs: list) -> bool:
    """检查IP是否在任一配置的网段内（subnet_cidrs 为 CIDR 字符串列表）"""
    if not subnet_cidrs:
        # 如果没有配置任何网段，则允许所有IP入库
        return True

    try:
        ip = ipaddress.ip_address(ip_str)
        for cidr in subnet_cidrs:
            try:
                if ip in ipaddress.ip_network(cidr, strict=False):
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

            # started_at 用局部变量持有：循环里一旦 rollback，ORM 对象即被 expire，
            # 之后再读 task.started_at 会触发同步懒加载（async 下直接报错）。
            started_at = datetime.utcnow()
            task.status = TaskStatus.RUNNING
            task.started_at = started_at
            await db.commit()

            try:
                # Load system config for status thresholds
                cfg_result = await db.execute(select(SystemConfig).limit(1))
                cfg = cfg_result.scalar_one_or_none()
                online_days = cfg.online_days if cfg else settings.ONLINE_DAYS
                cleanup_days = cfg.cleanup_days if cfg else settings.CLEANUP_DAYS

                # Get active subnets for filtering。
                # 下面两个查询结果一律先转成纯 Python 数据：循环里出错会 rollback，
                # 而 rollback 会让 ORM 对象 expire，之后再读它们的属性就会触发同步
                # 懒加载，在 async 会话里直接抛 MissingGreenlet（历史故障根因之一）。
                subnet_result = await db.execute(select(ScanSubnet).where(ScanSubnet.is_active == True))
                active_subnet_cidrs = [s.cidr for s in subnet_result.scalars().all()]

                # Get active switches
                result = await db.execute(select(Switch).where(Switch.is_active == True))
                switches = [
                    {
                        "ip": str(s.ip),
                        "snmp_version": s.snmp_version.value,
                        "v3_config": s.snmp_v3_config_encrypted,
                        "community": s.community_encrypted,
                    }
                    for s in result.scalars().all()
                ]

                total_ips = 0
                updated_ips = 0
                filtered_ips = 0
                error_messages = []

                for switch in switches:
                    switch_ip = switch["ip"]
                    try:
                        # Decrypt SNMP v3 config if needed
                        snmp_config = None
                        if switch["v3_config"]:
                            snmp_config = __import__("json").loads(decrypt_data(switch["v3_config"]))

                        community_plain = None
                        if switch["community"]:
                            try:
                                community_plain = decrypt_data(switch["community"])
                            except Exception:
                                community_plain = None

                        scanner = SNMPScanner(
                            host=switch_ip,
                            snmp_version=switch["snmp_version"],
                            community=community_plain,
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
                            if not is_ip_in_subnets(ip_str, active_subnet_cidrs):
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
                        # 只用前面存好的纯数据，rollback 之后再读 ORM 属性会抛
                        # MissingGreenlet，导致真实错误被覆盖、任务卡在 RUNNING
                        await db.rollback()
                        error_messages.append(f"Switch {switch_ip}: {str(e)}")

                # Auto-create /24 subnets for discovered IPs (only matching scan_subnets)
                try:
                    all_ips_result = await db.execute(select(IPRecord.ip_address))
                    all_ips = all_ips_result.scalars().all()
                    discovered_cidrs = set()
                    for ip_val in all_ips:
                        try:
                            ip_str = str(ip_val).split('/')[0]
                            if active_subnet_cidrs and not is_ip_in_subnets(ip_str, active_subnet_cidrs):
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

                    if active_subnet_cidrs:
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

                # Refresh status for ALL IP records based on last_seen
                now = datetime.utcnow()
                online_cutoff = now - timedelta(days=online_days)
                cleanup_cutoff = now - timedelta(days=cleanup_days)
                # ONLINE: last_seen within online_days
                await db.execute(
                    update(IPRecord)
                    .where(IPRecord.last_seen != None, IPRecord.last_seen >= online_cutoff)
                    .values(status=IPStatus.ONLINE)
                )
                # OFFLINE: last_seen between online_days and cleanup_days
                await db.execute(
                    update(IPRecord)
                    .where(IPRecord.last_seen != None, IPRecord.last_seen < online_cutoff, IPRecord.last_seen >= cleanup_cutoff)
                    .values(status=IPStatus.OFFLINE)
                )

                # Find rows about to become UNUSED that still carry a stale MAC.
                # We emit one IP_RELEASED event per such row before clearing the
                # mac_address so that the event log keeps a permanent record of
                # which device last occupied this IP, while the live record
                # truthfully reports "no device here".
                released_rows = (await db.execute(
                    select(IPRecord)
                    .where(
                        IPRecord.last_seen != None,
                        IPRecord.last_seen < cleanup_cutoff,
                        IPRecord.mac_address.isnot(None),
                    )
                )).scalars().all()
                for r in released_rows:
                    db.add(IPEvent(
                        ip_address=str(r.ip_address).split('/')[0],
                        mac_address=r.mac_address,
                        event_type=IPEventType.IP_RELEASED,
                        seen_at=now,
                    ))

                # UNUSED: last_seen older than cleanup_days — also clear mac
                await db.execute(
                    update(IPRecord)
                    .where(IPRecord.last_seen != None, IPRecord.last_seen < cleanup_cutoff)
                    .values(status=IPStatus.UNUSED, mac_address=None)
                )
                await db.commit()

                # Finalize task
                success_count = len(switches) - len(error_messages)
                if not error_messages:
                    final_status = TaskStatus.SUCCESS
                elif success_count > 0:
                    final_status = TaskStatus.PARTIAL
                else:
                    final_status = TaskStatus.FAILED
                finished_at = datetime.utcnow()
                parts = []
                if success_count > 0:
                    parts.append(f"{success_count} 台交换机扫描成功，共 {total_ips} 个 IP，更新 {updated_ips} 个")
                if error_messages:
                    parts.append(f"{len(error_messages)} 台失败: " + "; ".join(error_messages))
                # 按 id 直接 UPDATE：不依赖 ORM 实例状态，避免 rollback 后的对象过期问题
                await db.execute(
                    update(ScanTask)
                    .where(ScanTask.id == task_id)
                    .values(
                        status=final_status,
                        finished_at=finished_at,
                        duration=int((finished_at - started_at).total_seconds()),
                        total_ips=total_ips,
                        updated_ips=updated_ips,
                        error_message="，".join(parts) if parts else None,
                    )
                )
                await db.commit()

            except Exception as e:
                # 任何未捕获异常都必须把任务落成 FAILED，否则任务会永远停在 RUNNING。
                # 关键：不能用 task 实例去写——rollback 之后 ORM 对象已过期，在 async
                # 会话里读它的属性会触发同步懒加载并抛 MissingGreenlet，异常被吞掉后
                # 状态就永远停留在 RUNNING（这正是历史上一堆 RUNNING 的根因）。
                logger.exception("scan task %s failed", task_id)
                try:
                    await db.rollback()
                except Exception:
                    pass
                try:
                    failed_at = datetime.utcnow()
                    async with session_maker() as fail_db:
                        await fail_db.execute(
                            update(ScanTask)
                            .where(ScanTask.id == task_id)
                            .values(
                                status=TaskStatus.FAILED,
                                finished_at=failed_at,
                                duration=int((failed_at - started_at).total_seconds()),
                                error_message=f"扫描异常: {str(e)}",
                            )
                        )
                        await fail_db.commit()
                except Exception:
                    logger.exception("failed to mark scan task %s as FAILED", task_id)
                    try:
                        await db.rollback()
                    except Exception:
                        pass

        await engine.dispose()

    import asyncio
    asyncio.run(_run())


async def fail_interrupted_tasks(db: AsyncSession) -> int:
    """把残留的 RUNNING 扫描任务标记为失败。

    celery 任务不会跨进程/容器重启存活，因此服务启动时仍处于 RUNNING 的记录
    必然是上次中断残留的，不清理就会一直显示“运行中”。
    """
    now = datetime.utcnow()
    result = await db.execute(
        update(ScanTask)
        .where(ScanTask.status == TaskStatus.RUNNING)
        .values(
            status=TaskStatus.FAILED,
            finished_at=now,
            duration=cast(func.extract("epoch", now - ScanTask.started_at), Integer),
            error_message="扫描中断（服务重启或进程退出，任务未正常结束）",
        )
    )
    await db.commit()
    return result.rowcount or 0
