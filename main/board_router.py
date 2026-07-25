"""
Routes each piece of content to its single best-matching Pinterest board.

Pinterest's algorithm rewards board relevance; posting the same pin to
multiple boards reads as duplicate/spammy content, so each pin goes to
exactly one board - whichever is the closest topical match.
"""

BOARDS = {
    "philosophy_psychology": "1102326514984549418",  # original catch-all
    "ancient_wisdom": "1102326514984569130",
    "cognitive_bias": "1102326514984569127",
    "deep_quotes": "1102326514984569131",
    "marcus_aurelius": "1102326514984569125",
    "mindset_growth": "1102326514984569129",
    "philosophy_quotes": "1102326514984569128",
    "psychology_facts": "1102326514984569126",
    "stoic_quotes": "1102326514984569124",
}

STOIC_PHILOSOPHERS = {"marcus aurelius", "epictetus", "seneca"}

# Facts whose source/text suggests a "bias" framing go to Cognitive Bias Explained
BIAS_KEYWORDS = ["bias", "effect", "heuristic", "fallacy", "illusion"]

# Rotate general philosophy quotes (non-Stoic, non-Marcus-Aurelius-specific)
# across these boards so they don't all pile onto one
GENERAL_QUOTE_ROTATION = [
    "philosophy_quotes", "deep_quotes", "mindset_growth", "ancient_wisdom",
]


def route(attribution, content_type, text, entry_id):
    attr_lower = attribution.strip().lower()

    try:
        n = int(entry_id)
    except (ValueError, TypeError):
        n = 0

    if content_type == "fact":
        text_lower = text.lower()
        if any(k in text_lower for k in BIAS_KEYWORDS):
            return BOARDS["cognitive_bias"]
        return BOARDS["psychology_facts"]

    # quote
    if attr_lower == "marcus aurelius":
        return BOARDS["marcus_aurelius"]
    if attr_lower in STOIC_PHILOSOPHERS:
        return BOARDS["stoic_quotes"]

    key = GENERAL_QUOTE_ROTATION[n % len(GENERAL_QUOTE_ROTATION)]
    return BOARDS[key]


if __name__ == "__main__":
    with open('_selected_attribution.txt') as f:
        attribution = f.read()
    with open('_selected_type.txt') as f:
        content_type = f.read().strip()
    with open('_selected_text.txt') as f:
        text = f.read()
    with open('_selected_id.txt') as f:
        entry_id = f.read().strip()

    board_id = route(attribution, content_type, text, entry_id)
    with open('_pin_board_id.txt', 'w') as f:
        f.write(board_id)
    board_name = [k for k, v in BOARDS.items() if v == board_id][0]
    print(f"Routed to board: {board_name} ({board_id})")
