import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.image import Image
from app.image_processing import generate_thumbnail
from app.storage import put_bytes, presign_get_url, delete_object

router = APIRouter(prefix='/images', tags=['images'])

@router.post('')
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Invalid image type")
    
    contents = await file.read()

    image_id = uuid.uuid4()

    original_key = f'originals/{image_id}'
    thumb_key = f'thumbnails/{image_id}.jpg'

    # store original
    put_bytes(
        key=original_key,
        data=contents,
        content_type=file.content_type,
    )

    # generate thumbnail
    thumb_bytes, width, height, thumb_content_type = generate_thumbnail(contents)

    # store thumbnail
    put_bytes(
        key=thumb_key,
        data=thumb_bytes,
        content_type=thumb_content_type,
    )

    # insert db row
    db_image = Image(
        id=image_id,
        original_key=original_key,
        thumb_key=thumb_key,
        content_type=file.content_type,
        size_bytes=len(contents),
        width=width,
        height=height,
    )

    db.add(db_image)
    db.commit()
    db.refresh(db_image)

    return {
        'id': str(db_image.id),
        'original_key': original_key,
        'thumb_key': thumb_key,
        'width': width,
        'height': height,
    }

@router.get('')
def list_images(
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    images = (
        db.query(Image)
        .order_by(Image.created_at.desc())
        .limit(limit)
        .all()
    )

    items = []
    for img in images:
        items.append({
            "id": str(img.id),
            "created_at": img.created_at.isoformat() if img.created_at else None,
            "content_type": img.content_type,
            "size_bytes": img.size_bytes,
            "width": img.width,
            "height": img.height,
            "original_url": presign_get_url(key=img.original_key),
            "thumbnail_url": presign_get_url(key=img.thumb_key),
        })

    return {"items": items}

@router.delete('/{image_id}', status_code=204)
def delete_image(
    image_id: uuid.UUID = Path(...),
    db: Session = Depends(get_db),
):
    image = db.query(Image).filter(Image.id == image_id).first()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # delete S3 objects
    delete_object(key=image.original_key)
    delete_object(key=image.thumb_key)

    # delete DB row
    db.delete(image)
    db.commit()

    return