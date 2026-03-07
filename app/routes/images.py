import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Path
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.image import Image
from app.models.image_variant import ImageVariant
from app.storage import put_bytes, presign_get_url, delete_object

from app.jobs import generate_thumbnail_job
from app.queue import thumbnail_queue

router = APIRouter(prefix="/images", tags=["images"])


@router.post("")
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid image type")

    contents = await file.read()
    image_id = uuid.uuid4()

    original_key = f"originals/{image_id}"

    # store original
    put_bytes(
        key=original_key,
        data=contents,
        content_type=file.content_type,
    )

    # insert db row
    db_image = Image(
        id=image_id,
        content_type=file.content_type,
        size_bytes=len(contents),
        width=0,
        height=0,
    )
    db.add(db_image)
    db.flush()

    db.add(
        ImageVariant(
            image_id=db_image.id,
            variant="original",
            s3_key=original_key,
            content_type=file.content_type,
            size_bytes=len(contents),
            width=0,
            height=0,
        )
    )

    db.commit()
    db.refresh(db_image)

    thumbnail_queue.enqueue(
        generate_thumbnail_job,
        str(db_image.id),
        original_key,
    )

    return {
        "id": str(db_image.id),
    }


def _build_variants_payload(image: Image):
    """
    Returns:
      variants: list[{variant, url, content_type, size_bytes, width, height}]
      original_url: str|None
      thumbnail_url: str|None
    """
    variants = []
    original_url = None
    thumbnail_url = None

    # if not loaded, this will be empty
    for v in getattr(image, "variants", []) or []:
        url = presign_get_url(key=v.s3_key)
        variants.append(
            {
                "variant": v.variant,
                "url": url,
                "content_type": v.content_type,
                "size_bytes": v.size_bytes,
                "width": v.width,
                "height": v.height,
            }
        )
        if v.variant == "original":
            original_url = url
        elif v.variant == "thumbnail":
            thumbnail_url = url

    return variants, original_url, thumbnail_url


@router.get("")
def list_images(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    total = db.query(Image).count()
    offset = (page - 1) * page_size

    images = (
        db.query(Image)
        .options(selectinload(Image.variants))
        .order_by(Image.created_at.desc(), Image.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = []
    for img in images:
        variants, original_url, thumbnail_url = _build_variants_payload(img)

        # if variants weren't backfilled for some older row, still give urls
        if original_url is None and getattr(img, "original_key", None):
            original_url = presign_get_url(key=img.original_key)
        if thumbnail_url is None and getattr(img, "thumb_key", None):
            thumbnail_url = presign_get_url(key=img.thumb_key)

        items.append(
            {
                "id": str(img.id),
                "created_at": img.created_at.isoformat() if img.created_at else None,
                "content_type": img.content_type,
                "size_bytes": img.size_bytes,
                "width": img.width,
                "height": img.height,
                "original_url": original_url,
                "thumbnail_url": thumbnail_url,
                "variants": variants,
            }
        )

    has_next = offset + len(items) < total

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "has_next": has_next,
    }


@router.get("/{image_id}")
def get_image(
    image_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
):
    image = (
        db.query(Image)
        .options(selectinload(Image.variants))
        .filter(Image.id == image_id)
        .first()
    )

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    variants, original_url, thumbnail_url = _build_variants_payload(image)

    # backwards compatible fallback
    if original_url is None and getattr(image, "original_key", None):
        original_url = presign_get_url(key=image.original_key)
    if thumbnail_url is None and getattr(image, "thumb_key", None):
        thumbnail_url = presign_get_url(key=image.thumb_key)

    return {
        "id": str(image.id),
        "created_at": image.created_at.isoformat() if image.created_at else None,
        "content_type": image.content_type,
        "size_bytes": image.size_bytes,
        "width": image.width,
        "height": image.height,
        "original_url": original_url,
        "thumbnail_url": thumbnail_url,
        "variants": variants,
    }


@router.delete("/{image_id}", status_code=204)
def delete_image(
    image_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
):
    image = (
        db.query(Image)
        .options(selectinload(Image.variants))
        .filter(Image.id == image_id)
        .first()
    )

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # delete by variant
    variant_keys = [v.s3_key for v in getattr(image, "variants", []) or []]

    # backwards compatible fallback
    if not variant_keys:
        if getattr(image, "original_key", None):
            variant_keys.append(image.original_key)
        if getattr(image, "thumb_key", None):
            variant_keys.append(image.thumb_key)

    for key in variant_keys:
        delete_object(key=key)

    db.delete(image)
    db.commit()
    return