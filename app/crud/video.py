from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.video import VideoLinkata
from typing import List

async def get_videos_linkata(db: AsyncSession, skip: int = 0, limit: int = 20) -> List[VideoLinkata]:
    result = await db.execute(select(VideoLinkata).offset(skip).limit(limit))
    return result.scalars().all()
