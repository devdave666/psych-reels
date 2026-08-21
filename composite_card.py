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
    "aristotle": "aristotle",
    "cicero": "cicero",
    "francis bacon": "francis_bacon",
    "thomas hobbes": "thomas_hobbes",
    "georg wilhelm friedrich hegel": "hegel",
    "ralph waldo emerson": "emerson",
    "henry david thoreau": "thoreau",
    "benjamin franklin": "benjamin_franklin",
}

def get_background(attribution, row_id):
    key = attribution.strip().lower()
    if key in IMAGE_MAP:
        return IMAGE_MAP[key]
    # Psychology facts: alternate between the two confirmed-good images
    # (both approved directly by the human - gold-crack "psychology1" and
    # sparkle-dust "psychology2")
    try:
        n = int(row_id)
    except ValueError:
        n = 0
    return "psychology1" if n % 2 == 0 else "psychology2"

GOLD = (222, 178, 110)

# Shared by composite_card.py's own Pinterest-card render AND
# render_hook_reveal.py's video-card render, so a layout fix (or a safety
# fix like the auto-shrink below) only ever needs to happen in one place -
# the statue-spacing fix previously had to be patched in both files
# separately because this used to be duplicated.
def render_quote_card(bg_name, quote_text, attribution, source, row_id, top_reserved_frac=0, out_path="card.png"):
    from PIL import Image, ImageDraw, ImageFont

    src = Image.open(f"backgrounds/{bg_name}.jpg").convert("RGB")
    w, h = src.size

    # Shift the background right to open up breathing room between the
    # subject and the quote text - subject was sitting right up against
    # the text. Crops the (already near-black) right edge and pads the
    # newly exposed left edge with black, which blends in since these
    # backgrounds are already black there.
    shift = int(w * 0.091)
    img = Image.new("RGB", (w, h), (0, 0, 0))
    img.paste(src, (shift, 0))
    draw = ImageDraw.Draw(img)

    x_margin = int(w * 0.065)
    max_text_width = int(w * 0.38)
    attr_font = ImageFont.truetype("fonts/IBMPlexSerif-Bold.ttf", int(h * 0.014))
    source_font = ImageFont.truetype("fonts/IBMPlexSerif-Regular.ttf", int(h * 0.013))
    handle_font = ImageFont.truetype("fonts/IBMPlexSerif-BoldItalic.ttf", int(h * 0.021))

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

    # Collision with the hook strip is structurally impossible regardless
    # of content length: y_start below is a max() against top_reserved, so
    # text can never start above where the strip ends. What's NOT
    # structurally bounded is the BOTTOM - a long enough entry could run
    # off the canvas with nothing to catch it. So: try the normal quote
    # size first, and if the full block (quote + divider + attribution +
    # source + handle) would run past the safe bottom margin, shrink the
    # quote font and re-wrap until it fits or we hit a readability floor.
    BOTTOM_LIMIT = int(h * 0.94)
    MIN_QUOTE_SIZE = h * 0.020
    quote_size = h * 0.034

    while True:
        quote_font = ImageFont.truetype("fonts/IBMPlexSerif-BoldItalic.ttf", int(quote_size))
        lines = wrap_text(quote_text, quote_font, max_text_width)
        line_height = int(quote_size * 1.265)
        total_text_height = len(lines) * line_height + int(h * 0.067)
        y_start = max(int(h * 0.08), int(h * top_reserved_frac), (h - total_text_height) / 2)

        content_bottom = y_start + total_text_height + int(h * 0.019) + int(h * 0.021) + line_height
        if content_bottom <= BOTTOM_LIMIT or quote_size <= MIN_QUOTE_SIZE:
            break
        quote_size *= 0.92

    if content_bottom > BOTTOM_LIMIT:
        # Hard-fail rather than warn-and-continue: this runs unattended in
        # GitHub Actions, so a print() here would be a log line nobody
        # reads. Failing the step stops the pipeline before anything
        # broken gets committed or posted - content.json's cursor is left
        # unadvanced, same recovery path as an Instagram post failure.
        raise SystemExit(
            f"row {row_id} text still overflows the canvas at minimum font size "
            f"({len(lines)} lines) - this entry needs shortening in content.json."
        )

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


if __name__ == "__main__":
    quote_text = sys.argv[1]
    attribution = sys.argv[2]
    source = sys.argv[3]
    row_id = sys.argv[4]

    bg_name = get_background(attribution, row_id)
    bg_name, n_lines = render_quote_card(bg_name, quote_text, attribution, source, row_id)
    print(f"Used background: {bg_name}.jpg, wrapped to {n_lines} lines")
