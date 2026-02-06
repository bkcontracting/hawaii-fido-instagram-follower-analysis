"""Batch processing orchestrator with crash recovery and retry logic."""
import datetime
import sqlite3

from src import config
from src.database import get_pending, update_follower, get_status_counts
from src.location_detector import is_hawaii
from src.classifier import classify
from src.scorer import score


def create_batch(db_path):
    """Claim up to BATCH_SIZE pending records after crash recovery.

    Resets any 'processing' records older than 5 minutes to 'pending',
    then atomically claims pending records as 'processing'.
    Returns list of dicts, or [] when no pending records remain.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Crash recovery: reset stale processing records
    cutoff = (datetime.datetime.now() - datetime.timedelta(minutes=5)).isoformat()
    conn.execute(
        "UPDATE followers SET status = 'pending' "
        "WHERE status = 'processing' AND processed_at < ?",
        (cutoff,)
    )
    conn.commit()

    # Claim pending records atomically
    batch_size = config.BATCH_SIZE
    rows = conn.execute(
        "SELECT * FROM followers WHERE status = 'pending' LIMIT ?",
        (batch_size,)
    ).fetchall()

    batch = [dict(row) for row in rows]

    if batch:
        handles = [r["handle"] for r in batch]
        placeholders = ",".join("?" for _ in handles)
        now = datetime.datetime.now().isoformat()
        conn.execute(
            f"UPDATE followers SET status = 'processing', processed_at = ? "
            f"WHERE handle IN ({placeholders})",
            [now] + handles,
        )
        conn.commit()

    conn.close()
    return batch


def process_batch(db_path, batch, fetcher_fn):
    """Process a batch of followers through the enrichment pipeline.

    Returns {completed: int, errors: int}.
    Error on a single follower doesn't stop the batch.
    """
    completed = 0
    errors = 0

    for follower in batch:
        handle = follower["handle"]
        profile_url = follower.get("profile_url", "")
        display_name = follower.get("display_name", "")

        try:
            enriched = fetcher_fn(handle, profile_url)

            bio = enriched.get("bio") or ""
            combined_text = f"{handle} {display_name} {bio}"

            hi = is_hawaii(combined_text)

            profile = {**enriched, "handle": handle, "display_name": display_name,
                       "is_hawaii": hi}
            classification = classify(profile)
            profile["category"] = classification["category"]
            profile["subcategory"] = classification["subcategory"]

            scoring = score(profile)

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
                "status": "completed",
                "processed_at": datetime.datetime.now().isoformat(),
            }
            update_follower(db_path, handle, update_data)
            completed += 1

        except Exception as e:
            update_follower(db_path, handle, {
                "status": "error",
                "error_message": str(e),
                "processed_at": datetime.datetime.now().isoformat(),
            })
            errors += 1

    return {"completed": completed, "errors": errors}


def run_with_retries(db_path, batch, fetcher_fn):
    """Process batch with up to MAX_RETRIES total attempts.

    Returns {completed: int, errors: int, retries_used: int, exhausted: bool}.
    """
    max_retries = config.MAX_RETRIES
    total_completed = 0
    retries_used = 0

    current_batch = batch

    for attempt in range(max_retries):
        result = process_batch(db_path, current_batch, fetcher_fn)
        total_completed += result["completed"]

        if result["errors"] == 0:
            break

        if attempt < max_retries - 1:
            retries_used += 1
            # Reset error records to pending for retry
            error_handles = []
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            for follower in current_batch:
                row = conn.execute(
                    "SELECT status FROM followers WHERE handle = ?",
                    (follower["handle"],)
                ).fetchone()
                if row and row["status"] == "error":
                    error_handles.append(follower["handle"])

            for h in error_handles:
                conn.execute(
                    "UPDATE followers SET status = 'pending', error_message = NULL WHERE handle = ?",
                    (h,)
                )
            conn.commit()

            # Re-fetch the error records for retry
            current_batch = []
            for h in error_handles:
                row = conn.execute(
                    "SELECT * FROM followers WHERE handle = ?", (h,)
                ).fetchone()
                if row:
                    current_batch.append(dict(row))
            conn.close()

    # Count remaining errors
    final_errors = 0
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    for follower in batch:
        row = conn.execute(
            "SELECT status FROM followers WHERE handle = ?",
            (follower["handle"],)
        ).fetchone()
        if row and row["status"] == "error":
            final_errors += 1
    conn.close()

    return {
        "completed": total_completed,
        "errors": final_errors,
        "retries_used": retries_used,
        "exhausted": final_errors > 0,
    }


def run_all(db_path, fetcher_fn):
    """Process all pending followers in batches.

    Returns {batches_run, total_completed, total_errors, stopped, reason}.
    Stops on exhausted retries with {stopped: True, reason: "batch_exhausted"}.
    """
    batches_run = 0
    total_completed = 0
    total_errors = 0

    while True:
        batch = create_batch(db_path)
        if not batch:
            return {
                "batches_run": batches_run,
                "total_completed": total_completed,
                "total_errors": total_errors,
                "stopped": False,
                "reason": "all_complete",
            }

        batches_run += 1
        result = run_with_retries(db_path, batch, fetcher_fn)
        total_completed += result["completed"]
        total_errors += result["errors"]

        if result["exhausted"]:
            return {
                "batches_run": batches_run,
                "total_completed": total_completed,
                "total_errors": total_errors,
                "stopped": True,
                "reason": "batch_exhausted",
            }
