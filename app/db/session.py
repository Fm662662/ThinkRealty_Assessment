# app/db/session.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
import os

from app.db.base_class import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:1299@localhost:5432/thinkrealty_leads"
)

# Async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,   # set to False in production
    future=True
)

# Async session factory
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
