#!/usr/bin/env python3
"""Apply human-reviewed corrections to the database.

Reads corrections from JSONL file and applies them to the database with
audit trail. Can run in dry-run mode to preview changes before applying.

Usage:
    python3 scripts/audit_apply.py [--corrections output/audit_corrections.jsonl] [--db data/followers.db] [--dry-run]
"""
import argparse
import sqlite3
import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Any

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scorer import score


def _connect(db_path):
    """Open database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _get_profile(db_path: str, handle: str) -> Dict[str, Any]:
    """Get profile from database."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM followers WHERE handle = ?",
            (handle,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _load_corrections(corrections_path: str) -> List[Dict]:
    """Load corrections from JSONL file."""
    corrections = []
    if not os.path.exists(corrections_path):
        print(f"Corrections file not found: {corrections_path}")
        return []

    with open(corrections_path, "r") as f:
        for line in f:
            if line.strip():
                corrections.append(json.loads(line))

    return corrections


def _apply_correction(db_path: str, correction: Dict, dry_run: bool = False) -> Dict[str, Any]:
    """Apply a single correction to database."""
    handle = correction.get("handle")
    decision = correction.get("decision")

    # Get current profile
    profile = _get_profile(db_path, handle)
    if not profile:
        return {
            "handle": handle,
            "status": "error",
            "message": "Profile not found in database"
        }

    result = {
        "handle": handle,
        "decision": decision,
        "old_category": profile.get("category"),
        "old_subcategory": profile.get("subcategory"),
        "old_score": profile.get("priority_score"),
    }

    if decision == "approved":
        result["status"] = "approved"
        result["message"] = "Classification approved"

    elif decision == "reclassified":
        new_category = correction.get("new_category")
        new_subcategory = correction.get("new_subcategory")

        # Update profile with new classification
        updated_profile = dict(profile)
        updated_profile["category"] = new_category
        updated_profile["subcategory"] = new_subcategory

        # Recalculate priority score
        new_score_data = score(updated_profile)
        new_score = new_score_data["priority_score"]

        result["new_category"] = new_category
        result["new_subcategory"] = new_subcategory
        result["new_score"] = new_score
        result["score_change"] = new_score - (profile.get("priority_score") or 0)

        if not dry_run:
            # Apply to database
            conn = _connect(db_path)
            try:
                conn.execute(
                    """UPDATE followers
                       SET category = ?,
                           subcategory = ?,
                           priority_score = ?,
                           audit_status = 'corrected',
                           audit_note = ?,
                           audited_at = ?
                       WHERE handle = ?""",
                    (new_category, new_subcategory, new_score,
                     correction.get("note"), datetime.now().isoformat(), handle)
                )
                conn.commit()
                result["status"] = "applied"
                result["message"] = f"Reclassified to {new_category}/{new_subcategory}"
            finally:
                conn.close()
        else:
            result["status"] = "ready_to_apply"
            result["message"] = f"Ready: Reclassify to {new_category}/{new_subcategory}"

    elif decision == "noted":
        note = correction.get("note")

        if not dry_run:
            # Apply note to database
            conn = _connect(db_path)
            try:
                conn.execute(
                    """UPDATE followers
                       SET audit_status = 'noted',
                           audit_note = ?,
                           audited_at = ?
                       WHERE handle = ?""",
                    (note, datetime.now().isoformat(), handle)
                )
                conn.commit()
                result["status"] = "applied"
                result["message"] = f"Note added: {note[:50]}..."
            finally:
                conn.close()
        else:
            result["status"] = "ready_to_apply"
            result["message"] = f"Ready: Add note"

    return result


def apply_corrections(db_path: str, corrections_path: str, dry_run: bool = False) -> Dict[str, Any]:
    """Apply all corrections to database."""
    corrections = _load_corrections(corrections_path)

    if not corrections:
        return {"total": 0, "applied": []}

    print(f"{'DRY RUN: ' if dry_run else ''}Processing {len(corrections)} corrections...")

    results = []
    stats = {
        "approved": 0,
        "reclassified": 0,
        "noted": 0,
        "error": 0,
    }

    for i, correction in enumerate(corrections, 1):
        result = _apply_correction(db_path, correction, dry_run)
        results.append(result)

        decision = correction.get("decision")
        if result["status"] in ["applied", "ready_to_apply"]:
            if decision == "reclassified":
                stats["reclassified"] += 1
            elif decision == "approved":
                stats["approved"] += 1
            elif decision == "noted":
                stats["noted"] += 1
        else:
            stats["error"] += 1

        # Progress indicator
        if i % 10 == 0:
            print(f"  {i}/{len(corrections)} processed...")

    return {
        "total": len(corrections),
        "dry_run": dry_run,
        "stats": stats,
        "applied": results
    }


def print_summary(result: Dict) -> None:
    """Print human-readable summary."""
    print("\n" + "=" * 70)
    print("AUDIT CORRECTIONS APPLICATION - SUMMARY")
    print("=" * 70)

    if result["dry_run"]:
        print("(DRY RUN - No changes applied to database)\n")

    print(f"Total corrections: {result['total']}")
    print(f"Successfully applied: {result['stats']['approved'] + result['stats']['reclassified'] + result['stats']['noted']}")
    print(f"Errors: {result['stats']['error']}\n")

    print(f"Breakdown:")
    print(f"  • Approved: {result['stats']['approved']}")
    print(f"  • Reclassified: {result['stats']['reclassified']}")
    print(f"  • Noted: {result['stats']['noted']}")

    # Show sample of reclassifications
    reclassified = [r for r in result["applied"] if r.get("decision") == "reclassified" and r.get("new_category")]
    if reclassified:
        print(f"\nTop Reclassifications:")
        for i, r in enumerate(reclassified[:5], 1):
            old = f"{r['old_category']}/{r['old_subcategory']}"
            new = f"{r['new_category']}/{r['new_subcategory']}"
            score_change = r.get("score_change", 0)
            score_symbol = "↑" if score_change > 0 else "↓" if score_change < 0 else "="
            print(f"  {i}. @{r['handle']}: {old} → {new} (score {score_symbol}{abs(score_change):+.0f})")

    # Show errors if any
    errors = [r for r in result["applied"] if r["status"] == "error"]
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for r in errors[:5]:
            print(f"  • @{r['handle']}: {r['message']}")


def main():
    parser = argparse.ArgumentParser(
        description="Apply corrections to database"
    )
    parser.add_argument(
        "--corrections",
        default="output/audit_corrections.jsonl",
        help="Path to corrections JSONL file (default: output/audit_corrections.jsonl)"
    )
    parser.add_argument(
        "--db",
        default="data/followers.db",
        help="Path to followers database (default: data/followers.db)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying to database"
    )

    args = parser.parse_args()

    # Run application
    result = apply_corrections(args.db, args.corrections, args.dry_run)

    # Print summary
    print_summary(result)

    if args.dry_run:
        print(f"\nTo apply changes, run:")
        print(f"  python3 scripts/audit_apply.py --corrections {args.corrections} --db {args.db}")
    else:
        # Save application report
        os.makedirs("output", exist_ok=True)
        report_path = os.path.join("output", "audit_apply_report.json")
        with open(report_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n✓ Application report saved to {report_path}")


if __name__ == "__main__":
    main()
