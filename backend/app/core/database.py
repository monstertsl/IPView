import logging

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.schema import CreateColumn

from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=20, max_overflow=10)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


def _add_missing_columns(conn) -> None:
    """给已存在的表补上模型里新增的列。

    create_all 只建缺失的表，不会给老表补列。这里把模型元数据和现有表结构做一次
    diff，只执行 ADD COLUMN：不改类型、不改约束、不删列、不动数据，可重复执行。
    因此以后新增字段只要改模型、重启即可，不再需要任何迁移脚本。
    """
    inspector = inspect(conn)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue  # 新表由 create_all 负责，列一定是全的
        existing = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            if not column.nullable and column.default is None and column.server_default is None:
                # 非空又无默认值，没法安全加到已有数据的表上 → 留给人工处理
                logger.warning("skip non-nullable column %s.%s (manual migration required)", table.name, column.name)
                continue
            ddl = CreateColumn(column).compile(dialect=conn.dialect)
            conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {ddl}"))
            logger.info("added missing column %s.%s", table.name, column.name)


async def init_db():
    from app.models import user, switch, ip, scan, log  # noqa
    from app.models.scan import scan_subnet_model  # noqa - for scan_subnets table
    from app.models.log import system_log_model  # noqa - for system_logs table
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)
