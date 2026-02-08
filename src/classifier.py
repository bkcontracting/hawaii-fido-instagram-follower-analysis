"""Classify Instagram profiles into categories using priority-ordered rules."""
import re


# ── Keyword lists ──────────────────────────────────────────────────
_SERVICE_DOG_KEYWORDS = [
    "service dog", "therapy dog", "assistance dog", "guide dog",
    "service animal", "working dog", "canine assisted",
    "animal assisted therapy", "ptsd dog", "seizure dog",
]

_PET_KEYWORDS = [
    "veterinar", "vet clinic", "pet ", "dog trainer", "dog training",
    "groomer", "grooming", "kennel", "animal hospital", "canine", "paws",
    "pet food", "pet supply", "dog gym", "k9", "daycare", "boarding",
    "pet sitting", "dog walking", "obedience", "rehab", "dog treat",
    "pet collar",
    "pomsk", "goldendoodle", "labradoodle", "frenchie", "pomeranian",
    "shichon", "aussiedoodle",
]

# Strong pet keywords classify as pet_industry WITHOUT requiring
# is_business or commercial signal.
_STRONG_PET_KEYWORDS = [
    "veterinar", "vet clinic", "animal hospital", "dog trainer",
    "dog training", "kennel", "groomer", "grooming", "k9", "daycare",
    "boarding", "pet sitting", "dog walking", "obedience",
    "breeder", "breeding", "puppies for", "litter",
    "dog trick",
    "pet rehab", "pet rehabilitation", "animal rehab", "animal rehabilitation",
]

# Commercial markers for pet_industry fallback when is_business=False.
# Use boundary-aware matching to avoid substring false positives such as
# "community", "coffee", and "welcome".
_COMMERCIAL_SIGNAL_PATTERNS = [
    re.compile(r"\bshops?\b"),
    re.compile(r"\bstores?\b"),
    re.compile(r"\bservices?\b"),
    re.compile(r"\bclinics?\b"),
    re.compile(r"\bsupply\b"),
    re.compile(r"\binc\b"),
    re.compile(r"\bllc\b"),
    re.compile(r"\bco\b\.?"),
]

_CORPORATE_KEYWORDS = [
    "electric", "utility", "airline", "telecom", "insurance",
    "corporation", "corporate", "headquarters", "global",
]

# Strong business keywords classify as business_local/business_national
# WITHOUT requiring the is_business IG flag.
_STRONG_BUSINESS_KEYWORDS = [
    "brewery", "brewing", "restaurant", "cafe", "bakery", "catering",
    "hotel", "resort",
    "salon", "barbershop",
    "real estate", "realty", "realtor",
    "law firm",
    "mortgage",
]

_CHARITY_KEYWORDS = [
    "rescue", "humane", "nonprofit", "501c", "shelter", "charity",
    "spca", "humane society",
]

_PARTNER_CHARITY_KEYWORDS = [
    "disability", "disabled", "accessible", "accessibility",
    "independent living", "special needs", "adaptive",
    "spca", "animal welfare", "animal control",
    "humane society",
]

# Patterns that indicate "rescue" is personal, not organizational.
_PERSONAL_RESCUE_RE = re.compile(
    r"rescue\s+(pup|dog|cat|baby|mutt|mix|kitty)"
    r"|rescued\s+(from|my|our)"
    r"|my\s+rescue"
    r"|our\s+rescue"
    r"|adopted\s+from"
    r"|adoptee\s+from"
)

# Strong charity keywords that override personal-rescue exclusion.
_STRONG_CHARITY_KEYWORDS = ["humane", "nonprofit", "501c", "shelter", "charity"]

_ORG_KEYWORDS = [
    "church", "school", "rotary", "club", "golf",
    "chamber", "association", "chapter", "foundation",
    "coalition", "initiative", "alliance",
]

_GOVERNMENT_KEYWORDS = [
    "government organization", "military", "marine corps",
    "veterans", "job corps",
]

# Guard-rail exclusions to prevent false positives from expanded org keywords.
_FOUNDATION_BEAUTY_RE = re.compile(
    r"foundation\s*(shade|makeup|routine|primer|skin|beauty|cosmetic)"
    r"|makeup\s+foundation"
)
_CHAPTER_BOOK_RE = re.compile(
    r"chapter\s+\d"
    r"|chapter\s+(book|novel|story|read)"
    r"|book\s+chapter"
)

# Patterns where "school" is in an address or job title (not an organization).
_SCHOOL_EXCLUSION_RE = re.compile(
    r"school\s+(st|street|rd|ave|blvd|dr)\b"
    r"|school\s+counselor"
    r"|school\s+teacher"
    r"|school\s+nurse"
    r"|@\s*\w+\s+school\s+(at|of)\b"
    r"|faculty\b.*\bschool\b"
)

_ELECTED_KEYWORDS = ["council", "mayor", "senator", "representative", "governor"]

_MEDIA_KEYWORDS = [
    "event", "tournament", "festival", "magazine", "news",
    "photographer", "media", "press", "competition",
    "marathon", "triathlon", "5k", "10k", "aloha run",
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
    return any(pattern.search(text) for pattern in _COMMERCIAL_SIGNAL_PATTERNS)


# ── Subcategory detection ──────────────────────────────────────────
def _service_dog_subcategory(text):
    if "therapy dog" in text or "canine assisted" in text or "animal assisted" in text:
        return "therapy"
    if "guide dog" in text:
        return "guide"
    if "emotional support" in text:
        return "emotional_support"
    if "service dog" in text or "service animal" in text:
        return "service"
    return "general"


def _pet_subcategory(text):
    if "veterinar" in text or "vet clinic" in text or "animal hospital" in text:
        return "veterinary"
    if "dog trainer" in text or "dog training" in text or "trainer" in text:
        return "trainer"
    if "dog trick" in text:
        return "trainer"
    if "breeder" in text or "breeding" in text or "puppies for" in text or "litter" in text:
        return "breeder"
    if "pet store" in text or "pet supply" in text:
        return "pet_store"
    if "groomer" in text or "grooming" in text:
        return "groomer"
    if "pet food" in text:
        return "pet_food"
    if "boarding" in text or "daycare" in text or "kennel" in text:
        return "boarding"
    if "pet sitting" in text or "dog walking" in text:
        return "pet_care"
    if "pet rehab" in text or "animal rehab" in text:
        return "rehabilitation"
    return "general"


def _bank_subcategory(text):
    if "credit union" in text:
        return "credit_union"
    if "financial advisor" in text or "advisor" in text:
        return "financial_advisor"
    if re.search(r'(?<![a-z])bank(?![a-z])', text):
        return "bank"
    return "general"


def _org_subcategory(text):
    if _has_any(text, _GOVERNMENT_KEYWORDS):
        return "government"
    if "church" in text:
        return "church"
    if "school" in text:
        return "school"
    if "club" in text or "rotary" in text or "golf" in text:
        return "club"
    if _has_any(text, ["chamber", "association", "foundation", "coalition", "alliance"]):
        return "community_group"
    if "initiative" in text or "chapter" in text:
        return "community_group"
    return "community_group"


def _media_subcategory(text):
    if "photographer" in text:
        return "photographer"
    if "news" in text:
        return "news"
    if "magazine" in text or "media" in text or "press" in text:
        return "media"
    if _has_any(text, ["marathon", "triathlon", "5k", "10k", "aloha run"]):
        return "event"
    if "event" in text or "tournament" in text or "festival" in text or "competition" in text:
        return "event"
    return "general"


def _business_subcategory(text):
    if "restaurant" in text or "cafe" in text or "coffee" in text or "food" in text:
        return "restaurant"
    if "brewery" in text or "brewing" in text:
        return "restaurant"
    if "hotel" in text or "resort" in text:
        return "hospitality"
    if "real estate" in text or "realty" in text or "realtor" in text or "mortgage" in text:
        return "real_estate"
    if "law firm" in text:
        return "legal"
    if "retail" in text or "boutique" in text or "shop" in text:
        return "retail"
    if "salon" in text or "barbershop" in text:
        return "service"
    if "service" in text or "plumb" in text:
        return "service"
    return "general"


def _is_personal_rescue(text):
    """Return True if 'rescue' appears only in personal pet-owner context."""
    if "rescue" not in text:
        return False
    if _has_any(text, _STRONG_CHARITY_KEYWORDS):
        return False
    if _PERSONAL_RESCUE_RE.search(text):
        return True
    if _has_any(text, ["organization", "foundation", "society", "network"]):
        return False
    return True


def _is_school_exclusion(text):
    """Return True if 'school' appears in address or job title context."""
    if "school" not in text:
        return False
    return bool(_SCHOOL_EXCLUSION_RE.search(text))


# ── Main classifier ───────────────────────────────────────────────
def classify(profile):
    """Classify a profile into {category, subcategory, confidence}.

    Evaluates rules in priority order. First match wins.
    Scans handle + display_name + bio for keyword matches.
    """
    text = _combined_text(profile)
    is_biz = bool(profile.get("is_business"))
    is_hi = bool(profile.get("is_hawaii"))
    follower_count = profile.get("follower_count")
    following_count = profile.get("following_count")
    post_count = profile.get("post_count")

    # Rule 0: service_dog_aligned (highest priority)
    if _has_any(text, _SERVICE_DOG_KEYWORDS):
        return {"category": "service_dog_aligned",
                "subcategory": _service_dog_subcategory(text),
                "confidence": 0.95}

    # Rule 1: bank_financial (word boundary on "bank", treating _ as separator)
    if re.search(r'(?<![a-z])bank(?![a-z])', text) or _has_any(text, ["financial", "credit union"]):
        return {"category": "bank_financial",
                "subcategory": _bank_subcategory(text),
                "confidence": 0.9}

    # Rule 2: corporate
    if _has_any(text, _CORPORATE_KEYWORDS):
        return {"category": "corporate",
                "subcategory": "general",
                "confidence": 0.8}
    if is_biz and follower_count is not None and follower_count >= 25000:
        return {"category": "corporate",
                "subcategory": "general",
                "confidence": 0.8}

    # Rule 3: pet_industry
    # Strong pet keywords classify without requiring is_business or commercial signal
    if _has_any(text, _STRONG_PET_KEYWORDS):
        return {"category": "pet_industry",
                "subcategory": _pet_subcategory(text),
                "confidence": 0.85}
    # Weak pet keywords require is_business or commercial signal
    if _has_any(text, _PET_KEYWORDS) and (is_biz or _has_commercial_signal(text)):
        return {"category": "pet_industry",
                "subcategory": _pet_subcategory(text),
                "confidence": 0.85}

    # Rule 4a: government/military organization
    if _has_any(text, _GOVERNMENT_KEYWORDS):
        return {"category": "organization",
                "subcategory": "government",
                "confidence": 0.85}

    # Rule 4b: organization (excludes charity keywords, school address/job exclusion)
    if _has_any(text, _ORG_KEYWORDS) and not _has_any(text, _CHARITY_KEYWORDS):
        # Guard rails: exclude false positives from expanded keywords
        # "foundation" in beauty/makeup context → not an org
        if "foundation" in text and _FOUNDATION_BEAUTY_RE.search(text):
            other_org = [kw for kw in _ORG_KEYWORDS if kw != "foundation" and kw in text]
            if not other_org:
                pass  # Skip — beauty context
            else:
                return {"category": "organization",
                        "subcategory": _org_subcategory(text),
                        "confidence": 0.8}
        # "chapter" in book context → not an org
        elif "chapter" in text and _CHAPTER_BOOK_RE.search(text):
            other_org = [kw for kw in _ORG_KEYWORDS if kw != "chapter" and kw in text]
            if not other_org:
                pass  # Skip — book context
            else:
                return {"category": "organization",
                        "subcategory": _org_subcategory(text),
                        "confidence": 0.8}
        # Check if the only org match is "school" in an excluded context
        elif "school" in text and _is_school_exclusion(text):
            # Check if there are other org keywords besides "school"
            other_org = [kw for kw in _ORG_KEYWORDS if kw != "school" and kw in text]
            if not other_org:
                pass  # Skip organization classification
            else:
                return {"category": "organization",
                        "subcategory": _org_subcategory(text),
                        "confidence": 0.8}
        else:
            return {"category": "organization",
                    "subcategory": _org_subcategory(text),
                    "confidence": 0.8}

    # Rule 5: charity (with personal-rescue exclusion)
    if _has_any(text, _CHARITY_KEYWORDS) and not _is_personal_rescue(text):
        charity_sub = "partner" if _has_any(text, _PARTNER_CHARITY_KEYWORDS) else "general"
        return {"category": "charity",
                "subcategory": charity_sub,
                "confidence": 0.85}

    # Rule 6: elected_official (requires Hawaii)
    if _has_any(text, _ELECTED_KEYWORDS) and is_hi:
        return {"category": "elected_official",
                "subcategory": "general",
                "confidence": 0.8}

    # Rule 7: media_event
    if _has_any(text, _MEDIA_KEYWORDS):
        return {"category": "media_event",
                "subcategory": _media_subcategory(text),
                "confidence": 0.75}

    # Rule 8: business_local (is_business flag OR strong business keywords)
    if (is_biz or _has_any(text, _STRONG_BUSINESS_KEYWORDS)) and is_hi:
        return {"category": "business_local",
                "subcategory": _business_subcategory(text),
                "confidence": 0.7}

    # Rule 9: business_national
    if (is_biz or _has_any(text, _STRONG_BUSINESS_KEYWORDS)) and not is_hi:
        return {"category": "business_national",
                "subcategory": _business_subcategory(text),
                "confidence": 0.7}

    # Rule 10: influencer (10k+ followers, not business)
    if follower_count is not None and follower_count >= 10000 and not is_biz:
        return {"category": "influencer",
                "subcategory": "general",
                "confidence": 0.7}

    # Rule 11: spam_bot (following > 10x followers AND posts < 5)
    if (follower_count is not None and following_count is not None
            and post_count is not None
            and following_count > 10 * follower_count
            and post_count < 5):
        return {"category": "spam_bot",
                "subcategory": "general",
                "confidence": 0.8}

    # Rule 12: personal_engaged (posts > 50, not business)
    if post_count is not None and post_count > 50 and not is_biz:
        return {"category": "personal_engaged",
                "subcategory": "general",
                "confidence": 0.6}

    # Rule 13: personal_passive (posts <= 50, not business)
    if post_count is not None and not is_biz:
        return {"category": "personal_passive",
                "subcategory": "general",
                "confidence": 0.5}

    # Rule 14: unknown (fallback)
    return {"category": "unknown",
            "subcategory": "general",
            "confidence": 0.3}
