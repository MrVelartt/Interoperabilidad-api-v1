from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

class VideoLinkataBase(BaseModel):
    id: UUID
    video_id: str
    title: str
    published_at: Optional[datetime] = None
    url: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # Pydantic v2 (antes orm_mode=True)
