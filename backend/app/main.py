from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, async_session_maker
from app.core.redis import close_redis
from app.api import deps, user, switch, ip, scan, log


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    # Create default admin if no users
    from sqlalchemy import select
    from app.models.user.user_model import User
    from app.core.auth import hash_password
    async with async_session_maker() as db:
        result = await db.execute(select(User).limit(1))
        if not result.scalar_one_or_none():
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                role="admin",
            )
            db.add(admin)
            await db.commit()
    yield
    # Shutdown
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(deps.router)
app.include_router(user.router)
app.include_router(switch.router)
app.include_router(ip.router)
app.include_router(scan.router)
app.include_router(log.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/")
async def root():
    return {"message": f"{settings.APP_NAME} API", "docs": "/docs"}
