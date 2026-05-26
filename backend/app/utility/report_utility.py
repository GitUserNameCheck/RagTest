import colorsys
import base64
from io import BytesIO
import io
from PIL import Image

def generate_distinct_colors(n):
    colors = []

    for i in range(n):
        hue = i / max(n, 1)

        rgb = colorsys.hsv_to_rgb(
            hue,
            0.75,
            0.95
        )

        colors.append(rgb)

    return colors

def base64_to_pil(base64_str: str) -> Image.Image:
    
    if "," in base64_str:
        base64_str = base64_str.split(",", 1)[1]

    image_bytes = base64.b64decode(base64_str)
    return Image.open(BytesIO(image_bytes)).convert("RGB")

def get_aspect_ratio_from_base64(data_uri: str) -> float:
    base64_str = data_uri.split(",", 1)[1]

    image_bytes = base64.b64decode(base64_str)
    image = Image.open(io.BytesIO(image_bytes))

    width, height = image.size
    return max(width / height, height / width)

def safe_open_image(image_bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        return image
    except Exception:
        return None