import ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.settings import settings
from sqlalchemy.orm import declarative_base

Base = declarative_base()

db_url = settings.DATABASE_URL

connect_args = {}
if "supabase.co" in (db_url or ""):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE   # <-- No valida el certificado
    connect_args = {"ssl": ssl_context}

engine = create_async_engine(
    db_url,
    echo=True,
    future=True,
    connect_args=connect_args
)

SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with SessionLocal() as session:
        yield session
