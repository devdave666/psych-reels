"""
Generates keyword-rich Pinterest titles and descriptions.

Pinterest ranks primarily on keywords in titles/descriptions/board names.
Hashtags contribute almost nothing (~1%), so we use natural long-tail
keyword phrases instead of hashtag stuffing.
"""

# Long-tail keyword clusters people actually search on Pinterest in this niche
QUOTE_KEYWORDS = [
    "stoic quotes", "philosophy quotes", "wisdom quotes",
    "deep quotes about life", "mindset quotes", "quotes to live by",
]
FACT_KEYWORDS = [
    "psychology facts", "interesting psychology facts", "human behavior psychology",
    "cognitive bias explained", "psychology of the mind", "mental health facts",
]

# Philosopher-specific search terms (people search these by name directly)
PHILOSOPHER_TERMS = {
    "marcus aurelius": "Marcus Aurelius quotes",
    "epictetus": "Epictetus quotes",
    "seneca": "Seneca quotes",
    "plato": "Plato quotes",
    "aristotle": "Aristotle quotes",
    "friedrich nietzsche": "Nietzsche quotes",
    "immanuel kant": "Kant philosophy",
    "baruch spinoza": "Spinoza philosophy",
    "rene descartes": "Descartes philosophy",
    "arthur schopenhauer": "Schopenhauer quotes",
    "soren kierkegaard": "Kierkegaard quotes",
    "david hume": "David Hume philosophy",
    "john locke": "John Locke philosophy",
    "john stuart mill": "John Stuart Mill quotes",
    "voltaire": "Voltaire quotes",
    "jean-jacques rousseau": "Rousseau quotes",
    "blaise pascal": "Pascal quotes",
    "michel de montaigne": "Montaigne quotes",
    "cicero": "Cicero quotes",
    "francis bacon": "Francis Bacon quotes",
    "thomas hobbes": "Hobbes philosophy",
    "georg wilhelm friedrich hegel": "Hegel philosophy",
    "ralph waldo emerson": "Emerson quotes",
    "henry david thoreau": "Thoreau quotes",
    "benjamin franklin": "Benjamin Franklin quotes",
}

STOIC_PHILOSOPHERS = {"marcus aurelius", "epictetus", "seneca"}


def build_title(text, attribution, content_type, entry_id):
    """
    Keyword-first title, under ~100 chars. Pinterest wants relevance, not cleverness.
    """
    attr_lower = attribution.strip().lower()

    if content_type == "quote":
        named = PHILOSOPHER_TERMS.get(attr_lower)
        if named:
            base = named
        else:
            base = "Philosophy quotes"
        if attr_lower in STOIC_PHILOSOPHERS:
            base = f"{base} on Stoicism"
        # Add a short excerpt for specificity/context
        snippet = text.strip().rstrip(".")
        if len(snippet) > 55:
            snippet = snippet[:55].rsplit(" ", 1)[0] + "..."
        title = f"{base}: {snippet}"
    else:
        # Facts: lead with the searchable category
        idx = entry_id_to_index(entry_id, len(FACT_KEYWORDS))
        base = FACT_KEYWORDS[idx].capitalize()
        snippet = text.strip().rstrip(".")
        if len(snippet) > 55:
            snippet = snippet[:55].rsplit(" ", 1)[0] + "..."
        title = f"{base}: {snippet}"

    return title[:100]


def build_description(text, attribution, source, content_type, entry_id):
    """
    Natural-language description blending primary + secondary keywords.
    Reads like a person wrote it, not a keyword dump.
    """
    attr_lower = attribution.strip().lower()

    if content_type == "quote":
        named = PHILOSOPHER_TERMS.get(attr_lower)
        kw_primary = named if named else "philosophy quotes"
        idx = entry_id_to_index(entry_id, len(QUOTE_KEYWORDS))
        kw_secondary = QUOTE_KEYWORDS[idx]

        stoic_line = ""
        if attr_lower in STOIC_PHILOSOPHERS:
            stoic_line = " A core idea from Stoic philosophy, still practical today."

        desc = (
            f'"{text.strip()}" — {attribution}, {source}.'
            f"{stoic_line} "
            f"Saved from a daily collection of {kw_primary.lower()} and {kw_secondary} "
            f"paired with modern psychology. Follow for one idea a day on philosophy, "
            f"self improvement, and how ancient thinkers understood the mind."
        )
    else:
        idx = entry_id_to_index(entry_id, len(FACT_KEYWORDS))
        kw_primary = FACT_KEYWORDS[idx]
        desc = (
            f"{text.strip()} "
            f"One of many {kw_primary} from a daily collection exploring human behavior "
            f"psychology, cognitive bias, and personal growth. Follow for a new "
            f"psychology fact or philosophy idea every day."
        )

    # Pinterest truncates long descriptions in some placements; keep it reasonable
    return desc[:480]


def entry_id_to_index(entry_id, length):
    """Deterministic rotation through keyword variants so pins don't all read identically."""
    try:
        n = int(entry_id)
    except (ValueError, TypeError):
        n = 0
    return n % length


if __name__ == "__main__":
    import sys, json
    with open('_selected_text.txt') as f:
        text = f.read()
    with open('_selected_attribution.txt') as f:
        attribution = f.read()
    with open('_selected_source.txt') as f:
        source = f.read()
    with open('_selected_type.txt') as f:
        content_type = f.read().strip()
    with open('_selected_id.txt') as f:
        entry_id = f.read().strip()

    title = build_title(text, attribution, content_type, entry_id)
    desc = build_description(text, attribution, source, content_type, entry_id)

    with open('_pin_title.txt', 'w') as f:
        f.write(title)
    with open('_pin_description.txt', 'w') as f:
        f.write(desc)

    print(f"TITLE ({len(title)} chars): {title}")
    print()
    print(f"DESCRIPTION ({len(desc)} chars): {desc}")
