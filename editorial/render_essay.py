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
        title_lines = wrap_paragraph(title, title_font, MAX_WIDTH, draw)
        for tline in title_lines:
            draw.text((MARGIN, y), tline, font=title_font, fill=(255, 255, 255))
            y += 54
        y += 40
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

def render_cta_slide(cta, page_num, total_pages, out_path):
    """A dedicated final slide, just for the CTA -- the standard IG carousel convention."""
    img = Image.new('RGB', (W, H), (10, 10, 10))
    draw = ImageDraw.Draw(img)

    cta_font = ImageFont.truetype(TITLE_FONT_PATH, 52)
    eyebrow_font = ImageFont.truetype(TITLE_FONT_PATH, 22)
    page_font = ImageFont.truetype(BODY_FONT_PATH, 20)

    eyebrow = "YOUR TURN"
    eyebrow_bbox = draw.textbbox((0, 0), eyebrow, font=eyebrow_font)
    eyebrow_w = eyebrow_bbox[2] - eyebrow_bbox[0]

    cta_lines = wrap_paragraph(cta, cta_font, MAX_WIDTH, draw)
    line_height = 66
    total_text_height = len(cta_lines) * line_height

    # Vertically center the whole block (eyebrow + rule + CTA text)
    block_height = 40 + 30 + total_text_height
    start_y = (H - block_height) / 2

    eyebrow_x = (W - eyebrow_w) / 2
    draw.text((eyebrow_x, start_y), eyebrow, font=eyebrow_font, fill=(184, 134, 46))

    rule_y = start_y + 40
    draw.line([(W/2 - 40, rule_y), (W/2 + 40, rule_y)], fill=(184, 134, 46), width=2)

    y = rule_y + 40
    for line in cta_lines:
        line_bbox = draw.textbbox((0, 0), line, font=cta_font)
        line_w = line_bbox[2] - line_bbox[0]
        x = (W - line_w) / 2
        draw.text((x, y), line, font=cta_font, fill=(255, 255, 255))
        y += line_height

    footer_text = "@the_higher_being"
    footer_bbox = draw.textbbox((0, 0), footer_text, font=page_font)
    footer_w = footer_bbox[2] - footer_bbox[0]
    draw.text(((W - footer_w) / 2, H - 90), footer_text, font=page_font, fill=(150, 150, 150))
    draw.text((W - MARGIN - 50, H - 90), f"{page_num}/{total_pages}", font=page_font, fill=(150, 150, 150))

    img.save(out_path)

def main():
    row_id = sys.argv[1]
    title = sys.argv[2]
    label = sys.argv[3]
    body = sys.argv[4]
    cta = sys.argv[5] if len(sys.argv) > 5 else None

    dummy_img = Image.new('RGB', (W, H))
    draw = ImageDraw.Draw(dummy_img)
    body_font = ImageFont.truetype(BODY_FONT_PATH, 34)
    title_font = ImageFont.truetype(TITLE_FONT_PATH, 46)

    paragraphs = body.split('\n\n')
    title_lines = wrap_paragraph(title, title_font, MAX_WIDTH, draw)
    title_height = len(title_lines) * 54 + 40
    usable_height_page1 = H - 155 - title_height - 120
    usable_height_pagen = H - 155 - 20 - 120
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

    total_pages = len(pages) + (1 if cta else 0)
    os.makedirs('output', exist_ok=True)
    for i, page_lines in enumerate(pages, start=1):
        out_path = f'output/row-{row_id}-slide{i}.png'
        render_slide(title, label, page_lines, i, total_pages, out_path)
        print(f"Rendered {out_path}")

    if cta:
        cta_path = f'output/row-{row_id}-slide{total_pages}.png'
        render_cta_slide(cta, total_pages, total_pages, cta_path)
        print(f"Rendered {cta_path}")

    print(f"TOTAL_SLIDES={total_pages}")

if __name__ == "__main__":
    main()
