from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

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


async def init_db():
    from app.models import user, switch, ip, scan, log  # noqa
    from app.models.scan import scan_subnet_model  # noqa - for scan_subnets table
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Migrate: add PARTIAL to taskstatus enum (must run outside transaction)
    try:
        raw_conn = await engine.raw_connection()
        await raw_conn.driver_connection.execute(
            "ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'PARTIAL' AFTER 'SUCCESS'"
        )
        await raw_conn.close()
    except Exception:
        pass  # already exists or not supported
