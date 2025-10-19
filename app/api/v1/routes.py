from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.database import get_db
from app.crud.video import get_videos_linkata
from app.schemas.video import VideoLinkataBase
from typing import List

# 👇 Importación RELATIVA, evita el import circular
from . import bac_routes

router = APIRouter()

# === Rutas base ===

@router.get("/ping")
def ping():
    return {"message": "pong"}

@router.get("/db-check")
async def db_check(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT NOW()"))
    current_time = result.scalar_one()
    return {"status": "ok", "supabase_time": str(current_time)}

@router.get("/videos", response_model=List[VideoLinkataBase])
async def list_videos(skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)):
    videos = await get_videos_linkata(db, skip=skip, limit=limit)
    return videos

# === Incluir BAC ===
router.include_router(bac_routes.router, prefix="/bac", tags=["BAC"])
