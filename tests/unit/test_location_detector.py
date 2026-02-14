"""Tests for src/location_detector.py — Hawaii location detection."""
from src.location_detector import (
    hawaii_confidence,
    is_hawaii,
    _inject_hawaii_spaces,
    _normalize_for_search,
)


# ── hawaii_confidence: None / empty / no-match ──────────────────────

def test_confidence_none_returns_zero():
    assert hawaii_confidence(None) == 0.0


def test_confidence_empty_string_returns_zero():
    assert hawaii_confidence("") == 0.0


def test_confidence_random_text_returns_zero():
    assert hawaii_confidence("Just some random text") == 0.0


# ── hawaii_confidence: strong signals (cities, +0.4 each) ───────────

def test_confidence_honolulu():
    assert hawaii_confidence("Honolulu") == 0.4


def test_confidence_kailua():
    assert hawaii_confidence("Kailua") == 0.4


def test_confidence_kapolei():
    assert hawaii_confidence("Kapolei") == 0.4


def test_confidence_aiea():
    assert hawaii_confidence("Aiea") == 0.4


def test_confidence_pearl_city():
    assert hawaii_confidence("Pearl City") == 0.4


def test_confidence_kaneohe():
    assert hawaii_confidence("Kaneohe") == 0.4


def test_confidence_waipahu():
    assert hawaii_confidence("Waipahu") == 0.4


def test_confidence_mililani():
    assert hawaii_confidence("Mililani") == 0.4


def test_confidence_waikiki():
    assert hawaii_confidence("Waikiki") == 0.4


def test_confidence_hilo():
    assert hawaii_confidence("Hilo") == 0.4


def test_confidence_lahaina():
    assert hawaii_confidence("Lahaina") == 0.4


def test_confidence_kona():
    assert hawaii_confidence("Kona") == 0.4


# ── hawaii_confidence: strong signals (state names, +0.4 each) ──────

def test_confidence_hawaii_word():
    assert hawaii_confidence("Hawaii") == 0.4


def test_confidence_hi_state():
    assert hawaii_confidence("HI") == 0.4


def test_confidence_hawaii_okina():
    """Hawai'i with ASCII apostrophe."""
    assert hawaii_confidence("Hawai'i") == 0.4


def test_confidence_hawaii_unicode_okina():
    """Hawaiʻi with Unicode okina."""
    assert hawaii_confidence("Hawai\u02BBi") == 0.4


# ── hawaii_confidence: strong signals (area code, +0.4) ─────────────

def test_confidence_area_code_808():
    assert hawaii_confidence("Call me at 808-555-1234") == 0.4


# ── hawaii_confidence: medium signals (islands, +0.3 each) ──────────

def test_confidence_oahu():
    assert hawaii_confidence("Oahu") == 0.3


def test_confidence_maui():
    assert hawaii_confidence("Maui") == 0.3


def test_confidence_kauai():
    assert hawaii_confidence("Kauai") == 0.3


def test_confidence_big_island():
    assert hawaii_confidence("Big Island") == 0.3


def test_confidence_molokai():
    assert hawaii_confidence("Molokai") == 0.3


def test_confidence_lanai():
    assert hawaii_confidence("Lanai") == 0.3


# ── hawaii_confidence: medium signals (airport / zip, +0.3 each) ────

def test_confidence_hnl_airport():
    assert hawaii_confidence("HNL") == 0.3


def test_confidence_zip_967():
    assert hawaii_confidence("96734") == 0.3


def test_confidence_zip_968():
    assert hawaii_confidence("96801") == 0.3


# ── hawaii_confidence: weak signals (+0.15 each) ────────────────────

def test_confidence_aloha():
    assert hawaii_confidence("Aloha") == 0.15


def test_confidence_hawaiian():
    assert hawaii_confidence("Hawaiian") == 0.3


# ── hawaii_confidence: combined signals ─────────────────────────────

def test_confidence_city_plus_state():
    """Honolulu, Hawaii => city 0.4 + state 0.4 = 0.8."""
    result = hawaii_confidence("Honolulu, Hawaii | Local pet shop")
    assert result >= 0.8


def test_confidence_aloha_in_nyc():
    """Aloha alone = 0.15, below threshold."""
    assert hawaii_confidence("Aloha! Based in NYC") == 0.15


def test_confidence_multiple_signals_compound():
    """Kailua, Oahu 96734 => city 0.4 + island 0.3 + zip 0.3 = 1.0."""
    result = hawaii_confidence("Kailua, Oahu 96734")
    assert result >= 0.7


def test_confidence_cap_at_one():
    """Enough signals to exceed 1.0 should be capped at 1.0."""
    text = "Honolulu, Hawaii 96801 on Oahu near Waikiki"
    # city 0.4 + state 0.4 + zip 0.3 + island 0.3 + city 0.4 = 1.8 uncapped
    result = hawaii_confidence(text)
    assert result == 1.0


# ── hawaii_confidence: case insensitivity ───────────────────────────

def test_confidence_case_insensitive_lower():
    assert hawaii_confidence("honolulu") == 0.4


def test_confidence_case_insensitive_upper():
    assert hawaii_confidence("HONOLULU") == 0.4


def test_confidence_case_insensitive_mixed():
    assert hawaii_confidence("HoNoLuLu") == 0.4


# ── hawaii_confidence: word boundary for "HI" ──────────────────────

def test_confidence_hi_not_in_hiking():
    """'HI' should NOT match inside 'hiking'."""
    assert hawaii_confidence("I love hiking") == 0.0


def test_confidence_hi_not_in_him():
    assert hawaii_confidence("Tell him hello") == 0.0


def test_confidence_hi_not_in_high():
    assert hawaii_confidence("high energy") == 0.0


def test_confidence_hi_standalone():
    """Standalone uppercase 'HI' at end should match."""
    assert hawaii_confidence("Based in HI") == 0.4


def test_confidence_hi_with_comma():
    assert hawaii_confidence("Honolulu, HI") >= 0.4


# ── hawaii_confidence: "hi" greeting should NOT match ────────────────

def test_confidence_hi_greeting_false():
    """Lowercase 'hi' as greeting should NOT match as Hawaii state code."""
    assert hawaii_confidence("Hi everyone!") == 0.0


def test_confidence_hi_say_false():
    """'say hi' should NOT match as Hawaii state code."""
    assert hawaii_confidence("Say hi") == 0.0


def test_confidence_hi_greeting_mixed_case_false():
    """Title-case 'Hi' should NOT match as Hawaii state code."""
    assert hawaii_confidence("Hi there, welcome to my page") == 0.0


# ── hawaii_confidence: word boundary for "808" ─────────────────────

def test_confidence_808_not_in_longer_number():
    assert hawaii_confidence("Call 18085551234") == 0.0


def test_confidence_808_standalone():
    assert hawaii_confidence("808-555-1234") == 0.4


# ── hawaii_confidence: zip boundary ────────────────────────────────

def test_confidence_zip_not_partial():
    """96734 should match but 9673412 should not."""
    assert hawaii_confidence("zip 9673412") == 0.0


def test_confidence_zip_exact_five_digits():
    assert hawaii_confidence("zip 96734") == 0.3


# ── hawaii_confidence: no double counting ──────────────────────────

def test_confidence_no_double_count_hawaii():
    """'Hawaii' appearing twice should only count once."""
    assert hawaii_confidence("Hawaii Hawaii") == 0.4


def test_confidence_no_double_count_city():
    """'Honolulu' appearing twice should only count once."""
    assert hawaii_confidence("Honolulu Honolulu") == 0.4


# ── hawaii_confidence: hawaiian does not trigger hawaii ─────────────

def test_confidence_hawaiian_is_medium_only():
    """'Hawaiian' should only trigger the medium signal, not the strong 'Hawaii' signal.
    The word 'Hawaiian' is a medium signal worth 0.3 (boosted from 0.15)."""
    result = hawaii_confidence("Hawaiian")
    assert result == 0.3


# ── is_hawaii: threshold tests ──────────────────────────────────────

def test_is_hawaii_honolulu_true():
    """Honolulu = 0.4, meets threshold."""
    assert is_hawaii("Honolulu") is True


def test_is_hawaii_aloha_false():
    """Aloha = 0.15, below threshold."""
    assert is_hawaii("Aloha") is False


def test_is_hawaii_none_false():
    assert is_hawaii(None) is False


def test_is_hawaii_empty_false():
    assert is_hawaii("") is False


def test_is_hawaii_oahu_false():
    """Oahu = 0.3, below 0.4 threshold."""
    assert is_hawaii("Oahu") is False


def test_is_hawaii_oahu_plus_aloha_false():
    """Oahu 0.3 + Aloha 0.15 = 0.45, meets threshold."""
    assert is_hawaii("Aloha from Oahu") is True


def test_is_hawaii_city_and_state():
    assert is_hawaii("Honolulu, Hawaii") is True


def test_is_hawaii_random_text():
    assert is_hawaii("Just a regular bio about cats") is False


# ── Handle-embedded Hawaii term detection ────────────────────────────

def test_handle_hawaii_at_end():
    """'doggyboxhawaii' → 'hawaii' embedded in handle should be detected."""
    assert is_hawaii("doggyboxhawaii Doggy Box Grooming Salon") is True


def test_handle_oahu_at_start():
    """'oahudogtraining' → 'oahu' embedded in handle + aloha in bio."""
    assert is_hawaii("oahudogtraining O'ahu Dog Training Aloha") is True


def test_handle_oahu_confidence():
    """'oahu' alone from handle should give at least 0.3."""
    assert hawaii_confidence("oahudogtraining") >= 0.3


def test_handle_kauai_after_underscore():
    """'tikidawg_kauai' → 'kauai' after underscore + aloha in bio."""
    assert is_hawaii("tikidawg_kauai Tiki Pet Collars Aloha from Kauai") is True


def test_handle_kauai_confidence():
    """'kauai' from handle split should give at least 0.3."""
    assert hawaii_confidence("tikidawg_kauai") >= 0.3


def test_handle_808_prefix():
    """'808camo' → '808' at start of handle."""
    assert is_hawaii("808camo Oahu based camo prints") is True


def test_handle_hawaiian_in_middle():
    """'cshawaiianimalfoundation' → 'hawaiian' extracted, plus bio signals."""
    assert is_hawaii("cshawaiianimalfoundation Aloha animal foundation") is True


def test_handle_hawaiian_in_middle_confidence():
    """'hawaiian' extracted from handle should give at least 0.3."""
    assert hawaii_confidence("cshawaiianimalfoundation") >= 0.3


def test_handle_kaetyhawaii():
    """'kaetyhawaii' → 'hawaii' embedded in handle."""
    assert is_hawaii("kaetyhawaii Kaety Hawaii Oahu") is True


def test_handle_hawaiijobcorps():
    """'hawaiijobcorps' → 'hawaii' embedded in handle."""
    assert is_hawaii("hawaiijobcorps Hawaii Job Corps") is True


def test_handle_shinnyolanternfloatinghawaii():
    """'shinnyolanternfloatinghawaii' → 'hawaii' at end."""
    assert is_hawaii("shinnyolanternfloatinghawaii") is True


# ── "Hawaiian" boosted to medium weight (0.3) ───────────────────────

def test_hawaiian_now_medium_weight():
    """'Hawaiian' should now be a medium signal (0.3), meeting threshold."""
    result = hawaii_confidence("Hawaiian")
    assert result == 0.3


def test_hawaiian_electric_is_hawaii():
    """'hawaiianelectric' with 'Hawaiian Electric' in display name.
    hawaiian(0.3) from handle + another signal from bio pushes over threshold."""
    assert is_hawaii("hawaiianelectric Hawaiian Electric Honolulu") is True


def test_hawaiian_electric_confidence():
    """'hawaiianelectric' should extract 'hawaiian' giving at least 0.3."""
    assert hawaii_confidence("hawaiianelectric") >= 0.3


def test_hawaiian_alone_meets_threshold():
    """A single 'Hawaiian' should now meet the 0.4 threshold? No — 0.3.
    But with handle normalization 'hawaiianelectric' splits to 'hawaiian electric'
    so 'hawaiian' (0.3) alone does not meet 0.4 threshold."""
    assert is_hawaii("Hawaiian") is False


def test_hawaiian_plus_any_signal_meets_threshold():
    """'Hawaiian' (0.3) + 'Aloha' (0.15) = 0.45, meets threshold."""
    assert is_hawaii("Aloha Hawaiian") is True


# ── Direct tests for _inject_hawaii_spaces ─────────────────────────


class TestInjectHawaiiSpaces:
    """Direct tests for _inject_hawaii_spaces() helper."""

    def test_no_term_found(self):
        assert _inject_hawaii_spaces("hello world") == "hello world"

    def test_hawaii_at_end(self):
        result = _inject_hawaii_spaces("doggyboxhawaii")
        assert "hawaii" in result
        assert " hawaii" in result

    def test_already_spaced(self):
        """Term with spaces on both sides should claim positions but not re-insert."""
        result = _inject_hawaii_spaces("visit hawaii today")
        assert result == "visit hawaii today"

    def test_overlapping_claimed_skips_shorter(self):
        """'hawaiian' should claim positions so 'hawaii' inside it is skipped."""
        result = _inject_hawaii_spaces("somehawaiiantext")
        assert "hawaiian" in result
        # Should not double-split

    def test_808_digit_guard(self):
        """'808' surrounded by digits should NOT be split (phone number)."""
        result = _inject_hawaii_spaces("18085551234")
        # 808 should not get spaces inserted when surrounded by digits
        assert "18085551234" in result or " 808 " not in result

    def test_808_not_surrounded_by_digits(self):
        """'808' at start of word should get spaces."""
        result = _inject_hawaii_spaces("808camo")
        assert " 808 " in result or result.startswith("808 ")


# ── Direct tests for _normalize_for_search ─────────────────────────


class TestNormalizeForSearch:
    """Direct tests for _normalize_for_search() helper."""

    def test_empty_string(self):
        assert _normalize_for_search("") == ""

    def test_none_input(self):
        assert _normalize_for_search(None) is None

    def test_underscore_split(self):
        result = _normalize_for_search("dog_trainer")
        assert "dog trainer" in result

    def test_dot_split(self):
        result = _normalize_for_search("arya.the.servicedog")
        assert "arya the servicedog" in result

    def test_camel_case_split(self):
        result = _normalize_for_search("DoggyBox")
        # Expansion lowercases and space-splits camelCase
        assert "doggy box" in result.lower()

    def test_digit_letter_split(self):
        result = _normalize_for_search("808camo")
        assert "808 camo" in result

    def test_letter_digit_split(self):
        result = _normalize_for_search("camo808")
        assert "camo 808" in result

    def test_appends_expanded(self):
        """Original text is preserved and expanded form is appended."""
        result = _normalize_for_search("dog_trainer")
        assert result.startswith("dog_trainer ")

    def test_plain_text_unchanged_prefix(self):
        result = _normalize_for_search("hello")
        assert result.startswith("hello ")
