import colorsys

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