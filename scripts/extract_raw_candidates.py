#!/usr/bin/env python3
"""Extract raw candidate data from database and fetch website content.

This script ONLY extracts raw Instagram fields and fetches website content.
NO classification, evaluation, or intelligence is applied here.
All analysis is performed by Claude AI.
"""

import json
import re
import sqlite3
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error
from urllib.parse import urlparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import _connect

# Domains that never yield useful classification content
SKIP_DOMAINS = frozenset({
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",  # email providers
    "youtube.com", "youtu.be",  # video platforms (JS-rendered)
    "facebook.com", "twitter.com", "tiktok.com", "x.com",  # social media (login walls)
    "accounts.google.com",
})

# Boilerplate patterns to strip from extracted text
_BOILERPLATE_PATTERNS = [
    re.compile(r"(?i)\b(we use cookies|accept all cookies|cookie (policy|preferences|settings)|by continuing to (use|browse))\b.*?\."),
    re.compile(r"(?i)skip to (main )?content"),
    re.compile(r"(?i)^(loading\.{0,3}|please wait\.{0,3})$", re.MULTILINE),
    re.compile(r"(?i)powered by (shopify|wordpress|wix|squarespace|weebly|godaddy|webflow)"),
]


def _should_skip_url(url: str) -> bool:
    """Return True if the URL's domain is in the skip list."""
    parsed = urlparse(url if "://" in url else "https://" + url)
    domain = parsed.hostname or ""
    if domain.startswith("www."):
        domain = domain[4:]
    return domain in SKIP_DOMAINS


class HTMLTextExtractor(HTMLParser):
    """Extract visible text and meta info from HTML."""

    SKIP_TAGS = frozenset(("script", "style", "noscript", "nav", "footer", "header"))

    def __init__(self):
        super().__init__()
        self._pieces: list[str] = []
        self._skip_depth = 0
        self._meta_title = ""
        self._meta_description = ""
        self._og_description = ""
        self._in_title = False
        self._title_pieces: list[str] = []
        self._in_head = False

    def handle_starttag(self, tag, attrs):
        if tag == "head":
            self._in_head = True
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        if tag == "meta":
            attrs_dict = dict(attrs)
            name = attrs_dict.get("name", "").lower()
            prop = attrs_dict.get("property", "").lower()
            content = attrs_dict.get("content", "")
            if name == "description" and content:
                self._meta_description = content
            elif prop == "og:description" and content:
                self._og_description = content
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "head":
            self._in_head = False
        if tag in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
            self._meta_title = " ".join(self._title_pieces).strip()

    def handle_data(self, data):
        if self._in_title:
            self._title_pieces.append(data)
        elif self._skip_depth == 0 and not self._in_head:
            self._pieces.append(data)

    def get_body_text(self) -> str:
        raw = " ".join(self._pieces)
        text = re.sub(r"[ \t]+", " ", raw)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def get_meta_summary(self) -> str:
        """Return combined meta title + description."""
        parts = []
        if self._meta_title:
            parts.append(self._meta_title)
        desc = self._og_description or self._meta_description
        if desc and desc != self._meta_title:
            parts.append(desc)
        return " — ".join(parts)


def _clean_boilerplate(text: str) -> str:
    """Remove common boilerplate phrases from extracted text."""
    for pattern in _BOILERPLATE_PATTERNS:
        text = pattern.sub("", text)
    # Collapse whitespace left behind by removals
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_meaningful_content(html: str) -> str:
    """Extract clean, meaningful text from HTML.

    Combines meta info (title, description) with visible body text.
    Falls back to meta description when body text is too short (JS-rendered pages).
    """
    extractor = HTMLTextExtractor()
    extractor.feed(html)

    meta_summary = extractor.get_meta_summary()
    body_text = extractor.get_body_text()
    body_text = _clean_boilerplate(body_text)

    # If body text is too short, rely on meta info
    if len(body_text) < 50:
        if meta_summary:
            return meta_summary
        return body_text

    # Combine meta summary with body text, avoiding duplication
    if meta_summary and meta_summary not in body_text:
        return f"{meta_summary}\n\n{body_text}"
    return body_text


def _truncate_on_word_boundary(text: str, max_chars: int = 1500) -> str:
    """Truncate text to max_chars, extending to include the full last word."""
    if len(text) <= max_chars:
        return text
    # Find the end of the word that straddles the boundary
    end = max_chars
    while end < len(text) and not text[end].isspace():
        end += 1
    return text[:end].rstrip()


def fetch_website_content(url: str, timeout: int = 5) -> Optional[str]:
    """Fetch website content, extract meaningful text, return up to ~1500 chars.

    Skips domains that never provide useful content (email providers, social media).
    Returns None if fetch fails or domain is skipped.
    """
    if not url:
        return None

    if _should_skip_url(url):
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
            html = response.read().decode("utf-8", errors="ignore")
            text = _extract_meaningful_content(html)
            return _truncate_on_word_boundary(text) or None
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
                if _should_skip_url(row["website"]):
                    print(f"[{i}/{len(rows)}] Skipped {row['handle']} (domain in skip list)")
                else:
                    print(f"[{i}/{len(rows)}] Fetching website for {row['handle']}...", end="", flush=True)
                    content = fetch_website_content(row["website"])
                    if content:
                        candidate["website_content"] = content
                        print(" ✓")
                    else:
                        print(" (failed)")
            else:
                print(f"[{i}/{len(rows)}] Skipped {row['handle']} (no URL)")

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
