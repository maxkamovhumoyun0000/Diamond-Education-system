import os
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from pathlib import Path
from config import DATABASE_URL

Base = declarative_base()

# Auto-create SQLite file directory for local DB
parsed = urlparse(DATABASE_URL)
if parsed.scheme.startswith('sqlite'):
    if parsed.path and not parsed.path == ':memory:':
        db_file = parsed.path
        if db_file.startswith('/') and db_file.count('/') > 1:
            # local file path e.g. /home/user/project/data/diamond.db
            path = os.path.abspath(db_file)
        else:
            path = os.path.abspath(db_file)
        folder = os.path.dirname(path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # SQLite faylni yaratishni kafolatlaydi
    Path('data').mkdir(parents=True, exist_ok=True)
