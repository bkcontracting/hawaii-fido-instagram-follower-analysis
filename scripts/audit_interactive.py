#!/usr/bin/env python3
"""Interactive terminal UI for classifying auditor to review and correct classifications.

Provides an interactive interface to:
- Review flagged accounts with full context
- Approve or reclassify accounts
- Add notes to corrections
- Save/resume audit sessions
- Export corrections to JSONL format

Usage:
    python3 scripts/audit_interactive.py [--queue output/audit_queue.json] [--output-dir output] [--resume audit_corrections.jsonl]
"""
import argparse
import json
import sys
import os
from datetime import datetime
from typing import List, Dict, Any, Optional


def _load_queue(queue_path: str) -> List[Dict]:
    """Load audit queue from JSON file."""
    with open(queue_path, "r") as f:
        data = json.load(f)
    return data.get("queue", [])


def _load_corrections(corrections_path: str) -> Dict[str, Dict]:
    """Load existing corrections from JSONL file."""
    corrections = {}
    if os.path.exists(corrections_path):
        with open(corrections_path, "r") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    corrections[entry["handle"]] = entry
    return corrections


def _save_correction(corrections_path: str, handle: str, correction: Dict) -> None:
    """Append a correction to JSONL file."""
    with open(corrections_path, "a") as f:
        f.write(json.dumps(correction) + "\n")


def _format_profile_display(entry: Dict) -> str:
    """Format profile information for display."""
    lines = []
    lines.append("")
    lines.append("┌" + "─" * 68 + "┐")

    # Handle and display name
    handle = entry["handle"]
    display_name = entry["display_name"] or "(no display name)"
    lines.append(f"│ @{handle:<65} │")
    lines.append(f"│ Display Name: {display_name:<50} │")

    # Bio preview
    bio = entry.get("bio") or "(no bio)"
    bio_lines = bio.split("\n")
    for bio_line in bio_lines[:2]:
        preview = bio_line[:66]
        lines.append(f"│ {preview:<67} │")

    lines.append("│" + " " * 68 + "│")

    # Metrics
    metrics = entry["metrics"]
    followers = metrics.get("follower_count") or 0
    posts = metrics.get("post_count") or 0
    is_business = metrics.get("is_business")
    is_hawaii = metrics.get("is_hawaii")
    is_private = metrics.get("is_private")

    business_str = "Business" if is_business else "Personal"
    hawaii_str = "Hawaii" if is_hawaii else "Not Hawaii"
    private_str = "Private" if is_private else "Public"

    metrics_str = f"{followers:,} followers | {posts} posts | {business_str} | {hawaii_str} | {private_str}"
    lines.append(f"│ {metrics_str:<67} │")

    lines.append("│" + " " * 68 + "│")

    # Current classification
    classification = entry["classification"]
    current_cat = classification["category"]
    current_subcat = classification.get("subcategory", "general")
    current_conf = classification.get("confidence", 0)
    current_score = classification.get("priority_score", 0)

    lines.append(f"│ CURRENT CLASSIFICATION:                                               │")
    lines.append(f"│   Category: {current_cat:<50} │")
    lines.append(f"│   Subcategory: {current_subcat:<45} │")
    lines.append(f"│   Confidence: {current_conf:.2f} | Score: {current_score} (Tier TBD)│")

    lines.append("│" + " " * 68 + "│")

    # Audit context and suggested change
    audit_ctx = entry["audit_context"]
    suggested_cat = audit_ctx.get("suggested_category")
    suggested_subcat = audit_ctx.get("suggested_subcategory")
    likely_misclassified = audit_ctx.get("likely_misclassified")

    review_reason = audit_ctx.get("review_reason", "Unknown reason")
    lines.append(f"│ REVIEW REASON: {review_reason:<51} │")

    if likely_misclassified and suggested_cat != current_cat:
        lines.append(f"│ LIKELY MISCLASSIFIED - Suggested: {suggested_cat:<30} │")

    lines.append("│" + " " * 68 + "│")

    # Matched rules / conflicts
    priority_queue = audit_ctx.get("priority_queue", [])
    if priority_queue:
        primary = priority_queue[0]
        lines.append(f"│ Priority Queue: {primary:<51} │")

    lines.append("└" + "─" * 68 + "┘")
    lines.append("")

    return "\n".join(lines)


def _display_categories() -> None:
    """Display available categories for user selection."""
    categories = [
        ("1", "service_dog_aligned", "Service dog org / therapy"),
        ("2", "bank_financial", "Bank or financial"),
        ("3", "corporate", "Large corporation"),
        ("4", "pet_industry", "Pet service/business"),
        ("5", "organization", "Non-profit org / club"),
        ("6", "charity", "Rescue / charity"),
        ("7", "elected_official", "Government official"),
        ("8", "media_event", "Media / event / photographer"),
        ("9", "business_local", "Local Hawaii business"),
        ("10", "business_national", "National business"),
        ("11", "influencer", "Influencer (10k+)"),
        ("12", "spam_bot", "Spam/bot account"),
        ("13", "personal_engaged", "Personal (50+ posts)"),
        ("14", "personal_passive", "Personal (<50 posts)"),
        ("15", "unknown", "Unknown/unclassified"),
    ]

    print("\nSelect category:")
    for num, cat, desc in categories:
        print(f"  {num:>2}. {cat:<25} - {desc}")


def _get_subcategories(category: str) -> List[tuple]:
    """Get available subcategories for a category."""
    subcategory_map = {
        "service_dog_aligned": [
            ("1", "service", "Service dog"),
            ("2", "therapy", "Therapy dog"),
            ("3", "guide", "Guide dog"),
            ("4", "emotional_support", "Emotional support"),
            ("5", "general", "General"),
        ],
        "pet_industry": [
            ("1", "veterinary", "Veterinarian"),
            ("2", "trainer", "Dog trainer"),
            ("3", "breeder", "Breeder"),
            ("4", "pet_store", "Pet store"),
            ("5", "groomer", "Groomer"),
            ("6", "pet_food", "Pet food"),
            ("7", "boarding", "Boarding/daycare"),
            ("8", "pet_care", "Pet sitting/walking"),
            ("9", "rehabilitation", "Rehabilitation"),
            ("10", "general", "General"),
        ],
        "organization": [
            ("1", "government", "Government"),
            ("2", "church", "Church"),
            ("3", "school", "School"),
            ("4", "club", "Club"),
            ("5", "community_group", "Community group"),
        ],
        "charity": [
            ("1", "partner", "Partner (disability/animal welfare)"),
            ("2", "general", "General charity"),
        ],
        "media_event": [
            ("1", "photographer", "Photographer"),
            ("2", "news", "News/media"),
            ("3", "event", "Event/tournament"),
            ("4", "general", "General"),
        ],
        "business_local": [
            ("1", "restaurant", "Restaurant/cafe"),
            ("2", "hospitality", "Hotel/resort"),
            ("3", "real_estate", "Real estate"),
            ("4", "legal", "Legal"),
            ("5", "retail", "Retail"),
            ("6", "service", "Service"),
            ("7", "general", "General"),
        ],
        "business_national": [
            ("1", "restaurant", "Restaurant/cafe"),
            ("2", "hospitality", "Hotel/resort"),
            ("3", "real_estate", "Real estate"),
            ("4", "legal", "Legal"),
            ("5", "retail", "Retail"),
            ("6", "service", "Service"),
            ("7", "general", "General"),
        ],
    }

    return subcategory_map.get(category, [("1", "general", "General")])


def _get_user_choice(prompt: str, valid_options: List[str]) -> Optional[str]:
    """Get user choice with validation."""
    while True:
        try:
            choice = input(prompt).strip().lower()
            if choice in valid_options:
                return choice
            print(f"Invalid choice. Please enter one of: {', '.join(valid_options)}")
        except KeyboardInterrupt:
            return None
        except EOFError:
            return None


def _get_category_choice() -> Optional[str]:
    """Guide user through category selection."""
    _display_categories()
    choice = _get_user_choice("Enter category number [1-15]: ", [str(i) for i in range(1, 16)])

    if choice is None:
        return None

    categories = [
        "service_dog_aligned", "bank_financial", "corporate", "pet_industry",
        "organization", "charity", "elected_official", "media_event",
        "business_local", "business_national", "influencer", "spam_bot",
        "personal_engaged", "personal_passive", "unknown"
    ]
    return categories[int(choice) - 1]


def _get_subcategory_choice(category: str) -> Optional[str]:
    """Guide user through subcategory selection."""
    subcategories = _get_subcategories(category)

    if len(subcategories) == 1:
        return subcategories[0][1]  # Return default

    print(f"\nSelect subcategory for {category}:")
    for num, subcat, desc in subcategories:
        print(f"  {num}. {desc:<40} ({subcat})")

    valid = [str(i) for i in range(1, len(subcategories) + 1)]
    choice = _get_user_choice(f"Enter subcategory number [1-{len(subcategories)}]: ", valid)

    if choice is None:
        return None

    return subcategories[int(choice) - 1][1]


def run_interactive_audit(queue_path: str, corrections_path: str) -> None:
    """Run the interactive audit tool."""
    print("\n" + "=" * 70)
    print("INTERACTIVE CLASSIFICATION AUDIT TOOL")
    print("=" * 70)

    # Load queue
    try:
        queue = _load_queue(queue_path)
    except FileNotFoundError:
        print(f"Error: Queue file not found: {queue_path}")
        print(f"Generate it first with: python3 scripts/audit_queue.py")
        return

    if not queue:
        print("No accounts in queue.")
        return

    # Load existing corrections if resuming
    corrections = _load_corrections(corrections_path)
    start_index = len(corrections)

    print(f"\nLoaded {len(queue)} accounts to review")
    print(f"Resuming from account {start_index + 1}\n")

    # Process each account
    for i, entry in enumerate(queue[start_index:], start=start_index + 1):
        handle = entry["handle"]

        # Skip if already corrected
        if handle in corrections:
            print(f"[{i}/{len(queue)}] ✓ @{handle} - Already reviewed, skipping")
            continue

        # Display profile
        print(f"[{i}/{len(queue)}] @{handle}")
        print(_format_profile_display(entry))

        # Get user action
        while True:
            action = _get_user_choice(
                "Action [a=approve, r=reclassify, s=skip, n=note, q=quit]: ",
                ["a", "r", "s", "n", "q"]
            )

            if action is None:
                print("\nInterrupted. Progress saved to " + corrections_path)
                return

            if action == "q":
                print(f"\nStopping. Reviewed {i} accounts. Progress saved to {corrections_path}")
                return

            elif action == "a":
                # Approve current classification
                correction = {
                    "handle": handle,
                    "decision": "approved",
                    "old_category": entry["classification"]["category"],
                    "old_subcategory": entry["classification"].get("subcategory"),
                    "timestamp": datetime.now().isoformat(),
                    "auditor": "human",
                }
                _save_correction(corrections_path, handle, correction)
                print("✓ Classification approved\n")
                break

            elif action == "r":
                # Reclassify
                new_category = _get_category_choice()
                if new_category is None:
                    print("Cancelled.")
                    continue

                new_subcategory = _get_subcategory_choice(new_category)
                if new_subcategory is None:
                    print("Cancelled.")
                    continue

                # Get optional note
                print("\nAdd note (optional, press Enter to skip):")
                note = input("> ").strip() or None

                # Save correction
                correction = {
                    "handle": handle,
                    "decision": "reclassified",
                    "old_category": entry["classification"]["category"],
                    "old_subcategory": entry["classification"].get("subcategory"),
                    "new_category": new_category,
                    "new_subcategory": new_subcategory,
                    "note": note,
                    "timestamp": datetime.now().isoformat(),
                    "auditor": "human",
                }
                _save_correction(corrections_path, handle, correction)
                print(f"✓ Reclassified to {new_category}/{new_subcategory}\n")
                break

            elif action == "s":
                # Skip
                print("Skipped\n")
                break

            elif action == "n":
                # Add note without changing category
                print("\nAdd note:")
                note = input("> ").strip()

                correction = {
                    "handle": handle,
                    "decision": "noted",
                    "category": entry["classification"]["category"],
                    "note": note,
                    "timestamp": datetime.now().isoformat(),
                    "auditor": "human",
                }
                _save_correction(corrections_path, handle, correction)
                print(f"✓ Note saved\n")
                break

    print(f"\nAudit complete! Reviewed all {len(queue)} accounts.")
    print(f"Corrections saved to {corrections_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Interactive audit tool for classification review"
    )
    parser.add_argument(
        "--queue",
        default="output/audit_queue.json",
        help="Path to audit queue JSON file (default: output/audit_queue.json)"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory for correction files (default: output)"
    )
    parser.add_argument(
        "--resume",
        default=None,
        help="Resume from existing corrections file (default: create new)"
    )

    args = parser.parse_args()

    # Determine corrections file path
    if args.resume:
        corrections_path = args.resume
    else:
        os.makedirs(args.output_dir, exist_ok=True)
        corrections_path = os.path.join(args.output_dir, "audit_corrections.jsonl")

    # Run interactive audit
    run_interactive_audit(args.queue, corrections_path)


if __name__ == "__main__":
    main()
