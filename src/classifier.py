"""Classify Instagram profiles into categories using 13 priority-ordered rules."""
import re
from src.location_detector import is_hawaii as detect_hawaii


# ── Keyword lists ──────────────────────────────────────────────────
_PET_KEYWORDS = [
    "veterinar", "vet clinic", "pet ", "dog trainer", "groomer",
    "kennel", "animal hospital", "canine", "paws", "pet food",
    "pet supply", "dog gym",
]

_COMMERCIAL_SIGNALS = ["shop", "store", "service", "clinic", "supply", "co", "inc"]

_CHARITY_KEYWORDS = ["rescue", "humane", "nonprofit", "501c", "shelter", "charity", "foundation"]

_ORG_KEYWORDS = ["church", "school", "rotary", "club", "golf"]

_ELECTED_KEYWORDS = ["council", "mayor", "senator", "representative", "governor"]

_MEDIA_KEYWORDS = [
    "event", "tournament", "festival", "magazine", "news",
    "photographer", "media", "press",
]


def _combined_text(profile):
    """Build searchable text from handle + display_name + bio."""
    parts = [
        profile.get("handle") or "",
        profile.get("display_name") or "",
        profile.get("bio") or "",
    ]
    return " ".join(parts).lower()


def _has_any(text, keywords):
    """Return True if any keyword appears in text."""
    return any(kw in text for kw in keywords)


def _has_commercial_signal(text):
    """Return True if text contains a commercial signal."""
    return _has_any(text, _COMMERCIAL_SIGNALS)


# ── Subcategory detection ──────────────────────────────────────────
def _pet_subcategory(text):
    if "veterinar" in text or "vet clinic" in text or "animal hospital" in text:
        return "veterinary"
    if "dog trainer" in text or "trainer" in text:
        return "trainer"
    if "pet store" in text or "pet supply" in text:
        return "pet_store"
    if "groomer" in text:
        return "groomer"
    if "pet food" in text:
        return "pet_food"
    return "general"


def _bank_subcategory(text):
    if "credit union" in text:
        return "credit_union"
    if "financial advisor" in text or "advisor" in text:
        return "financial_advisor"
    if "bank" in text:
        return "bank"
    return "general"


def _org_subcategory(text):
    if "church" in text:
        return "church"
    if "school" in text:
        return "school"
    if "club" in text or "rotary" in text or "golf" in text:
        return "club"
    return "community_group"


def _media_subcategory(text):
    if "photographer" in text:
        return "photographer"
    if "news" in text:
        return "news"
    if "magazine" in text or "media" in text or "press" in text:
        return "media"
    if "event" in text or "tournament" in text or "festival" in text:
        return "event"
    return "general"


def _business_subcategory(text):
    if "restaurant" in text or "cafe" in text or "coffee" in text or "food" in text:
        return "restaurant"
    if "real estate" in text or "realty" in text:
        return "real_estate"
    if "retail" in text or "boutique" in text or "shop" in text:
        return "retail"
    return "service"


# ── Main classifier ───────────────────────────────────────────────
def classify(profile):
    """Classify a profile into {category, subcategory, confidence}.

    Evaluates 13 rules in priority order. First match wins.
    Scans handle + display_name + bio for keyword matches.
    """
    text = _combined_text(profile)
    is_biz = bool(profile.get("is_business"))
    is_hi = bool(profile.get("is_hawaii"))
    follower_count = profile.get("follower_count")
    following_count = profile.get("following_count")
    post_count = profile.get("post_count")

    # Rule 1: bank_financial
    if _has_any(text, ["bank", "financial", "credit union"]):
        return {"category": "bank_financial",
                "subcategory": _bank_subcategory(text),
                "confidence": 0.9}

    # Rule 2: pet_industry (requires business OR commercial signal)
    if _has_any(text, _PET_KEYWORDS) and (is_biz or _has_commercial_signal(text)):
        return {"category": "pet_industry",
                "subcategory": _pet_subcategory(text),
                "confidence": 0.85}

    # Rule 3: organization (excludes charity keywords)
    if _has_any(text, _ORG_KEYWORDS) and not _has_any(text, _CHARITY_KEYWORDS):
        return {"category": "organization",
                "subcategory": _org_subcategory(text),
                "confidence": 0.8}

    # Rule 4: charity
    if _has_any(text, _CHARITY_KEYWORDS):
        return {"category": "charity",
                "subcategory": "general",
                "confidence": 0.85}

    # Rule 5: elected_official (requires Hawaii)
    if _has_any(text, _ELECTED_KEYWORDS) and is_hi:
        return {"category": "elected_official",
                "subcategory": "general",
                "confidence": 0.8}

    # Rule 6: media_event
    if _has_any(text, _MEDIA_KEYWORDS):
        return {"category": "media_event",
                "subcategory": _media_subcategory(text),
                "confidence": 0.75}

    # Rule 7: business_local
    if is_biz and is_hi:
        return {"category": "business_local",
                "subcategory": _business_subcategory(text),
                "confidence": 0.7}

    # Rule 8: business_national
    if is_biz and not is_hi:
        return {"category": "business_national",
                "subcategory": _business_subcategory(text),
                "confidence": 0.7}

    # Rule 9: influencer (10k+ followers, not business)
    if follower_count is not None and follower_count >= 10000 and not is_biz:
        return {"category": "influencer",
                "subcategory": "general",
                "confidence": 0.7}

    # Rule 10: spam_bot (following > 10x followers AND posts < 5)
    if (follower_count is not None and following_count is not None
            and post_count is not None
            and following_count > 10 * follower_count
            and post_count < 5):
        return {"category": "spam_bot",
                "subcategory": "general",
                "confidence": 0.8}

    # Rule 11: personal_engaged (posts > 50, not business)
    if post_count is not None and post_count > 50 and not is_biz:
        return {"category": "personal_engaged",
                "subcategory": "general",
                "confidence": 0.6}

    # Rule 12: personal_passive (posts <= 50, not business)
    if post_count is not None and not is_biz:
        return {"category": "personal_passive",
                "subcategory": "general",
                "confidence": 0.5}

    # Rule 13: unknown (fallback)
    return {"category": "unknown",
            "subcategory": "general",
            "confidence": 0.3}
