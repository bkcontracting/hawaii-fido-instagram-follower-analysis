"""Tests for src/classifier.py — 13 decision rules in priority order."""
import pytest
from src.classifier import classify


# ── Helper to build profile dicts ──────────────────────────────────
def _profile(handle="testuser", display_name="Test User", bio="",
             is_business=False, is_hawaii=False, follower_count=100,
             following_count=50, post_count=10, **kw):
    p = dict(handle=handle, display_name=display_name, bio=bio,
             is_business=is_business, is_hawaii=is_hawaii,
             follower_count=follower_count, following_count=following_count,
             post_count=post_count)
    p.update(kw)
    return p


# ── Rule 1: bank_financial ─────────────────────────────────────────
class TestRule1BankFinancial:
    def test_bank_in_bio(self):
        r = classify(_profile(bio="First Hawaiian Bank"))
        assert r["category"] == "bank_financial"

    def test_financial_in_name(self):
        r = classify(_profile(display_name="ABC Financial Services"))
        assert r["category"] == "bank_financial"

    def test_credit_union_in_bio(self):
        r = classify(_profile(bio="Hawaii State Federal Credit Union"))
        assert r["category"] == "bank_financial"

    def test_bank_in_handle(self):
        r = classify(_profile(handle="fhb_bank_official"))
        assert r["category"] == "bank_financial"

    def test_subcategory_bank(self):
        r = classify(_profile(bio="First Hawaiian Bank"))
        assert r["subcategory"] == "bank"

    def test_subcategory_credit_union(self):
        r = classify(_profile(bio="Hawaii Credit Union"))
        assert r["subcategory"] == "credit_union"

    def test_subcategory_financial_advisor(self):
        r = classify(_profile(bio="Financial advisor serving Honolulu"))
        assert r["subcategory"] == "financial_advisor"

    def test_has_confidence(self):
        r = classify(_profile(bio="Bank of Hawaii"))
        assert 0.0 < r["confidence"] <= 1.0


# ── Rule 2: pet_industry ──────────────────────────────────────────
class TestRule2PetIndustry:
    def test_vet_business(self):
        r = classify(_profile(bio="Veterinary clinic for your pets", is_business=True))
        assert r["category"] == "pet_industry"

    def test_dog_trainer_with_commercial_signal(self):
        r = classify(_profile(bio="Dog trainer service in Honolulu"))
        assert r["category"] == "pet_industry"

    def test_pet_keyword_no_business_no_commercial(self):
        """Pet keyword alone without business or commercial signal should NOT match pet_industry."""
        r = classify(_profile(bio="I love my pet dog", is_business=False))
        assert r["category"] != "pet_industry"

    def test_groomer_business(self):
        r = classify(_profile(bio="Professional groomer", is_business=True))
        assert r["category"] == "pet_industry"

    def test_pet_store_commercial(self):
        r = classify(_profile(bio="Best pet supply store"))
        assert r["category"] == "pet_industry"

    def test_canine_in_handle(self):
        r = classify(_profile(handle="caninecardiohawaii", bio="Mobile Dog Gym", is_business=True))
        assert r["category"] == "pet_industry"

    def test_subcategory_veterinary(self):
        r = classify(_profile(bio="Veterinary clinic", is_business=True))
        assert r["subcategory"] == "veterinary"

    def test_subcategory_trainer(self):
        r = classify(_profile(bio="Dog trainer services", is_business=True))
        assert r["subcategory"] == "trainer"

    def test_subcategory_groomer(self):
        r = classify(_profile(bio="Professional groomer", is_business=True))
        assert r["subcategory"] == "groomer"

    def test_subcategory_pet_store(self):
        r = classify(_profile(bio="Your local pet store", is_business=True))
        assert r["subcategory"] == "pet_store"

    def test_subcategory_pet_food(self):
        r = classify(_profile(bio="Organic pet food", is_business=True))
        assert r["subcategory"] == "pet_food"

    def test_pet_keyword_with_community_not_commercial(self):
        r = classify(_profile(bio="Pet lover in the community garden", is_business=False))
        assert r["category"] != "pet_industry"

    def test_pet_keyword_with_coffee_not_commercial(self):
        r = classify(_profile(bio="Pet stories and coffee chats", is_business=False))
        assert r["category"] != "pet_industry"

    def test_pet_keyword_with_welcome_not_commercial(self):
        r = classify(_profile(bio="Pet tips welcome everyone", is_business=False))
        assert r["category"] != "pet_industry"

    def test_pet_keyword_with_inc_is_commercial(self):
        r = classify(_profile(bio="Island Pet Inc", is_business=False))
        assert r["category"] == "pet_industry"


# ── Rule 3: organization ──────────────────────────────────────────
class TestRule3Organization:
    def test_rotary_club(self):
        r = classify(_profile(bio="Rotary Club of Honolulu"))
        assert r["category"] == "organization"

    def test_church(self):
        r = classify(_profile(bio="First Presbyterian Church"))
        assert r["category"] == "organization"

    def test_school(self):
        r = classify(_profile(bio="Punahou School alumni"))
        assert r["category"] == "organization"

    def test_golf_club(self):
        r = classify(_profile(bio="Hawaii Golf Club members"))
        assert r["category"] == "organization"

    def test_org_with_charity_keyword_excluded(self):
        """Organization rule excludes profiles with charity keywords."""
        r = classify(_profile(bio="Rotary Club nonprofit rescue foundation"))
        assert r["category"] != "organization"

    def test_subcategory_church(self):
        r = classify(_profile(bio="Community Church"))
        assert r["subcategory"] == "church"

    def test_subcategory_school(self):
        r = classify(_profile(bio="Local School"))
        assert r["subcategory"] == "school"

    def test_subcategory_club(self):
        r = classify(_profile(bio="Golf Club"))
        assert r["subcategory"] == "club"


# ── Rule 4: charity ───────────────────────────────────────────────
class TestRule4Charity:
    def test_rescue(self):
        r = classify(_profile(bio="Animal rescue organization"))
        assert r["category"] == "charity"

    def test_nonprofit(self):
        r = classify(_profile(bio="501c3 nonprofit serving communities"))
        assert r["category"] == "charity"

    def test_shelter(self):
        r = classify(_profile(bio="Hawaii pet shelter"))
        assert r["category"] == "charity"

    def test_humane_society(self):
        r = classify(_profile(bio="Humane society of Oahu"))
        assert r["category"] == "charity"


# ── Rule 5: elected_official ──────────────────────────────────────
class TestRule5ElectedOfficial:
    def test_councilmember_hawaii(self):
        r = classify(_profile(bio="Council member for District 4",
                              is_hawaii=True))
        assert r["category"] == "elected_official"

    def test_mayor_hawaii(self):
        r = classify(_profile(bio="Mayor of Honolulu", is_hawaii=True))
        assert r["category"] == "elected_official"

    def test_senator_not_hawaii(self):
        """Senator NOT in Hawaii should not match elected_official."""
        r = classify(_profile(bio="Senator for district 5", is_hawaii=False))
        assert r["category"] != "elected_official"

    def test_governor_hawaii(self):
        r = classify(_profile(bio="Governor of Hawaii", is_hawaii=True))
        assert r["category"] == "elected_official"

    def test_representative_hawaii(self):
        r = classify(_profile(bio="State Representative", is_hawaii=True))
        assert r["category"] == "elected_official"


# ── Rule 6: media_event ───────────────────────────────────────────
class TestRule6MediaEvent:
    def test_event(self):
        r = classify(_profile(bio="Annual surf event"))
        assert r["category"] == "media_event"

    def test_photographer(self):
        r = classify(_profile(bio="Professional photographer"))
        assert r["category"] == "media_event"

    def test_news(self):
        r = classify(_profile(bio="Local news coverage"))
        assert r["category"] == "media_event"

    def test_magazine(self):
        r = classify(_profile(bio="Hawaii lifestyle magazine"))
        assert r["category"] == "media_event"

    def test_festival(self):
        r = classify(_profile(bio="Annual music festival"))
        assert r["category"] == "media_event"

    def test_media_in_handle(self):
        r = classify(_profile(handle="oahu_media"))
        assert r["category"] == "media_event"

    def test_open_keyword(self):
        r = classify(_profile(bio="Kailua Open surf competition"))
        assert r["category"] == "media_event"

    def test_subcategory_event(self):
        r = classify(_profile(bio="Surf tournament"))
        assert r["subcategory"] == "event"

    def test_subcategory_photographer(self):
        r = classify(_profile(bio="Wedding photographer"))
        assert r["subcategory"] == "photographer"

    def test_subcategory_news(self):
        r = classify(_profile(bio="Breaking news daily"))
        assert r["subcategory"] == "news"


# ── Rule 7: business_local ────────────────────────────────────────
class TestRule7BusinessLocal:
    def test_hawaii_business(self):
        r = classify(_profile(is_business=True, is_hawaii=True))
        assert r["category"] == "business_local"

    def test_subcategory_restaurant(self):
        r = classify(_profile(bio="Best restaurant on Oahu", is_business=True, is_hawaii=True))
        assert r["subcategory"] == "restaurant"

    def test_subcategory_retail(self):
        r = classify(_profile(bio="Retail boutique shop", is_business=True, is_hawaii=True))
        assert r["subcategory"] == "retail"

    def test_subcategory_real_estate(self):
        r = classify(_profile(bio="Real estate agent", is_business=True, is_hawaii=True))
        assert r["subcategory"] == "real_estate"

    def test_subcategory_service(self):
        r = classify(_profile(bio="Professional plumbing service", is_business=True, is_hawaii=True))
        assert r["subcategory"] == "service"


# ── Rule 8: business_national ─────────────────────────────────────
class TestRule8BusinessNational:
    def test_non_hawaii_business(self):
        r = classify(_profile(is_business=True, is_hawaii=False))
        assert r["category"] == "business_national"


# ── Rule 9: influencer ────────────────────────────────────────────
class TestRule9Influencer:
    def test_high_followers_not_business(self):
        r = classify(_profile(follower_count=15000, is_business=False))
        assert r["category"] == "influencer"

    def test_high_followers_is_business(self):
        """Business with 10k+ should NOT be influencer (caught by rule 7/8)."""
        r = classify(_profile(follower_count=15000, is_business=True, is_hawaii=False))
        assert r["category"] != "influencer"


# ── Rule 10: spam_bot ─────────────────────────────────────────────
class TestRule10SpamBot:
    def test_spam_bot(self):
        r = classify(_profile(following_count=5000, follower_count=50,
                              post_count=2, is_business=False))
        assert r["category"] == "spam_bot"

    def test_not_spam_many_posts(self):
        """Should not be spam if post_count >= 5."""
        r = classify(_profile(following_count=5000, follower_count=50,
                              post_count=10, is_business=False))
        assert r["category"] != "spam_bot"


# ── Rule 11: personal_engaged ─────────────────────────────────────
class TestRule11PersonalEngaged:
    def test_active_poster(self):
        r = classify(_profile(post_count=75, is_business=False))
        assert r["category"] == "personal_engaged"


# ── Rule 12: personal_passive ─────────────────────────────────────
class TestRule12PersonalPassive:
    def test_low_activity(self):
        r = classify(_profile(post_count=50, is_business=False))
        assert r["category"] == "personal_passive"

    def test_zero_posts(self):
        r = classify(_profile(post_count=0, is_business=False))
        assert r["category"] == "personal_passive"


# ── Rule 13: unknown ──────────────────────────────────────────────
class TestRule13Unknown:
    def test_no_signals_falls_through(self):
        """A profile with None counts should fall through to unknown."""
        r = classify(_profile(post_count=None, follower_count=None,
                              following_count=None, is_business=False))
        assert r["category"] == "unknown"
        assert r["confidence"] < 0.5


# ── Priority order tests ──────────────────────────────────────────
class TestPriorityOrder:
    def test_bank_beats_business_local(self):
        """Hawaii bank should be bank_financial, not business_local."""
        r = classify(_profile(bio="First Hawaiian Bank",
                              is_business=True, is_hawaii=True))
        assert r["category"] == "bank_financial"

    def test_pet_beats_business_local(self):
        """Hawaii pet store should be pet_industry, not business_local."""
        r = classify(_profile(bio="Hawaii pet supply store",
                              is_business=True, is_hawaii=True))
        assert r["category"] == "pet_industry"

    def test_org_beats_media(self):
        """Rotary club event should be organization, not media_event."""
        r = classify(_profile(bio="Rotary Club annual event"))
        # Rule 3 (org) fires before rule 6 (media)
        assert r["category"] == "organization"

    def test_charity_beats_business(self):
        """Nonprofit rescue should be charity, not anything else."""
        r = classify(_profile(bio="Animal rescue nonprofit", is_business=True,
                              is_hawaii=True))
        assert r["category"] == "charity"


# ── Return structure ──────────────────────────────────────────────
class TestReturnStructure:
    def test_returns_dict_with_three_keys(self):
        r = classify(_profile())
        assert "category" in r
        assert "subcategory" in r
        assert "confidence" in r

    def test_confidence_is_float(self):
        r = classify(_profile())
        assert isinstance(r["confidence"], float)

    def test_subcategory_defaults_to_general(self):
        r = classify(_profile(post_count=75, is_business=False))
        assert r["subcategory"] == "general"
