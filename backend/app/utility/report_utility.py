import colorsys
import base64
from io import BytesIO
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
    
    # missing_padding = len(base64_str) % 4
    # if missing_padding:
    #     base64_str += '=' * (4 - missing_padding)

    if "," in base64_str:
        base64_str = base64_str.split(",", 1)[1]

    image_bytes = base64.b64decode(base64_str)
    return Image.open(BytesIO(image_bytes)).convert("RGB")