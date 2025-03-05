from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from service.app.config import settings

db = settings.DATABASE
DATABASE_URL = (
    f"postgresql+asyncpg://{db.USER_NAME}:{db.PASSWORD}@{db.HOST}:{db.PORT}/{db.NAME}"
)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[Any, Any]:
    async with async_session() as session:
        yield session
