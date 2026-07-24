import sys
import subprocess

with open('_selected_index.txt') as f:
    idx = f.read().strip()
with open('_selected_title.txt') as f:
    title = f.read()
with open('_selected_label.txt') as f:
    label = f.read()
with open('_selected_body.txt') as f:
    body = f.read()
try:
    with open('_selected_cta.txt') as f:
        cta = f.read().strip()
except FileNotFoundError:
    cta = None

# Reuse render_essay logic by calling its functions directly
import render_essay as re_mod
from PIL import Image, ImageDraw, ImageFont

dummy_img = Image.new('RGB', (re_mod.W, re_mod.H))
draw = ImageDraw.Draw(dummy_img)
body_font = ImageFont.truetype(re_mod.BODY_FONT_PATH, 34)
title_font = ImageFont.truetype(re_mod.TITLE_FONT_PATH, 46)

paragraphs = body.split('\n\n')
title_lines = re_mod.wrap_paragraph(title, title_font, re_mod.MAX_WIDTH, draw)
title_height = len(title_lines) * 54 + 40
usable_height_page1 = re_mod.H - 155 - title_height - 120
usable_height_pagen = re_mod.H - 155 - 20 - 120
line_height = 46
para_gap = 30

pages = []
current_lines = []
current_height = 0
first_page = True
for para in paragraphs:
    lines = re_mod.wrap_paragraph(para, body_font, re_mod.MAX_WIDTH, draw)
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
import os
os.makedirs('output', exist_ok=True)
for i, page_lines in enumerate(pages, start=1):
    out_path = f'output/row-{idx}-slide{i}.png'
    re_mod.render_slide(title, label, page_lines, i, total_pages, out_path)
    print(f"Rendered {out_path}")

if cta:
    cta_path = f'output/row-{idx}-slide{total_pages}.png'
    re_mod.render_cta_slide(cta, total_pages, total_pages, cta_path)
    print(f"Rendered {cta_path}")

with open('_total_slides.txt', 'w') as f:
    f.write(str(total_pages))
print(f"TOTAL_SLIDES={total_pages}")

# Render the Pinterest-specific teaser (deliberately incomplete, drives click-through to Instagram)
try:
    with open('_selected_pinterest_hook.txt') as f:
        pinterest_hook = f.read().strip()
except FileNotFoundError:
    pinterest_hook = ''

if pinterest_hook:
    import render_pinterest_teaser as teaser_mod
    teaser_mod.render_teaser(title, label, pinterest_hook, f'output/row-{idx}-pinterest-teaser.png')
