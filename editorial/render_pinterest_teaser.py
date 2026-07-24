from PIL import Image, ImageDraw, ImageFont
import render_essay as re_mod

def render_teaser(title, label, hook_text, out_path):
    """A Pinterest-specific teaser: title + opening hook, cut off deliberately,
    with a clear 'continued on Instagram' prompt. Never the full story."""
    W, H = re_mod.W, re_mod.H
    img = Image.new('RGB', (W, H), (10, 10, 10))
    draw = ImageDraw.Draw(img)

    title_font = ImageFont.truetype(re_mod.TITLE_FONT_PATH, 46)
    body_font = ImageFont.truetype(re_mod.BODY_FONT_PATH, 34)
    label_font = ImageFont.truetype(re_mod.TITLE_FONT_PATH, 20)
    prompt_font = ImageFont.truetype(re_mod.TITLE_FONT_PATH, 26)

    MARGIN = re_mod.MARGIN
    MAX_WIDTH = re_mod.MAX_WIDTH

    draw.line([(MARGIN, 80), (MARGIN + 60, 80)], fill=(184, 134, 46), width=2)
    draw.text((MARGIN, 100), label, font=label_font, fill=(184, 134, 46))

    y = 155
    title_lines = re_mod.wrap_paragraph(title, title_font, MAX_WIDTH, draw)
    for tline in title_lines:
        draw.text((MARGIN, y), tline, font=title_font, fill=(255, 255, 255))
        y += 54
    y += 40

    hook_lines = re_mod.wrap_paragraph(hook_text, body_font, MAX_WIDTH, draw)
    for line in hook_lines:
        draw.text((MARGIN, y), line, font=body_font, fill=(225, 225, 225))
        y += 46

    # Fade-style ellipsis to signal "there's more"
    y += 10
    draw.text((MARGIN, y), "...", font=body_font, fill=(120, 120, 120))

    # Continued-on-Instagram prompt, fixed near the bottom, visually distinct
    prompt_y = H - 220
    draw.line([(MARGIN, prompt_y - 30), (W - MARGIN, prompt_y - 30)], fill=(184, 134, 46), width=2)
    draw.text((MARGIN, prompt_y), "Full story on Instagram", font=prompt_font, fill=(230, 178, 96))
    draw.text((MARGIN, prompt_y + 40), "@the_higher_being", font=body_font, fill=(230, 178, 96))

    img.save(out_path)
    print(f"Rendered teaser: {out_path}")

if __name__ == "__main__":
    import sys
    idx = sys.argv[1]
    title = sys.argv[2]
    label = sys.argv[3]
    hook = sys.argv[4]
    render_teaser(title, label, hook, f'output/row-{idx}-pinterest-teaser.png')
