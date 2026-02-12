"""Priority scoring algorithm for Instagram follower profiles."""
import re


def score(profile):
    """Score a profile and return {priority_score, priority_reason}.

    Score is clamped 0-100. priority_reason lists applied factors.
    """
    total = 0
    reasons = []

    category = profile.get("category", "")
    subcategory = profile.get("subcategory", "")
    is_hawaii = bool(profile.get("is_hawaii"))
    is_business = bool(profile.get("is_business"))
    is_verified = bool(profile.get("is_verified"))
    is_private = bool(profile.get("is_private"))
    follower_count = profile.get("follower_count") or 0
    post_count = profile.get("post_count") or 0
    bio = profile.get("bio") or ""
    website = profile.get("website") or ""

    # ── Base scores ────────────────────────────────────────────────
    if is_hawaii:
        total += 30
        reasons.append("hawaii(+30)")

    if category == "service_dog_aligned":
        total += 35
        reasons.append("service_dog(+35)")
    elif category == "bank_financial":
        total += 30
        reasons.append("bank(+30)")
    elif category == "corporate":
        total += 25
        reasons.append("corporate(+25)")
    elif category == "pet_industry" and subcategory == "breeder":
        total += 10
        reasons.append("pet_breeder(+10)")
    elif category == "pet_industry":
        total += 25
        reasons.append("pet(+25)")
    elif category == "organization":
        total += 25
        reasons.append("org(+25)")
    elif category == "elected_official":
        total += 25
        reasons.append("elected(+25)")
    elif category == "business_local":
        total += 20
        reasons.append("local_biz(+20)")
    elif category == "business_national":
        total += 10
        reasons.append("national_biz(+10)")
    elif category == "influencer":
        total += 20
        reasons.append("influencer(+20)")
    elif category == "media_event":
        total += 15
        reasons.append("media(+15)")

    if is_business:
        total += 20
        reasons.append("business(+20)")

    if is_verified:
        total += 10
        reasons.append("verified(+10)")

    # ── Reach score ────────────────────────────────────────────────
    if follower_count >= 50000:
        total += 20
        reasons.append("reach(+20)")
    elif follower_count >= 10000:
        total += 15
        reasons.append("reach(+15)")
    elif follower_count >= 5000:
        total += 10
        reasons.append("reach(+10)")
    elif follower_count >= 1000:
        total += 5
        reasons.append("reach(+5)")

    # ── Engagement indicators ──────────────────────────────────────
    if website:
        total += 5
        reasons.append("website(+5)")

    if post_count > 100:
        total += 5
        reasons.append("active_posting(+5)")

    bio_lower = bio.lower()

    # ── Bio alignment bonuses (no-stack hierarchy) ────────────────
    # These three bonuses are mutually exclusive to prevent double-counting:
    #   1. service_dog_aligned category already gets +35 — skip mission_aligned
    #   2. mission_aligned (+10) awarded if bio mentions service/therapy/disability
    #   3. dogs_pets_bio (+10) awarded only if neither #1 nor #2 applied,
    #      and category isn't pet_industry (which already gets its own +25)
    has_mission = (category != "service_dog_aligned"
                   and re.search(r'\b(service\s+dog|therapy\s+dog|assistance|disability)\b', bio_lower))
    if has_mission:
        total += 10
        reasons.append("mission_aligned(+10)")

    if (category not in ("pet_industry", "service_dog_aligned")
            and not has_mission
            and re.search(r'\b(dogs?|pets?|dog\s+mom|dog\s+dad|fur\s+parent|pup\s+parent)\b', bio_lower)):
        total += 10
        reasons.append("dogs_pets_bio(+10)")

    if re.search(r'\b(community|giving)\b', bio_lower):
        total += 5
        reasons.append("community_giving(+5)")

    # Veteran/military bonus — potential partnership signal
    if re.search(r'\b(veterans?|military|armed forces)\b', bio_lower):
        total += 5
        reasons.append("veteran(+5)")

    # Donor language bio bonus
    if re.search(r'\b(sponsor|partner(?:ship)?|support\s+local|give\s+back|philanthrop|donate|fundrais)\b', bio_lower):
        total += 5
        reasons.append("donor_language(+5)")

    # ── Penalties ──────────────────────────────────────────────────
    if category == "charity" and subcategory != "partner":
        total -= 50
        reasons.append("charity(-50)")

    if is_private:
        total -= 20
        reasons.append("private(-20)")

    if category == "spam_bot":
        total -= 100
        reasons.append("spam(-100)")

    if not bio:
        total -= 10
        reasons.append("no_bio(-10)")

    # ── Clamp ──────────────────────────────────────────────────────
    total = max(0, min(100, total))

    return {
        "priority_score": total,
        "priority_reason": ", ".join(reasons),
    }


def get_tier(priority_score):
    """Map a priority score to its tier string."""
    if priority_score >= 80:
        return "Tier 1 - High Priority"
    elif priority_score >= 60:
        return "Tier 2 - Medium Priority"
    elif priority_score >= 40:
        return "Tier 3 - Low Priority"
    else:
        return "Tier 4 - Skip"
