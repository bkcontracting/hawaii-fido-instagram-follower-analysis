#!/usr/bin/env python3
"""Standalone browser-based Instagram enrichment — no LLM required.

Replaces the Claude-driven subagent approach with a deterministic
Selenium script that processes ALL pending followers unattended.
Uses the same pipeline (parse → hawaii → classify → score → DB update)
but drives Chrome directly instead of through Claude Code subagents.

Setup (one-time):
    pip install selenium

Usage:
    1. Launch Chrome with remote debugging enabled:

       # macOS
       /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\
           --remote-debugging-port=9222

       # Linux
       google-chrome --remote-debugging-port=9222

       # Windows
       chrome.exe --remote-debugging-port=9222

    2. Make sure you are logged into Instagram in that Chrome window.

    3. Run the script:

       python scripts/enrich_browser.py

    Options:
       --port PORT              Chrome debugging port (default: 9222)
       --db PATH                Database path (default: data/followers.db)
       --delay-min SECONDS      Min delay between profiles (default: 3)
       --delay-max SECONDS      Max delay between profiles (default: 5)
       --rate-limit-wait MIN    Minutes to wait on rate limit (default: 5)
       --max-errors N           Stop after N consecutive errors (default: 15)
       --batch-size N           Profiles to fetch per DB query (default: 50)
       --dry-run                Show what would be processed without doing it

The script is fully restartable. It reads pending records from the DB,
processes them one at a time, and updates status as it goes. If killed,
stale 'processing' records are reset to 'pending' on next run.
"""

import argparse
import datetime
import os
import random
import sqlite3
import sys
import time

# ---------------------------------------------------------------------------
# Project imports — add project root to sys.path
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from src.database import update_follower, get_status_counts, init_db  # noqa: E402
from src.profile_parser import parse_profile_page  # noqa: E402
from src.location_detector import is_hawaii  # noqa: E402
from src.classifier import classify  # noqa: E402
from src.scorer import score  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# JavaScript to extract page text — same as the subagent prompt uses.
# Targets the main content area first to avoid nav/footer noise.
EXTRACT_JS = """
return (function() {
    var main = document.querySelector('main');
    if (main) return main.innerText || '';
    var header = document.querySelector('header');
    if (header && header.closest('main'))
        return header.closest('main').innerText || '';
    return document.body.innerText || '';
})();
"""

# Page-load wait (seconds) — Instagram needs a moment to hydrate
PAGE_LOAD_WAIT = 2.5


# ---------------------------------------------------------------------------
# Chrome connection
# ---------------------------------------------------------------------------

def connect_to_chrome(port):
    """Connect to an already-running Chrome via its debugging port.

    Returns a Selenium WebDriver instance attached to that browser.
    Raises SystemExit with helpful message on failure.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except ImportError:
        print("ERROR: selenium is not installed.  Run:  pip install selenium")
        sys.exit(1)

    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")

    try:
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"ERROR: Could not connect to Chrome on port {port}")
        print(f"  {e}")
        print()
        print("Make sure Chrome is running with remote debugging:")
        print(f"  google-chrome --remote-debugging-port={port}")
        print()
        print("On macOS:")
        print(f'  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome'
              f' --remote-debugging-port={port}')
        sys.exit(1)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_pending_followers(db_path, limit=50):
    """Return up to `limit` pending followers as list of dicts."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM followers WHERE status = 'pending' LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def reset_stale_processing(db_path, minutes=5):
    """Reset 'processing' records older than N minutes back to 'pending'.

    This handles crash recovery — if the script was killed mid-run, those
    records won't be stuck forever.
    """
    conn = sqlite3.connect(db_path)
    try:
        cutoff = (datetime.datetime.now()
                  - datetime.timedelta(minutes=minutes)).isoformat()
        cursor = conn.execute(
            "UPDATE followers SET status = 'pending' "
            "WHERE status = 'processing' AND processed_at < ?",
            (cutoff,),
        )
        count = cursor.rowcount
        conn.commit()
        return count
    finally:
        conn.close()


def count_total(db_path):
    """Return total number of followers in the database."""
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) as n FROM followers").fetchone()
        return row[0]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Single-profile enrichment
# ---------------------------------------------------------------------------

def enrich_one(driver, db_path, follower):
    """Visit one Instagram profile and run the full enrichment pipeline.

    Returns a status string:
      'completed'       — success
      'private'         — private account (still enriched)
      'not_found'       — 404 page
      'suspended'       — suspended account
      'rate_limited'    — Instagram rate limit hit
      'login_required'  — need to log in
      'error:<msg>'     — unexpected error
    """
    handle = follower["handle"]
    profile_url = follower["profile_url"]
    display_name = follower.get("display_name") or ""

    # Mark as processing
    update_follower(db_path, handle, {
        "status": "processing",
        "processed_at": datetime.datetime.now().isoformat(),
    })

    try:
        # Navigate to the profile
        driver.get(profile_url)
        time.sleep(PAGE_LOAD_WAIT)

        # Extract page text via JavaScript
        raw_text = driver.execute_script(EXTRACT_JS)

        if not raw_text or len(raw_text.strip()) < 10:
            # Sometimes the page hasn't loaded — wait a bit more and retry
            time.sleep(3)
            raw_text = driver.execute_script(EXTRACT_JS)

        if not raw_text or len(raw_text.strip()) < 10:
            raise RuntimeError("empty_page_text")

        # ── Deterministic parse ──────────────────────────────────────
        enriched = parse_profile_page(raw_text)
        page_state = enriched.get("page_state", "normal")

        # Rate limit / login required → reset to pending for retry
        if page_state in ("rate_limited", "login_required"):
            update_follower(db_path, handle, {
                "status": "pending",
                "error_message": None,
                "processed_at": datetime.datetime.now().isoformat(),
            })
            return page_state

        # Not found / suspended → permanent error
        if page_state in ("not_found", "suspended"):
            update_follower(db_path, handle, {
                "status": "error",
                "error_message": page_state,
                "processed_at": datetime.datetime.now().isoformat(),
            })
            return page_state

        # ── Enrichment pipeline ──────────────────────────────────────
        bio = enriched.get("bio") or ""
        combined_text = f"{handle} {display_name} {bio}"
        hi = is_hawaii(combined_text)

        profile = {
            **enriched,
            "handle": handle,
            "display_name": display_name,
            "is_hawaii": hi,
        }

        classification = classify(profile)
        profile["category"] = classification["category"]
        profile["subcategory"] = classification["subcategory"]

        scoring = score(profile)

        status = "private" if enriched.get("is_private") else "completed"

        update_data = {
            "follower_count": enriched.get("follower_count"),
            "following_count": enriched.get("following_count"),
            "post_count": enriched.get("post_count"),
            "bio": bio,
            "website": enriched.get("website"),
            "is_verified": enriched.get("is_verified"),
            "is_private": enriched.get("is_private"),
            "is_business": enriched.get("is_business"),
            "category": classification["category"],
            "subcategory": classification["subcategory"],
            "confidence": classification["confidence"],
            "is_hawaii": hi,
            "location": "Hawaii" if hi else None,
            "priority_score": scoring["priority_score"],
            "priority_reason": scoring["priority_reason"],
            "status": status,
            "processed_at": datetime.datetime.now().isoformat(),
        }
        update_follower(db_path, handle, update_data)
        return status

    except Exception as e:
        update_follower(db_path, handle, {
            "status": "error",
            "error_message": str(e)[:200],
            "processed_at": datetime.datetime.now().isoformat(),
        })
        return f"error:{e}"


# ---------------------------------------------------------------------------
# Progress display
# ---------------------------------------------------------------------------

def print_status(db_path, total, session_processed, start_time):
    """Print a compact progress line."""
    counts = get_status_counts(db_path)
    done = counts.get("completed", 0) + counts.get("private", 0)
    pending = counts.get("pending", 0)
    errors = counts.get("error", 0)
    elapsed = time.time() - start_time
    rate = session_processed / elapsed * 60 if elapsed > 0 else 0
    eta_min = pending / rate if rate > 0 else 0

    print(f"\n  Progress: {done}/{total} done | {pending} pending | "
          f"{errors} errors | {rate:.1f}/min | ~{eta_min:.0f}m remaining")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Standalone Instagram follower enrichment via Selenium",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--port", type=int, default=9222,
        help="Chrome remote debugging port (default: 9222)")
    parser.add_argument(
        "--db", default=os.path.join(_PROJECT_ROOT, "data", "followers.db"),
        help="Path to followers.db (default: data/followers.db)")
    parser.add_argument(
        "--delay-min", type=float, default=3.0,
        help="Minimum delay between profiles in seconds (default: 3)")
    parser.add_argument(
        "--delay-max", type=float, default=5.0,
        help="Maximum delay between profiles in seconds (default: 5)")
    parser.add_argument(
        "--rate-limit-wait", type=int, default=5,
        help="Minutes to wait when rate-limited (default: 5)")
    parser.add_argument(
        "--max-errors", type=int, default=15,
        help="Stop after N consecutive unexpected errors (default: 15)")
    parser.add_argument(
        "--batch-size", type=int, default=50,
        help="Profiles to fetch per DB query (default: 50)")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show pending profiles without processing them")

    args = parser.parse_args()

    # ── Initialization ────────────────────────────────────────────────
    init_db(args.db)

    # Crash recovery
    reset = reset_stale_processing(args.db)
    if reset:
        print(f"Crash recovery: reset {reset} stale records to pending")

    total = count_total(args.db)
    counts = get_status_counts(args.db)
    pending = counts.get("pending", 0)
    done = counts.get("completed", 0) + counts.get("private", 0)
    errors = counts.get("error", 0)

    print(f"Database: {args.db}")
    print(f"Status:   {done}/{total} completed | {pending} pending | {errors} errors")
    print()

    if pending == 0:
        print("Nothing to do — all followers already processed.")
        return

    # ── Dry run ───────────────────────────────────────────────────────
    if args.dry_run:
        followers = get_pending_followers(args.db, limit=args.batch_size)
        print(f"Would process {pending} profiles. First {len(followers)}:")
        for f in followers:
            print(f"  @{f['handle']:30s}  {f['profile_url']}")
        return

    # ── Connect to Chrome ─────────────────────────────────────────────
    print(f"Connecting to Chrome on port {args.port}...")
    driver = connect_to_chrome(args.port)
    print(f"Connected. Current tab: {driver.title}")
    print()

    # Quick Instagram login check
    driver.get("https://www.instagram.com/")
    time.sleep(3)
    page_text = driver.execute_script("return document.body.innerText || '';")
    if "log in" in page_text.lower() and "sign up" in page_text.lower():
        print("WARNING: You do not appear to be logged into Instagram.")
        print("Please log in via the Chrome window, then press Enter here.")
        input("Press Enter to continue...")
        print()

    # ── Processing loop ───────────────────────────────────────────────
    start_time = time.time()
    session_processed = 0
    consecutive_errors = 0

    print(f"Starting enrichment of {pending} profiles...")
    print(f"Delay: {args.delay_min}-{args.delay_max}s | "
          f"Rate limit wait: {args.rate_limit_wait}m | "
          f"Max consecutive errors: {args.max_errors}")
    print("=" * 65)

    while True:
        followers = get_pending_followers(args.db, limit=args.batch_size)
        if not followers:
            break

        for follower in followers:
            handle = follower["handle"]

            # Progress indicator every 25 profiles
            if session_processed > 0 and session_processed % 25 == 0:
                print_status(args.db, total, session_processed, start_time)

            ts = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] ({session_processed + 1}) @{handle:30s} ", end="", flush=True)

            result = enrich_one(driver, args.db, follower)
            session_processed += 1

            # ── Handle result ─────────────────────────────────────────
            if result == "rate_limited":
                print(f"RATE LIMITED")
                print(f"  Sleeping {args.rate_limit_wait} minutes "
                      f"(until {_future_time(args.rate_limit_wait)})...")
                consecutive_errors = 0
                time.sleep(args.rate_limit_wait * 60)
                break  # Re-fetch pending list after sleep

            if result == "login_required":
                print(f"LOGIN REQUIRED")
                print("  Please log into Instagram in the Chrome window.")
                print("  Waiting 60 seconds...")
                time.sleep(60)
                break

            if result in ("completed", "private"):
                # Re-query to show category in output
                conn = sqlite3.connect(args.db)
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT category, priority_score FROM followers WHERE handle = ?",
                    (handle,)
                ).fetchone()
                conn.close()
                cat = row["category"] if row else "?"
                scr = row["priority_score"] if row else 0
                label = "PRIVATE" if result == "private" else "OK"
                print(f"{label:8s} | {cat:20s} | score={scr}")
                consecutive_errors = 0

            elif result in ("not_found", "suspended"):
                print(f"{result.upper()}")
                consecutive_errors = 0  # Expected — don't count

            else:
                # Unexpected error
                msg = result.replace("error:", "", 1)[:60]
                print(f"ERROR: {msg}")
                consecutive_errors += 1

            # ── Check error threshold ─────────────────────────────────
            if consecutive_errors >= args.max_errors:
                print(f"\nStopping: {args.max_errors} consecutive errors reached.")
                print("Check Chrome — you may need to log in or the page layout changed.")
                break

            # ── Delay ─────────────────────────────────────────────────
            delay = random.uniform(args.delay_min, args.delay_max)
            time.sleep(delay)

        else:
            # Inner loop completed normally — fetch next batch
            continue

        # Inner loop was broken (rate limit, login, or error threshold)
        if consecutive_errors >= args.max_errors:
            break
        # Otherwise (rate limit / login), continue outer loop to re-fetch

    # ── Final report ──────────────────────────────────────────────────
    elapsed = time.time() - start_time
    counts = get_status_counts(args.db)
    done = counts.get("completed", 0) + counts.get("private", 0)
    pending = counts.get("pending", 0)
    errors = counts.get("error", 0)

    print()
    print("=" * 65)
    print(f"FINISHED — {session_processed} profiles processed this session")
    print(f"  Time:      {elapsed / 60:.1f} minutes")
    print(f"  Rate:      {session_processed / elapsed * 60:.1f} profiles/minute"
          if elapsed > 0 else "")
    print(f"  Completed: {done}/{total}")
    print(f"  Pending:   {pending}")
    print(f"  Errors:    {errors}")
    print("=" * 65)

    if pending > 0:
        print(f"\n{pending} profiles still pending. Run again to continue.")


def _future_time(minutes):
    """Return HH:MM:SS string for `minutes` from now."""
    t = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
    return t.strftime("%H:%M:%S")


if __name__ == "__main__":
    main()
