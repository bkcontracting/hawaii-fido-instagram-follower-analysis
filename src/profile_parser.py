"""Deterministic parser for Instagram profile page text.

Extracts structured profile data from raw page text (accessibility tree
or DOM innerText) so the browser subagent only needs to grab text, not
reason about parsing. Saves ~500-1000 tokens per profile in LLM context.
"""
import re


def parse_count(text: str) -> int | None:
    """Parse an Instagram count string into an integer.

    Handles suffixes: K (thousands), M (millions), B (billions).
    Handles commas in numbers: "1,234" → 1234.

    Abbreviated counts are rounded to suffix-level granularity since
    Instagram's displayed decimals are already approximations:
    "64.1K" → 64000, "2.5M" → 3000000.

    Returns None if text is empty or unparseable.

    >>> parse_count("64.1K")
    64000
    >>> parse_count("5M")
    5000000
    >>> parse_count("1,234")
    1234
    >>> parse_count("42")
    42
    """
    if not text or not isinstance(text, str):
        return None

    text = text.strip().replace(",", "")

    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    match = re.match(r"^([\d.]+)\s*([KMBkmb])$", text)
    if match:
        number = float(match.group(1))
        suffix = match.group(2).upper()
        return round(number) * multipliers[suffix]

    match = re.match(r"^(\d+)$", text)
    if match:
        return int(match.group(1))

    return None


def detect_page_state(text: str) -> str:
    """Detect Instagram page state from raw page text.

    Returns one of: 'normal', 'not_found', 'suspended', 'rate_limited', 'login_required'.
    """
    if not text:
        return "not_found"

    lower = text.lower()

    if "sorry, this page isn't available" in lower:
        return "not_found"
    if "user not found" in lower:
        return "not_found"
    if "account has been suspended" in lower or "suspended" in lower and "violat" in lower:
        return "suspended"
    if "try again later" in lower or "rate limit" in lower or "wait a few minutes" in lower:
        return "rate_limited"
    if "log in" in lower and "to see" in lower:
        return "login_required"

    return "normal"


def parse_profile_page(text: str) -> dict:
    """Extract structured profile data from raw Instagram page text.

    Returns dict with keys: follower_count, following_count, post_count,
    bio, website, is_verified, is_private, is_business, page_state.

    The subagent should call this instead of doing its own parsing.
    Missing fields are returned as None (counts) or empty string (text)
    or False (booleans).
    """
    page_state = detect_page_state(text)
    result = {
        "follower_count": None,
        "following_count": None,
        "post_count": None,
        "bio": "",
        "website": "",
        "is_verified": False,
        "is_private": False,
        "is_business": False,
        "page_state": page_state,
    }

    if page_state != "normal":
        if page_state == "not_found":
            result["is_private"] = False
        return result

    # Posts / Followers / Following pattern: "123 posts 1.2K followers 456 following"
    count_pattern = r"([\d,.]+[KMBkmb]?)\s+posts?"
    match = re.search(count_pattern, text)
    if match:
        result["post_count"] = parse_count(match.group(1))

    count_pattern = r"([\d,.]+[KMBkmb]?)\s+followers?"
    match = re.search(count_pattern, text)
    if match:
        result["follower_count"] = parse_count(match.group(1))

    count_pattern = r"([\d,.]+[KMBkmb]?)\s+following"
    match = re.search(count_pattern, text)
    if match:
        result["following_count"] = parse_count(match.group(1))

    # Verified badge
    result["is_verified"] = bool(
        re.search(r"verified badge|verified", text, re.IGNORECASE)
        and "get verified" not in text.lower()
    )

    # Private account
    result["is_private"] = bool(
        re.search(r"this account is private|private account", text, re.IGNORECASE)
    )

    # Business/creator indicators
    result["is_business"] = bool(
        re.search(
            r"contact|email|call|directions|category:|"
            r"business|shopping|shop now|view shop",
            text, re.IGNORECASE,
        )
    )

    # Website: look for URLs in profile area
    url_match = re.search(
        r"(https?://[^\s<>\"']+|[\w.-]+\.(?:com|org|net|io|co|shop|store|biz|me|ee|us|info|xyz|gg|link)[/\w.-]*)",
        text,
    )
    if url_match:
        website = url_match.group(1)
        # Filter out instagram.com links
        if "instagram.com" not in website:
            result["website"] = website

    # Bio: text between the counts line and the posts grid is typically the bio.
    # This is a best-effort extraction — the subagent can override if needed.
    bio_match = re.search(
        r"following\s*\n(.*?)(?:\n.*?posts?\s|$)", text, re.DOTALL | re.IGNORECASE
    )
    if bio_match:
        bio = bio_match.group(1).strip()
        # Clean up: remove "Followed by..." lines
        bio = re.sub(r"Followed by .*", "", bio).strip()
        if bio and len(bio) < 500:
            result["bio"] = bio

    return result
