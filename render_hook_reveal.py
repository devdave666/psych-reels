import sys

from composite_card import get_background, render_quote_card

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

# Dark gap held above the strip so it clears Reels' UI-obscured top zone
# (back button/camera icon overlay the very top edge in-app) instead of
# sitting flush against it. First test post had the strip too high.
TOP_OFFSET_FRAC = 0.047

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
    """Same shared layout as composite_card.py's Pinterest card, but with
    extra top margin reserved so the quote never sits under the hook strip
    that gets overlaid later at the video-compositing step. Collision with
    the strip is structurally impossible regardless of content length -
    render_quote_card's y_start is a max() against this reserved fraction.
    Bottom-of-canvas overflow for very long entries is handled there too
    (auto-shrink font, then a loud warning if it still doesn't fit)."""
    bg_name = get_background(attribution, row_id)
    top_reserved_frac = TOP_OFFSET_FRAC + STRIP_HEIGHT_FRAC + 0.025
    return render_quote_card(bg_name, quote_text, attribution, source, row_id,
                              top_reserved_frac=top_reserved_frac, out_path=out_path)


def render_strip(hook_line, out_path="hook_strip.png", width=1080, height=1920):
    """Transparent 1080x1920 RGBA overlay with an opaque cream strip pinned
    to the top, containing the hook line. Composited AFTER the fade-in so it
    reads at full brightness/constant from frame 0, unlike the fading
    content beneath it."""
    from PIL import Image, ImageDraw, ImageFont

    top_offset = int(height * TOP_OFFSET_FRAC)
    strip_h = int(height * STRIP_HEIGHT_FRAC)
    strip_bottom = top_offset + strip_h
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, top_offset, width, strip_bottom], fill=(*CREAM, 255))
    draw.rectangle([0, strip_bottom - 4, width, strip_bottom], fill=(*GOLD, 255))

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
    y = top_offset + (strip_h - total_h) / 2

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
