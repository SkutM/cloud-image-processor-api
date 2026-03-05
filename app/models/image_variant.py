import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base

class ImageVariant(Base):
    __tablename__ = "image_variants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    image_id = Column(
        UUID(as_uuid=True),
        ForeignKey("images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    variant = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)

    content_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)

    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    image = relationship("Image", back_populates="variants")