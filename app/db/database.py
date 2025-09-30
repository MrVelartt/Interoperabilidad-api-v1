from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.settings import settings

# Crear el engine
engine = create_async_engine(settings.DATABASE_URL, echo=True, future=True)

# Crear la sesión
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependencia para FastAPI
async def get_db():
    async with SessionLocal() as session:
        yield session
