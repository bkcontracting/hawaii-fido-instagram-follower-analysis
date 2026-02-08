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

    def test_competition_keyword(self):
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


# ── Bug regression tests ─────────────────────────────────────────
class TestBugRegressions:
    """Regression tests for known misclassifications found in data audit."""

    # BUG 1: bank_financial false positive from name "Banks"
    def test_banks_name_not_bank_financial(self):
        """Child named 'Banks Mahealani' should NOT trigger bank_financial."""
        r = classify(_profile(display_name="Ashley Johnson",
                              bio="Mom life | Hawaii",
                              handle="traveling_pineapple"))
        # "BANKS MAHEALANI" appears in highlight titles, not handle/display/bio
        # But if it were in bio, it still shouldn't match
        r2 = classify(_profile(bio="BANKS MAHEALANI is my baby"))
        assert r2["category"] != "bank_financial"

    # BUG 2: pet businesses misclassified as personal_engaged
    def test_k9_daycare_is_pet_industry(self):
        """Dog daycare with K9 in name should be pet_industry."""
        r = classify(_profile(handle="kamaainak9",
                              bio="Dog Daycare | Dog Boarding",
                              is_business=False))
        assert r["category"] == "pet_industry"

    def test_dog_services_plural_is_pet_industry(self):
        """'Dog Services' (plural) should trigger pet_industry."""
        r = classify(_profile(handle="tarasdogservices",
                              bio="Dog boarding, pet sitting, doggie daycare, and dog walking",
                              is_business=False))
        assert r["category"] == "pet_industry"

    def test_vet_clinic_without_business_flag(self):
        """Vet clinic without is_business should still be pet_industry."""
        r = classify(_profile(handle="islandveterinarycare",
                              bio="Veterinarian - Caring hearts, healing hands",
                              is_business=False))
        assert r["category"] == "pet_industry"

    def test_doggie_daycare_keyword(self):
        """'daycare' should be recognized as pet keyword."""
        r = classify(_profile(bio="Hawaii's first cage-free daycare boarding facility",
                              is_business=False))
        assert r["category"] == "pet_industry"

    def test_dog_training_keyword(self):
        """'dog training' (not just 'dog trainer') should match."""
        r = classify(_profile(handle="oahudogtraining",
                              bio="O'ahu's Original Concierge Dog Trainer",
                              is_business=False))
        assert r["category"] == "pet_industry"

    def test_k9_kamp_is_pet_industry(self):
        """K9 in name should trigger pet_industry."""
        r = classify(_profile(handle="thek9kamp",
                              bio="Dog Training & Boarding",
                              is_business=False))
        assert r["category"] == "pet_industry"

    def test_pet_collars_inc_is_pet_industry(self):
        """Pet collars with 'Inc' should be pet_industry."""
        r = classify(_profile(handle="tikidawg_kauai",
                              display_name="Tiki Pet Collars Inc.",
                              bio="Cat and dog collars, harnesses, & leashes",
                              is_business=False))
        assert r["category"] == "pet_industry"

    def test_vet_neurosurgeon_is_pet_industry(self):
        """Veterinary professional should be pet_industry."""
        r = classify(_profile(bio="Veterinary Neurosurgeon",
                              is_business=False))
        assert r["category"] == "pet_industry"

    # BUG 3: charity false positives from rescue dog owners
    def test_rescue_pup_not_charity(self):
        """Personal rescue dog account should NOT be charity."""
        r = classify(_profile(bio="Sassy brindle rescue pup, here to make you smile",
                              post_count=80))
        assert r["category"] != "charity"

    def test_rescue_in_activity_list_not_charity(self):
        """'Rescue' as an activity (not organization) should NOT be charity."""
        r = classify(_profile(handle="oahupetsitting",
                              bio="Pet Sitting, Exercise Walk-Hike-Surf, Rescue, Photoshoots",
                              is_business=False))
        assert r["category"] != "charity"

    def test_humane_still_triggers_charity(self):
        """'Humane' is a strong charity signal even in personal adoption context."""
        r = classify(_profile(bio="Adopted from Kauai Humane Society. Living our best life!",
                              post_count=80))
        assert r["category"] == "charity"

    def test_rescue_alone_without_org_context_not_charity(self):
        """'rescue' without org keywords like 'humane/nonprofit/shelter' should NOT be charity."""
        r = classify(_profile(bio="My rescue mutt is the best boy ever",
                              post_count=80))
        assert r["category"] != "charity"

    # BUG 4: organization false positives
    def test_school_street_address_not_organization(self):
        """'School Street' in address should NOT trigger organization."""
        r = classify(_profile(handle="sunnyskalihi",
                              bio="Grocery Store | 2215 N. School Street, Honolulu",
                              is_business=True, is_hawaii=True))
        assert r["category"] != "organization"

    def test_school_counselor_not_organization(self):
        """Individual school counselor should NOT be organization."""
        r = classify(_profile(bio="School counselor | Mental health service",
                              post_count=80))
        assert r["category"] != "organization"

    def test_faculty_at_school_not_organization(self):
        """Faculty member referencing school should NOT be organization."""
        r = classify(_profile(bio="Faculty @ Thompson School at UHM",
                              post_count=80))
        assert r["category"] != "organization"

    # BUG 6: media_event overreach
    def test_open_for_all_not_media(self):
        """'Open' in non-media context should NOT trigger media_event."""
        r = classify(_profile(bio="Dog park open for all dogs daily",
                              post_count=80))
        assert r["category"] != "media_event"


# ── Rule 0: service_dog_aligned (NEW) ──────────────────────────────
class TestRule0ServiceDogAligned:
    def test_service_dog_keyword(self):
        r = classify(_profile(bio="Service dog training"))
        assert r["category"] == "service_dog_aligned"

    def test_therapy_dog_keyword(self):
        r = classify(_profile(bio="Certified therapy dog team"))
        assert r["category"] == "service_dog_aligned"

    def test_assistance_dog_keyword(self):
        r = classify(_profile(bio="Assistance dog provider"))
        assert r["category"] == "service_dog_aligned"

    def test_guide_dog_keyword(self):
        r = classify(_profile(bio="Guide dog foundation"))
        assert r["category"] == "service_dog_aligned"

    def test_service_animal_keyword(self):
        r = classify(_profile(bio="Service animal trainer"))
        assert r["category"] == "service_dog_aligned"

    def test_working_dog_keyword(self):
        r = classify(_profile(bio="Working dog handler"))
        assert r["category"] == "service_dog_aligned"

    def test_canine_assisted_keyword(self):
        r = classify(_profile(bio="Canine assisted therapy program"))
        assert r["category"] == "service_dog_aligned"

    def test_beats_all_other_categories(self):
        """service_dog_aligned should beat bank, pet_industry, etc."""
        r = classify(_profile(bio="Service dog training at First Hawaiian Bank",
                              is_business=True, is_hawaii=True))
        assert r["category"] == "service_dog_aligned"

    def test_subcategory_therapy(self):
        r = classify(_profile(bio="Therapy dog team"))
        assert r["subcategory"] == "therapy"

    def test_subcategory_guide(self):
        r = classify(_profile(bio="Guide dog foundation"))
        assert r["subcategory"] == "guide"

    def test_subcategory_service(self):
        r = classify(_profile(bio="Service dog in training"))
        assert r["subcategory"] == "service"

    def test_high_confidence(self):
        r = classify(_profile(bio="Service dog trainer"))
        assert r["confidence"] >= 0.9


# ── Rule 2: corporate (NEW) ──────────────────────────────────────
class TestRule2Corporate:
    def test_electric_utility(self):
        r = classify(_profile(bio="Hawaii's electric utility company",
                              follower_count=33000))
        assert r["category"] == "corporate"

    def test_airline(self):
        r = classify(_profile(bio="Major airline serving Hawaii"))
        assert r["category"] == "corporate"

    def test_insurance(self):
        r = classify(_profile(bio="Insurance company of Hawaii"))
        assert r["category"] == "corporate"

    def test_corporation_keyword(self):
        r = classify(_profile(bio="Corporation headquarters"))
        assert r["category"] == "corporate"

    def test_large_business_by_followers(self):
        """Business with 25k+ followers should be corporate."""
        r = classify(_profile(is_business=True, follower_count=30000,
                              bio="Our company values"))
        assert r["category"] == "corporate"

    def test_small_business_not_corporate(self):
        """Business with <25k followers should NOT be corporate (should be business_local/national)."""
        r = classify(_profile(is_business=True, follower_count=5000,
                              is_hawaii=True, bio="Local shop"))
        assert r["category"] != "corporate"

    def test_corporate_beats_pet_industry(self):
        """Corporate keywords should beat pet_industry."""
        r = classify(_profile(bio="Corporation pet supply chain",
                              is_business=True))
        assert r["category"] == "corporate"

    def test_bank_still_beats_corporate(self):
        """bank_financial should still beat corporate."""
        r = classify(_profile(bio="Bank corporation headquarters"))
        assert r["category"] == "bank_financial"


# ── Updated priority order tests ─────────────────────────────────
class TestNewPriorityOrder:
    def test_service_dog_beats_everything(self):
        """service_dog_aligned beats bank_financial."""
        r = classify(_profile(bio="Service dog training at bank",
                              is_business=True, is_hawaii=True))
        assert r["category"] == "service_dog_aligned"

    def test_bank_beats_corporate(self):
        """bank_financial beats corporate."""
        r = classify(_profile(bio="Bank corporation",
                              is_business=True))
        assert r["category"] == "bank_financial"

    def test_corporate_beats_pet(self):
        """corporate beats pet_industry."""
        r = classify(_profile(bio="Corporation pet supply global",
                              is_business=True))
        assert r["category"] == "corporate"

    def test_pet_industry_beats_business_local(self):
        """pet_industry should beat business_local for pet businesses."""
        r = classify(_profile(bio="Dog training salon in Honolulu",
                              is_business=False, is_hawaii=True))
        assert r["category"] == "pet_industry"


# ── Rule 8/9: business_local/national strong keywords (NEW) ──────
class TestBusinessLocalStrongKeywords:
    def test_brewery_without_business_flag(self):
        """Brewery without is_business should be business_local if Hawaii."""
        r = classify(_profile(handle="hanakoabrewing",
                              display_name="Hana Koa Brewing Co.",
                              bio="Craft beer | Brewed on site | Full kitchen",
                              is_business=False, is_hawaii=True))
        assert r["category"] == "business_local"
        assert r["subcategory"] == "restaurant"

    def test_hotel_without_business_flag(self):
        """Hotel without is_business should be business_local if Hawaii."""
        r = classify(_profile(display_name="Pearl Hotel Waikiki",
                              bio="Located in heart of Waikiki",
                              is_business=False, is_hawaii=True))
        assert r["category"] == "business_local"
        assert r["subcategory"] == "hospitality"

    def test_real_estate_without_business_flag(self):
        """Real estate agent without is_business should be business_local."""
        r = classify(_profile(bio="Real Estate Broker | Owner JC Hawaii Realty Corp",
                              is_business=False, is_hawaii=True))
        assert r["category"] == "business_local"
        assert r["subcategory"] == "real_estate"

    def test_law_firm_without_business_flag(self):
        """Law firm without is_business should be business_local."""
        r = classify(_profile(bio="Lawyer & Law Firm, We help people throughout Hawaii",
                              is_business=False, is_hawaii=True))
        assert r["category"] == "business_local"
        assert r["subcategory"] == "legal"

    def test_non_hawaii_brewery_is_national(self):
        """Brewery without Hawaii should be business_national."""
        r = classify(_profile(bio="Craft brewery and taproom",
                              is_business=False, is_hawaii=False))
        assert r["category"] == "business_national"

    def test_pet_industry_still_beats_business(self):
        """Pet industry keywords (Rule 3) should beat business (Rule 8)."""
        r = classify(_profile(bio="Dog training facility and salon",
                              is_business=False, is_hawaii=True))
        assert r["category"] == "pet_industry"


# ── Change 1: Expanded organization keywords ────────────────────
class TestExpandedOrgKeywords:
    def test_chamber_detected(self):
        """North Shore Chamber of Commerce → organization."""
        r = classify(_profile(handle="gonorthshore", bio="North Shore Chamber of Commerce"))
        assert r["category"] == "organization"
        assert r["subcategory"] == "community_group"

    def test_association_detected(self):
        """Hawaii Pacific association → organization."""
        r = classify(_profile(handle="iidahawaiipacific", bio="International Interior Design Association Hawaii Pacific Chapter"))
        assert r["category"] == "organization"

    def test_chapter_org_detected(self):
        """Military Order chapter → organization."""
        r = classify(_profile(handle="moph483", bio="Military Order of the Purple Heart Chapter 483"))
        assert r["category"] == "organization"

    def test_initiative_detected(self):
        """Community initiative → organization."""
        r = classify(_profile(handle="revitalizepuna", bio="Community revitalization initiative for Puna"))
        assert r["category"] == "organization"

    def test_coalition_detected(self):
        """Health coalition → organization."""
        r = classify(_profile(bio="Hawaii Health Coalition"))
        assert r["category"] == "organization"
        assert r["subcategory"] == "community_group"

    def test_alliance_detected(self):
        """Community alliance → organization."""
        r = classify(_profile(bio="Pacific Alliance for Community Engagement"))
        assert r["category"] == "organization"

    def test_foundation_detected(self):
        """Foundation without charity keywords → organization."""
        r = classify(_profile(bio="Kamehameha Schools Foundation"))
        assert r["category"] == "organization"

    def test_foundation_beauty_not_org(self):
        """'Foundation shade' in makeup context should NOT be organization."""
        r = classify(_profile(bio="Best foundation shade for summer skin", post_count=80))
        assert r["category"] != "organization"

    def test_makeup_foundation_not_org(self):
        """'Makeup foundation' should NOT be organization."""
        r = classify(_profile(bio="My favorite makeup foundation routine", post_count=80))
        assert r["category"] != "organization"

    def test_chapter_book_not_org(self):
        """'Chapter 3 of my novel' should NOT be organization."""
        r = classify(_profile(bio="Working on chapter 3 of my book", post_count=80))
        assert r["category"] != "organization"

    def test_chapter_with_number_book_not_org(self):
        """'chapter 12' in book context should NOT be organization."""
        r = classify(_profile(bio="Just finished reading chapter 12", post_count=80))
        assert r["category"] != "organization"

    def test_government_org_detected(self):
        """'Government organization' → organization/government."""
        r = classify(_profile(handle="efmphawaii", bio="Government organization serving Hawaii"))
        assert r["category"] == "organization"
        assert r["subcategory"] == "government"

    def test_military_detected(self):
        """Military base → organization/government."""
        r = classify(_profile(handle="jbphh_teencenter", bio="JBPHH Military Teen Center"))
        assert r["category"] == "organization"
        assert r["subcategory"] == "government"

    def test_veterans_detected(self):
        """Veterans org → organization/government."""
        r = classify(_profile(bio="Supporting our veterans community"))
        assert r["category"] == "organization"
        assert r["subcategory"] == "government"

    def test_job_corps_detected(self):
        """Job Corps → organization/government."""
        r = classify(_profile(bio="Hawaii Job Corps Center"))
        assert r["category"] == "organization"
        assert r["subcategory"] == "government"


# ── Change 2: Breeder and trainer pet_industry keywords ─────────
class TestBreederTrainerPetKeywords:
    def test_breeder_keyword(self):
        """'Breeder' → pet_industry/breeder."""
        r = classify(_profile(handle="galaxychihuahuas", bio="AKC registered chihuahua breeder"))
        assert r["category"] == "pet_industry"
        assert r["subcategory"] == "breeder"

    def test_breeding_keyword(self):
        """'Breeding' → pet_industry/breeder."""
        r = classify(_profile(handle="kula_teddybears", bio="Breeding quality shichon puppies"))
        assert r["category"] == "pet_industry"
        assert r["subcategory"] == "breeder"

    def test_puppies_for_keyword(self):
        """'Puppies for sale' → pet_industry/breeder."""
        r = classify(_profile(bio="Puppies for loving homes"))
        assert r["category"] == "pet_industry"
        assert r["subcategory"] == "breeder"

    def test_litter_keyword(self):
        """'Litter' → pet_industry/breeder."""
        r = classify(_profile(bio="New litter arriving spring 2026"))
        assert r["category"] == "pet_industry"
        assert r["subcategory"] == "breeder"

    def test_pomsky_breed_with_breeder(self):
        """Pomsky breeder → pet_industry."""
        r = classify(_profile(handle="mumblebluepomskies",
                              bio="Pomsky breeder in Hawaii"))
        assert r["category"] == "pet_industry"

    def test_dog_trick_keyword(self):
        """'Dog trick' → pet_industry/trainer."""
        r = classify(_profile(handle="macy_da_opihi", bio="Dog trick performer and trainer"))
        assert r["category"] == "pet_industry"
        assert r["subcategory"] == "trainer"

    def test_breed_name_without_commercial_not_pet(self):
        """Breed name alone (frenchie) without commercial signal or breeder keyword → not pet_industry."""
        r = classify(_profile(bio="My frenchie is the best boy", post_count=80))
        assert r["category"] != "pet_industry"

    def test_pet_rehab_strong(self):
        """'Pet rehab' → pet_industry/rehabilitation."""
        r = classify(_profile(handle="hawaiipetrehab", bio="Hawaii Pet Rehab specializing in canine rehabilitation"))
        assert r["category"] == "pet_industry"
        assert r["subcategory"] == "rehabilitation"

    def test_animal_rehabilitation_strong(self):
        """'Animal rehabilitation' → pet_industry."""
        r = classify(_profile(bio="Animal rehabilitation center"))
        assert r["category"] == "pet_industry"
        assert r["subcategory"] == "rehabilitation"


# ── Change 3: Charity partner subcategory ────────────────────────
class TestCharityPartner:
    def test_spca_is_charity_partner(self):
        """SPCA → charity/partner."""
        r = classify(_profile(handle="the_oahu_spca",
                              display_name="The Oahu SPCA",
                              bio="Events and adoption programs"))
        assert r["category"] == "charity"
        assert r["subcategory"] == "partner"

    def test_disability_nonprofit_is_partner(self):
        """Disability nonprofit → charity/partner (not general)."""
        r = classify(_profile(handle="alohailhawaii",
                              bio="Nonprofit serving people with disability in Hawaii"))
        assert r["category"] == "charity"
        assert r["subcategory"] == "partner"

    def test_humane_society_is_partner(self):
        """Humane Society → charity/partner."""
        r = classify(_profile(bio="Kauai Humane Society"))
        assert r["category"] == "charity"
        assert r["subcategory"] == "partner"

    def test_animal_welfare_is_partner(self):
        """Animal welfare org → charity/partner."""
        r = classify(_profile(bio="Nonprofit animal welfare organization"))
        assert r["category"] == "charity"
        assert r["subcategory"] == "partner"

    def test_generic_charity_is_general(self):
        """Generic charity without partner keywords → charity/general."""
        r = classify(_profile(bio="Feeding America nonprofit"))
        assert r["category"] == "charity"
        assert r["subcategory"] == "general"

    def test_special_needs_is_partner(self):
        """Special needs nonprofit → charity/partner."""
        r = classify(_profile(bio="Nonprofit for special needs children"))
        assert r["category"] == "charity"
        assert r["subcategory"] == "partner"

    def test_independent_living_is_partner(self):
        """Independent living → charity/partner."""
        r = classify(_profile(bio="Nonprofit independent living center"))
        assert r["category"] == "charity"
        assert r["subcategory"] == "partner"


# ── Change 5: Personal rescue patterns ──────────────────────────
class TestExpandedPersonalRescue:
    def test_adopted_from_with_rescue(self):
        """'Adopted from' + 'rescue' → personal rescue, not charity."""
        r = classify(_profile(bio="Rescue pup, adopted from a family on Oahu",
                              post_count=80))
        assert r["category"] != "charity"

    def test_adopted_from_excludes_charity(self):
        """'Adopted from' with just 'rescue' → not charity."""
        r = classify(_profile(bio="Our rescue dog, adopted from a foster home",
                              post_count=80))
        assert r["category"] != "charity"


# ── Change 6: Race/marathon media_event keywords ────────────────
class TestRaceMarathonKeywords:
    def test_marathon_keyword(self):
        """Marathon → media_event/event."""
        r = classify(_profile(bio="Honolulu Marathon"))
        assert r["category"] == "media_event"
        assert r["subcategory"] == "event"

    def test_great_aloha_run(self):
        """Great Aloha Run → media_event/event."""
        r = classify(_profile(handle="greataloharun", bio="Great Aloha Run"))
        assert r["category"] == "media_event"
        assert r["subcategory"] == "event"

    def test_5k_keyword(self):
        """5K race → media_event/event."""
        r = classify(_profile(bio="Annual 5k Race in Honolulu"))
        assert r["category"] == "media_event"
        assert r["subcategory"] == "event"

    def test_10k_keyword(self):
        """10K race → media_event."""
        r = classify(_profile(bio="Hawaii 10k Challenge"))
        assert r["category"] == "media_event"

    def test_triathlon_keyword(self):
        """Triathlon → media_event/event."""
        r = classify(_profile(bio="Kona Ironman Triathlon"))
        assert r["category"] == "media_event"
        assert r["subcategory"] == "event"
