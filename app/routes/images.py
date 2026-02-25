import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.image import Image
from app.image_processing import generate_thumbnail
from app.storage import put_bytes

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
