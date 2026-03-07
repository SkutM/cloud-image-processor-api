import uuid

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.image_processing import generate_thumbnail
from app.models.image import Image
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
        image = (
            db.query(Image)
            .filter(Image.id == image_uuid)
            .first()
        )

        if image is None:
            return

        image.width = width
        image.height = height

        original_variant = (
            db.query(ImageVariant)
            .filter(
                ImageVariant.image_id == image_uuid,
                ImageVariant.variant == "original",
            )
            .first()
        )

        if original_variant is not None:
            original_variant.width = width
            original_variant.height = height

        existing_thumbnail = (
            db.query(ImageVariant)
            .filter(
                ImageVariant.image_id == image_uuid,
                ImageVariant.variant == "thumbnail",
            )
            .first()
        )

        if existing_thumbnail is None:
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