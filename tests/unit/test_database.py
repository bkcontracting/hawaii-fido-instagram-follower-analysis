"""Tests for src/database.py — SQLite storage for follower data."""
import sqlite3


# ---------------------------------------------------------------------------
# 2.1  Schema — init_db
# ---------------------------------------------------------------------------

EXPECTED_COLUMNS = {
    "id": "INTEGER",
    "handle": "TEXT",
    "display_name": "TEXT",
    "profile_url": "TEXT",
    "follower_count": "INTEGER",
    "following_count": "INTEGER",
    "post_count": "INTEGER",
    "bio": "TEXT",
    "website": "TEXT",
    "is_verified": "BOOLEAN",
    "is_private": "BOOLEAN",
    "is_business": "BOOLEAN",
    "category": "TEXT",
    "subcategory": "TEXT",
    "location": "TEXT",
    "is_hawaii": "BOOLEAN",
    "confidence": "REAL",
    "priority_score": "INTEGER",
    "priority_reason": "TEXT",
    "status": "TEXT",
    "error_message": "TEXT",
    "processed_at": "DATETIME",
    "created_at": "DATETIME",
}


def test_init_db_creates_file(tmp_path):
    """init_db creates a SQLite file at the given path."""
    from src.database import init_db

    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    # File should exist and be a valid SQLite DB
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='followers'"
    )
    assert cursor.fetchone() is not None
    conn.close()


def test_init_db_has_all_22_columns(tmp_path):
    """followers table must have exactly the 22 specified columns."""
    from src.database import init_db

    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("PRAGMA table_info(followers)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}
    conn.close()

    assert len(columns) == 23
    for col_name, col_type in EXPECTED_COLUMNS.items():
        assert col_name in columns, f"Missing column: {col_name}"
        assert columns[col_name] == col_type, (
            f"Column {col_name} type mismatch: expected {col_type}, got {columns[col_name]}"
        )


def test_init_db_id_is_primary_key(tmp_path):
    """id column must be the primary key."""
    from src.database import init_db

    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("PRAGMA table_info(followers)")
    for row in cursor.fetchall():
        if row[1] == "id":
            assert row[5] == 1, "id column must be primary key (pk=1)"
            break
    else:
        raise AssertionError("id column not found")
    conn.close()


def test_init_db_handle_is_unique(tmp_path):
    """handle column must have a UNIQUE constraint."""
    from src.database import init_db

    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("PRAGMA index_list(followers)")
    indexes = cursor.fetchall()

    # Find a unique index that covers 'handle'
    found_unique_handle = False
    for idx in indexes:
        idx_name = idx[1]
        is_unique = idx[2]
        if is_unique:
            idx_info = conn.execute(f"PRAGMA index_info({idx_name})").fetchall()
            col_names = [info[2] for info in idx_info]
            if "handle" in col_names:
                found_unique_handle = True
                break
    conn.close()

    assert found_unique_handle, "handle column must have a UNIQUE constraint"


def test_init_db_created_at_default(tmp_path):
    """created_at column must have DEFAULT CURRENT_TIMESTAMP."""
    from src.database import init_db

    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("PRAGMA table_info(followers)")
    for row in cursor.fetchall():
        if row[1] == "created_at":
            assert row[4] is not None, "created_at must have a default value"
            assert "CURRENT_TIMESTAMP" in str(row[4]).upper(), (
                "created_at default must be CURRENT_TIMESTAMP"
            )
            break
    else:
        raise AssertionError("created_at column not found")
    conn.close()


def test_init_db_idempotent(tmp_path):
    """Calling init_db twice on the same path must not error."""
    from src.database import init_db

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    init_db(db_path)  # Should not raise


# ---------------------------------------------------------------------------
# 2.2  Insert — insert_followers
# ---------------------------------------------------------------------------

SAMPLE_FOLLOWERS = [
    {"handle": "alice_dog", "display_name": "Alice D", "profile_url": "https://instagram.com/alice_dog"},
    {"handle": "bob_pup", "display_name": "Bob P", "profile_url": "https://instagram.com/bob_pup"},
    {"handle": "carol_k9", "display_name": "Carol K", "profile_url": "https://instagram.com/carol_k9"},
]


def test_insert_followers_returns_count(tmp_path):
    """insert_followers returns the number of rows inserted."""
    from src.database import init_db, insert_followers

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    count = insert_followers(db_path, SAMPLE_FOLLOWERS)
    assert count == 3


def test_insert_followers_stores_data(tmp_path):
    """Inserted records appear in the database with correct fields."""
    from src.database import init_db, insert_followers

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    insert_followers(db_path, SAMPLE_FOLLOWERS)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM followers ORDER BY handle").fetchall()
    conn.close()

    assert len(rows) == 3
    assert rows[0]["handle"] == "alice_dog"
    assert rows[0]["display_name"] == "Alice D"
    assert rows[0]["profile_url"] == "https://instagram.com/alice_dog"


def test_insert_followers_sets_status_pending(tmp_path):
    """Every inserted follower has status='pending'."""
    from src.database import init_db, insert_followers

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    insert_followers(db_path, SAMPLE_FOLLOWERS)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT status FROM followers").fetchall()
    conn.close()

    for row in rows:
        assert row["status"] == "pending"


def test_insert_followers_sets_created_at(tmp_path):
    """created_at should be auto-populated by DEFAULT CURRENT_TIMESTAMP."""
    from src.database import init_db, insert_followers

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    insert_followers(db_path, SAMPLE_FOLLOWERS)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT created_at FROM followers").fetchall()
    conn.close()

    for row in rows:
        assert row["created_at"] is not None


def test_insert_followers_skips_duplicates(tmp_path):
    """Inserting the same followers twice returns 0 the second time."""
    from src.database import init_db, insert_followers

    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    first = insert_followers(db_path, SAMPLE_FOLLOWERS)
    assert first == 3

    second = insert_followers(db_path, SAMPLE_FOLLOWERS)
    assert second == 0


def test_insert_followers_partial_duplicates(tmp_path):
    """When some handles are new and some already exist, only new ones count."""
    from src.database import init_db, insert_followers

    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    insert_followers(db_path, SAMPLE_FOLLOWERS[:2])
    count = insert_followers(db_path, SAMPLE_FOLLOWERS)
    assert count == 1  # Only carol_k9 is new


def test_insert_followers_empty_list(tmp_path):
    """Inserting an empty list returns 0."""
    from src.database import init_db, insert_followers

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    count = insert_followers(db_path, [])
    assert count == 0


# ---------------------------------------------------------------------------
# 2.3  Queries — get_pending, update_follower, get_status_counts
# ---------------------------------------------------------------------------

def test_get_pending_returns_pending_only(tmp_path):
    """get_pending returns only followers with status='pending'."""
    from src.database import init_db, insert_followers, get_pending, update_follower

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    insert_followers(db_path, SAMPLE_FOLLOWERS)

    # Mark one as completed
    update_follower(db_path, "alice_dog", {"status": "completed"})

    pending = get_pending(db_path, limit=10)
    handles = [row["handle"] for row in pending]
    assert "alice_dog" not in handles
    assert len(pending) == 2


def test_get_pending_respects_limit(tmp_path):
    """get_pending returns at most `limit` rows."""
    from src.database import init_db, insert_followers, get_pending

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    insert_followers(db_path, SAMPLE_FOLLOWERS)

    pending = get_pending(db_path, limit=2)
    assert len(pending) == 2


def test_get_pending_returns_dicts(tmp_path):
    """get_pending returns list of dicts (not Row objects or tuples)."""
    from src.database import init_db, insert_followers, get_pending

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    insert_followers(db_path, SAMPLE_FOLLOWERS)

    pending = get_pending(db_path, limit=1)
    assert len(pending) == 1
    assert isinstance(pending[0], dict)
    assert "handle" in pending[0]


def test_get_pending_empty_when_none(tmp_path):
    """get_pending returns empty list when no pending followers exist."""
    from src.database import init_db, get_pending

    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    pending = get_pending(db_path, limit=10)
    assert pending == []


def test_update_follower_status(tmp_path):
    """update_follower can change a follower's status."""
    from src.database import init_db, insert_followers, update_follower

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    insert_followers(db_path, SAMPLE_FOLLOWERS)

    update_follower(db_path, "bob_pup", {"status": "completed"})

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT status FROM followers WHERE handle = ?", ("bob_pup",)
    ).fetchone()
    conn.close()

    assert row["status"] == "completed"


def test_update_follower_category(tmp_path):
    """update_follower can set category field."""
    from src.database import init_db, insert_followers, update_follower

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    insert_followers(db_path, SAMPLE_FOLLOWERS)

    update_follower(db_path, "carol_k9", {"category": "dog_lover", "subcategory": "trainer"})

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT category, subcategory FROM followers WHERE handle = ?", ("carol_k9",)
    ).fetchone()
    conn.close()

    assert row["category"] == "dog_lover"
    assert row["subcategory"] == "trainer"


def test_update_follower_multiple_fields(tmp_path):
    """update_follower can set multiple arbitrary fields at once."""
    from src.database import init_db, insert_followers, update_follower

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    insert_followers(db_path, SAMPLE_FOLLOWERS)

    update_follower(db_path, "alice_dog", {
        "bio": "Dog mom in Honolulu",
        "is_hawaii": True,
        "confidence": 0.95,
        "priority_score": 85,
        "status": "completed",
    })

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT bio, is_hawaii, confidence, priority_score, status FROM followers WHERE handle = ?",
        ("alice_dog",),
    ).fetchone()
    conn.close()

    assert row["bio"] == "Dog mom in Honolulu"
    assert row["is_hawaii"] == 1  # SQLite stores booleans as integers
    assert row["confidence"] == 0.95
    assert row["priority_score"] == 85
    assert row["status"] == "completed"


def test_get_status_counts(tmp_path):
    """get_status_counts returns dict of status -> count."""
    from src.database import init_db, insert_followers, update_follower, get_status_counts

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    insert_followers(db_path, SAMPLE_FOLLOWERS)

    # All start as pending
    counts = get_status_counts(db_path)
    assert counts == {"pending": 3}

    # Move one to completed, one to error
    update_follower(db_path, "alice_dog", {"status": "completed"})
    update_follower(db_path, "bob_pup", {"status": "error"})

    counts = get_status_counts(db_path)
    assert counts == {"pending": 1, "completed": 1, "error": 1}


def test_get_status_counts_empty(tmp_path):
    """get_status_counts returns empty dict when table is empty."""
    from src.database import init_db, get_status_counts

    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    counts = get_status_counts(db_path)
    assert counts == {}
