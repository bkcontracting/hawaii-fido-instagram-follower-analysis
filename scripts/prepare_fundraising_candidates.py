#!/usr/bin/env python3
"""
Prepare fundraising candidates by extracting and enriching follower data.

This script:
1. Queries the database for all completed follower profiles
2. Applies basic exclusions (spam, personal passive, etc.)
3. Fetches website content for profiles with websites
4. Generates a candidate dataset as JSON for AI analysis
"""

import json
import sqlite3
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional
import urllib.request
import urllib.error

# Add src to path for database module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database import _connect


def fetch_website_summary(url: str, timeout: int = 5) -> Optional[str]:
    """
    Attempt to fetch website content for analysis.
    Returns a summary of the page content or None if fetching fails.
    """
    if not url:
        return None

    # Ensure URL has protocol
    if not url.startswith('http'):
        url = 'https://' + url

    try:
        # Add a user agent to avoid blocking
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            # Read just the first 50KB to avoid huge downloads
            content = response.read(50000).decode('utf-8', errors='ignore')
            # Return first 1000 chars as summary
            return content[:1000]
    except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
        # Silently fail - website might not be accessible
        return None


def get_candidates(db_path: str) -> List[Dict]:
    """
    Extract all completed follower profiles from database and apply basic filters.
    """
    conn = _connect(db_path)

    # Query all completed profiles
    query = """
    SELECT
        id, handle, display_name, bio, profile_url,
        follower_count, following_count, post_count,
        is_business, is_verified, is_hawaii,
        location, website, category, subcategory
    FROM followers
    WHERE status = 'completed'
    ORDER BY follower_count DESC
    """

    rows = conn.execute(query).fetchall()
    candidates = [dict(row) for row in rows]

    # Apply basic exclusions
    filtered = []
    for candidate in candidates:
        # Exclude obvious spam
        if candidate['category'] == 'spam_bot':
            continue

        # Exclude very small personal passive accounts
        if (candidate['category'] == 'personal_passive' and
            candidate['follower_count'] < 500):
            continue

        # Keep everything else for AI evaluation
        filtered.append(candidate)

    return filtered


def enrich_with_websites(candidates: List[Dict], fetch_websites: bool = False) -> List[Dict]:
    """
    Optionally fetch website content for candidates that have websites.
    Website fetching can be slow, so it's off by default.
    Claude will fetch websites on-demand during analysis.
    """
    if not fetch_websites:
        # Just add empty placeholder for website_content
        for candidate in candidates:
            candidate['website_content'] = None
        return candidates

    print(f"Enriching {len(candidates)} candidates with website data...")

    enriched = []
    for i, candidate in enumerate(candidates):
        if candidate.get('website'):
            print(f"  [{i+1}/{len(candidates)}] Fetching {candidate['handle']}...")
            candidate['website_content'] = fetch_website_summary(candidate['website'])
        else:
            candidate['website_content'] = None

        enriched.append(candidate)

    return enriched


def save_candidates(candidates: List[Dict], output_path: str):
    """
    Save candidate data to JSON file.
    """
    with open(output_path, 'w') as f:
        json.dump(candidates, f, indent=2)

    print(f"Saved {len(candidates)} candidates to {output_path}")


def main(db_path: str = None, fetch_websites: bool = False):
    """
    Main function to prepare fundraising candidates.

    Args:
        db_path: Path to followers database
        fetch_websites: Whether to fetch website content (slow, default False)
    """
    if not db_path:
        db_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'data',
            'followers.db'
        )

    print(f"Preparing fundraising candidates...")
    print(f"Database: {db_path}")

    # Step 1: Extract candidates
    print("\n1. Extracting candidates from database...")
    candidates = get_candidates(db_path)
    print(f"   Found {len(candidates)} candidates after basic filtering")

    # Step 2: Enrich with website data (optional, can be slow)
    print("\n2. Processing website data...")
    candidates = enrich_with_websites(candidates, fetch_websites=fetch_websites)
    if fetch_websites:
        print("   Websites fetched and included")
    else:
        print("   Websites will be fetched on-demand during AI analysis")

    # Step 3: Save to JSON
    output_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'data',
        'fundraising_candidates.json'
    )
    print("\n3. Saving candidates to JSON...")
    save_candidates(candidates, output_path)

    print("\n✅ Data preparation complete!")
    print(f"\nCandidates ready for AI analysis: {output_path}")

    return candidates


if __name__ == '__main__':
    main()
