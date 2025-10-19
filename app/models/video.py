from sqlalchemy import Column, String, DateTime
from app.db.database import Base
from sqlalchemy.dialects.postgresql import UUID

class VideoLinkata(Base):
    __tablename__ = "videos_linkata"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    video_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    published_at = Column(DateTime, nullable=True)
    url = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=True)
