from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator
from app.core.config import settings

# Since SQLite is the default, we ensure the async driver is used.
# If database_url is sqlite:///... we convert it to sqlite+aiosqlite:///...
database_url = settings.database_url
if database_url.startswith("sqlite:///") and not database_url.startswith("sqlite+aiosqlite:///"):
    database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

engine = create_async_engine(
    database_url,
    echo=False,
    future=True,
    # SQLite-specific arguments, harmless for Postgres if used later but typically ignored
    connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to yield an asynchronous database session.
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
