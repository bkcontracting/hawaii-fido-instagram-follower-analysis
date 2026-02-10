#!/usr/bin/env python3
"""Aggregate batch analysis results and rank all profiles by score.

This script ONLY aggregates and sorts - NO intelligence or evaluation.
Merges batch_*_results.json files into a single sorted list.
"""

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


def load_batch(filepath: Path) -> List[Dict[str, Any]]:
    """Load a batch results file. Handles both wrapped and unwrapped formats."""
    with open(filepath, "r") as f:
        data = json.load(f)

    if isinstance(data, dict):
        if "candidates" in data:
            return data["candidates"]
        elif "results" in data:
            return data["results"]
        elif "profiles" in data:
            return data["profiles"]

    return data if isinstance(data, list) else [data]


def aggregate_and_rank(results_dir: Path, output_path: Path) -> None:
    """Aggregate all batch results and save sorted by score."""
    batch_files = sorted(results_dir.glob("batch_*_results.json"))

    if not batch_files:
        print(f"Error: No batch result files found in {results_dir}")
        sys.exit(1)

    print(f"Found {len(batch_files)} batch files:")
    all_profiles: List[Dict[str, Any]] = []

    for batch_file in batch_files:
        profiles = load_batch(batch_file)
        print(f"  {batch_file.name}: {len(profiles)} profiles")
        all_profiles.extend(profiles)

    print(f"\nTotal profiles loaded: {len(all_profiles)}")

    # Validate no duplicate handles
    handles = [p.get("handle", "") for p in all_profiles]
    duplicates = [h for h, count in Counter(handles).items() if count > 1]
    if duplicates:
        print(f"Error: Duplicate handles found: {duplicates}")
        sys.exit(1)
    print("✓ No duplicate handles")

    # Validate exclusions have score=0
    exclusion_errors = []
    for p in all_profiles:
        entity_type = p.get("entity_type", "")
        if entity_type.startswith("EXCLUDE_") and p.get("score", 0) != 0:
            exclusion_errors.append(f"  {p.get('handle')}: entity_type={entity_type}, score={p.get('score')}")
    if exclusion_errors:
        print(f"Error: {len(exclusion_errors)} excluded entities have non-zero scores:")
        for err in exclusion_errors:
            print(err)
        sys.exit(1)
    print("✓ All excluded entities have score=0")

    # Sort by score descending, then handle ascending
    all_profiles.sort(key=lambda p: (-p.get("score", 0), p.get("handle", "")))
    print("✓ Sorted by score (descending)")

    # Summary stats
    excluded = [p for p in all_profiles if p.get("entity_type", "").startswith("EXCLUDE_")]
    scored = [p for p in all_profiles if not p.get("entity_type", "").startswith("EXCLUDE_")]

    print(f"\n--- Summary ---")
    print(f"Total profiles:  {len(all_profiles)}")
    print(f"Excluded:        {len(excluded)}")
    print(f"Scored:          {len(scored)}")

    # Score distribution
    if scored:
        scores = [p.get("score", 0) for p in scored]
        print(f"\nScore distribution (scored profiles only):")
        print(f"  Max:    {max(scores)}")
        print(f"  Min:    {min(scores)}")
        print(f"  Mean:   {sum(scores) / len(scores):.1f}")
        brackets = {"80-100": 0, "60-79": 0, "40-59": 0, "20-39": 0, "1-19": 0, "0": 0}
        for s in scores:
            if s >= 80:
                brackets["80-100"] += 1
            elif s >= 60:
                brackets["60-79"] += 1
            elif s >= 40:
                brackets["40-59"] += 1
            elif s >= 20:
                brackets["20-39"] += 1
            elif s >= 1:
                brackets["1-19"] += 1
            else:
                brackets["0"] += 1
        for bracket, count in brackets.items():
            print(f"  {bracket:>6}: {count}")

    # Entity type breakdown
    entity_counts = Counter(p.get("entity_type", "unknown") for p in all_profiles)
    print(f"\nEntity type breakdown:")
    for entity_type, count in entity_counts.most_common():
        print(f"  {entity_type}: {count}")

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(all_profiles, f, indent=2)
    print(f"\n✓ Saved {len(all_profiles)} profiles to {output_path}")


if __name__ == "__main__":
    base_path = Path(__file__).parent.parent
    results_dir = base_path / "data" / "analysis_results"
    output_path = base_path / "data" / "all_analyzed_profiles.json"

    if not results_dir.exists():
        print(f"Error: Results directory not found: {results_dir}")
        sys.exit(1)

    aggregate_and_rank(results_dir, output_path)
