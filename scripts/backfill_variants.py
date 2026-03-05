from app.db.session import SessionLocal
from app.models.image import Image
from app.models.image_variant import ImageVariant


def main():
    db = SessionLocal()
    try:
        images = db.query(Image).all()

        created = 0
        skipped = 0

        for img in images:
            existing = {v.variant for v in getattr(img, "variants", [])}

            # original
            if img.original_key and "original" not in existing:
                db.add(
                    ImageVariant(
                        image_id=img.id,
                        variant="original",
                        s3_key=img.original_key,
                        content_type=img.content_type,
                        size_bytes=img.size_bytes,
                        width=img.width,
                        height=img.height,
                    )
                )
                created += 1

            # thumbnail
            if img.thumb_key and "thumbnail" not in existing:
                db.add(
                    ImageVariant(
                        image_id=img.id,
                        variant="thumbnail",
                        s3_key=img.thumb_key,
                        content_type="image/jpeg",
                    )
                )
                created += 1

            if (img.original_key and "original" in existing) and (img.thumb_key and "thumbnail" in existing):
                skipped += 1

        db.commit()
        print(f"Backfill complete. Created={created}, skipped_images={skipped}, total_images={len(images)}")

    finally:
        db.close()


if __name__ == "__main__":
    main()