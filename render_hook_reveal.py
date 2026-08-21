import sys

from composite_card import get_background

# Rotating pool of generic "hook strip" lines - pattern-interrupt anticipation
# copy that works with any quote/fact underneath it. Picked deterministically
# by row_id, same rotation pattern as the audio track selection in
# main-daily-post.yml (row_id % len(pool)), so a given entry always renders
# identically across retries.
HOOK_LINES = [
    "Someone sent me this... it's been stuck with me since.",
    "Read the last line twice.",
    "This is 1,900 years old. It still checks out.",
    "Modern science just caught up to this.",
    "Wait for the part that actually explains why.",
    "I didn't believe this until I saw the research.",
    "This one's uncomfortable. That's the point.",
    "Ancient intuition. Modern proof. Again.",
    "Most people scroll past this. Don't.",
    "This changed how I see my own mind.",
    "The evidence behind this is stronger than you'd think.",
    "Not a vibe. An actual mechanism.",
]

# Fraction of final 1080x1920 video height the top hook strip occupies.
# Keep in sync with STRIP_HEIGHT in the ffmpeg overlay step (main-daily-post
# style workflows) - both must agree so the card's reserved top margin
# actually lines up with where the strip gets composited.
STRIP_HEIGHT_FRAC = 0.135

CREAM = (245, 240, 230)
CHARCOAL = (26, 26, 26)
GOLD = (184, 134, 46)


def pick_hook_line(row_id):
    try:
        n = int(row_id)
    except ValueError:
        n = 0
    return HOOK_LINES[n % len(HOOK_LINES)]


def render_content_card(quote_text, attribution, source, row_id, out_path="hook_content.png"):
    """Same visual language as composite_card.py's card, but with extra top
    margin reserved so the quote never sits under the hook strip that gets
    overlaid later at the video-compositing step."""
    from PIL import Image, ImageDraw, ImageFont

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

    strip_reserved = int(h * STRIP_HEIGHT_FRAC) + int(h * 0.025)
    y_start = max(int(h * 0.08), strip_reserved, (h - total_text_height) / 2)

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

    handle_font = ImageFont.truetype("fonts/IBMPlexSerif-BoldItalic.ttf", int(h * 0.021))
    handle_text = "@the_higher_being"
    letter_spacing = int(h * 0.0022)
    y_handle = y + line_height
    x_cursor = x_margin
    for ch in handle_text:
        draw.text((x_cursor, y_handle), ch, font=handle_font, fill=GOLD)
        ch_bbox = draw.textbbox((0, 0), ch, font=handle_font)
        x_cursor += (ch_bbox[2] - ch_bbox[0]) + letter_spacing

    img.save(out_path)
    return bg_name, len(lines)


def render_strip(hook_line, out_path="hook_strip.png", width=1080, height=1920):
    """Transparent 1080x1920 RGBA overlay with an opaque cream strip pinned
    to the top, containing the hook line. Composited AFTER the fade-in so it
    reads at full brightness/constant from frame 0, unlike the fading
    content beneath it."""
    from PIL import Image, ImageDraw, ImageFont

    strip_h = int(height * STRIP_HEIGHT_FRAC)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, width, strip_h], fill=(*CREAM, 255))
    draw.rectangle([0, strip_h - 4, width, strip_h], fill=(*GOLD, 255))

    font = ImageFont.truetype("fonts/IBMPlexSerif-Bold.ttf", int(height * 0.028))
    max_width = int(width * 0.86)

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

    lines = wrap_text(hook_line, font, max_width)
    line_height = int(height * 0.038)
    total_h = len(lines) * line_height
    y = (strip_h - total_h) / 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (width - line_w) / 2
        draw.text((x, y), line, font=font, fill=(*CHARCOAL, 255))
        y += line_height

    img.save(out_path)
    return strip_h


if __name__ == "__main__":
    quote_text = sys.argv[1]
    attribution = sys.argv[2]
    source = sys.argv[3]
    row_id = sys.argv[4]

    hook_line = pick_hook_line(row_id)
    bg_name, n_lines = render_content_card(quote_text, attribution, source, row_id)
    strip_h = render_strip(hook_line)

    print(f"Used background: {bg_name}.jpg, wrapped to {n_lines} lines")
    print(f"Hook line: {hook_line}")
    print(f"hook_content.png + hook_strip.png written (strip height {strip_h}px)")
