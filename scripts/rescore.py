#!/usr/bin/env python3
"""Re-classify and re-score all enriched followers using updated rules.

Reads completed followers from the database, applies the current classifier
and scorer, writes updated values back, and prints a before/after report.

Usage:
    python3 scripts/rescore.py [--db data/followers.db] [--dry-run]
"""
import argparse
import sqlite3
import sys
import os

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.classifier import classify
from src.scorer import score, get_tier


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def rescore(db_path, dry_run=False):
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM followers WHERE status = 'completed'"
        ).fetchall()

        if not rows:
            print("No completed followers found.")
            return

        changes = []
        for row in rows:
            profile = dict(row)
            old_cat = profile.get("category")
            old_score = profile.get("priority_score")

            # Re-classify
            result = classify(profile)
            new_cat = result["category"]
            new_subcat = result["subcategory"]
            new_conf = result["confidence"]

            # Re-score with new category and subcategory
            score_profile = dict(profile)
            score_profile["category"] = new_cat
            score_profile["subcategory"] = new_subcat
            score_result = score(score_profile)
            new_score = score_result["priority_score"]
            new_reason = score_result["priority_reason"]

            cat_changed = old_cat != new_cat
            score_delta = (new_score - old_score) if old_score is not None else None
            big_score_change = score_delta is not None and abs(score_delta) > 10

            if cat_changed or big_score_change:
                old_tier = get_tier(old_score) if old_score is not None else "N/A"
                new_tier = get_tier(new_score)
                changes.append({
                    "handle": profile["handle"],
                    "old_category": old_cat,
                    "new_category": new_cat,
                    "old_score": old_score,
                    "new_score": new_score,
                    "score_delta": score_delta,
                    "old_tier": old_tier,
                    "new_tier": new_tier,
                })

            if not dry_run:
                conn.execute(
                    """UPDATE followers
                       SET category = ?, subcategory = ?, confidence = ?,
                           priority_score = ?, priority_reason = ?
                       WHERE handle = ?""",
                    (new_cat, new_subcat, new_conf, new_score, new_reason,
                     profile["handle"]),
                )

        if not dry_run:
            conn.commit()
    finally:
        conn.close()

    # Print report
    print(f"\nRescored {len(rows)} followers.")
    print(f"Accounts with changes: {len(changes)}\n")

    if not changes:
        print("No significant changes detected.")
        return

    # Category changes
    cat_changes = [c for c in changes if c["old_category"] != c["new_category"]]
    if cat_changes:
        print("=== Category Changes ===")
        print(f"{'Handle':<30} {'Old Category':<22} {'New Category':<22}")
        print("-" * 74)
        for c in cat_changes:
            print(f"{c['handle']:<30} {c['old_category'] or 'N/A':<22} {c['new_category']:<22}")
        print()

    # Score changes > 10
    score_changes = [c for c in changes
                     if c["score_delta"] is not None and abs(c["score_delta"]) > 10]
    if score_changes:
        print("=== Score Changes > 10 Points ===")
        print(f"{'Handle':<30} {'Old':<6} {'New':<6} {'Delta':<8} {'Tier Change'}")
        print("-" * 80)
        for c in sorted(score_changes, key=lambda x: -(x["score_delta"] or 0)):
            delta_str = f"+{c['score_delta']}" if c["score_delta"] > 0 else str(c["score_delta"])
            tier_str = f"{c['old_tier']} -> {c['new_tier']}" if c["old_tier"] != c["new_tier"] else ""
            print(f"{c['handle']:<30} {c['old_score'] or 0:<6} {c['new_score']:<6} {delta_str:<8} {tier_str}")
        print()

    # New Tier 1/2 accounts
    tier_upgrades = [c for c in changes
                     if c["new_score"] >= 60 and (c["old_score"] is None or c["old_score"] < 60)]
    if tier_upgrades:
        print("=== New Tier 1/2 Accounts ===")
        for c in tier_upgrades:
            print(f"  {c['handle']}: {c['old_score'] or 0} -> {c['new_score']} ({c['new_tier']})")
        print()

    if dry_run:
        print("[DRY RUN] No database changes were made.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-classify and re-score followers")
    parser.add_argument("--db", default="data/followers.db", help="Path to followers database")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Database not found: {args.db}")
        sys.exit(1)

    rescore(args.db, dry_run=args.dry_run)
