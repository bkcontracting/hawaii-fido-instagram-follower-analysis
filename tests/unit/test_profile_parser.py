"""Tests for src/profile_parser.py — deterministic Instagram page parsing."""
from src.profile_parser import parse_count, detect_page_state, parse_profile_page


# ── parse_count ──────────────────────────────────────────────────────

class TestParseCount:
    def test_plain_integer(self):
        assert parse_count("42") == 42

    def test_commas(self):
        assert parse_count("1,234") == 1234

    def test_large_commas(self):
        assert parse_count("1,234,567") == 1234567

    def test_k_suffix_rounds(self):
        assert parse_count("1.2K") == 1000

    def test_k_lowercase_rounds(self):
        assert parse_count("1.2k") == 1000

    def test_k_rounds_up(self):
        assert parse_count("1.5K") == 2000

    def test_64_1k_rounds_to_64k(self):
        assert parse_count("64.1K") == 64000

    def test_64_9k_rounds_to_65k(self):
        assert parse_count("64.9K") == 65000

    def test_m_suffix(self):
        assert parse_count("5M") == 5000000

    def test_m_decimal_rounds(self):
        assert parse_count("2.5M") == 2000000  # banker's rounding: round(2.5) == 2

    def test_m_rounds_up(self):
        assert parse_count("2.7M") == 3000000

    def test_m_decimal_rounds_down(self):
        assert parse_count("2.3M") == 2000000

    def test_b_suffix(self):
        assert parse_count("1B") == 1000000000

    def test_none_for_empty(self):
        assert parse_count("") is None

    def test_none_for_none(self):
        assert parse_count(None) is None

    def test_none_for_garbage(self):
        assert parse_count("abc") is None

    def test_zero(self):
        assert parse_count("0") == 0

    def test_whitespace_stripped(self):
        assert parse_count("  1.5K  ") == 2000

    def test_k_with_space(self):
        assert parse_count("10 K") == 10000

    def test_whole_number_k_unchanged(self):
        assert parse_count("64K") == 64000


# ── detect_page_state ────────────────────────────────────────────────

class TestDetectPageState:
    def test_normal_page(self):
        assert detect_page_state("123 posts 456 followers 78 following") == "normal"

    def test_not_found(self):
        assert detect_page_state("Sorry, this page isn't available.") == "not_found"

    def test_user_not_found(self):
        assert detect_page_state("User not found") == "not_found"

    def test_suspended(self):
        text = "This account has been suspended for violating terms."
        assert detect_page_state(text) == "suspended"

    def test_rate_limited(self):
        assert detect_page_state("Please try again later") == "rate_limited"

    def test_rate_limited_wait(self):
        assert detect_page_state("Please wait a few minutes") == "rate_limited"

    def test_login_required(self):
        assert detect_page_state("Log in to see photos") == "login_required"

    def test_empty(self):
        assert detect_page_state("") == "not_found"

    def test_none(self):
        assert detect_page_state(None) == "not_found"


# ── parse_profile_page ──────────────────────────────────────────────

class TestParseProfilePage:
    SAMPLE_PAGE = (
        "username\n"
        "Verified badge\n"
        "42 posts 1.2K followers 345 following\n"
        "Hawaii dog rescue | Saving lives one paw at a time\n"
        "linktr.ee/hawaiidogs\n"
        "Contact Email Category: Nonprofit\n"
        "Posts\n"
    )

    def test_follower_count(self):
        result = parse_profile_page(self.SAMPLE_PAGE)
        assert result["follower_count"] == 1000

    def test_following_count(self):
        result = parse_profile_page(self.SAMPLE_PAGE)
        assert result["following_count"] == 345

    def test_post_count(self):
        result = parse_profile_page(self.SAMPLE_PAGE)
        assert result["post_count"] == 42

    def test_is_verified(self):
        result = parse_profile_page(self.SAMPLE_PAGE)
        assert result["is_verified"] is True

    def test_is_business(self):
        result = parse_profile_page(self.SAMPLE_PAGE)
        assert result["is_business"] is True

    def test_website_extracted(self):
        result = parse_profile_page(self.SAMPLE_PAGE)
        assert "linktr.ee" in result["website"]

    def test_page_state_normal(self):
        result = parse_profile_page(self.SAMPLE_PAGE)
        assert result["page_state"] == "normal"

    def test_not_found_page(self):
        result = parse_profile_page("Sorry, this page isn't available.")
        assert result["page_state"] == "not_found"
        assert result["follower_count"] is None

    def test_private_account(self):
        text = "10 posts 50 followers 30 following\nThis account is private"
        result = parse_profile_page(text)
        assert result["is_private"] is True
        assert result["follower_count"] == 50

    def test_large_counts(self):
        text = "5,432 posts 2.5M followers 123 following"
        result = parse_profile_page(text)
        assert result["post_count"] == 5432
        assert result["follower_count"] == 2000000
        assert result["following_count"] == 123

    def test_no_website(self):
        text = "10 posts 20 followers 5 following\nJust a bio"
        result = parse_profile_page(text)
        assert result["website"] == ""

    def test_instagram_url_filtered(self):
        text = "10 posts 20 followers 5 following\nhttps://instagram.com/someone"
        result = parse_profile_page(text)
        assert result["website"] == ""

    def test_not_verified_when_get_verified(self):
        text = "10 posts 20 followers 5 following\nGet verified on Instagram"
        result = parse_profile_page(text)
        assert result["is_verified"] is False

    def test_rate_limited_page(self):
        result = parse_profile_page("Please try again later")
        assert result["page_state"] == "rate_limited"
        assert result["follower_count"] is None
