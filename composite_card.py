import sys
import os

# Philosopher/attribution -> background image filename lookup
IMAGE_MAP = {
    "marcus aurelius": "marcus_aurelius",
    "epictetus": "epictetus",
    "seneca": "seneca",
    "rene descartes": "descartes",
    "baruch spinoza": "spinoza",
    "immanuel kant": "kant",
    "friedrich nietzsche": "nietzsche",
    "arthur schopenhauer": "schopenhauer",
    "soren kierkegaard": "kierkegaard",
    "david hume": "hume",
    "john locke": "locke",
    "john stuart mill": "mill",
    "voltaire": "voltaire",
    "jean-jacques rousseau": "rousseau",
    "blaise pascal": "pascal",
    "michel de montaigne": "montaigne",
    "plato": "plato",
}

def get_background(attribution, row_id):
    key = attribution.strip().lower()
    if key in IMAGE_MAP:
        return IMAGE_MAP[key]
    # Psychology facts: alternate between the two abstract images
    try:
        n = int(row_id)
    except ValueError:
        n = 0
    return "psychology1" if n % 2 == 0 else "psychology2"

if __name__ == "__main__":
    from PIL import Image, ImageDraw, ImageFont

    quote_text = sys.argv[1]
    attribution = sys.argv[2]
    source = sys.argv[3]
    row_id = sys.argv[4]

    bg_name = get_background(attribution, row_id)
    img = Image.open(f"backgrounds/{bg_name}.jpg").convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)

    quote_font = ImageFont.truetype("fonts/IBMPlexSerif-BoldItalic.ttf", int(h * 0.034))
    attr_font = ImageFont.truetype("fonts/IBMPlexSerif-Bold.ttf", int(h * 0.014))
    source_font = ImageFont.truetype("fonts/IBMPlexSerif-Regular.ttf", int(h * 0.013))

    x_margin = int(w * 0.065)
    max_text_width = int(w * 0.42)

    def wrap_text(text, font, max_width):
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    lines = wrap_text(quote_text, quote_font, max_text_width)
    line_height = int(h * 0.043)
    total_text_height = len(lines) * line_height + int(h * 0.067)
    y_start = max(int(h * 0.08), (h - total_text_height) / 2)

    y = y_start
    for line in lines:
        draw.text((x_margin, y), line, font=quote_font, fill=(255, 255, 255))
        y += line_height

    y += int(h * 0.02)
    draw.line([(x_margin, y), (x_margin + int(w * 0.08), y)], fill=(255, 255, 255), width=2)
    y += int(h * 0.019)
    draw.text((x_margin, y), attribution.upper(), font=attr_font, fill=(240, 240, 240))
    y += int(h * 0.021)
    draw.text((x_margin, y), source, font=source_font, fill=(190, 190, 190))

    y_handle = h - int(h * 0.052)
    draw.text((x_margin, y_handle), "@the_higher_being", font=source_font, fill=(255, 255, 255))
    handle_bbox = draw.textbbox((x_margin, y_handle), "@the_higher_being", font=source_font)

    img.save("card.png")
    print(f"Used background: {bg_name}.jpg, wrapped to {len(lines)} lines")
