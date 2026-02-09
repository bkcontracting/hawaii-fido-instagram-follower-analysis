#!/usr/bin/env python3
"""Extract raw candidate data from database and fetch website content.

This script ONLY extracts raw Instagram fields and fetches website content.
NO classification, evaluation, or intelligence is applied here.
All analysis is performed by Claude AI.
"""

import json
import sqlite3
import sys
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error
from urllib.parse import urlparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import _connect


def fetch_website_content(url: str, timeout: int = 5) -> Optional[str]:
    """Fetch website content and return first 4500 chars of main content.

    Returns None if fetch fails.
    """
    if not url:
        return None

    # Ensure URL has a scheme
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read().decode("utf-8", errors="ignore")
            # Return first 4500 chars (rough main content)
            return content[:4500]
    except (urllib.error.URLError, urllib.error.HTTPError, Exception):
        # Silently fail - website not available
        return None


def extract_candidates(db_path: str, output_path: str) -> None:
    """Extract raw candidate data from database.

    Extracts ONLY these fields:
    - id, handle, display_name, bio, profile_url
    - follower_count, following_count, post_count
    - is_business, is_verified, website

    Does NOT extract:
    - category, subcategory, location, is_hawaii
    - confidence, priority_score, priority_reason

    For each profile with a website, fetches website content.
    """
    conn = _connect(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT
                id, handle, display_name, bio, profile_url,
                follower_count, following_count, post_count,
                is_business, is_verified, website
            FROM followers
            WHERE status = 'completed'
            ORDER BY follower_count DESC
            """
        )
        rows = cursor.fetchall()

        candidates = []
        for i, row in enumerate(rows, 1):
            candidate = {
                "id": row["id"],
                "handle": row["handle"],
                "display_name": row["display_name"],
                "bio": row["bio"],
                "profile_url": row["profile_url"],
                "follower_count": row["follower_count"],
                "following_count": row["following_count"],
                "post_count": row["post_count"],
                "is_business": bool(row["is_business"]),
                "is_verified": bool(row["is_verified"]),
                "website": row["website"],
            }

            # Fetch website content if available
            if row["website"]:
                print(f"[{i}/{len(rows)}] Fetching website for {row['handle']}...", end="", flush=True)
                content = fetch_website_content(row["website"])
                if content:
                    candidate["website_content"] = content
                    print(" ✓")
                else:
                    print(" (failed)")
            else:
                print(f"[{i}/{len(rows)}] Skipped website fetch (no URL) for {row['handle']}")

            candidates.append(candidate)

        # Write to JSON
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(candidates, f, indent=2)

        print(f"\n✓ Extracted {len(candidates)} candidates to {output_path}")
        print(f"  - {sum(1 for c in candidates if 'website_content' in c)} with website content")

    finally:
        conn.close()


if __name__ == "__main__":
    db_path = Path(__file__).parent.parent / "data" / "followers.db"
    output_path = Path(__file__).parent.parent / "data" / "candidates_raw.json"

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    extract_candidates(str(db_path), str(output_path))
