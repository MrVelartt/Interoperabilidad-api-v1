from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.database import get_db
from app.crud.video import get_videos_linkata
from app.schemas.video import VideoLinkataBase
from typing import List
from . import bac_routes

router = APIRouter()

# === Incluir BAC ===
router.include_router(bac_routes.router, prefix="/bac", tags=["BAC"])
