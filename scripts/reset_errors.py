#!/usr/bin/env python3
"""Reset followers with error status to pending."""
import sqlite3
from pathlib import Path

def reset_error_followers(db_path: str) -> int:
    """Set all followers with status='error' to status='pending'.

    Returns the number of followers updated.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        # Get current error count
        cursor = conn.execute(
            "SELECT COUNT(*) as cnt FROM followers WHERE status = 'error'"
        )
        error_count = cursor.fetchone()["cnt"]

        if error_count == 0:
            print("No followers with error status found.")
            return 0

        # Update error status to pending
        cursor = conn.execute(
            "UPDATE followers SET status = 'pending', error_message = NULL WHERE status = 'error'"
        )
        updated = cursor.rowcount
        conn.commit()

        print(f"Updated {updated} followers from error to pending status.")

        # Show status counts
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM followers GROUP BY status ORDER BY status"
        ).fetchall()
        print("\nUpdated status counts:")
        for row in rows:
            print(f"  {row['status']}: {row['cnt']}")

        return updated
    finally:
        conn.close()

if __name__ == "__main__":
    db_path = Path(__file__).parent.parent / "data" / "followers.db"
    reset_error_followers(str(db_path))
