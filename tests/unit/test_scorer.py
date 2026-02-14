"""Tests for src/scorer.py — priority scoring and tier assignment."""
import pytest
from src.scorer import score, get_tier


# ── Helper ─────────────────────────────────────────────────────────
def _profile(category="personal_passive", is_hawaii=False, is_business=False,
             is_verified=False, is_private=False, follower_count=100,
             post_count=10, bio="Some bio", website=None, **kw):
    """Build a profile dict. Default bio is non-empty to avoid no_bio penalty."""
    p = dict(category=category, is_hawaii=is_hawaii, is_business=is_business,
             is_verified=is_verified, is_private=is_private,
             follower_count=follower_count, post_count=post_count,
             bio=bio, website=website)
    p.update(kw)
    return p


# ── 5.1 Base scores ───────────────────────────────────────────────
class TestBaseScores:
    def test_hawaii_bonus(self):
        with_hi = score(_profile(is_hawaii=True))
        without = score(_profile(is_hawaii=False))
        assert with_hi["priority_score"] == without["priority_score"] + 30
        assert "hawaii" in with_hi["priority_reason"].lower()

    def test_bank_bonus(self):
        r = score(_profile(category="bank_financial"))
        base = score(_profile(category="personal_passive"))
        assert r["priority_score"] == base["priority_score"] + 30

    def test_pet_industry_bonus(self):
        r = score(_profile(category="pet_industry"))
        base = score(_profile(category="personal_passive"))
        assert r["priority_score"] == base["priority_score"] + 25

    def test_organization_bonus(self):
        r = score(_profile(category="organization"))
        base = score(_profile(category="personal_passive"))
        assert r["priority_score"] == base["priority_score"] + 25

    def test_elected_official_bonus(self):
        r = score(_profile(category="elected_official"))
        base = score(_profile(category="personal_passive"))
        assert r["priority_score"] == base["priority_score"] + 25

    def test_business_bonus(self):
        with_biz = score(_profile(is_business=True))
        without = score(_profile(is_business=False))
        assert with_biz["priority_score"] == without["priority_score"] + 20

    def test_media_bonus(self):
        r = score(_profile(category="media_event"))
        base = score(_profile(category="personal_passive"))
        assert r["priority_score"] == base["priority_score"] + 15

    def test_influencer_bonus(self):
        r = score(_profile(category="influencer"))
        base = score(_profile(category="personal_passive"))
        assert r["priority_score"] == base["priority_score"] + 20

    def test_verified_bonus(self):
        with_v = score(_profile(is_verified=True))
        without = score(_profile(is_verified=False))
        assert with_v["priority_score"] == without["priority_score"] + 10


# ── 5.2 Reach score ───────────────────────────────────────────────
class TestReachScore:
    def test_50k_plus(self):
        r = score(_profile(follower_count=60000))
        base = score(_profile(follower_count=500))
        assert r["priority_score"] == base["priority_score"] + 20
        assert "reach" in r["priority_reason"].lower()

    def test_10k_to_50k(self):
        r = score(_profile(follower_count=25000))
        base = score(_profile(follower_count=500))
        assert r["priority_score"] == base["priority_score"] + 15

    def test_5k_to_10k(self):
        r = score(_profile(follower_count=7000))
        base = score(_profile(follower_count=500))
        assert r["priority_score"] == base["priority_score"] + 10

    def test_1k_to_5k(self):
        r = score(_profile(follower_count=2000))
        base = score(_profile(follower_count=500))
        assert r["priority_score"] == base["priority_score"] + 5

    def test_under_1k(self):
        r = score(_profile(follower_count=500))
        assert r["priority_score"] >= 0


# ── 5.2 Engagement indicators ─────────────────────────────────────
class TestEngagement:
    def test_website_bonus(self):
        with_site = score(_profile(website="https://example.com"))
        without = score(_profile(website=None))
        assert with_site["priority_score"] == without["priority_score"] + 5

    def test_active_posting_bonus(self):
        active = score(_profile(post_count=150))
        inactive = score(_profile(post_count=50))
        assert active["priority_score"] == inactive["priority_score"] + 5

    def test_dogs_pets_bio_bonus(self):
        with_pets = score(_profile(bio="I love dogs and pets"))
        without = score(_profile(bio="Just a regular person"))
        assert with_pets["priority_score"] == without["priority_score"] + 10

    def test_community_giving_bio_bonus(self):
        with_community = score(_profile(bio="Our mission is community giving"))
        without = score(_profile(bio="Just a regular person"))
        assert with_community["priority_score"] == without["priority_score"] + 5

    def test_no_stack_pet_industry(self):
        """pet_industry category should NOT get dogs/pets bio bonus."""
        pet_biz = score(_profile(category="pet_industry",
                                 bio="We love dogs and pets"))
        pet_biz_no_bio = score(_profile(category="pet_industry",
                                        bio="Professional services"))
        assert pet_biz["priority_score"] == pet_biz_no_bio["priority_score"]


# ── 5.2 Penalties ─────────────────────────────────────────────────
class TestPenalties:
    def test_charity_penalty(self):
        r = score(_profile(category="charity", is_hawaii=True))
        # Hawaii(30) - charity(50) = -20 → clamped to 0
        assert r["priority_score"] <= 30

    def test_private_penalty(self):
        # Use hawaii bonus to ensure score is high enough to see the penalty
        priv = score(_profile(is_private=True, is_hawaii=True))
        pub = score(_profile(is_private=False, is_hawaii=True))
        assert pub["priority_score"] - priv["priority_score"] == 20

    def test_spam_penalty(self):
        r = score(_profile(category="spam_bot"))
        assert r["priority_score"] == 0  # clamped to 0

    def test_no_bio_penalty(self):
        # Use hawaii bonus to ensure score is high enough to see the penalty
        no_bio = score(_profile(bio="", is_hawaii=True))
        with_bio = score(_profile(bio="Some bio text", is_hawaii=True))
        assert with_bio["priority_score"] - no_bio["priority_score"] == 10

    def test_clamp_at_zero(self):
        r = score(_profile(category="spam_bot", is_private=True, bio=""))
        assert r["priority_score"] == 0

    def test_clamp_at_100(self):
        r = score(_profile(category="bank_financial", is_hawaii=True,
                           is_business=True, is_verified=True,
                           follower_count=60000, post_count=200,
                           bio="dogs pets community giving",
                           website="https://example.com"))
        assert r["priority_score"] == 100


# ── 5.3 Tiers ─────────────────────────────────────────────────────
class TestTiers:
    def test_tier_1(self):
        assert get_tier(80) == "Tier 1 - High Priority"
        assert get_tier(100) == "Tier 1 - High Priority"

    def test_tier_2(self):
        assert get_tier(60) == "Tier 2 - Medium Priority"
        assert get_tier(79) == "Tier 2 - Medium Priority"

    def test_tier_3(self):
        assert get_tier(40) == "Tier 3 - Low Priority"
        assert get_tier(59) == "Tier 3 - Low Priority"

    def test_tier_4(self):
        assert get_tier(0) == "Tier 4 - Skip"
        assert get_tier(39) == "Tier 4 - Skip"


# ── PRD Reference Scoring Examples ────────────────────────────────
class TestPRDExamples:
    def test_hawaii_bank(self):
        """hawaii(30) + bank(30) + business(20) = 80 → Tier 1"""
        r = score(_profile(category="bank_financial", is_hawaii=True,
                           is_business=True, bio="Bank of Hawaii"))
        assert r["priority_score"] == 80
        assert get_tier(r["priority_score"]) == "Tier 1 - High Priority"

    def test_hawaii_pet_store(self):
        """hawaii(30) + pet(25) + business(20) = 75 → Tier 2"""
        r = score(_profile(category="pet_industry", is_hawaii=True,
                           is_business=True, bio="Local store"))
        assert r["priority_score"] == 75
        assert get_tier(r["priority_score"]) == "Tier 2 - Medium Priority"

    def test_hawaii_pet_store_website(self):
        """hawaii(30) + pet(25) + business(20) + website(5) = 80 → Tier 1"""
        r = score(_profile(category="pet_industry", is_hawaii=True,
                           is_business=True, bio="Local store",
                           website="https://pets.com"))
        assert r["priority_score"] == 80
        assert get_tier(r["priority_score"]) == "Tier 1 - High Priority"

    def test_hawaii_councilmember(self):
        """hawaii(30) + elected(25) + verified(10) + reach_10k(15) = 80 → Tier 1"""
        r = score(_profile(category="elected_official", is_hawaii=True,
                           is_verified=True, follower_count=12000,
                           bio="Serving my district"))
        assert r["priority_score"] == 80
        assert get_tier(r["priority_score"]) == "Tier 1 - High Priority"

    def test_hawaii_church(self):
        """hawaii(30) + org(25) + reach_5k(10) + website(5) = 70 → Tier 2"""
        r = score(_profile(category="organization", is_hawaii=True,
                           follower_count=5000,
                           website="https://church.org",
                           bio="Local church"))
        assert r["priority_score"] == 70
        assert get_tier(r["priority_score"]) == "Tier 2 - Medium Priority"

    def test_non_hawaii_influencer(self):
        """influencer(20) + reach_50k(20) + website(5) = 45 → Tier 3"""
        r = score(_profile(category="influencer", is_hawaii=False,
                           follower_count=55000,
                           website="https://influencer.com",
                           bio="Content creator"))
        assert r["priority_score"] == 45
        assert get_tier(r["priority_score"]) == "Tier 3 - Low Priority"


# ── Return structure ──────────────────────────────────────────────
class TestReturnStructure:
    def test_returns_dict(self):
        r = score(_profile())
        assert isinstance(r, dict)

    def test_has_priority_score(self):
        r = score(_profile())
        assert "priority_score" in r
        assert isinstance(r["priority_score"], int)

    def test_has_priority_reason(self):
        r = score(_profile())
        assert "priority_reason" in r
        assert isinstance(r["priority_reason"], str)


# ── New category base scores ──────────────────────────────────────
class TestNewCategoryScores:
    def test_service_dog_aligned_bonus(self):
        """service_dog_aligned should get +35 bonus (highest)."""
        r = score(_profile(category="service_dog_aligned"))
        base = score(_profile(category="personal_passive"))
        assert r["priority_score"] == base["priority_score"] + 35
        assert "service_dog" in r["priority_reason"]

    def test_corporate_bonus(self):
        """corporate should get +25 bonus."""
        r = score(_profile(category="corporate"))
        base = score(_profile(category="personal_passive"))
        assert r["priority_score"] == base["priority_score"] + 25
        assert "corporate" in r["priority_reason"]


# ── New engagement signals ────────────────────────────────────────
class TestNewEngagementSignals:
    def test_mission_alignment_bonus(self):
        """Bio mentioning 'service dog' should get +10 mission bonus."""
        aligned = score(_profile(bio="We support service dog programs"))
        unaligned = score(_profile(bio="Just a regular bio"))
        assert aligned["priority_score"] == unaligned["priority_score"] + 10
        assert "mission_aligned" in aligned["priority_reason"]

    def test_therapy_dog_mission_bonus(self):
        """Bio mentioning 'therapy dog' should get +10 mission bonus."""
        r = score(_profile(bio="Therapy dog handler and advocate"))
        assert "mission_aligned" in r["priority_reason"]

    def test_disability_mission_bonus(self):
        """Bio mentioning 'disability' should get +10 mission bonus."""
        r = score(_profile(bio="Disability advocacy and access"))
        assert "mission_aligned" in r["priority_reason"]

    def test_donor_language_bonus(self):
        """Bio with 'sponsor' should get +5 donor language bonus."""
        with_donor = score(_profile(bio="Proud sponsor of local events"))
        without = score(_profile(bio="Just a regular bio"))
        assert with_donor["priority_score"] == without["priority_score"] + 5
        assert "donor_language" in with_donor["priority_reason"]

    def test_support_local_bonus(self):
        """Bio with 'support local' should get +5."""
        r = score(_profile(bio="We support local businesses"))
        assert "donor_language" in r["priority_reason"]

    def test_give_back_bonus(self):
        """Bio with 'give back' should get +5."""
        r = score(_profile(bio="We love to give back to community"))
        assert "donor_language" in r["priority_reason"]

    def test_mission_no_stack_service_dog_category(self):
        """service_dog_aligned category should NOT double-dip mission bonus."""
        sda = score(_profile(category="service_dog_aligned",
                             bio="Service dog training program"))
        sda_no_bio = score(_profile(category="service_dog_aligned",
                                     bio="Professional program"))
        assert sda["priority_score"] == sda_no_bio["priority_score"]


# ── Updated PRD examples for new categories ──────────────────────
class TestNewPRDExamples:
    def test_hawaii_service_dog_org(self):
        """hawaii(30) + service_dog(35) + website(5) = 70 -> Tier 2"""
        r = score(_profile(category="service_dog_aligned", is_hawaii=True,
                           website="https://guidedogs.org",
                           bio="Guide dog foundation"))
        assert r["priority_score"] == 70

    def test_hawaii_corporate_verified(self):
        """hawaii(30) + corporate(25) + business(20) + verified(10) + reach(20) = 100 (clamped)"""
        r = score(_profile(category="corporate", is_hawaii=True,
                           is_business=True, is_verified=True,
                           follower_count=60000, bio="Hawaii's utility"))
        assert r["priority_score"] == 100


# ── Business local/national category bonuses ─────────────────────
class TestBusinessCategoryScores:
    def test_business_local_bonus(self):
        """business_local should get +20 bonus."""
        r = score(_profile(category="business_local"))
        base = score(_profile(category="personal_passive"))
        assert r["priority_score"] == base["priority_score"] + 20
        assert "local_biz(+20)" in r["priority_reason"]

    def test_business_national_bonus(self):
        """business_national should get +10 bonus."""
        r = score(_profile(category="business_national"))
        base = score(_profile(category="personal_passive"))
        assert r["priority_score"] == base["priority_score"] + 10
        assert "national_biz(+10)" in r["priority_reason"]


# ── Charity partner scoring ──────────────────────────────────────
class TestCharityPartnerScoring:
    def test_charity_general_gets_penalty(self):
        """charity/general should get -50 penalty."""
        r = score(_profile(category="charity", subcategory="general", is_hawaii=True))
        assert "charity(-50)" in r["priority_reason"]

    def test_charity_partner_no_penalty(self):
        """charity/partner should NOT get -50 penalty."""
        r = score(_profile(category="charity", subcategory="partner", is_hawaii=True))
        assert "charity(-50)" not in r["priority_reason"]

    def test_charity_partner_hawaii_score(self):
        """charity/partner + hawaii(30) → score 30 (no penalty)."""
        r = score(_profile(category="charity", subcategory="partner", is_hawaii=True))
        assert r["priority_score"] >= 30

    def test_charity_general_hawaii_score(self):
        """charity/general + hawaii(30) - charity(50) → clamped to 0."""
        r = score(_profile(category="charity", subcategory="general",
                           is_hawaii=True))
        assert r["priority_score"] == 0


# ── Pet breeder reduced scoring ──────────────────────────────────
class TestBreederScoring:
    def test_breeder_gets_reduced_bonus(self):
        """pet_industry/breeder should get +10 (not +25)."""
        r = score(_profile(category="pet_industry", subcategory="breeder"))
        assert "pet_breeder(+10)" in r["priority_reason"]
        assert "pet(+25)" not in r["priority_reason"]

    def test_regular_pet_gets_full_bonus(self):
        """pet_industry/veterinary should get +25."""
        r = score(_profile(category="pet_industry", subcategory="veterinary"))
        assert "pet(+25)" in r["priority_reason"]

    def test_breeder_score_vs_regular_pet(self):
        """Breeder should score 15 less than regular pet_industry."""
        breeder = score(_profile(category="pet_industry", subcategory="breeder"))
        regular = score(_profile(category="pet_industry", subcategory="veterinary"))
        assert regular["priority_score"] - breeder["priority_score"] == 15


# ── Veteran/military bonus ──────────────────────────────────────
class TestVeteranBonus:
    def test_veteran_bonus(self):
        """Bio mentioning 'veteran' should get +5."""
        with_vet = score(_profile(bio="Proud veteran and dog lover"))
        without = score(_profile(bio="Just a regular person"))
        assert with_vet["priority_score"] == without["priority_score"] + 15  # veteran(+5) + dogs_pets_bio(+10)
        assert "veteran(+5)" in with_vet["priority_reason"]

    def test_military_bonus(self):
        """Bio mentioning 'military' should get +5."""
        r = score(_profile(bio="Military family stationed in Hawaii"))
        assert "veteran(+5)" in r["priority_reason"]

    def test_armed_forces_bonus(self):
        """Bio mentioning 'armed forces' should get +5."""
        r = score(_profile(bio="Armed forces spouse"))
        assert "veteran(+5)" in r["priority_reason"]


# ── Dog community bio expansion ─────────────────────────────────
class TestDogCommunityBioExpansion:
    def test_dog_mom_bonus(self):
        """Bio mentioning 'dog mom' should get dogs_pets_bio bonus."""
        r = score(_profile(bio="Proud dog mom of 3"))
        assert "dogs_pets_bio(+10)" in r["priority_reason"]

    def test_dog_dad_bonus(self):
        """Bio mentioning 'dog dad' should get dogs_pets_bio bonus."""
        r = score(_profile(bio="Dog dad to a golden retriever"))
        assert "dogs_pets_bio(+10)" in r["priority_reason"]

    def test_fur_parent_bonus(self):
        """Bio mentioning 'fur parent' should get dogs_pets_bio bonus."""
        r = score(_profile(bio="Fur parent and coffee lover"))
        assert "dogs_pets_bio(+10)" in r["priority_reason"]

    def test_pup_parent_bonus(self):
        """Bio mentioning 'pup parent' should get dogs_pets_bio bonus."""
        r = score(_profile(bio="Pup parent | Hawaii life"))
        assert "dogs_pets_bio(+10)" in r["priority_reason"]


# ── Additional coverage for category branches ────────────────────

class TestCategoryFallthrough:
    """Test categories that don't match any elif branch (no category bonus)."""

    def test_personal_engaged_no_category_bonus(self):
        """personal_engaged should not get any category bonus."""
        r = score(_profile(category="personal_engaged"))
        # No category-specific reason in output
        for keyword in ["service_dog", "bank", "corporate", "pet", "org",
                        "elected", "local_biz", "national_biz", "influencer", "media"]:
            assert keyword not in r["priority_reason"]

    def test_personal_passive_no_category_bonus(self):
        """personal_passive should not get any category bonus."""
        r = score(_profile(category="personal_passive"))
        for keyword in ["service_dog", "bank", "corporate", "pet", "org",
                        "elected", "local_biz", "national_biz", "influencer", "media"]:
            assert keyword not in r["priority_reason"]


class TestFollowerCountNone:
    """Test follower_count=None path (or 0 fallback)."""

    def test_none_follower_count_no_reach_bonus(self):
        """follower_count=None should not trigger any reach bonus."""
        r = score(_profile(follower_count=None))
        assert "reach" not in r["priority_reason"]

    def test_none_post_count_no_active_posting(self):
        """post_count=None should not trigger active_posting bonus."""
        r = score(_profile(post_count=None))
        assert "active_posting" not in r["priority_reason"]


class TestDonorLanguagePatterns:
    """Test each individual donor language regex pattern."""

    def test_partnership(self):
        r = score(_profile(bio="We value our partnership"))
        assert "donor_language" in r["priority_reason"]

    def test_sponsor(self):
        r = score(_profile(bio="Proud sponsor of community"))
        assert "donor_language" in r["priority_reason"]

    def test_support_local(self):
        r = score(_profile(bio="We support local business"))
        assert "donor_language" in r["priority_reason"]

    def test_donate(self):
        r = score(_profile(bio="Donate to help our mission"))
        assert "donor_language" in r["priority_reason"]
