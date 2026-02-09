#!/usr/bin/env python3
"""Standalone enrichment — no Claude required.

Usage:
  1. Launch Chrome with remote debugging:
 /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 
  --user-data-dir=/tmp/chrome-debug

  2. Log into Instagram in that Chrome window

  3. Run:
     python3 scripts/enrich.py [--db data/followers.db] [--delay-min 3] [--delay-max 5]

Setup (one-time):
  pip install playwright
  playwright install chromium
"""
import argparse
import os
import random
import signal
import sqlite3
import sys
import time

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: Playwright not installed. Run:")
    print("  pip install playwright")
    print("  playwright install chromium")
    sys.exit(1)

from src.batch_orchestrator import run_all
from src.database import get_status_counts
from src.profile_parser import parse_profile_page

# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------
shutdown_requested = False


def _handle_signal(sig, frame):
    global shutdown_requested
    shutdown_requested = True
    print("\nShutdown requested. Finishing current profile...")


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

# ---------------------------------------------------------------------------
# Browser Connection Manager
# ---------------------------------------------------------------------------


class BrowserConnectionManager:
    """Manages CDP browser connection lifecycle with automatic reconnection.

    Features:
    - Auto-reconnect after time threshold (default: 30 minutes)
    - Auto-reconnect after operation count threshold (default: 100 profiles)
    - Configurable timeouts on browser/context/page operations
    - Auto-recovery from CDP connection errors
    """

    def __init__(self, pw, cdp_url, max_age_seconds=1800, max_operations=100, page_timeout=30000):
        """
        Args:
            pw: Playwright sync_api instance
            cdp_url: CDP endpoint (e.g., "http://localhost:9222")
            max_age_seconds: Reconnect after N seconds (default: 1800 = 30 min)
            max_operations: Reconnect after N profile fetches (default: 100)
            page_timeout: Page operation timeout in ms (default: 30000 = 30s)
        """
        self.pw = pw
        self.cdp_url = cdp_url
        self.max_age_seconds = max_age_seconds
        self.max_operations = max_operations
        self.page_timeout = page_timeout

        self.browser = None
        self.context = None
        self.page = None
        self.connection_start_time = None
        self.operations_count = 0

    def connect(self):
        """Establish CDP connection and configure timeouts."""
        # Close existing connection if any
        if self.browser is not None:
            try:
                self.browser.close()
            except:
                pass

        # Connect via CDP
        self.browser = self.pw.chromium.connect_over_cdp(self.cdp_url)

        # Get context and page
        self.context = self.browser.contexts[0]
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()

        # Configure timeouts
        self.context.set_default_timeout(self.page_timeout)
        self.page.set_default_navigation_timeout(self.page_timeout)

        # Reset operation counter and track connection age
        self.connection_start_time = time.time()
        self.operations_count = 0

    def should_reconnect(self):
        """Check if reconnection is needed based on time or count."""
        if self.connection_start_time is None:
            return False

        # Check age
        elapsed = time.time() - self.connection_start_time
        if elapsed > self.max_age_seconds:
            return True

        # Check operation count
        if self.operations_count >= self.max_operations:
            return True

        return False

    def reconnect(self, reason="threshold"):
        """Force reconnection."""
        print(f"Reconnecting browser (reason: {reason})...")
        self.connect()

    def get_page(self):
        """Get current page, reconnecting if needed."""
        # Every 50 operations, clear browser cache
        if self.operations_count > 0 and self.operations_count % 50 == 0:
            try:
                self.page.evaluate(
                    "() => { "
                    "window.localStorage.clear(); "
                    "window.sessionStorage.clear(); "
                    "}"
                )
            except:
                pass  # Ignore errors, this is optional cleanup

        # Check if reconnection is needed
        if self.should_reconnect():
            elapsed = time.time() - self.connection_start_time
            reason = (
                f"age ({int(elapsed)}s > {self.max_age_seconds}s)"
                if elapsed > self.max_age_seconds
                else f"operations ({self.operations_count} >= {self.max_operations})"
            )
            self.reconnect(reason=reason)

        return self.page

    def increment_operations(self):
        """Increment operation counter after each profile fetch."""
        self.operations_count += 1

    def close(self):
        """Clean shutdown."""
        if self.browser is not None:
            try:
                self.browser.close()
            except:
                pass
        self.browser = None
        self.context = None
        self.page = None


# ---------------------------------------------------------------------------
# Fetcher
# ---------------------------------------------------------------------------


def make_fetcher(connection_manager, delay_min, delay_max):
    """Return a fetcher_fn(handle, profile_url) closure using Playwright."""
    processed = 0
    total = [0]  # mutable so closure can read updated value

    def fetcher_fn(handle, profile_url):
        nonlocal processed
        if shutdown_requested:
            raise SystemExit("shutdown")

        # CDP error handling with reconnection
        max_attempts = 2
        last_error = None

        for attempt in range(max_attempts):
            try:
                # Get page (auto-reconnects if threshold reached)
                page = connection_manager.get_page()

                # Existing fetch logic
                page.goto(profile_url)
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(2000)

                raw_text = page.evaluate(
                    "document.querySelector('header')?.closest('main')?.innerText"
                    " || document.body.innerText"
                )

                enriched = parse_profile_page(raw_text)

                # Increment operation counter
                connection_manager.increment_operations()

                # Existing progress display logic
                processed += 1
                page_state = (enriched.get("page_state") or "normal").lower()
                status_label = page_state if page_state != "normal" else (
                    "private" if enriched.get("is_private") else "completed"
                )
                score_info = ""
                if status_label == "completed":
                    # Score/category aren't computed yet — batch_orchestrator does that.
                    # Just show the raw extraction summary.
                    fc = enriched.get("follower_count")
                    score_info = f" ({fc} followers)" if fc is not None else ""
                print(f"  [{processed}/{total[0]}] @{handle} — {status_label}{score_info}")

                # Human-cadence delay
                delay = random.uniform(delay_min, delay_max)
                time.sleep(delay)

                return enriched

            except Exception as e:
                last_error = e
                # Check if it's a CDP/Playwright connection error
                error_str = str(e).lower()
                is_cdp_error = any(keyword in error_str for keyword in
                                  ['target closed', 'connection closed', 'session closed',
                                   'browser closed', 'context closed'])

                if is_cdp_error and attempt < max_attempts - 1:
                    print(f"  CDP error on @{handle}, reconnecting: {e}")
                    connection_manager.reconnect(reason="error")
                    continue

                # Not a CDP error or out of retries, propagate
                raise

        # Should not reach here, but just in case
        raise last_error

    def set_total(n):
        total[0] = n

    fetcher_fn.set_total = set_total
    return fetcher_fn

# ---------------------------------------------------------------------------
# Rate-limit reset
# ---------------------------------------------------------------------------


def reset_rate_limited(db_path):
    """Reset rate-limited errors back to pending so they can be retried."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "UPDATE followers SET status = 'pending', error_message = NULL "
        "WHERE status = 'error' AND error_message = 'rate_limited'"
    )
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count

# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------


def dry_run(connection_manager, db_path, delay_min, delay_max, count=1):
    """Fetch N profiles, print parsed results, don't write to DB."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT handle, profile_url FROM followers WHERE status = 'pending' LIMIT ?",
        (count,)
    ).fetchall()
    conn.close()

    if not rows:
        print("No pending followers for dry run.")
        return

    print(f"Dry run: fetching {len(rows)} profile(s)\n")
    fetcher = make_fetcher(connection_manager, delay_min, delay_max)
    fetcher.set_total(len(rows))

    for row in rows:
        handle = row["handle"]
        profile_url = row["profile_url"]
        result = fetcher(handle, profile_url)

        print(f"\n  Parsed result for @{handle}:")
        for k, v in sorted(result.items()):
            print(f"    {k}: {v}")

    print("\n[DRY RUN] No database changes were made.")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Standalone Instagram profile enrichment (no Claude required)"
    )
    parser.add_argument("--db", default="data/followers.db",
                        help="Path to followers database")
    parser.add_argument("--delay-min", type=float, default=3.0,
                        help="Minimum delay between profiles in seconds")
    parser.add_argument("--delay-max", type=float, default=5.0,
                        help="Maximum delay between profiles in seconds")
    parser.add_argument("--pause-minutes", type=int, default=10,
                        help="Minutes to pause on rate limit before retrying")
    parser.add_argument("--dry-run", nargs="?", type=int, const=1, default=None,
                        metavar="N",
                        help="Fetch N profiles (default 1) and print results without writing to DB")
    parser.add_argument("--reconnect-minutes", type=int, default=30,
                        help="Reconnect browser every N minutes (default: 30)")
    parser.add_argument("--reconnect-count", type=int, default=100,
                        help="Reconnect browser every N profiles (default: 100)")
    parser.add_argument("--page-timeout", type=int, default=30,
                        help="Page operation timeout in seconds (default: 30)")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Database not found: {args.db}")
        sys.exit(1)

    # Connect to existing Chrome via CDP
    pw = sync_playwright().start()
    try:
        connection_manager = BrowserConnectionManager(
            pw=pw,
            cdp_url="http://localhost:9222",
            max_age_seconds=args.reconnect_minutes * 60,
            max_operations=args.reconnect_count,
            page_timeout=args.page_timeout * 1000  # convert to ms
        )
        connection_manager.connect()
    except Exception as e:
        pw.stop()
        print(f"Could not connect to Chrome on port 9222: {e}")
        print("Launch Chrome with: /Applications/Google\\ Chrome.app/Contents/MacOS/"
              "Google\\ Chrome --remote-debugging-port=9222")
        sys.exit(1)

    try:
        if args.dry_run is not None:
            dry_run(connection_manager, args.db, args.delay_min, args.delay_max, count=args.dry_run)
            return

        # Print starting status
        counts = get_status_counts(args.db)
        total = sum(counts.values())
        print(f"\nDatabase status ({total} total):")
        for status, count in sorted(counts.items()):
            print(f"  {status}: {count}")
        print()

        fetcher = make_fetcher(connection_manager, args.delay_min, args.delay_max)
        pending = counts.get("pending", 0) + counts.get(None, 0)
        fetcher.set_total(pending)

        # Outer retry loop for rate limits
        while True:
            if shutdown_requested:
                print("Shutdown before starting batch. Exiting.")
                break

            result = run_all(args.db, fetcher)

            if result["reason"] == "all_complete":
                print(f"\nAll done! Completed {result['total_completed']} profiles "
                      f"across {result['batches_run']} batches.")
                break

            if result["stopped"]:
                reset_count = reset_rate_limited(args.db)
                if reset_count > 0:
                    print(f"\nReset {reset_count} rate-limited records to pending.")
                    print(f"Pausing {args.pause_minutes} minutes for rate limit cooldown...")
                    time.sleep(args.pause_minutes * 60)
                    # Refresh total for progress display
                    counts = get_status_counts(args.db)
                    fetcher.set_total(sum(counts.values()))
                    continue
                # Stopped but not from rate limits
                print("\nBatch exhausted (non-rate-limit errors). Stopping.")
                break

            break

        # Final status
        counts = get_status_counts(args.db)
        print(f"\nFinal database status ({sum(counts.values())} total):")
        for status, count in sorted(counts.items()):
            print(f"  {status}: {count}")

        # Show error summary if any
        error_count = counts.get("error", 0)
        if error_count > 0:
            conn = sqlite3.connect(args.db)
            conn.row_factory = sqlite3.Row
            errors = conn.execute(
                "SELECT handle, error_message FROM followers WHERE status = 'error'"
            ).fetchall()
            conn.close()
            print(f"\nError details ({error_count} records):")
            for err in errors:
                print(f"  @{err['handle']}: {err['error_message']}")

    finally:
        # Reset any records stuck in "processing" from our interrupted batch
        conn = sqlite3.connect(args.db)
        reset = conn.execute(
            "UPDATE followers SET status = 'pending' WHERE status = 'processing'"
        )
        if reset.rowcount > 0:
            print(f"\nReset {reset.rowcount} processing records to pending.")
        conn.commit()
        conn.close()

        connection_manager.close()
        pw.stop()


if __name__ == "__main__":
    main()
