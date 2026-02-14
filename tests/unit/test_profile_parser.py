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

    def test_k_suffix(self):
        assert parse_count("1.2K") == 1200

    def test_k_lowercase(self):
        assert parse_count("1.2k") == 1200

    def test_64_1k_preserves_precision(self):
        assert parse_count("64.1K") == 64100

    def test_k_whole_number(self):
        assert parse_count("64K") == 64000

    def test_m_suffix(self):
        assert parse_count("5M") == 5000000

    def test_m_decimal(self):
        assert parse_count("2.5M") == 2500000

    def test_m_decimal_small(self):
        assert parse_count("2.3M") == 2300000

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
        assert parse_count("  1.5K  ") == 1500

    def test_k_with_space(self):
        assert parse_count("10 K") == 10000


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
        assert result["follower_count"] == 1200

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
        assert result["follower_count"] == 2500000
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


# ── Additional parse_count coverage ──────────────────────────────────

class TestParseCountNonString:
    """Cover the `not isinstance(text, str)` branch."""

    def test_integer_input_returns_none(self):
        assert parse_count(42) is None

    def test_float_input_returns_none(self):
        assert parse_count(3.14) is None

    def test_list_input_returns_none(self):
        assert parse_count([]) is None


# ── Additional detect_page_state coverage ────────────────────────────

class TestDetectPageStateAdditional:
    """Cover branches not exercised by existing tests."""

    def test_suspended_via_violat_keyword(self):
        """'suspended' + 'violat' path (second branch of OR)."""
        assert detect_page_state("This page is suspended for policy violating behavior") == "suspended"

    def test_rate_limit_keyword(self):
        """'rate limit' keyword path."""
        assert detect_page_state("You hit the rate limit") == "rate_limited"


# ── Additional parse_profile_page coverage ───────────────────────────

class TestParseProfilePageAdditional:
    """Cover additional branches in parse_profile_page."""

    def test_bio_over_500_chars_not_extracted(self):
        """Bio longer than 500 characters should not be extracted."""
        long_bio = "A" * 501
        text = f"10 posts 20 followers 5 following\n{long_bio}\nsome posts"
        result = parse_profile_page(text)
        assert result["bio"] == ""

    def test_followed_by_line_stripped(self):
        """'Followed by ...' lines should be removed from bio."""
        text = (
            "10 posts 20 followers 5 following\n"
            "My cool bio\n"
            "Followed by user1, user2\n"
            "some posts"
        )
        result = parse_profile_page(text)
        assert "Followed by" not in result["bio"]
        assert "My cool bio" in result["bio"]

    def test_business_via_shop_now(self):
        text = "10 posts 20 followers 5 following\nShop Now\nsome posts"
        result = parse_profile_page(text)
        assert result["is_business"] is True

    def test_business_via_view_shop(self):
        text = "10 posts 20 followers 5 following\nView Shop\nsome posts"
        result = parse_profile_page(text)
        assert result["is_business"] is True

    def test_business_via_shopping(self):
        text = "10 posts 20 followers 5 following\nShopping available\nsome posts"
        result = parse_profile_page(text)
        assert result["is_business"] is True
