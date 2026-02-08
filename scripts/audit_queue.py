#!/usr/bin/env python3
"""Generate prioritized review queue for classification audit.

Creates a queue of accounts that need human review, prioritized by likelihood
of misclassification and impact on outreach strategy.

Usage:
    python3 scripts/audit_queue.py [--db data/followers.db] [--output-dir output] [--sample-size 20]
"""
import argparse
import sqlite3
import sys
import os
import json
import random
from typing import List, Dict, Any

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.classifier import classify


def _connect(db_path):
    """Open database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _get_all_classified(db_path) -> List[Dict[str, Any]]:
    """Get all classified followers from database."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM followers WHERE status = 'completed' AND category IS NOT NULL"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _suggest_category(profile: Dict) -> Dict[str, str]:
    """Suggest what category this profile should be in using current rules."""
    result = classify(profile)
    return {
        "category": result["category"],
        "subcategory": result["subcategory"],
        "confidence": result["confidence"]
    }


def _categorize_account(profile: Dict, suggested: Dict) -> List[str]:
    """Categorize account by priority queue priority."""
    current_category = profile.get("category")
    current_confidence = profile.get("confidence")
    suggested_category = suggested["category"]
    follower_count = profile.get("follower_count") or 0
    post_count = profile.get("post_count") or 0
    is_hawaii = profile.get("is_hawaii")

    priorities = []

    # Priority 1: High-value categories with low confidence or rule conflicts
    high_value_categories = ["service_dog_aligned", "bank_financial", "corporate", "pet_industry", "elected_official"]

    if current_category in high_value_categories:
        if current_confidence is not None and current_confidence < 0.8:
            priorities.append("P1_low_confidence_high_value")
        if current_category != suggested_category:
            priorities.append("P1_rule_conflict_high_value")

    # Priority 1: Charity with partner subcategory (shouldn't get -50 penalty)
    if current_category == "charity" and profile.get("subcategory") == "partner":
        priorities.append("P1_charity_partner")

    # Priority 2: Known problematic categories
    if current_category == "corporate":
        priorities.append("P2_corporate_keyword_review")
    if current_category in ["charity", "organization"] and current_confidence is not None and current_confidence < 0.85:
        priorities.append("P2_org_charity_low_confidence")
    if current_category == "pet_industry" and profile.get("subcategory") == "veterinary":
        priorities.append("P2_pet_industry_veterinary")

    # Priority 3: Boundary cases
    if 9000 <= follower_count <= 11000:  # Influencer boundary
        if current_category in ["personal_engaged", "personal_passive"]:
            priorities.append("P3_influencer_boundary")
        if current_category == "influencer":
            priorities.append("P3_influencer_boundary")

    if 45 <= post_count <= 55:  # Engaged boundary
        if current_category in ["personal_engaged", "personal_passive"]:
            priorities.append("P3_engagement_boundary")

    if is_hawaii and current_category in ["business_local", "business_national"]:
        if current_category != suggested_category:
            priorities.append("P3_hawaii_business_boundary")

    # Priority 4: Low confidence in non-personal categories
    if current_category not in ["personal_engaged", "personal_passive", "unknown"]:
        if current_confidence is not None and current_confidence < 0.6:
            priorities.append("P4_low_confidence")

    return priorities if priorities else ["P5_random_sample"]


def _build_queue_entry(profile: Dict, suggested: Dict, priorities: List[str]) -> Dict:
    """Build a complete audit queue entry with context."""
    current_category = profile.get("category")
    suggested_category = suggested["category"]
    current_conf = profile.get("confidence")
    suggested_conf = suggested["confidence"]

    # Determine if this is likely a misclassification
    is_likely_misclassified = current_category != suggested_category

    return {
        "handle": profile.get("handle"),
        "display_name": profile.get("display_name"),
        "bio": profile.get("bio"),
        "metrics": {
            "follower_count": profile.get("follower_count"),
            "following_count": profile.get("following_count"),
            "post_count": profile.get("post_count"),
            "is_private": profile.get("is_private"),
            "is_business": profile.get("is_business"),
            "is_verified": profile.get("is_verified"),
            "is_hawaii": profile.get("is_hawaii"),
            "website": profile.get("website"),
        },
        "classification": {
            "category": current_category,
            "subcategory": profile.get("subcategory"),
            "confidence": current_conf,
            "priority_score": profile.get("priority_score"),
            "priority_reason": profile.get("priority_reason"),
        },
        "audit_context": {
            "likely_misclassified": is_likely_misclassified,
            "suggested_category": suggested_category,
            "suggested_subcategory": suggested["subcategory"],
            "suggested_confidence": suggested_conf,
            "priority_queue": priorities,
            "primary_priority": priorities[0] if priorities else "P5_random_sample",
            "review_reason": _describe_review_reason(priorities, current_category, suggested_category),
        }
    }


def _describe_review_reason(priorities: List[str], current_cat: str, suggested_cat: str) -> str:
    """Create human-readable description of why this account needs review."""
    if not priorities or priorities[0] == "P5_random_sample":
        return "Random sample for accuracy baseline"

    primary = priorities[0]

    descriptions = {
        "P1_low_confidence_high_value": f"Low confidence on high-value category {current_cat}",
        "P1_rule_conflict_high_value": f"High-value category {current_cat} conflicts with suggested {suggested_cat}",
        "P1_charity_partner": "Charity with partner subcategory (may need special handling)",
        "P2_corporate_keyword_review": "Corporate classification needs review for keyword ambiguity",
        "P2_org_charity_low_confidence": f"Low confidence {current_cat} classification",
        "P2_pet_industry_veterinary": "Pet industry/veterinary subcategory - may be content creator",
        "P3_influencer_boundary": "Account near influencer threshold (10k followers)",
        "P3_engagement_boundary": "Account near engagement threshold (50 posts)",
        "P3_hawaii_business_boundary": "Hawaii business classification needs verification",
        "P4_low_confidence": f"Low confidence {current_cat} classification",
    }

    return descriptions.get(primary, "Needs review")


def generate_queue(db_path: str, sample_size: int = 20) -> Dict[str, Any]:
    """Generate prioritized queue for manual review."""
    followers = _get_all_classified(db_path)

    if not followers:
        print("No classified followers found.")
        return {"total": 0, "queue": []}

    print(f"Generating review queue for {len(followers)} classified followers...")

    # Build queue entries with suggestions and priorities
    queue_entries = []
    for profile in followers:
        suggested = _suggest_category(profile)
        priorities = _categorize_account(profile, suggested)
        entry = _build_queue_entry(profile, suggested, priorities)
        queue_entries.append(entry)

    # Sort by priority queue order
    priority_order = {
        "P1_low_confidence_high_value": (1, 0),
        "P1_rule_conflict_high_value": (1, 1),
        "P1_charity_partner": (1, 2),
        "P2_corporate_keyword_review": (2, 0),
        "P2_org_charity_low_confidence": (2, 1),
        "P2_pet_industry_veterinary": (2, 2),
        "P3_influencer_boundary": (3, 0),
        "P3_engagement_boundary": (3, 1),
        "P3_hawaii_business_boundary": (3, 2),
        "P4_low_confidence": (4, 0),
        "P5_random_sample": (5, 0),
    }

    def sort_key(entry):
        priorities = entry["audit_context"]["priority_queue"]
        primary = priorities[0] if priorities else "P5_random_sample"
        return priority_order.get(primary, (99, 0))

    queue_entries.sort(key=sort_key)

    # Extract priority 1-4 accounts
    priority_1 = [e for e in queue_entries if e["audit_context"]["primary_priority"].startswith("P1")]
    priority_2 = [e for e in queue_entries if e["audit_context"]["primary_priority"].startswith("P2")]
    priority_3 = [e for e in queue_entries if e["audit_context"]["primary_priority"].startswith("P3")]
    priority_4 = [e for e in queue_entries if e["audit_context"]["primary_priority"].startswith("P4")]

    # Add random sample for baseline accuracy
    priority_5_candidates = [e for e in queue_entries if e["audit_context"]["primary_priority"] == "P5_random_sample"]
    random.seed(42)  # Deterministic randomness
    priority_5_sample = random.sample(priority_5_candidates, min(sample_size, len(priority_5_candidates)))

    # Build final queue
    final_queue = priority_1 + priority_2 + priority_3 + priority_4 + priority_5_sample

    return {
        "total_classified": len(followers),
        "queue_size": len(final_queue),
        "priority_breakdown": {
            "P1_high_value": len(priority_1),
            "P2_known_issues": len(priority_2),
            "P3_boundary_cases": len(priority_3),
            "P4_low_confidence": len(priority_4),
            "P5_random_sample": len(priority_5_sample),
        },
        "queue": final_queue
    }


def print_summary(result: Dict) -> None:
    """Print human-readable summary."""
    print("\n" + "="*70)
    print("CLASSIFICATION AUDIT QUEUE - SUMMARY")
    print("="*70)
    print(f"\nTotal Classified: {result['total_classified']}")
    print(f"Review Queue Size: {result['queue_size']}")

    print("\nQueue Breakdown:")
    for priority, count in result["priority_breakdown"].items():
        print(f"  • {priority}: {count}")

    print("\nTop Accounts in Review Queue:")
    for i, entry in enumerate(result["queue"][:10], 1):
        handle = entry["handle"]
        category = entry["classification"]["category"]
        primary = entry["audit_context"]["primary_priority"]
        reason = entry["audit_context"]["review_reason"]
        print(f"  {i}. @{handle} ({category}) - {primary}: {reason}")

    if len(result["queue"]) > 10:
        print(f"  ... and {len(result['queue']) - 10} more accounts")


def export_csv(queue_data: Dict, output_path: str) -> None:
    """Export queue to CSV for spreadsheet review."""
    import csv

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            "Priority",
            "Handle",
            "Display Name",
            "Current Category",
            "Suggested Category",
            "Confidence",
            "Followers",
            "Posts",
            "Is Business",
            "Is Hawaii",
            "Review Reason",
            "Bio (first 100 chars)",
        ])

        # Data
        for entry in queue_data["queue"]:
            bio_preview = (entry.get("bio") or "")[:100]
            confidence = entry['classification']['confidence']
            confidence_str = f"{confidence:.2f}" if confidence is not None else "N/A"
            writer.writerow([
                entry["audit_context"]["primary_priority"],
                entry["handle"],
                entry["display_name"],
                entry["classification"]["category"],
                entry["audit_context"]["suggested_category"],
                confidence_str,
                entry["metrics"]["follower_count"],
                entry["metrics"]["post_count"],
                entry["metrics"]["is_business"],
                entry["metrics"]["is_hawaii"],
                entry["audit_context"]["review_reason"],
                bio_preview,
            ])


def main():
    parser = argparse.ArgumentParser(
        description="Generate prioritized audit queue for classification review"
    )
    parser.add_argument(
        "--db",
        default="data/followers.db",
        help="Path to followers database (default: data/followers.db)"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory to save queue files (default: output)"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=20,
        help="Size of random sample for P5 baseline accuracy (default: 20)"
    )

    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Generate queue
    queue_data = generate_queue(args.db, args.sample_size)

    # Print summary
    print_summary(queue_data)

    # Save JSON queue
    json_path = os.path.join(args.output_dir, "audit_queue.json")
    with open(json_path, "w") as f:
        json.dump(queue_data, f, indent=2)
    print(f"\n✓ Queue saved to {json_path}")

    # Export CSV
    csv_path = os.path.join(args.output_dir, "audit_queue.csv")
    export_csv(queue_data, csv_path)
    print(f"✓ Queue exported to {csv_path}")


if __name__ == "__main__":
    main()
