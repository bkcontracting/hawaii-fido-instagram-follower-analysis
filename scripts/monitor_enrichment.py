#!/usr/bin/env python3
"""Monitor enrichment progress by tracking processed followers every 30 seconds.

Usage:
  python scripts/monitor_enrichment.py [--db data/followers.db]

This script queries the database for followers with processed_at timestamp and prints
the count every 30 seconds with a timestamp. Includes completed, private, and error statuses.
"""
import argparse
import os
import signal
import sys
import time
from datetime import datetime

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import _connect

# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------
shutdown_requested = False


def _handle_signal(sig, frame):
    global shutdown_requested
    shutdown_requested = True
    print("\nShutdown requested. Exiting...")


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

# ---------------------------------------------------------------------------
# Monitor
# ---------------------------------------------------------------------------


def get_enriched_count(db_path: str) -> int:
    """Query database for count of all processed followers (completed, private, error)."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM followers WHERE processed_at IS NOT NULL"
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Monitor enrichment progress by tracking processed followers"
    )
    parser.add_argument("--db", default="data/followers.db",
                        help="Path to followers database")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Database not found: {args.db}")
        sys.exit(1)

    # Print initial count
    count = get_enriched_count(args.db)
    print(f"Processed followers: {count:,}")

    # Monitor loop
    while not shutdown_requested:
        time.sleep(30)
        if shutdown_requested:
            break
        count = get_enriched_count(args.db)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Processed followers: {count:,}")


if __name__ == "__main__":
    main()
