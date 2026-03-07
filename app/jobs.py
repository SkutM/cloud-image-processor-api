import io
import uuid

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.image_processing import generate_thumbnail
from app.models.image_variant import ImageVariant
from app.storage import get_bytes, put_bytes


def generate_thumbnail_job(image_id: str, original_key: str) -> None:
    image_uuid = uuid.UUID(image_id)

    original_bytes = get_bytes(key=original_key)

    thumb_bytes, width, height, thumb_content_type = generate_thumbnail(original_bytes)
    thumb_key = f"thumbnails/{image_uuid}.jpg"

    put_bytes(
        key=thumb_key,
        data=thumb_bytes,
        content_type=thumb_content_type,
    )

    db: Session = SessionLocal()
    try:
        existing = (
            db.query(ImageVariant)
            .filter(
                ImageVariant.image_id == image_uuid,
                ImageVariant.variant == "thumbnail",
            )
            .first()
        )

        if existing is None:
            db.add(
                ImageVariant(
                    image_id=image_uuid,
                    variant="thumbnail",
                    s3_key=thumb_key,
                    content_type=thumb_content_type,
                    size_bytes=len(thumb_bytes),
                    width=width,
                    height=height,
                )
            )
            db.commit()
    finally:
        db.close()