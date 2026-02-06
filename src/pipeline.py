"""Pipeline runners for Phase 1 (CSV import) and Phase 2 (enrichment)."""
from src.csv_parser import parse_followers
from src.database import init_db, insert_followers
from src.batch_orchestrator import run_all


def run_phase1(csv_path, db_path):
    """Parse CSV, init DB, insert followers. Idempotent.

    Returns {inserted: int}.
    """
    followers = parse_followers(csv_path)
    init_db(db_path)
    count = insert_followers(db_path, followers)
    return {"inserted": count}


def run_phase2(db_path, fetcher_fn):
    """Run enrichment on all pending followers.

    Returns {batches_run, total_completed, total_errors, stopped, reason}.
    """
    result = run_all(db_path, fetcher_fn)
    return {
        "batches_run": result["batches_run"],
        "total_completed": result["total_completed"],
        "total_errors": result["total_errors"],
        "stopped": result["stopped"],
        "reason": result["reason"],
    }
