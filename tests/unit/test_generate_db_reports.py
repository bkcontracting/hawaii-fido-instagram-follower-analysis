"""Tests for scripts/generate_db_reports.py — database-derived outreach reports.

100% coverage target: every function, every branch, every edge case.
Uses in-memory SQLite and tmp_path to avoid touching data/followers.db.
"""
import csv
import io
import sqlite3

import pytest

from scripts.generate_db_reports import (
    _bio_text,
    _enrich,
    _is_excluded,
    _is_marketing_excluded,
    _load_completed_profiles,
    _suggested_ask,
    _write_fundraising_csv,
    _write_markdown,
    _write_marketing_csv,
    generate_reports,
    _CATEGORY_TO_ENTITY,
    _CATEGORY_TO_OUTREACH,
    _EXCLUDED_CATEGORIES,
    _PET_MICRO_SUBCATEGORIES,
)


# ── Helpers ──────────────────────────────────────────────────────────

def _row(category="business_local", subcategory="general", is_hawaii=1,
         is_business=1, is_verified=0, follower_count=500, following_count=200,
         post_count=50, bio="Test bio", website="example.com", handle="test_handle",
         display_name="Test User", priority_score=70, priority_reason="hawaii(+30), local_biz(+20), business(+20)",
         **kw):
    """Build a row dict matching the DB schema."""
    d = dict(
        id=1, handle=handle, display_name=display_name,
        profile_url=f"https://instagram.com/{handle}",
        follower_count=follower_count, following_count=following_count,
        post_count=post_count, bio=bio, website=website,
        is_verified=is_verified, is_private=0, is_business=is_business,
        category=category, subcategory=subcategory, location=None,
        is_hawaii=is_hawaii, confidence=0.7, priority_score=priority_score,
        priority_reason=priority_reason, status="completed",
        error_message=None, processed_at=None, created_at=None,
    )
    d.update(kw)
    return d


_DB_SCHEMA = """
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


def _create_test_db(db_path, rows):
    """Create a test database with given rows."""
    conn = sqlite3.connect(db_path)
    conn.execute(_DB_SCHEMA)
    for i, r in enumerate(rows, 1):
        conn.execute(
            "INSERT INTO followers "
            "(id, handle, display_name, profile_url, follower_count, following_count, "
            "post_count, bio, website, is_verified, is_private, is_business, "
            "category, subcategory, location, is_hawaii, confidence, "
            "priority_score, priority_reason, status, error_message, processed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (i, r["handle"], r.get("display_name"), r.get("profile_url"),
             r.get("follower_count"), r.get("following_count"), r.get("post_count"),
             r.get("bio"), r.get("website"), r.get("is_verified"), r.get("is_private", 0),
             r.get("is_business"), r.get("category"), r.get("subcategory"),
             r.get("location"), r.get("is_hawaii"), r.get("confidence"),
             r.get("priority_score"), r.get("priority_reason"), r.get("status", "completed"),
             r.get("error_message"), r.get("processed_at")),
        )
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════════════════
# _is_excluded
# ══════════════════════════════════════════════════════════════════════

class TestIsExcluded:
    """Test hard-exclusion rules for fundraising."""

    def test_service_dog_aligned_excluded(self):
        excluded, reason = _is_excluded(_row(category="service_dog_aligned"))
        assert excluded is True
        assert reason == "EXCLUDE_competitor"

    def test_charity_excluded(self):
        excluded, reason = _is_excluded(_row(category="charity"))
        assert excluded is True
        assert reason == "EXCLUDE_nonprofit"

    def test_personal_engaged_excluded(self):
        excluded, reason = _is_excluded(_row(category="personal_engaged"))
        assert excluded is True
        assert reason == "EXCLUDE_personal"

    def test_personal_passive_excluded(self):
        excluded, reason = _is_excluded(_row(category="personal_passive"))
        assert excluded is True
        assert reason == "EXCLUDE_personal"

    def test_spam_bot_excluded(self):
        excluded, reason = _is_excluded(_row(category="spam_bot"))
        assert excluded is True
        assert reason == "EXCLUDE_spam"

    def test_unknown_excluded(self):
        excluded, reason = _is_excluded(_row(category="unknown"))
        assert excluded is True
        assert reason == "EXCLUDE_unknown"

    def test_pet_trainer_excluded(self):
        excluded, reason = _is_excluded(_row(category="pet_industry", subcategory="trainer"))
        assert excluded is True
        assert reason == "EXCLUDE_pet_micro"

    def test_pet_groomer_excluded(self):
        excluded, reason = _is_excluded(_row(category="pet_industry", subcategory="groomer"))
        assert excluded is True
        assert reason == "EXCLUDE_pet_micro"

    def test_pet_breeder_excluded(self):
        excluded, reason = _is_excluded(_row(category="pet_industry", subcategory="breeder"))
        assert excluded is True
        assert reason == "EXCLUDE_pet_micro"

    def test_pet_care_excluded(self):
        excluded, reason = _is_excluded(_row(category="pet_industry", subcategory="pet_care"))
        assert excluded is True
        assert reason == "EXCLUDE_pet_micro"

    # ── Non-excluded categories ──

    def test_corporate_not_excluded(self):
        excluded, _ = _is_excluded(_row(category="corporate"))
        assert excluded is False

    def test_bank_financial_not_excluded(self):
        excluded, _ = _is_excluded(_row(category="bank_financial"))
        assert excluded is False

    def test_organization_not_excluded(self):
        excluded, _ = _is_excluded(_row(category="organization"))
        assert excluded is False

    def test_elected_official_not_excluded(self):
        excluded, _ = _is_excluded(_row(category="elected_official"))
        assert excluded is False

    def test_business_local_not_excluded(self):
        excluded, _ = _is_excluded(_row(category="business_local"))
        assert excluded is False

    def test_business_national_not_excluded(self):
        excluded, _ = _is_excluded(_row(category="business_national"))
        assert excluded is False

    def test_media_event_not_excluded(self):
        excluded, _ = _is_excluded(_row(category="media_event"))
        assert excluded is False

    def test_influencer_not_excluded(self):
        excluded, _ = _is_excluded(_row(category="influencer"))
        assert excluded is False

    def test_pet_veterinary_not_excluded(self):
        excluded, _ = _is_excluded(_row(category="pet_industry", subcategory="veterinary"))
        assert excluded is False

    def test_pet_boarding_not_excluded(self):
        excluded, _ = _is_excluded(_row(category="pet_industry", subcategory="boarding"))
        assert excluded is False

    def test_pet_store_not_excluded(self):
        excluded, _ = _is_excluded(_row(category="pet_industry", subcategory="pet_store"))
        assert excluded is False

    def test_pet_food_not_excluded(self):
        excluded, _ = _is_excluded(_row(category="pet_industry", subcategory="pet_food"))
        assert excluded is False

    def test_pet_rehabilitation_not_excluded(self):
        excluded, _ = _is_excluded(_row(category="pet_industry", subcategory="rehabilitation"))
        assert excluded is False

    def test_pet_general_not_excluded(self):
        excluded, _ = _is_excluded(_row(category="pet_industry", subcategory="general"))
        assert excluded is False

    def test_null_category_not_excluded(self):
        excluded, _ = _is_excluded(_row(category=None, subcategory=None))
        assert excluded is False

    def test_empty_category_not_excluded(self):
        excluded, _ = _is_excluded(_row(category="", subcategory=""))
        assert excluded is False

    def test_non_excluded_returns_empty_reason(self):
        _, reason = _is_excluded(_row(category="business_local"))
        assert reason == ""


# ══════════════════════════════════════════════════════════════════════
# _is_marketing_excluded
# ══════════════════════════════════════════════════════════════════════

class TestIsMarketingExcluded:
    """Test looser exclusion rules for marketing partners."""

    def test_competitor_excluded(self):
        excluded, reason = _is_marketing_excluded(_row(category="service_dog_aligned"))
        assert excluded is True
        assert reason == "EXCLUDE_competitor"

    def test_spam_excluded(self):
        excluded, reason = _is_marketing_excluded(_row(category="spam_bot"))
        assert excluded is True
        assert reason == "EXCLUDE_spam"

    def test_personal_engaged_excluded(self):
        excluded, reason = _is_marketing_excluded(_row(category="personal_engaged"))
        assert excluded is True
        assert reason == "EXCLUDE_personal"

    def test_personal_passive_excluded(self):
        excluded, reason = _is_marketing_excluded(_row(category="personal_passive"))
        assert excluded is True
        assert reason == "EXCLUDE_personal"

    def test_unknown_excluded(self):
        excluded, reason = _is_marketing_excluded(_row(category="unknown"))
        assert excluded is True
        assert reason == "EXCLUDE_personal"

    # ── Kept for marketing (looser rules) ──

    def test_charity_kept_for_marketing(self):
        excluded, _ = _is_marketing_excluded(_row(category="charity"))
        assert excluded is False

    def test_pet_trainer_kept_for_marketing(self):
        excluded, _ = _is_marketing_excluded(_row(category="pet_industry", subcategory="trainer"))
        assert excluded is False

    def test_pet_groomer_kept_for_marketing(self):
        excluded, _ = _is_marketing_excluded(_row(category="pet_industry", subcategory="groomer"))
        assert excluded is False

    def test_pet_general_kept_for_marketing(self):
        excluded, _ = _is_marketing_excluded(_row(category="pet_industry", subcategory="general"))
        assert excluded is False

    def test_corporate_kept_for_marketing(self):
        excluded, _ = _is_marketing_excluded(_row(category="corporate"))
        assert excluded is False

    def test_organization_kept_for_marketing(self):
        excluded, _ = _is_marketing_excluded(_row(category="organization"))
        assert excluded is False

    def test_business_local_kept_for_marketing(self):
        excluded, _ = _is_marketing_excluded(_row(category="business_local"))
        assert excluded is False

    def test_null_category_kept(self):
        excluded, _ = _is_marketing_excluded(_row(category=None))
        assert excluded is False


# ══════════════════════════════════════════════════════════════════════
# _suggested_ask
# ══════════════════════════════════════════════════════════════════════

class TestSuggestedAsk:
    """Test suggested ask derivation for every outreach type and tier."""

    # ── CORPORATE_SPONSORSHIP ──

    def test_corporate_verified(self):
        assert _suggested_ask("CORPORATE_SPONSORSHIP", 100, True) == "$10,000-$25,000"

    def test_corporate_50k_followers(self):
        assert _suggested_ask("CORPORATE_SPONSORSHIP", 50000, False) == "$10,000-$25,000"

    def test_corporate_above_50k(self):
        assert _suggested_ask("CORPORATE_SPONSORSHIP", 80000, False) == "$10,000-$25,000"

    def test_corporate_10k_followers(self):
        assert _suggested_ask("CORPORATE_SPONSORSHIP", 10000, False) == "$5,000-$15,000"

    def test_corporate_30k_followers(self):
        assert _suggested_ask("CORPORATE_SPONSORSHIP", 30000, False) == "$5,000-$15,000"

    def test_corporate_default(self):
        assert _suggested_ask("CORPORATE_SPONSORSHIP", 5000, False) == "$5,000-$10,000"

    def test_corporate_zero_followers(self):
        assert _suggested_ask("CORPORATE_SPONSORSHIP", 0, False) == "$5,000-$10,000"

    def test_corporate_none_followers(self):
        assert _suggested_ask("CORPORATE_SPONSORSHIP", None, False) == "$5,000-$10,000"

    # ── TABLE_PURCHASE ──

    def test_table_5k_followers(self):
        assert _suggested_ask("TABLE_PURCHASE", 5000, False) == "$2,500-$5,000"

    def test_table_above_5k(self):
        assert _suggested_ask("TABLE_PURCHASE", 8000, False) == "$2,500-$5,000"

    def test_table_1k_followers(self):
        assert _suggested_ask("TABLE_PURCHASE", 1000, False) == "$2,000-$3,500"

    def test_table_3k_followers(self):
        assert _suggested_ask("TABLE_PURCHASE", 3000, False) == "$2,000-$3,500"

    def test_table_default(self):
        assert _suggested_ask("TABLE_PURCHASE", 500, False) == "$1,000-$3,000"

    def test_table_none_followers(self):
        assert _suggested_ask("TABLE_PURCHASE", None, False) == "$1,000-$3,000"

    # ── MEMBER_PRESENTATION ──

    def test_member_presentation(self):
        assert _suggested_ask("MEMBER_PRESENTATION", 10000, False) == "$0 (access value)"

    def test_member_presentation_ignores_followers(self):
        assert _suggested_ask("MEMBER_PRESENTATION", 0, True) == "$0 (access value)"

    # ── INDIVIDUAL_DONOR ──

    def test_individual_10k_followers(self):
        assert _suggested_ask("INDIVIDUAL_DONOR", 10000, False) == "$1,000-$2,000"

    def test_individual_above_10k(self):
        assert _suggested_ask("INDIVIDUAL_DONOR", 25000, False) == "$1,000-$2,000"

    def test_individual_1k_followers(self):
        assert _suggested_ask("INDIVIDUAL_DONOR", 1000, False) == "$500-$1,000"

    def test_individual_5k_followers(self):
        assert _suggested_ask("INDIVIDUAL_DONOR", 5000, False) == "$500-$1,000"

    def test_individual_default(self):
        assert _suggested_ask("INDIVIDUAL_DONOR", 500, False) == "$200-$500"

    def test_individual_none_followers(self):
        assert _suggested_ask("INDIVIDUAL_DONOR", None, False) == "$200-$500"

    # ── DOOR_OPENER ──

    def test_door_opener(self):
        assert _suggested_ask("DOOR_OPENER", 5000, False) == "N/A (access value)"

    def test_door_opener_ignores_followers(self):
        assert _suggested_ask("DOOR_OPENER", 0, True) == "N/A (access value)"

    # ── Unknown / SKIP ──

    def test_skip_type(self):
        assert _suggested_ask("SKIP", 1000, False) == "N/A"

    def test_unknown_type(self):
        assert _suggested_ask("SOMETHING_ELSE", 1000, False) == "N/A"

    def test_empty_type(self):
        assert _suggested_ask("", 1000, False) == "N/A"


# ══════════════════════════════════════════════════════════════════════
# _bio_text
# ══════════════════════════════════════════════════════════════════════

class TestBioText:
    """Test full bio text preservation."""

    def test_normal_bio(self):
        assert _bio_text("Hello world") == "Hello world"

    def test_multiline_bio_preserved(self):
        bio = "Line 1\nLine 2\nLine 3"
        assert _bio_text(bio) == bio

    def test_none_bio(self):
        assert _bio_text(None) == "N/A"

    def test_empty_bio(self):
        assert _bio_text("") == "N/A"

    def test_whitespace_only_bio(self):
        assert _bio_text("   \n  \n  ") == "N/A"

    def test_bio_with_leading_trailing_whitespace(self):
        assert _bio_text("  Hello  ") == "Hello"

    def test_bio_with_special_chars(self):
        bio = 'Bio with "quotes" and, commas'
        assert _bio_text(bio) == bio

    def test_bio_with_unicode(self):
        bio = "Hawai\u02bbi \u2014 Aloha \U0001f30a"
        assert _bio_text(bio) == bio

    def test_bio_with_newlines_preserved_full(self):
        bio = "Pet Service\nDoggy Daycare\n808-555-1234\nHonolulu, Hawaii"
        result = _bio_text(bio)
        assert "Pet Service" in result
        assert "Doggy Daycare" in result
        assert "808-555-1234" in result
        assert "Honolulu, Hawaii" in result


# ══════════════════════════════════════════════════════════════════════
# _enrich
# ══════════════════════════════════════════════════════════════════════

class TestEnrich:
    """Test entity type, outreach type, and suggested ask enrichment."""

    def test_corporate_mapping(self):
        p = _enrich(_row(category="corporate", follower_count=60000, is_verified=1))
        assert p["entity_type"] == "corporation"
        assert p["outreach_type"] == "CORPORATE_SPONSORSHIP"
        assert "$10,000" in p["suggested_ask"]

    def test_bank_financial_mapping(self):
        p = _enrich(_row(category="bank_financial"))
        assert p["entity_type"] == "bank_financial"
        assert p["outreach_type"] == "CORPORATE_SPONSORSHIP"

    def test_organization_mapping(self):
        p = _enrich(_row(category="organization"))
        assert p["entity_type"] == "member_organization"
        assert p["outreach_type"] == "MEMBER_PRESENTATION"
        assert "access value" in p["suggested_ask"]

    def test_elected_official_mapping(self):
        p = _enrich(_row(category="elected_official"))
        assert p["entity_type"] == "government_official"
        assert p["outreach_type"] == "DOOR_OPENER"
        assert "access value" in p["suggested_ask"]

    def test_business_local_mapping(self):
        p = _enrich(_row(category="business_local", follower_count=2000))
        assert p["entity_type"] == "established_business"
        assert p["outreach_type"] == "TABLE_PURCHASE"
        assert "$2,000" in p["suggested_ask"]

    def test_business_national_mapping(self):
        p = _enrich(_row(category="business_national"))
        assert p["entity_type"] == "established_business"
        assert p["outreach_type"] == "TABLE_PURCHASE"

    def test_media_event_mapping(self):
        p = _enrich(_row(category="media_event"))
        assert p["entity_type"] == "media_event_org"
        assert p["outreach_type"] == "DOOR_OPENER"

    def test_influencer_mapping(self):
        p = _enrich(_row(category="influencer", follower_count=15000))
        assert p["entity_type"] == "wealthy_individual"
        assert p["outreach_type"] == "INDIVIDUAL_DONOR"
        assert "$1,000" in p["suggested_ask"]

    def test_pet_industry_surviving_mapping(self):
        p = _enrich(_row(category="pet_industry", subcategory="veterinary"))
        assert p["entity_type"] == "established_business"
        assert p["outreach_type"] == "TABLE_PURCHASE"

    def test_charity_mapping(self):
        p = _enrich(_row(category="charity"))
        assert p["entity_type"] == "nonprofit"

    def test_unknown_category_fallback(self):
        p = _enrich(_row(category="some_new_category"))
        assert p["entity_type"] == "some_new_category"
        assert p["outreach_type"] == "SKIP"
        assert p["suggested_ask"] == "N/A"

    def test_null_category_fallback(self):
        p = _enrich(_row(category=None))
        assert p["entity_type"] == ""
        assert p["outreach_type"] == "SKIP"

    def test_enrich_returns_same_dict(self):
        row = _row(category="corporate")
        result = _enrich(row)
        assert result is row  # mutates in place

    def test_enrich_preserves_existing_fields(self):
        p = _enrich(_row(category="corporate", handle="test", bio="my bio"))
        assert p["handle"] == "test"
        assert p["bio"] == "my bio"


# ══════════════════════════════════════════════════════════════════════
# _load_completed_profiles
# ══════════════════════════════════════════════════════════════════════

class TestLoadCompletedProfiles:
    """Test database loading with various record states."""

    def test_loads_completed_profiles(self, tmp_path):
        db = str(tmp_path / "test.db")
        _create_test_db(db, [
            _row(handle="completed1", priority_score=80, status="completed"),
            _row(handle="completed2", priority_score=60, status="completed"),
        ])
        profiles = _load_completed_profiles(db)
        assert len(profiles) == 2
        assert profiles[0]["handle"] == "completed1"
        assert profiles[1]["handle"] == "completed2"

    def test_excludes_private_status(self, tmp_path):
        db = str(tmp_path / "test.db")
        _create_test_db(db, [
            _row(handle="public", status="completed"),
            _row(handle="private1", status="private"),
        ])
        profiles = _load_completed_profiles(db)
        assert len(profiles) == 1
        assert profiles[0]["handle"] == "public"

    def test_excludes_pending_status(self, tmp_path):
        db = str(tmp_path / "test.db")
        _create_test_db(db, [
            _row(handle="done", status="completed"),
            _row(handle="waiting", status="pending"),
        ])
        profiles = _load_completed_profiles(db)
        assert len(profiles) == 1
        assert profiles[0]["handle"] == "done"

    def test_excludes_error_status(self, tmp_path):
        db = str(tmp_path / "test.db")
        _create_test_db(db, [
            _row(handle="ok", status="completed"),
            _row(handle="failed", status="error"),
        ])
        profiles = _load_completed_profiles(db)
        assert len(profiles) == 1

    def test_ordered_by_priority_score_desc(self, tmp_path):
        db = str(tmp_path / "test.db")
        _create_test_db(db, [
            _row(handle="low", priority_score=30, status="completed"),
            _row(handle="high", priority_score=90, status="completed"),
            _row(handle="mid", priority_score=60, status="completed"),
        ])
        profiles = _load_completed_profiles(db)
        scores = [p["priority_score"] for p in profiles]
        assert scores == [90, 60, 30]

    def test_returns_dict_format(self, tmp_path):
        db = str(tmp_path / "test.db")
        _create_test_db(db, [_row(handle="test", bio="Test bio")])
        profiles = _load_completed_profiles(db)
        assert isinstance(profiles[0], dict)
        assert "handle" in profiles[0]
        assert "bio" in profiles[0]
        assert "priority_score" in profiles[0]

    def test_empty_database(self, tmp_path):
        db = str(tmp_path / "test.db")
        _create_test_db(db, [])
        profiles = _load_completed_profiles(db)
        assert profiles == []

    def test_all_columns_present(self, tmp_path):
        db = str(tmp_path / "test.db")
        _create_test_db(db, [_row()])
        profiles = _load_completed_profiles(db)
        p = profiles[0]
        expected_keys = {
            "id", "handle", "display_name", "profile_url",
            "follower_count", "following_count", "post_count",
            "bio", "website", "is_verified", "is_private", "is_business",
            "category", "subcategory", "location", "is_hawaii", "confidence",
            "priority_score", "priority_reason", "status",
            "error_message", "processed_at", "created_at",
        }
        assert expected_keys.issubset(set(p.keys()))


# ══════════════════════════════════════════════════════════════════════
# _write_markdown
# ══════════════════════════════════════════════════════════════════════

class TestWriteMarkdown:
    """Test markdown report generation."""

    def _enriched_profile(self, **kw):
        """Create an enriched profile ready for markdown writing."""
        return _enrich(_row(**kw))

    def test_heading_structure(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(handle="fund1")]
        mktg = [self._enriched_profile(handle="mktg1")]
        _write_markdown(fund, mktg, md)
        content = open(md).read()
        assert "# Hawaii Fi-Do Outreach Recommendations" in content
        assert "## Top 25 Fundraising Prospects" in content
        assert "## Top 15 Marketing Campaign Partners" in content

    def test_fundraising_section_present(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(handle="corp1", category="corporate",
                                       display_name="Big Corp")]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "### 1. Big Corp" in content
        assert "@corp1" in content

    def test_marketing_section_present(self, tmp_path):
        md = str(tmp_path / "test.md")
        mktg = [self._enriched_profile(handle="mktg1", display_name="Marketing Co")]
        _write_markdown([], mktg, md)
        content = open(md).read()
        assert "### 1. Marketing Co" in content
        assert "@mktg1" in content

    def test_followers_formatted_with_commas(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(follower_count=15000)]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "15,000" in content

    def test_followers_none_shows_na(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(follower_count=None)]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "**Followers**: N/A" in content

    def test_following_none_shows_na(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(following_count=None)]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "**Following**: N/A" in content

    def test_posts_none_shows_na(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(post_count=None)]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "**Posts**: N/A" in content

    def test_verified_yes(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(is_verified=1)]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "**Verified**: Yes" in content

    def test_verified_no(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(is_verified=0)]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "**Verified**: No" in content

    def test_business_account_yes(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(is_business=1)]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "**Business Account**: Yes" in content

    def test_business_account_no(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(is_business=0)]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "**Business Account**: No" in content

    def test_website_included_when_present(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(website="example.com")]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "**Website**: example.com" in content

    def test_website_omitted_when_empty(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(website="")]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "**Website**:" not in content

    def test_website_omitted_when_none(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(website=None)]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "**Website**:" not in content

    def test_full_bio_preserved(self, tmp_path):
        md = str(tmp_path / "test.md")
        bio = "Line 1\nLine 2\nLine 3"
        fund = [self._enriched_profile(bio=bio)]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "Line 1\nLine 2\nLine 3" in content

    def test_entity_type_shown(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(category="corporate")]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "**Entity Type**: corporation" in content

    def test_category_with_subcategory_shown(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(category="business_local", subcategory="restaurant")]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "business_local (restaurant)" in content

    def test_category_without_subcategory(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(subcategory=None)]
        _write_markdown(fund, [], md)
        content = open(md).read()
        # Should show category but no parenthetical
        assert "**Category**: business_local\n" in content

    def test_priority_score_shown(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(priority_score=85)]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "**Priority Score**: 85/100" in content

    def test_score_breakdown_shown(self, tmp_path):
        md = str(tmp_path / "test.md")
        reason = "hawaii(+30), corporate(+25)"
        fund = [self._enriched_profile(priority_reason=reason)]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "**Score Breakdown**: hawaii(+30), corporate(+25)" in content

    def test_outreach_type_shown(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(category="corporate")]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "**Outreach Type**: CORPORATE_SPONSORSHIP" in content

    def test_suggested_ask_shown(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(category="corporate")]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "**Suggested Ask**:" in content

    def test_display_name_fallback_to_handle(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(display_name=None, handle="fallback_handle")]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "### 1. fallback_handle" in content

    def test_hawaii_based_yes(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(is_hawaii=1)]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "**Hawaii-Based**: Yes" in content

    def test_hawaii_based_no(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(is_hawaii=0)]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "**Hawaii-Based**: No" in content

    def test_multiple_fundraising_numbered(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [
            self._enriched_profile(handle="first", display_name="First"),
            self._enriched_profile(handle="second", display_name="Second"),
            self._enriched_profile(handle="third", display_name="Third"),
        ]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "### 1. First" in content
        assert "### 2. Second" in content
        assert "### 3. Third" in content

    def test_multiple_marketing_numbered(self, tmp_path):
        md = str(tmp_path / "test.md")
        mktg = [
            self._enriched_profile(handle="m1", display_name="Partner A"),
            self._enriched_profile(handle="m2", display_name="Partner B"),
        ]
        _write_markdown([], mktg, md)
        content = open(md).read()
        assert "### 1. Partner A" in content
        assert "### 2. Partner B" in content

    def test_empty_lists_produce_valid_markdown(self, tmp_path):
        md = str(tmp_path / "test.md")
        _write_markdown([], [], md)
        content = open(md).read()
        assert "# Hawaii Fi-Do" in content
        assert "## Top 25 Fundraising Prospects" in content
        assert "## Top 15 Marketing Campaign Partners" in content

    def test_horizontal_rules_present(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile()]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "---" in content

    def test_marketing_has_score_breakdown(self, tmp_path):
        md = str(tmp_path / "test.md")
        reason = "hawaii(+30), pet(+25)"
        mktg = [self._enriched_profile(priority_reason=reason)]
        _write_markdown([], mktg, md)
        content = open(md).read()
        assert "**Score Breakdown**: hawaii(+30), pet(+25)" in content

    def test_null_bio_shows_na(self, tmp_path):
        md = str(tmp_path / "test.md")
        fund = [self._enriched_profile(bio=None)]
        _write_markdown(fund, [], md)
        content = open(md).read()
        assert "**Bio**: N/A" in content


# ══════════════════════════════════════════════════════════════════════
# _write_fundraising_csv
# ══════════════════════════════════════════════════════════════════════

class TestWriteFundraisingCsv:
    """Test fundraising CSV report generation."""

    def _enriched(self, **kw):
        return _enrich(_row(**kw))

    def test_correct_headers(self, tmp_path):
        csv_path = str(tmp_path / "fund.csv")
        _write_fundraising_csv([self._enriched()], csv_path)
        with open(csv_path) as f:
            reader = csv.reader(f)
            headers = next(reader)
        expected = [
            "Rank", "Handle", "Display Name", "Followers",
            "Entity Type", "Category", "Hawaii-Based",
            "Priority Score", "Score Breakdown",
            "Outreach Type", "Suggested Ask", "Website", "Bio",
        ]
        assert headers == expected

    def test_13_columns(self, tmp_path):
        csv_path = str(tmp_path / "fund.csv")
        _write_fundraising_csv([self._enriched()], csv_path)
        with open(csv_path) as f:
            reader = csv.reader(f)
            headers = next(reader)
        assert len(headers) == 13

    def test_rank_sequential(self, tmp_path):
        csv_path = str(tmp_path / "fund.csv")
        profiles = [
            self._enriched(handle=f"h{i}") for i in range(5)
        ]
        _write_fundraising_csv(profiles, csv_path)
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            ranks = [row["Rank"] for row in reader]
        assert ranks == ["1", "2", "3", "4", "5"]

    def test_hawaii_based_yes_no(self, tmp_path):
        csv_path = str(tmp_path / "fund.csv")
        profiles = [
            self._enriched(handle="hi", is_hawaii=1),
            self._enriched(handle="mainland", is_hawaii=0),
        ]
        _write_fundraising_csv(profiles, csv_path)
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert rows[0]["Hawaii-Based"] == "Yes"
        assert rows[1]["Hawaii-Based"] == "No"

    def test_full_bio_in_csv(self, tmp_path):
        csv_path = str(tmp_path / "fund.csv")
        bio = "Line 1\nLine 2\nLine 3"
        _write_fundraising_csv([self._enriched(bio=bio)], csv_path)
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert "Line 1" in row["Bio"]
        assert "Line 2" in row["Bio"]
        assert "Line 3" in row["Bio"]

    def test_empty_fields_no_none(self, tmp_path):
        csv_path = str(tmp_path / "fund.csv")
        _write_fundraising_csv([self._enriched(
            display_name=None, website=None, bio=None
        )], csv_path)
        with open(csv_path) as f:
            content = f.read()
        assert "None" not in content

    def test_bio_with_commas_quoted(self, tmp_path):
        csv_path = str(tmp_path / "fund.csv")
        bio = 'Has commas, quotes "here", and more'
        _write_fundraising_csv([self._enriched(bio=bio)], csv_path)
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert row["Bio"] == bio

    def test_creates_parent_dirs(self, tmp_path):
        csv_path = str(tmp_path / "deep" / "nested" / "fund.csv")
        _write_fundraising_csv([self._enriched()], csv_path)
        assert open(csv_path).readable()

    def test_entity_type_in_output(self, tmp_path):
        csv_path = str(tmp_path / "fund.csv")
        _write_fundraising_csv([self._enriched(category="corporate")], csv_path)
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert row["Entity Type"] == "corporation"

    def test_outreach_type_in_output(self, tmp_path):
        csv_path = str(tmp_path / "fund.csv")
        _write_fundraising_csv([self._enriched(category="organization")], csv_path)
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert row["Outreach Type"] == "MEMBER_PRESENTATION"

    def test_empty_list_writes_header_only(self, tmp_path):
        csv_path = str(tmp_path / "fund.csv")
        _write_fundraising_csv([], csv_path)
        with open(csv_path) as f:
            lines = f.readlines()
        assert len(lines) == 1  # header only

    def test_follower_count_zero(self, tmp_path):
        csv_path = str(tmp_path / "fund.csv")
        _write_fundraising_csv([self._enriched(follower_count=0)], csv_path)
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            row = next(reader)
        # 0 is falsy — gets written as empty string via `or ""`
        assert row["Followers"] == ""


# ══════════════════════════════════════════════════════════════════════
# _write_marketing_csv
# ══════════════════════════════════════════════════════════════════════

class TestWriteMarketingCsv:
    """Test marketing partners CSV report generation."""

    def _enriched(self, **kw):
        return _enrich(_row(**kw))

    def test_correct_headers(self, tmp_path):
        csv_path = str(tmp_path / "mktg.csv")
        _write_marketing_csv([self._enriched()], csv_path)
        with open(csv_path) as f:
            reader = csv.reader(f)
            headers = next(reader)
        expected = [
            "Rank", "Handle", "Display Name", "Followers",
            "Entity Type", "Hawaii-Based", "Priority Score",
            "Score Breakdown", "Website", "Bio",
        ]
        assert headers == expected

    def test_10_columns(self, tmp_path):
        csv_path = str(tmp_path / "mktg.csv")
        _write_marketing_csv([self._enriched()], csv_path)
        with open(csv_path) as f:
            reader = csv.reader(f)
            headers = next(reader)
        assert len(headers) == 10

    def test_rank_sequential(self, tmp_path):
        csv_path = str(tmp_path / "mktg.csv")
        profiles = [self._enriched(handle=f"m{i}") for i in range(3)]
        _write_marketing_csv(profiles, csv_path)
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            ranks = [row["Rank"] for row in reader]
        assert ranks == ["1", "2", "3"]

    def test_full_bio_in_csv(self, tmp_path):
        csv_path = str(tmp_path / "mktg.csv")
        bio = "Multi\nLine\nBio"
        _write_marketing_csv([self._enriched(bio=bio)], csv_path)
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert "Multi" in row["Bio"]
        assert "Line" in row["Bio"]

    def test_hawaii_based_formatting(self, tmp_path):
        csv_path = str(tmp_path / "mktg.csv")
        _write_marketing_csv([self._enriched(is_hawaii=1)], csv_path)
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert row["Hawaii-Based"] == "Yes"

    def test_score_breakdown_in_output(self, tmp_path):
        csv_path = str(tmp_path / "mktg.csv")
        reason = "hawaii(+30), pet(+25)"
        _write_marketing_csv([self._enriched(priority_reason=reason)], csv_path)
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert row["Score Breakdown"] == reason

    def test_creates_parent_dirs(self, tmp_path):
        csv_path = str(tmp_path / "sub" / "mktg.csv")
        _write_marketing_csv([self._enriched()], csv_path)
        assert open(csv_path).readable()

    def test_empty_list_writes_header_only(self, tmp_path):
        csv_path = str(tmp_path / "mktg.csv")
        _write_marketing_csv([], csv_path)
        with open(csv_path) as f:
            lines = f.readlines()
        assert len(lines) == 1


# ══════════════════════════════════════════════════════════════════════
# generate_reports (integration)
# ══════════════════════════════════════════════════════════════════════

class TestGenerateReports:
    """End-to-end integration tests."""

    def _make_db(self, tmp_path, rows):
        db = str(tmp_path / "test.db")
        _create_test_db(db, rows)
        return db

    def _output_paths(self, tmp_path):
        return (
            str(tmp_path / "recs.md"),
            str(tmp_path / "fund.csv"),
            str(tmp_path / "mktg.csv"),
        )

    def test_three_files_created(self, tmp_path):
        db = self._make_db(tmp_path, [
            _row(handle=f"biz{i}", category="business_local", priority_score=80-i,
                 follower_count=1000+i)
            for i in range(5)
        ])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        assert open(md).read()
        assert open(fc).read()
        assert open(mc).read()

    def test_exclusions_applied_to_fundraising(self, tmp_path):
        db = self._make_db(tmp_path, [
            _row(handle="good_biz", category="business_local", priority_score=90, follower_count=5000),
            _row(handle="competitor", category="service_dog_aligned", priority_score=85, follower_count=4000),
            _row(handle="nonprofit", category="charity", priority_score=80, follower_count=3000),
            _row(handle="spam", category="spam_bot", priority_score=0, follower_count=100),
            _row(handle="personal", category="personal_engaged", priority_score=50, follower_count=200),
            _row(handle="micro_groomer", category="pet_industry", subcategory="groomer",
                 priority_score=75, follower_count=1500),
        ])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        with open(fc) as f:
            content = f.read()
        assert "good_biz" in content
        assert "competitor" not in content
        assert "nonprofit" not in content
        assert "spam" not in content
        assert "personal" not in content
        assert "micro_groomer" not in content

    def test_marketing_keeps_pet_businesses(self, tmp_path):
        db = self._make_db(tmp_path, [
            _row(handle="pet_biz", category="pet_industry", subcategory="boarding",
                 priority_score=70, follower_count=5000),
            _row(handle="pet_groomer", category="pet_industry", subcategory="groomer",
                 priority_score=70, follower_count=4000),
            _row(handle="charity_org", category="charity", priority_score=60, follower_count=3000),
        ])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        with open(mc) as f:
            content = f.read()
        assert "pet_biz" in content
        assert "pet_groomer" in content
        assert "charity_org" in content

    def test_marketing_excludes_competitors(self, tmp_path):
        db = self._make_db(tmp_path, [
            _row(handle="competitor", category="service_dog_aligned",
                 priority_score=80, follower_count=5000),
            _row(handle="biz", category="business_local",
                 priority_score=70, follower_count=3000),
        ])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        with open(mc) as f:
            content = f.read()
        assert "competitor" not in content
        assert "biz" in content

    def test_fundraising_top_25_by_score(self, tmp_path):
        rows = [
            _row(handle=f"biz{i}", category="business_local",
                 priority_score=100-i, follower_count=1000+i)
            for i in range(30)
        ]
        db = self._make_db(tmp_path, rows)
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        with open(fc) as f:
            reader = csv.DictReader(f)
            handles = [row["Handle"] for row in reader]
        assert len(handles) == 25
        assert handles[0] == "biz0"  # highest score
        assert "biz25" not in handles  # 26th not included

    def test_marketing_top_15_by_followers(self, tmp_path):
        rows = [
            _row(handle=f"biz{i}", category="business_local",
                 priority_score=50, follower_count=20000-i*1000)
            for i in range(20)
        ]
        db = self._make_db(tmp_path, rows)
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        with open(mc) as f:
            reader = csv.DictReader(f)
            handles = [row["Handle"] for row in reader]
        assert len(handles) == 15
        assert handles[0] == "biz0"   # most followers (20000)
        assert "biz15" not in handles  # 16th not included

    def test_fewer_than_25_fundraising(self, tmp_path):
        db = self._make_db(tmp_path, [
            _row(handle=f"biz{i}", category="business_local",
                 priority_score=80-i, follower_count=1000)
            for i in range(3)
        ])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        with open(fc) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 3

    def test_fewer_than_15_marketing(self, tmp_path):
        db = self._make_db(tmp_path, [
            _row(handle=f"biz{i}", category="business_local",
                 priority_score=50, follower_count=1000)
            for i in range(5)
        ])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        with open(mc) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 5

    def test_all_excluded_empty_output(self, tmp_path):
        db = self._make_db(tmp_path, [
            _row(handle="spam1", category="spam_bot", priority_score=0, follower_count=10),
            _row(handle="personal1", category="personal_engaged", priority_score=30, follower_count=100),
        ])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        with open(fc) as f:
            reader = csv.DictReader(f)
            assert list(reader) == []

    def test_entity_types_in_output(self, tmp_path):
        db = self._make_db(tmp_path, [
            _row(handle="corp", category="corporate", priority_score=90, follower_count=50000),
            _row(handle="org", category="organization", priority_score=80, follower_count=5000),
            _row(handle="official", category="elected_official", priority_score=75, follower_count=3000),
        ])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        with open(fc) as f:
            reader = csv.DictReader(f)
            types = {row["Entity Type"] for row in reader}
        assert "corporation" in types
        assert "member_organization" in types
        assert "government_official" in types

    def test_outreach_types_in_output(self, tmp_path):
        db = self._make_db(tmp_path, [
            _row(handle="corp", category="corporate", priority_score=90, follower_count=50000),
            _row(handle="org", category="organization", priority_score=80, follower_count=5000),
        ])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        with open(fc) as f:
            reader = csv.DictReader(f)
            types = {row["Outreach Type"] for row in reader}
        assert "CORPORATE_SPONSORSHIP" in types
        assert "MEMBER_PRESENTATION" in types

    def test_markdown_contains_both_sections(self, tmp_path):
        db = self._make_db(tmp_path, [
            _row(handle="biz1", category="business_local", priority_score=80,
                 follower_count=5000, display_name="Local Biz"),
        ])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        content = open(md).read()
        assert "## Top 25 Fundraising Prospects" in content
        assert "## Top 15 Marketing Campaign Partners" in content
        assert "Local Biz" in content

    def test_bio_with_newlines_in_csv(self, tmp_path):
        bio = "First line\nSecond line\nThird line"
        db = self._make_db(tmp_path, [
            _row(handle="biz1", category="business_local", priority_score=80,
                 follower_count=1000, bio=bio),
        ])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        with open(fc) as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert "First line" in row["Bio"]
        assert "Second line" in row["Bio"]

    def test_null_fields_handled(self, tmp_path):
        db = self._make_db(tmp_path, [
            _row(handle="minimal", category="business_local", priority_score=50,
                 follower_count=None, following_count=None, post_count=None,
                 bio=None, website=None, display_name=None, is_verified=0, is_business=0),
        ])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        content = open(md).read()
        assert "**Bio**: N/A" in content
        assert "**Followers**: N/A" in content

    def test_private_profiles_excluded_from_db_load(self, tmp_path):
        db = self._make_db(tmp_path, [
            _row(handle="public", category="business_local", priority_score=80,
                 follower_count=1000, status="completed"),
            _row(handle="private", category="business_local", priority_score=90,
                 follower_count=2000, status="private"),
        ])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        with open(fc) as f:
            content = f.read()
        assert "public" in content
        assert "private" not in content

    def test_empty_database(self, tmp_path):
        db = self._make_db(tmp_path, [])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        # Should produce files with headers/structure but no data rows
        with open(fc) as f:
            reader = csv.DictReader(f)
            assert list(reader) == []
        content = open(md).read()
        assert "# Hawaii Fi-Do" in content


# ══════════════════════════════════════════════════════════════════════
# Constants validation
# ══════════════════════════════════════════════════════════════════════

class TestConstants:
    """Verify mapping constants are complete and consistent."""

    def test_all_excluded_categories_in_set(self):
        expected = {"service_dog_aligned", "charity", "spam_bot",
                    "personal_engaged", "personal_passive", "unknown"}
        assert _EXCLUDED_CATEGORIES == expected

    def test_pet_micro_subcategories(self):
        expected = {"trainer", "groomer", "breeder", "pet_care"}
        assert _PET_MICRO_SUBCATEGORIES == expected

    def test_entity_map_covers_scoreable_categories(self):
        scoreable = {"corporate", "bank_financial", "organization",
                     "elected_official", "business_local", "business_national",
                     "media_event", "influencer", "pet_industry"}
        for cat in scoreable:
            assert cat in _CATEGORY_TO_ENTITY, f"{cat} missing from entity map"

    def test_outreach_map_covers_scoreable_categories(self):
        scoreable = {"corporate", "bank_financial", "organization",
                     "elected_official", "business_local", "business_national",
                     "media_event", "influencer", "pet_industry"}
        for cat in scoreable:
            assert cat in _CATEGORY_TO_OUTREACH, f"{cat} missing from outreach map"

    def test_entity_types_match_ai_plan(self):
        ai_plan_types = {"corporation", "bank_financial", "member_organization",
                         "government_official", "established_business",
                         "wealthy_individual", "media_event_org"}
        mapped_types = set(_CATEGORY_TO_ENTITY.values()) - {"nonprofit"}
        assert mapped_types == ai_plan_types

    def test_outreach_types_match_ai_plan(self):
        ai_plan_types = {"CORPORATE_SPONSORSHIP", "TABLE_PURCHASE",
                         "MEMBER_PRESENTATION", "INDIVIDUAL_DONOR", "DOOR_OPENER"}
        mapped_types = set(_CATEGORY_TO_OUTREACH.values())
        assert mapped_types == ai_plan_types


# ══════════════════════════════════════════════════════════════════════
# Additional generate_reports coverage
# ══════════════════════════════════════════════════════════════════════

class TestGenerateReportsPrintOutput:
    """Cover print statements and edge cases in generate_reports."""

    def _make_db(self, tmp_path, rows):
        db = str(tmp_path / "test.db")
        _create_test_db(db, rows)
        return db

    def _output_paths(self, tmp_path):
        return (
            str(tmp_path / "recs.md"),
            str(tmp_path / "fund.csv"),
            str(tmp_path / "mktg.csv"),
        )

    def test_loading_message_printed(self, tmp_path, capsys):
        """generate_reports prints loading message."""
        db = self._make_db(tmp_path, [
            _row(handle="biz1", category="business_local", priority_score=70),
        ])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        captured = capsys.readouterr()
        assert "Loading profiles from database..." in captured.out
        assert "Loaded 1 completed profiles" in captured.out

    def test_exclusion_counts_printed(self, tmp_path, capsys):
        """Exclusion counts are printed in output."""
        db = self._make_db(tmp_path, [
            _row(handle="biz1", category="business_local", priority_score=70),
            _row(handle="spam1", category="spam_bot", priority_score=0),
        ])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        captured = capsys.readouterr()
        assert "EXCLUDE_spam: 1" in captured.out

    def test_no_fundraising_prospects_message(self, tmp_path, capsys):
        """When all are excluded from fundraising, print 'no prospects' message."""
        db = self._make_db(tmp_path, [
            _row(handle="spam1", category="spam_bot", priority_score=0, follower_count=10),
        ])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        captured = capsys.readouterr()
        assert "No scoreable fundraising prospects found." in captured.out

    def test_no_marketing_partners_message(self, tmp_path, capsys):
        """When all are excluded from marketing, print 'no partners' message."""
        db = self._make_db(tmp_path, [
            _row(handle="spam1", category="spam_bot", priority_score=0, follower_count=10),
        ])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        captured = capsys.readouterr()
        assert "No scoreable marketing partners found." in captured.out

    def test_marketing_display_name_none_fallback(self, tmp_path):
        """Marketing report uses handle as fallback when display_name is None."""
        db = self._make_db(tmp_path, [
            _row(handle="fallback_handle", display_name=None,
                 category="business_local", priority_score=70, follower_count=5000),
        ])
        md, fc, mc = self._output_paths(tmp_path)
        generate_reports(db, md, fc, mc)
        content = open(md).read()
        # In the marketing section, the name should fallback to handle
        assert "fallback_handle" in content
