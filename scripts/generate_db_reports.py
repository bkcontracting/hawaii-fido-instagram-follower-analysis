#!/usr/bin/env python3
"""Generate outreach reports directly from the followers database.

Uses pre-calculated priority_score, category, and classification from the
database — no AI layer required. Follows the exclusion and entity-type
mapping from AI_IMPLEMENTATION_PLAN.md.

Output (new files, does not overwrite AI-generated reports):
  output/db_fundraising_recommendations.md
  output/db_fundraising_outreach.csv
  output/db_marketing_partners.csv
"""

import csv
import sqlite3
from pathlib import Path


# ── Exclusion rules (AI plan hard-exclusion logic) ───────────────────

_EXCLUDED_CATEGORIES = {
    "service_dog_aligned",  # EXCLUDE_competitor
    "charity",              # EXCLUDE_nonprofit
    "spam_bot",             # EXCLUDE_spam
    "personal_engaged",     # EXCLUDE_personal
    "personal_passive",     # EXCLUDE_personal
    "unknown",              # EXCLUDE_unknown
}

# Pet-industry subcategories treated as solo micro-businesses
_PET_MICRO_SUBCATEGORIES = {"trainer", "groomer", "breeder", "pet_care"}


def _is_excluded(row):
    """Return (excluded, reason) applying AI plan hard-exclusion rules."""
    cat = row["category"] or ""
    subcat = row["subcategory"] or ""

    if cat == "service_dog_aligned":
        return True, "EXCLUDE_competitor"
    if cat == "charity":
        return True, "EXCLUDE_nonprofit"
    if cat in ("personal_engaged", "personal_passive"):
        return True, "EXCLUDE_personal"
    if cat == "spam_bot":
        return True, "EXCLUDE_spam"
    if cat == "unknown":
        return True, "EXCLUDE_unknown"
    if cat == "pet_industry" and subcat in _PET_MICRO_SUBCATEGORIES:
        return True, "EXCLUDE_pet_micro"
    return False, ""


def _is_marketing_excluded(row):
    """Looser exclusions for marketing partners — keep pet businesses for
    cross-promotion, only drop competitors, spam, and personal accounts."""
    cat = row["category"] or ""
    if cat == "service_dog_aligned":
        return True, "EXCLUDE_competitor"
    if cat == "spam_bot":
        return True, "EXCLUDE_spam"
    if cat in ("personal_engaged", "personal_passive", "unknown"):
        return True, "EXCLUDE_personal"
    return False, ""


# ── Entity type mapping ──────────────────────────────────────────────

_CATEGORY_TO_ENTITY = {
    "corporate":         "corporation",
    "bank_financial":    "bank_financial",
    "organization":      "member_organization",
    "elected_official":  "government_official",
    "business_local":    "established_business",
    "business_national": "established_business",
    "media_event":       "media_event_org",
    "influencer":        "wealthy_individual",
    "pet_industry":      "established_business",
    "charity":           "nonprofit",
}


# ── Outreach type mapping ────────────────────────────────────────────

_CATEGORY_TO_OUTREACH = {
    "corporate":         "CORPORATE_SPONSORSHIP",
    "bank_financial":    "CORPORATE_SPONSORSHIP",
    "organization":      "MEMBER_PRESENTATION",
    "elected_official":  "DOOR_OPENER",
    "business_local":    "TABLE_PURCHASE",
    "business_national": "TABLE_PURCHASE",
    "media_event":       "DOOR_OPENER",
    "influencer":        "INDIVIDUAL_DONOR",
    "pet_industry":      "TABLE_PURCHASE",
}


def _suggested_ask(outreach_type, follower_count, is_verified):
    """Derive suggested ask range from outreach type and reach signals."""
    followers = follower_count or 0
    verified = bool(is_verified)

    if outreach_type == "CORPORATE_SPONSORSHIP":
        if verified or followers >= 50000:
            return "$10,000-$25,000"
        if followers >= 10000:
            return "$5,000-$15,000"
        return "$5,000-$10,000"

    if outreach_type == "TABLE_PURCHASE":
        if followers >= 5000:
            return "$2,500-$5,000"
        if followers >= 1000:
            return "$2,000-$3,500"
        return "$1,000-$3,000"

    if outreach_type == "MEMBER_PRESENTATION":
        return "$0 (access value)"

    if outreach_type == "INDIVIDUAL_DONOR":
        if followers >= 10000:
            return "$1,000-$2,000"
        if followers >= 1000:
            return "$500-$1,000"
        return "$200-$500"

    if outreach_type == "DOOR_OPENER":
        return "N/A (access value)"

    return "N/A"


# ── Database query ───────────────────────────────────────────────────

def _load_completed_profiles(db_path):
    """Load all completed, non-private profiles ordered by priority_score."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM followers "
        "WHERE status = 'completed' "
        "ORDER BY priority_score DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Enrichment ───────────────────────────────────────────────────────

def _enrich(profile):
    """Add entity_type, outreach_type, suggested_ask to a profile dict."""
    cat = profile["category"] or ""
    profile["entity_type"] = _CATEGORY_TO_ENTITY.get(cat, cat)
    profile["outreach_type"] = _CATEGORY_TO_OUTREACH.get(cat, "SKIP")
    profile["suggested_ask"] = _suggested_ask(
        profile["outreach_type"], profile["follower_count"], profile["is_verified"]
    )
    return profile


# ── Report writers ───────────────────────────────────────────────────

def _bio_text(bio):
    """Return full bio text, or N/A if empty."""
    if not bio:
        return "N/A"
    stripped = bio.strip()
    return stripped if stripped else "N/A"


def _write_markdown(top_fundraising, top_marketing, output_path):
    """Write comprehensive markdown report."""
    with open(output_path, "w") as f:
        f.write("# Hawaii Fi-Do Outreach Recommendations (Database-Derived)\n\n")
        f.write("> Rankings from pre-calculated database scoring: "
                "category, hawaii detection, reach, engagement signals\n")
        f.write("> Exclusions follow AI Implementation Plan: "
                "competitors, nonprofits, pet micro-businesses, personal accounts\n\n")

        # ── Top 25 Fundraising ──
        f.write("## Top 25 Fundraising Prospects\n\n")
        f.write("High-value prospects for direct fundraising outreach, "
                "ranked by database priority score.\n\n")

        for i, p in enumerate(top_fundraising, 1):
            name = p["display_name"] or p["handle"]
            f.write(f"### {i}. {name}\n\n")
            f.write(f"**Handle**: @{p['handle']}\n\n")

            f.write("#### Profile\n")
            fc = p["follower_count"]
            f.write(f"- **Followers**: {fc:,}\n"
                    if isinstance(fc, int) else "- **Followers**: N/A\n")
            foc = p["following_count"]
            f.write(f"- **Following**: {foc:,}\n"
                    if isinstance(foc, int) else "- **Following**: N/A\n")
            pc = p["post_count"]
            f.write(f"- **Posts**: {pc:,}\n"
                    if isinstance(pc, int) else "- **Posts**: N/A\n")
            f.write(f"- **Verified**: {'Yes' if p['is_verified'] else 'No'}\n")
            f.write(f"- **Business Account**: {'Yes' if p['is_business'] else 'No'}\n")
            if p.get("website"):
                f.write(f"- **Website**: {p['website']}\n")
            f.write(f"- **Bio**: {_bio_text(p.get('bio'))}\n\n")

            f.write("#### Outreach Analysis\n")
            f.write(f"- **Hawaii-Based**: {'Yes' if p['is_hawaii'] else 'No'}\n")
            f.write(f"- **Entity Type**: {p['entity_type']}\n")
            f.write(f"- **Category**: {p['category']}")
            if p.get("subcategory"):
                f.write(f" ({p['subcategory']})")
            f.write("\n")
            f.write(f"- **Priority Score**: {p['priority_score']}/100\n")
            f.write(f"- **Score Breakdown**: {p['priority_reason']}\n")
            f.write(f"- **Outreach Type**: {p['outreach_type']}\n")
            f.write(f"- **Suggested Ask**: {p['suggested_ask']}\n\n")
            f.write("---\n\n")

        # ── Top 15 Marketing Partners ──
        f.write("## Top 15 Marketing Campaign Partners\n\n")
        f.write("High-follower accounts for shared marketing campaigns "
                "and audience reach.\n\n")

        for i, p in enumerate(top_marketing, 1):
            name = p["display_name"] or p["handle"]
            f.write(f"### {i}. {name}\n\n")
            f.write(f"**Handle**: @{p['handle']}\n\n")

            f.write("#### Profile\n")
            fc = p["follower_count"]
            f.write(f"- **Followers**: {fc:,}\n"
                    if isinstance(fc, int) else "- **Followers**: N/A\n")
            foc = p["following_count"]
            f.write(f"- **Following**: {foc:,}\n"
                    if isinstance(foc, int) else "- **Following**: N/A\n")
            pc = p["post_count"]
            f.write(f"- **Posts**: {pc:,}\n"
                    if isinstance(pc, int) else "- **Posts**: N/A\n")
            f.write(f"- **Verified**: {'Yes' if p['is_verified'] else 'No'}\n")
            f.write(f"- **Business Account**: {'Yes' if p['is_business'] else 'No'}\n")
            if p.get("website"):
                f.write(f"- **Website**: {p['website']}\n")
            f.write(f"- **Bio**: {_bio_text(p.get('bio'))}\n\n")

            f.write("#### Outreach Analysis\n")
            f.write(f"- **Hawaii-Based**: {'Yes' if p['is_hawaii'] else 'No'}\n")
            f.write(f"- **Entity Type**: {p['entity_type']}\n")
            f.write(f"- **Priority Score**: {p['priority_score']}/100\n")
            f.write(f"- **Score Breakdown**: {p['priority_reason']}\n\n")
            f.write("---\n\n")


def _write_fundraising_csv(top_fundraising, output_path):
    """Write top 25 fundraising outreach CSV."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "Rank", "Handle", "Display Name", "Followers",
            "Entity Type", "Category", "Hawaii-Based",
            "Priority Score", "Score Breakdown",
            "Outreach Type", "Suggested Ask", "Website", "Bio",
        ])
        writer.writeheader()
        for i, p in enumerate(top_fundraising, 1):
            writer.writerow({
                "Rank": i,
                "Handle": p["handle"],
                "Display Name": p.get("display_name") or "",
                "Followers": p.get("follower_count") or "",
                "Entity Type": p["entity_type"],
                "Category": p["category"],
                "Hawaii-Based": "Yes" if p["is_hawaii"] else "No",
                "Priority Score": p["priority_score"],
                "Score Breakdown": p["priority_reason"],
                "Outreach Type": p["outreach_type"],
                "Suggested Ask": p["suggested_ask"],
                "Website": p.get("website") or "",
                "Bio": _bio_text(p.get("bio")),
            })


def _write_marketing_csv(top_marketing, output_path):
    """Write top 15 marketing partners CSV."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "Rank", "Handle", "Display Name", "Followers",
            "Entity Type", "Hawaii-Based", "Priority Score",
            "Score Breakdown", "Website", "Bio",
        ])
        writer.writeheader()
        for i, p in enumerate(top_marketing, 1):
            writer.writerow({
                "Rank": i,
                "Handle": p["handle"],
                "Display Name": p.get("display_name") or "",
                "Followers": p.get("follower_count") or "",
                "Entity Type": p["entity_type"],
                "Hawaii-Based": "Yes" if p["is_hawaii"] else "No",
                "Priority Score": p["priority_score"],
                "Score Breakdown": p["priority_reason"],
                "Website": p.get("website") or "",
                "Bio": _bio_text(p.get("bio")),
            })


# ── Main ─────────────────────────────────────────────────────────────

def generate_reports(db_path, md_output, csv_outreach, csv_marketing):
    """Generate all three reports from database rankings."""
    print("Loading profiles from database...")
    profiles = _load_completed_profiles(db_path)
    print(f"  Loaded {len(profiles)} completed profiles")

    # ── Fundraising: strict exclusions ──
    fundraising_pool = []
    excluded_counts = {}
    for p in profiles:
        excluded, reason = _is_excluded(p)
        if excluded:
            excluded_counts[reason] = excluded_counts.get(reason, 0) + 1
            continue
        fundraising_pool.append(_enrich(p))

    print(f"\nFundraising exclusions:")
    for reason, count in sorted(excluded_counts.items()):
        print(f"  {reason}: {count}")
    print(f"  Scoreable for fundraising: {len(fundraising_pool)}")

    top_fundraising = fundraising_pool[:25]

    # ── Marketing: looser exclusions (keep pet biz for cross-promo) ──
    marketing_pool = []
    for p in profiles:
        excluded, _ = _is_marketing_excluded(p)
        if excluded:
            continue
        marketing_pool.append(_enrich(dict(p)))  # fresh copy

    # Sort by follower count for marketing reach
    marketing_pool.sort(
        key=lambda p: p.get("follower_count") or 0, reverse=True
    )
    top_marketing = marketing_pool[:15]

    print(f"  Scoreable for marketing: {len(marketing_pool)}")

    if top_fundraising:
        print(f"\nTop {len(top_fundraising)} fundraising (score range: "
              f"{top_fundraising[-1]['priority_score']}"
              f"-{top_fundraising[0]['priority_score']})")
    else:
        print("\nNo scoreable fundraising prospects found.")

    if top_marketing:
        print(f"Top {len(top_marketing)} marketing (follower range: "
              f"{(top_marketing[-1].get('follower_count') or 0):,}"
              f"-{(top_marketing[0].get('follower_count') or 0):,})")
    else:
        print("No scoreable marketing partners found.")

    # ── Write reports ──
    print(f"\nWriting markdown report...")
    _write_markdown(top_fundraising, top_marketing, md_output)
    print(f"  Saved to {md_output}")

    print(f"Writing fundraising CSV...")
    _write_fundraising_csv(top_fundraising, csv_outreach)
    print(f"  Saved to {csv_outreach}")

    print(f"Writing marketing partners CSV...")
    _write_marketing_csv(top_marketing, csv_marketing)
    print(f"  Saved to {csv_marketing}")

    print(f"\nAll reports generated successfully!")


if __name__ == "__main__":
    base = Path(__file__).parent.parent
    db = base / "data" / "followers.db"

    if not db.exists():
        print(f"Error: {db} not found")
        exit(1)

    generate_reports(
        str(db),
        str(base / "output" / "db_fundraising_recommendations.md"),
        str(base / "output" / "db_fundraising_outreach.csv"),
        str(base / "output" / "db_marketing_partners.csv"),
    )
