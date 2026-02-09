"""Hawaii location detection from free-text bios and profile fields."""
import re

# ── Signal definitions ───────────────────────────────────────────────
# Each tuple: (compiled regex, weight)
# Order matters: more-specific patterns should be checked before less-specific
# ones so that "Hawaiian" is caught as a weak signal before "Hawaii" could
# match as a strong signal inside it.

_STRONG_WEIGHT = 0.4
_MEDIUM_WEIGHT = 0.3
_WEAK_WEIGHT = 0.15

# Weak signals — checked first so "Hawaiian" is consumed before "Hawaii"
_WEAK_SIGNALS = [
    (re.compile(r'\baloha\b', re.IGNORECASE), _WEAK_WEIGHT),
]

# "Hawaiian" is a medium signal — it strongly implies Hawaii
_HAWAIIAN_SIGNALS = [
    (re.compile(r'\bhawaiian\b', re.IGNORECASE), _MEDIUM_WEIGHT),
]

# Strong signals — cities
_STRONG_CITY_SIGNALS = [
    (re.compile(r'\bhonolulu\b', re.IGNORECASE), _STRONG_WEIGHT),
    (re.compile(r'\bkailua\b', re.IGNORECASE), _STRONG_WEIGHT),
    (re.compile(r'\bkapolei\b', re.IGNORECASE), _STRONG_WEIGHT),
    (re.compile(r'\baiea\b', re.IGNORECASE), _STRONG_WEIGHT),
    (re.compile(r'\bpearl\s+city\b', re.IGNORECASE), _STRONG_WEIGHT),
    (re.compile(r'\bkaneohe\b', re.IGNORECASE), _STRONG_WEIGHT),
    (re.compile(r'\bwaipahu\b', re.IGNORECASE), _STRONG_WEIGHT),
    (re.compile(r'\bmililani\b', re.IGNORECASE), _STRONG_WEIGHT),
    (re.compile(r'\bwaikiki\b', re.IGNORECASE), _STRONG_WEIGHT),
    (re.compile(r'\bhilo\b', re.IGNORECASE), _STRONG_WEIGHT),
    (re.compile(r'\blahaina\b', re.IGNORECASE), _STRONG_WEIGHT),
    (re.compile(r'\bkona\b', re.IGNORECASE), _STRONG_WEIGHT),
]

# Strong signals — state names + area code
_STRONG_STATE_SIGNALS = [
    # hawai'i / hawaiʻi with okina variants — must come before bare "hawaii"
    (re.compile(r"\bhawai['\u02BB]i\b", re.IGNORECASE), _STRONG_WEIGHT),
    # bare "hawaii" — but NOT "hawaiian" (negative lookahead)
    (re.compile(r'\bhawaii\b(?!an)', re.IGNORECASE), _STRONG_WEIGHT),
    # "HI" as a state abbreviation — uppercase only to avoid matching "hi" greeting
    (re.compile(r'\bHI\b'), _STRONG_WEIGHT),
    # area code
    (re.compile(r'\b808\b'), _STRONG_WEIGHT),
]

# Medium signals — islands
_MEDIUM_ISLAND_SIGNALS = [
    (re.compile(r'\boahu\b', re.IGNORECASE), _MEDIUM_WEIGHT),
    (re.compile(r'\bmaui\b', re.IGNORECASE), _MEDIUM_WEIGHT),
    (re.compile(r'\bkauai\b', re.IGNORECASE), _MEDIUM_WEIGHT),
    (re.compile(r'\bbig\s+island\b', re.IGNORECASE), _MEDIUM_WEIGHT),
    (re.compile(r'\bmolokai\b', re.IGNORECASE), _MEDIUM_WEIGHT),
    (re.compile(r'\blanai\b', re.IGNORECASE), _MEDIUM_WEIGHT),
]

# Medium signals — airport + zip prefixes
_MEDIUM_OTHER_SIGNALS = [
    (re.compile(r'\bhnl\b', re.IGNORECASE), _MEDIUM_WEIGHT),
    (re.compile(r'\b967\d{2}\b'), _MEDIUM_WEIGHT),
    (re.compile(r'\b968\d{2}\b'), _MEDIUM_WEIGHT),
]

# All signal groups in evaluation order
# "Hawaiian" is checked before strong state signals so the substring is
# consumed and not re-matched by the "hawaii" pattern.
_ALL_SIGNAL_GROUPS = [
    _WEAK_SIGNALS,
    _HAWAIIAN_SIGNALS,
    _STRONG_CITY_SIGNALS,
    _STRONG_STATE_SIGNALS,
    _MEDIUM_ISLAND_SIGNALS,
    _MEDIUM_OTHER_SIGNALS,
]


# Known Hawaii terms to look for when splitting concatenated handle words.
# Order matters: longer/more-specific terms first to avoid partial matches
# (e.g. "hawaiian" before "hawaii", "honolulu" before shorter terms).
_HAWAII_TERMS_FOR_SPLIT = [
    "hawaiian", "hawaii", "honolulu", "kailua", "kapolei", "aiea",
    "kaneohe", "waipahu", "mililani", "waikiki", "hilo", "lahaina",
    "kona", "oahu", "maui", "kauai", "molokai", "lanai", "808",
]


def _inject_hawaii_spaces(text: str) -> str:
    """Insert spaces around known Hawaii terms embedded in concatenated words.

    For each known term, if it appears as a substring without a space boundary
    on at least one side, insert spaces around it. Once a term is isolated,
    shorter terms that are substrings of it (e.g. "hawaii" inside "hawaiian")
    are skipped.

    >>> _inject_hawaii_spaces("doggyboxhawaii")
    'doggybox hawaii'
    >>> _inject_hawaii_spaces("oahudogtraining")
    'oahu dogtraining'
    """
    result = text.lower()
    # Track which character positions have already been claimed by a term
    # so shorter terms don't re-split longer ones.
    claimed = set()
    for term in _HAWAII_TERMS_FOR_SPLIT:
        idx = result.find(term)
        if idx == -1:
            continue
        # Skip if this position overlaps with an already-claimed longer term
        term_positions = set(range(idx, idx + len(term)))
        if term_positions & claimed:
            continue
        before_char = result[idx - 1] if idx > 0 else ' '
        after_char = result[idx + len(term)] if (idx + len(term)) < len(result) else ' '
        before = before_char not in (' ', '\t', '\n')
        after = after_char not in (' ', '\t', '\n')
        # For numeric terms like "808", don't split if surrounded by digits
        # (e.g., phone numbers like "18085551234").
        if term.isdigit() and (before_char.isdigit() or after_char.isdigit()):
            continue
        if before or after:
            # Insert spaces and recalculate position
            new_result = result[:idx] + ' ' + term + ' ' + result[idx + len(term):]
            # Adjust claimed positions for the offset (2 spaces added)
            offset = len(new_result) - len(result)
            claimed = {p + offset if p >= idx else p for p in claimed}
            # Claim the new position of this term (after the space)
            new_idx = idx + 1  # +1 for the space we inserted before
            claimed.update(range(new_idx, new_idx + len(term)))
            result = new_result
        else:
            # Already has spaces; claim the positions
            claimed.update(range(idx, idx + len(term)))
    return result


def _normalize_for_search(text: str) -> str:
    """Pre-process text so Hawaii terms embedded in handles become searchable.

    Splits on common IG handle separators (``_``, ``.``), camelCase boundaries,
    digit-to-letter / letter-to-digit transitions, and known Hawaii terms
    embedded in concatenated words, inserting spaces so that ``\\b`` word
    boundaries in the signal regexes can match.

    >>> _normalize_for_search("doggyboxhawaii")
    'doggyboxhawaii doggybox hawaii'
    """
    if not text:
        return text

    # Step 1: split on _ and .
    expanded = re.sub(r'[_.]', ' ', text)

    # Step 2: split camelCase  (e.g. "DoggyBox" → "Doggy Box")
    expanded = re.sub(r'([a-z])([A-Z])', r'\1 \2', expanded)

    # Step 3: split digit↔letter transitions (e.g. "808camo" → "808 camo")
    expanded = re.sub(r'(\d)([A-Za-z])', r'\1 \2', expanded)
    expanded = re.sub(r'([A-Za-z])(\d)', r'\1 \2', expanded)

    # Step 4: inject spaces around known Hawaii terms in concatenated words
    expanded = _inject_hawaii_spaces(expanded)

    # Collapse multiple spaces
    expanded = re.sub(r' +', ' ', expanded).strip()

    # Append the expanded form so original text is still searchable too
    return text + " " + expanded


def hawaii_confidence(text: str) -> float:
    """Return 0.0-1.0 confidence that *text* indicates a Hawaii location.

    Scans the input for known Hawaii-related signals at three strength
    tiers (strong 0.4, medium 0.3, weak 0.15). Each unique signal is
    counted at most once. The sum is capped at 1.0.

    Returns 0.0 for None or empty input.
    """
    if not text:
        return 0.0

    # Normalize handles so embedded Hawaii terms get word boundaries.
    # Also strip okina variants so "O'ahu" → "Oahu", "Hawai'i" → "Hawaii".
    text = re.sub(r"['\u02BB]", "", text)
    text = _normalize_for_search(text)

    # Work on a copy we can mask consumed spans from so that, e.g.,
    # "Hawaiian" is matched as a medium signal and the substring is not
    # re-matched by the strong "hawaii" pattern.
    remaining = text
    total = 0.0

    for group in _ALL_SIGNAL_GROUPS:
        for pattern, weight in group:
            match = pattern.search(remaining)
            if match:
                # Blank out the matched span to prevent overlapping matches
                start, end = match.start(), match.end()
                remaining = remaining[:start] + (" " * (end - start)) + remaining[end:]
                total += weight

    return min(total, 1.0)


def is_hawaii(text: str) -> bool:
    """Return True if *hawaii_confidence(text)* >= 0.4."""
    return hawaii_confidence(text) >= 0.4
