from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.database import get_db

router = APIRouter()

@router.get("/ping")
def ping():
    return {"message": "pong"}

@router.get("/db-check")
async def db_check(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT NOW()"))
    current_time = result.scalar_one()
    return {"status": "ok", "supabase_time": str(current_time)}
