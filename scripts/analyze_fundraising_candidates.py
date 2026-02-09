#!/usr/bin/env python3
"""
AI-Driven Analysis of Fundraising Candidates

This script loads the prepared candidate data and outputs it in a format
suitable for Claude AI analysis.
"""

import json
import sys
import os
from typing import List, Dict

def load_candidates(json_path: str) -> List[Dict]:
    """Load candidates from JSON file."""
    with open(json_path, 'r') as f:
        return json.load(f)

def format_candidate_for_analysis(candidate: Dict) -> str:
    """Format a candidate profile for AI analysis."""
    return f"""
Handle: {candidate['handle']}
Display Name: {candidate['display_name']}
Bio: {candidate['bio'][:500]}...
---
Followers: {candidate['follower_count']:,}
Following: {candidate['following_count']:,}
Posts: {candidate['post_count']}
Business Account: {'Yes' if candidate['is_business'] else 'No'}
Verified: {'Yes' if candidate['is_verified'] else 'No'}
Hawaii-Based: {'Yes' if candidate['is_hawaii'] else 'No'}
Location: {candidate['location'] or 'Not specified'}
Website: {candidate['website'] if candidate['website'] else 'None'}
Category: {candidate['category']}
Subcategory: {candidate['subcategory']}
URL: {candidate['profile_url']}
"""

def main():
    """Load and format candidates for analysis."""
    candidates_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'data',
        'fundraising_candidates.json'
    )

    print("Loading candidates...")
    candidates = load_candidates(candidates_path)
    print(f"✅ Loaded {len(candidates)} candidates")

    # Print summary statistics
    print("\n" + "="*60)
    print("CANDIDATE SUMMARY")
    print("="*60)

    # Category breakdown
    categories = {}
    for c in candidates:
        cat = c['category']
        categories[cat] = categories.get(cat, 0) + 1

    print("\nBreakdown by category:")
    for cat in sorted(categories.keys(), key=lambda x: -categories[x]):
        print(f"  {cat}: {categories[cat]}")

    # Hawaii connection
    hawaii_count = sum(1 for c in candidates if c['is_hawaii'])
    print(f"\nHawaii-based: {hawaii_count} ({hawaii_count*100//len(candidates)}%)")

    # Business accounts
    business_count = sum(1 for c in candidates if c['is_business'])
    print(f"Business Accounts: {business_count} ({business_count*100//len(candidates)}%)")

    # Followers distribution
    followers = [c['follower_count'] for c in candidates if c['follower_count'] is not None]
    followers.sort(reverse=True)
    print(f"\nFollower Distribution:")
    print(f"  Max: {followers[0]:,}")
    print(f"  Top 10 avg: {sum(followers[:10])//10:,}")
    print(f"  Median: {followers[len(followers)//2]:,}")
    print(f"  Min: {followers[-1]:,}")

    # Top 20 for reference
    print("\n" + "="*60)
    print("TOP 20 BY FOLLOWER COUNT (for reference)")
    print("="*60)
    for i, c in enumerate(candidates[:20], 1):
        print(f"\n{i}. {c['display_name']} (@{c['handle']})")
        print(f"   Followers: {c['follower_count']:,}")
        print(f"   Category: {c['category']}")
        print(f"   Website: {c['website'] if c['website'] else 'None'}")

    print("\n" + "="*60)
    print("Ready for AI analysis")
    print("="*60)

    return candidates


if __name__ == '__main__':
    main()
