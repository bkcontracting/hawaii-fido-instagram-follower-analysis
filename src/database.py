"""SQLite storage for Instagram follower data."""
import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS followers (
    id              INTEGER PRIMARY KEY,
    handle          TEXT UNIQUE,
    display_name    TEXT,
    profile_url     TEXT,
    follower_count  INTEGER,
    following_count INTEGER,
    post_count      INTEGER,
    bio             TEXT,
    website         TEXT,
    is_verified     BOOLEAN,
    is_private      BOOLEAN,
    is_business     BOOLEAN,
    category        TEXT,
    subcategory     TEXT,
    location        TEXT,
    is_hawaii       BOOLEAN,
    confidence      REAL,
    priority_score  INTEGER,
    priority_reason TEXT,
    status          TEXT,
    error_message   TEXT,
    processed_at    DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

_VALID_COLUMNS = {
    "handle", "display_name", "profile_url", "follower_count",
    "following_count", "post_count", "bio", "website", "is_verified",
    "is_private", "is_business", "category", "subcategory", "location",
    "is_hawaii", "confidence", "priority_score", "priority_reason",
    "status", "error_message", "processed_at",
}


def _connect(db_path: str) -> sqlite3.Connection:
    """Open a connection with Row factory and WAL mode for concurrent access."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: str) -> None:
    """Create SQLite file and followers table. Idempotent."""
    conn = _connect(db_path)
    try:
        conn.execute(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def insert_followers(db_path: str, followers: list) -> int:
    """Insert followers, skipping duplicates by handle. Returns count inserted.

    Each follower dict must have: handle, display_name, profile_url.
    Sets status='pending'. created_at is filled by DEFAULT CURRENT_TIMESTAMP.
    """
    if not followers:
        return 0

    conn = _connect(db_path)
    try:
        inserted = 0
        for f in followers:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO followers (handle, display_name, profile_url, status) "
                "VALUES (?, ?, ?, 'pending')",
                (f["handle"], f["display_name"], f["profile_url"]),
            )
            inserted += cursor.rowcount
        conn.commit()
        return inserted
    finally:
        conn.close()


def get_pending(db_path: str, limit: int) -> list:
    """Return up to `limit` followers with status='pending' as list of dicts."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM followers WHERE status = 'pending' LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_follower(db_path: str, handle: str, data: dict) -> None:
    """Update arbitrary fields on the row matching handle."""
    if not data:
        return
    invalid = set(data) - _VALID_COLUMNS
    if invalid:
        raise ValueError(f"Invalid column(s): {invalid}")
    columns = ", ".join(f"{key} = ?" for key in data)
    values = list(data.values()) + [handle]
    conn = _connect(db_path)
    try:
        conn.execute(
            f"UPDATE followers SET {columns} WHERE handle = ?",
            values,
        )
        conn.commit()
    finally:
        conn.close()


def get_status_counts(db_path: str) -> dict:
    """Return {'pending': N, 'completed': N, 'error': N, ...} for all statuses present."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM followers GROUP BY status"
        ).fetchall()
        return {row["status"]: row["cnt"] for row in rows}
    finally:
        conn.close()
