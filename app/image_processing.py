from io import BytesIO
from typing import Tuple
from PIL import Image

def generate_thumbnail(
        image_bytes: bytes,
        max_size: int = 300,
) -> Tuple[bytes, int, int, str]:
    '''
    returns:
        thumbnail_bytes
        width
        height
        content_type
    '''

    with Image.open(BytesIO(image_bytes)) as img:
        # convert to rgb to ensure jpeg compatibility
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RBG')

        img.thumbnail((max_size, max_size))
        
        width, height = img.size

        output = BytesIO()

        # save as JPEG
        img.save(output, format='JPEG', quality=85, optimize=True)

        return output.getvalue(), width, height, 'image/jpeg'