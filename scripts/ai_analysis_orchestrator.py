#!/usr/bin/env python3
"""Orchestrate parallel AI analysis of candidates using Claude subagents.

This script:
1. Loads raw candidate data
2. Launches 15 subagents (in 3 waves) to analyze batches of ~30 profiles each
3. Launches 1 Opus 4.6 thinking subagent to rank and select top candidates
4. Saves results to JSON files

All intelligence is performed by Claude AI - this script only orchestrates.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# This script will be invoked by Claude Code task tool
# It outputs candidate batches as JSON for each subagent


def load_candidates(filepath: str) -> List[Dict[str, Any]]:
    """Load raw candidates from JSON."""
    with open(filepath, "r") as f:
        return json.load(f)


def split_into_batches(candidates: List[Dict[str, Any]], batch_size: int = 30) -> List[List[Dict[str, Any]]]:
    """Split candidates into batches for parallel processing."""
    batches = []
    for i in range(0, len(candidates), batch_size):
        batches.append(candidates[i:i+batch_size])
    return batches


def save_batch_file(batch: List[Dict[str, Any]], batch_num: int, output_dir: str) -> str:
    """Save a batch to a JSON file and return the path."""
    output_path = Path(output_dir) / f"batch_{batch_num}.json"
    with open(output_path, "w") as f:
        json.dump({
            "batch_number": batch_num,
            "candidate_count": len(batch),
            "candidates": batch
        }, f, indent=2)
    return str(output_path)


def prepare_analysis_batches(candidates_file: str, output_dir: str = None) -> List[str]:
    """Prepare batch files for subagent analysis."""
    if output_dir is None:
        output_dir = Path(candidates_file).parent / "analysis_batches"

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading candidates...")
    candidates = load_candidates(candidates_file)
    print(f"✓ Loaded {len(candidates)} candidates")

    print("Splitting into batches...")
    batches = split_into_batches(candidates, batch_size=30)
    print(f"✓ Created {len(batches)} batches")

    batch_files = []
    for i, batch in enumerate(batches, 1):
        filepath = save_batch_file(batch, i, output_dir)
        batch_files.append(filepath)
        print(f"  Batch {i}: {len(batch)} candidates → {filepath}")

    return batch_files


if __name__ == "__main__":
    base_path = Path(__file__).parent.parent
    candidates_file = base_path / "data" / "candidates_raw.json"

    if not candidates_file.exists():
        print(f"Error: {candidates_file} not found")
        sys.exit(1)

    batch_files = prepare_analysis_batches(str(candidates_file))
    print(f"\n✓ Prepared {len(batch_files)} batch files for analysis")
    print("\nBatch files are ready for Claude AI subagent analysis.")
