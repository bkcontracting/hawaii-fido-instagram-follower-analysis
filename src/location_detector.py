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
    (re.compile(r'\bhawaiian\b', re.IGNORECASE), _WEAK_WEIGHT),
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
_ALL_SIGNAL_GROUPS = [
    _WEAK_SIGNALS,
    _STRONG_CITY_SIGNALS,
    _STRONG_STATE_SIGNALS,
    _MEDIUM_ISLAND_SIGNALS,
    _MEDIUM_OTHER_SIGNALS,
]


def hawaii_confidence(text: str) -> float:
    """Return 0.0-1.0 confidence that *text* indicates a Hawaii location.

    Scans the input for known Hawaii-related signals at three strength
    tiers (strong 0.4, medium 0.3, weak 0.15). Each unique signal is
    counted at most once. The sum is capped at 1.0.

    Returns 0.0 for None or empty input.
    """
    if not text:
        return 0.0

    # Work on a copy we can mask consumed spans from so that, e.g.,
    # "Hawaiian" is matched as a weak signal and the substring is not
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
