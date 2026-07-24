import json
import sys
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
MARGIN = 90
MAX_WIDTH = W - MARGIN * 2
TITLE_FONT_PATH = '../fonts/IBMPlexSerif-Bold.ttf'
BODY_FONT_PATH = '../fonts/IBMPlexSerif-Regular.ttf'

def wrap_paragraph(text, font, max_width, draw):
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

def paginate(paragraphs, body_font, draw, usable_height, line_height, para_gap):
    """Split paragraphs into pages that each fit within usable_height."""
    pages = []
    current_page_lines = []
    current_height = 0
    for para in paragraphs:
        lines = wrap_paragraph(para, body_font, MAX_WIDTH, draw)
        para_height = len(lines) * line_height + para_gap
        if current_height + para_height > usable_height and current_page_lines:
            pages.append(current_page_lines)
            current_page_lines = []
            current_height = 0
        current_page_lines.extend(lines)
        current_page_lines.append(None)  # paragraph break marker
        current_height += para_height
    if current_page_lines:
        pages.append(current_page_lines)
    return pages

def render_slide(title, label, lines, page_num, total_pages, out_path):
    img = Image.new('RGB', (W, H), (10, 10, 10))
    draw = ImageDraw.Draw(img)

    title_font = ImageFont.truetype(TITLE_FONT_PATH, 46)
    body_font = ImageFont.truetype(BODY_FONT_PATH, 34)
    label_font = ImageFont.truetype(TITLE_FONT_PATH, 20)
    page_font = ImageFont.truetype(BODY_FONT_PATH, 20)

    draw.line([(MARGIN, 80), (MARGIN + 60, 80)], fill=(184, 134, 46), width=2)
    draw.text((MARGIN, 100), label, font=label_font, fill=(184, 134, 46))

    y = 155
    if page_num == 1:
        draw.text((MARGIN, y), title, font=title_font, fill=(255, 255, 255))
        y += 105
    else:
        y += 20

    line_height = 46
    for item in lines:
        if item is None:
            y += 30
            continue
        draw.text((MARGIN, y), item, font=body_font, fill=(225, 225, 225))
        y += line_height

    draw.text((MARGIN, H - 90), "@the_higher_being", font=page_font, fill=(150, 150, 150))
    draw.text((W - MARGIN - 50, H - 90), f"{page_num}/{total_pages}", font=page_font, fill=(150, 150, 150))

    img.save(out_path)

def main():
    row_id = sys.argv[1]
    title = sys.argv[2]
    label = sys.argv[3]
    body = sys.argv[4]

    dummy_img = Image.new('RGB', (W, H))
    draw = ImageDraw.Draw(dummy_img)
    body_font = ImageFont.truetype(BODY_FONT_PATH, 34)

    paragraphs = body.split('\n\n')
    usable_height_page1 = H - 155 - 105 - 120  # after title
    usable_height_pagen = H - 155 - 20 - 120   # no title on continuation pages
    line_height = 46
    para_gap = 30

    # Simple approach: paginate assuming page1 has less room (title), rest have more
    pages = []
    current_lines = []
    current_height = 0
    first_page = True
    for para in paragraphs:
        lines = wrap_paragraph(para, body_font, MAX_WIDTH, draw)
        para_height = len(lines) * line_height + para_gap
        limit = usable_height_page1 if first_page else usable_height_pagen
        if current_height + para_height > limit and current_lines:
            pages.append(current_lines)
            current_lines = []
            current_height = 0
            first_page = False
            limit = usable_height_pagen
        current_lines.extend(lines)
        current_lines.append(None)
        current_height += para_height
    if current_lines:
        pages.append(current_lines)

    total_pages = len(pages)
    os.makedirs('output', exist_ok=True)
    for i, page_lines in enumerate(pages, start=1):
        out_path = f'output/row-{row_id}-slide{i}.png'
        render_slide(title, label, page_lines, i, total_pages, out_path)
        print(f"Rendered {out_path}")

    print(f"TOTAL_SLIDES={total_pages}")

if __name__ == "__main__":
    main()
