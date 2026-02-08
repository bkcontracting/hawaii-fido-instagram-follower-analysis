#!/usr/bin/env python3
"""Analyze classifications to detect suspicious patterns and potential misclassifications.

Uses heuristic detection without human review to identify accounts that likely need
correction, enabling efficient prioritization for the interactive audit tool.

Usage:
    python3 scripts/audit_analyze.py [--db data/followers.db] [--output-dir output]
"""
import argparse
import sqlite3
import sys
import os
import json
import re
from typing import List, Dict, Any
from collections import defaultdict

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


def _rule_conflict_detection(profile: Dict) -> List[Dict]:
    """Detect when lower-priority rule matched but higher-priority keywords present."""
    issues = []
    text = f"{profile.get('handle', '')} {profile.get('display_name', '')} {profile.get('bio', '')}".lower()

    current_category = profile.get("category")
    confidence = profile.get("confidence")

    # Re-run classifier to see what it would assign
    test_result = classify(profile)
    suggested_category = test_result["category"]

    # If categories differ, rule conflict detected
    if current_category != suggested_category:
        issues.append({
            "type": "rule_conflict",
            "severity": "high",
            "description": f"Current rule matched {current_category}, but classifier now suggests {suggested_category}",
            "current_category": current_category,
            "suggested_category": suggested_category,
            "current_confidence": confidence,
            "suggested_confidence": test_result["confidence"]
        })

    return issues


def _confidence_mismatch_detection(profile: Dict) -> List[Dict]:
    """Detect low confidence on high-value categories."""
    issues = []
    category = profile.get("category")
    confidence = profile.get("confidence")

    # High-value categories should have high confidence
    high_value_categories = {
        "service_dog_aligned": 0.90,  # Target 0.95 - allow 0.90 minimum
        "bank_financial": 0.85,        # Target 0.90
        "corporate": 0.75,              # Target 0.80
        "pet_industry": 0.80,           # Target 0.85
    }

    if category in high_value_categories:
        min_confidence = high_value_categories[category]
        if confidence is not None and confidence < min_confidence:
            issues.append({
                "type": "confidence_mismatch",
                "severity": "medium",
                "description": f"{category} should have confidence >= {min_confidence}, has {confidence}",
                "category": category,
                "current_confidence": confidence,
                "expected_minimum": min_confidence
            })

    # Low-value categories with high confidence suggest overfitting
    ambiguous_categories = ["personal_engaged", "personal_passive"]
    if category in ambiguous_categories and confidence is not None and confidence > 0.65:
        issues.append({
            "type": "confidence_overfit",
            "severity": "low",
            "description": f"{category} is ambiguous, confidence {confidence} seems high",
            "category": category,
            "current_confidence": confidence
        })

    return issues


def _keyword_analysis(profile: Dict) -> List[Dict]:
    """Detect when keywords from multiple categories appear in bio."""
    issues = []

    # Service dog keywords
    service_dog_keywords = [
        "service dog", "therapy dog", "assistance dog", "guide dog",
        "service animal", "working dog", "canine assisted",
        "animal assisted therapy", "ptsd dog", "seizure dog",
    ]

    # Pet industry keywords
    pet_keywords = [
        "veterinar", "vet clinic", "pet ", "dog trainer", "dog training",
        "groomer", "grooming", "kennel", "animal hospital", "canine", "paws",
        "pet food", "pet supply", "dog gym", "k9", "daycare", "boarding",
        "pet sitting", "dog walking", "obedience"
    ]

    # Corporate keywords
    corporate_keywords = [
        "electric", "utility", "airline", "telecom", "insurance",
        "corporation", "corporate", "headquarters", "global",
    ]

    # Business keywords
    business_keywords = [
        "brewery", "brewing", "restaurant", "cafe", "bakery", "catering",
        "hotel", "resort", "salon", "barbershop", "real estate", "realty",
        "realtor", "law firm", "mortgage",
    ]

    text = f"{profile.get('handle', '')} {profile.get('display_name', '')} {profile.get('bio', '')}".lower()
    current_category = profile.get("category")

    # Check for cross-contamination
    service_dog_match = any(kw in text for kw in service_dog_keywords)
    pet_match = any(kw in text for kw in pet_keywords)
    corporate_match = any(kw in text for kw in corporate_keywords)
    business_match = any(kw in text for kw in business_keywords)

    keyword_count = sum([service_dog_match, pet_match, corporate_match, business_match])

    if keyword_count > 1 and current_category not in ["personal_engaged", "personal_passive"]:
        keywords_found = []
        if service_dog_match:
            keywords_found.append("service_dog")
        if pet_match:
            keywords_found.append("pet_industry")
        if corporate_match:
            keywords_found.append("corporate")
        if business_match:
            keywords_found.append("business")

        issues.append({
            "type": "keyword_cross_contamination",
            "severity": "medium" if keyword_count == 2 else "high",
            "description": f"Bio contains keywords from multiple categories: {', '.join(keywords_found)}",
            "keywords_found": keywords_found,
            "current_category": current_category
        })

    return issues


def _priority_score_anomalies(profile: Dict) -> List[Dict]:
    """Detect misalignment between category and priority score."""
    issues = []

    category = profile.get("category")
    score = profile.get("priority_score")
    is_hawaii = profile.get("is_hawaii")
    follower_count = profile.get("follower_count", 0)

    # High-value category should have high priority score
    if category in ["service_dog_aligned", "bank_financial"] and score is not None and score < 60:
        issues.append({
            "type": "priority_score_anomaly",
            "severity": "high",
            "description": f"High-value category {category} has low score {score}",
            "category": category,
            "priority_score": score,
            "expected_minimum": 60
        })

    # Hawaii location anomalies
    if not is_hawaii and follower_count and "808" in profile.get("bio", ""):
        issues.append({
            "type": "hawaii_detection_anomaly",
            "severity": "medium",
            "description": "Bio contains 808 area code but is_hawaii=False",
            "is_hawaii": is_hawaii,
            "signal": "808 area code in bio"
        })

    return issues


def _business_flag_inconsistency(profile: Dict) -> List[Dict]:
    """Detect misalignment between is_business flag and content."""
    issues = []

    is_business = profile.get("is_business")
    bio = profile.get("bio", "").lower()

    commercial_signals = ["llc", "inc.", "inc", "co.", "co", "shop", "store", "service", "business"]
    has_commercial_signal = any(signal in bio for signal in commercial_signals)

    # is_business=False but strong commercial signals
    if not is_business and has_commercial_signal:
        issues.append({
            "type": "business_flag_inconsistency",
            "severity": "medium",
            "description": "is_business=False but bio contains commercial signals",
            "is_business": is_business,
            "commercial_signals_found": [s for s in commercial_signals if s in bio]
        })

    return issues


def _engagement_boundary_detection(profile: Dict) -> List[Dict]:
    """Detect accounts near category boundaries."""
    issues = []

    follower_count = profile.get("follower_count")
    post_count = profile.get("post_count")
    category = profile.get("category")

    # Influencer boundary (10,000 followers)
    if follower_count and 9000 <= follower_count <= 11000 and category in ["personal_engaged", "personal_passive"]:
        issues.append({
            "type": "engagement_boundary",
            "severity": "low",
            "description": f"Near influencer threshold: {follower_count} followers",
            "follower_count": follower_count,
            "boundary": "influencer (10k)",
            "category": category
        })

    # Engagement boundary (50 posts)
    if post_count and 45 <= post_count <= 55 and category in ["personal_engaged", "personal_passive"]:
        issues.append({
            "type": "engagement_boundary",
            "severity": "low",
            "description": f"Near engagement threshold: {post_count} posts",
            "post_count": post_count,
            "boundary": "personal_engaged (50)",
            "category": category
        })

    return issues


def analyze_all(db_path: str) -> Dict[str, Any]:
    """Analyze all classified followers for suspicious patterns."""
    followers = _get_all_classified(db_path)

    if not followers:
        print("No classified followers found.")
        return {"total": 0, "flagged": []}

    print(f"Analyzing {len(followers)} classified followers...")

    all_issues = []
    flagged_counts = defaultdict(int)
    severity_counts = defaultdict(int)

    for profile in followers:
        profile_issues = []

        # Run all detection heuristics
        profile_issues.extend(_rule_conflict_detection(profile))
        profile_issues.extend(_confidence_mismatch_detection(profile))
        profile_issues.extend(_keyword_analysis(profile))
        profile_issues.extend(_priority_score_anomalies(profile))
        profile_issues.extend(_business_flag_inconsistency(profile))
        profile_issues.extend(_engagement_boundary_detection(profile))

        if profile_issues:
            # Aggregate issues for this profile
            flagged_entry = {
                "handle": profile.get("handle"),
                "display_name": profile.get("display_name"),
                "category": profile.get("category"),
                "confidence": profile.get("confidence"),
                "priority_score": profile.get("priority_score"),
                "issues": profile_issues,
                "max_severity": max(i["severity"] for i in profile_issues)
            }

            all_issues.append(flagged_entry)

            for issue in profile_issues:
                flagged_counts[issue["type"]] += 1
                severity_counts[issue["severity"]] += 1

    # Sort by severity (high > medium > low) then by type
    severity_order = {"high": 0, "medium": 1, "low": 2}
    all_issues.sort(key=lambda x: (severity_order.get(x["max_severity"], 3), x["max_severity"]))

    return {
        "total_classified": len(followers),
        "total_flagged": len(all_issues),
        "flagged_percentage": f"{len(all_issues) / len(followers) * 100:.1f}%",
        "flagged_by_type": dict(flagged_counts),
        "flagged_by_severity": dict(severity_counts),
        "flagged": all_issues
    }


def print_summary(analysis: Dict) -> None:
    """Print human-readable summary."""
    print("\n" + "="*70)
    print("CLASSIFICATION AUDIT ANALYSIS - SUMMARY")
    print("="*70)
    print(f"\nTotal Classified: {analysis['total_classified']}")
    print(f"Total Flagged: {analysis['total_flagged']} ({analysis['flagged_percentage']})")

    print("\nFlagged by Issue Type:")
    for issue_type, count in sorted(analysis["flagged_by_type"].items(), key=lambda x: -x[1]):
        print(f"  • {issue_type}: {count}")

    print("\nFlagged by Severity:")
    for severity in ["high", "medium", "low"]:
        count = analysis["flagged_by_severity"].get(severity, 0)
        print(f"  • {severity.upper()}: {count}")

    print("\nTop Flagged Accounts (HIGH SEVERITY):")
    high_severity = [f for f in analysis["flagged"] if f["max_severity"] == "high"]
    for i, flagged in enumerate(high_severity[:10], 1):
        print(f"  {i}. @{flagged['handle']} ({flagged['category']}) - {len(flagged['issues'])} issues")

    if len(high_severity) > 10:
        print(f"  ... and {len(high_severity) - 10} more")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze classifications for suspicious patterns"
    )
    parser.add_argument(
        "--db",
        default="data/followers.db",
        help="Path to followers database (default: data/followers.db)"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory to save analysis results (default: output)"
    )

    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Run analysis
    analysis = analyze_all(args.db)

    # Print summary
    print_summary(analysis)

    # Save JSON report
    json_path = os.path.join(args.output_dir, "audit_analysis.json")
    with open(json_path, "w") as f:
        json.dump(analysis, f, indent=2)
    print(f"\n✓ Analysis saved to {json_path}")


if __name__ == "__main__":
    main()
