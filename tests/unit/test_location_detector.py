"""Tests for src/location_detector.py — Hawaii location detection."""
from src.location_detector import hawaii_confidence, is_hawaii


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
    assert hawaii_confidence("Hawaiian") == 0.15


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

def test_confidence_hawaiian_is_weak_only():
    """'Hawaiian' should only trigger the weak signal, not the strong 'Hawaii' signal.
    The word 'Hawaiian' is specifically a weak signal worth 0.15."""
    result = hawaii_confidence("Hawaiian")
    assert result == 0.15


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
