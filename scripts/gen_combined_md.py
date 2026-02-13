#!/usr/bin/env python3
"""Generate combined_top_followers.md from the existing AI markdown (entries 1-25)
plus 6 hand-written entries for the DB misses (entries 26-31)."""

import os, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_MD = os.path.join(BASE, "output", "fundraising_recommendations.md")
OUT_MD = os.path.join(BASE, "output", "combined_top_followers.md")

# ── 6 new entries in the same markdown format ────────────────────────────
NEW_ENTRIES = r"""
### 26. fishcake

**Handle**: @fishcakehawaii

#### Profile
- **Followers**: 15,800
- **Following**: 2,302
- **Posts**: 1,275
- **Verified**: No
- **Business Account**: No
- **Bio**: Community
third space for co creatives, art, handmade retail, test cafe, clay studio, @fishschoolhawaii + events
307c Kamani St, Honolulu, Hawaii 96813
beacons.ai/fishcakehawaii

#### AI Analysis
- **Hawaii-Based**: Yes
- **Entity Type**: member_organization
- **Financial Capacity**: 22/40
- **Donor Access Multiplier**: 20/25
- **Dinner Ticket/Table Potential**: 16/20
- **Hawaii Connection**: 14/15
- **Total Fundraising Score**: 72/100
- **Score Breakdown**: Financial: 22/40 + Donor Access: 20/25 + Dinner: 16/20 + Hawaii: 14/15 = 72/100
- **Outreach Type**: MEMBER_PRESENTATION
- **Suggested Ask**: $0 (access value)

**Hawaii Connection**: Physical space at 307c Kamani St, Honolulu. Deep roots in Honolulu creative community with events, workshops, and vendor showcases.

**Financial Capacity**: TIER_C - Community creative space with retail, cafe, clay studio, and event hosting. Revenue comes from multiple streams (classes, retail, events, cafe) but operates as community hub rather than high-margin business. Moderate financial capacity.

**Donor Access**: HIGH - fishcake is a gathering place for Honolulu's creative and small-business community. Hosts events, vendor markets, and workshops that attract entrepreneurs, artists, and community-minded professionals. One presentation or event partnership = access to dozens of local business owners and creative professionals who value community causes.

**Dinner Potential**: VENUE_PARTNER - fishcake's event space and community programming make it an ideal partner for hosting a pre-dinner fundraiser, trunk show, or awareness event. Could also promote dinner through their vendor and workshop networks.

**Hawaii Connection Detail**: LOCAL_STRONG - Established Honolulu creative hub in Kakaako, deeply embedded in local arts and small-business ecosystem. Regular community events and workshops.

**Outreach Strategy**: Partner with fishcake to host a Hawaii FIDO awareness event or fundraiser at their space. Request inclusion in their events calendar and vendor network communications. fishcake's value is as a community connector and event venue, not a direct donor. One event at fishcake reaches their entire creative/entrepreneurial network.

---

### 27. Hawaii Doggie Bakery

**Handle**: @hawaiidoggiebakery

#### Profile
- **Followers**: 9,755
- **Following**: 1,750
- **Posts**: 3,075
- **Verified**: No
- **Business Account**: Yes
- **Website**: shop.hawaiidoggiebakery.org
- **Bio**: Pet Service
Hawaii's 1st dog bakery founded in 1998
Closed Tuesdays, open all other days
10am-3pm
Call/Text, no DMs
2961C East Manoa Rd, Honolulu, Hawaii 96822
shop.hawaiidoggiebakery.org

#### AI Analysis
- **Hawaii-Based**: Yes
- **Entity Type**: established_business
- **Financial Capacity**: 24/40
- **Donor Access Multiplier**: 18/25
- **Dinner Ticket/Table Potential**: 15/20
- **Hawaii Connection**: 14/15
- **Total Fundraising Score**: 71/100
- **Score Breakdown**: Financial: 24/40 + Donor Access: 18/25 + Dinner: 15/20 + Hawaii: 14/15 = 71/100
- **Outreach Type**: TABLE_PURCHASE
- **Suggested Ask**: $2,500-$5,000

**Hawaii Connection**: Hawaii's first dog bakery, founded 1998, located at 2961C East Manoa Rd, Honolulu. 25+ years serving Hawaii's pet community.

**Financial Capacity**: TIER_B - 25+ year established pet business with dedicated retail location in Manoa, online shop, and nearly 10K followers. Longevity indicates sustained profitability. Pet bakeries serving affluent pet owners have strong margins on specialty products.

**Donor Access**: MEDIUM-HIGH - Customer base of dedicated, spending-oriented pet owners who prioritize their dogs. 25 years of operations means deep relationships with Hawaii's pet community, veterinarians, groomers, and pet event organizers. Natural mission alignment with service dog organization.

**Dinner Potential**: TABLE_BUYER - Established pet business with strong community ties. Table purchase aligns with brand positioning as Hawaii's premier dog bakery. Could also donate auction items (gift baskets, gift cards).

**Hawaii Connection Detail**: LOCAL_STRONG - Hawaii's FIRST dog bakery, 25+ years in Manoa. Pioneer in Hawaii's pet industry. Deep institutional knowledge of the local pet community.

**Outreach Strategy**: Direct outreach to owner emphasizing natural mission alignment - Hawaii's oldest dog bakery supporting Hawaii's service dog nonprofit. Request table purchase and auction item donation (gift basket of signature treats). Propose co-branded fundraising product (limited-edition FIDO treats). Their 10K-follower Instagram could amplify dinner promotion.

---

### 28. THE PUBLIC PET

**Handle**: @thepublicpet

#### Profile
- **Followers**: 15,500
- **Following**: 2,850
- **Posts**: 4,551
- **Verified**: No
- **Business Account**: No
- **Website**: linktr.ee/thepublicpet
- **Bio**: Pet Supplies
URBAN PET SUPPLY for CATS & DOGS
Open TUE-SUN 9-6p / Closed MONDAYS
3422 Waialae Ave, Honolulu, Hawaii 96816
linktr.ee/thepublicpet

#### AI Analysis
- **Hawaii-Based**: Yes
- **Entity Type**: established_business
- **Financial Capacity**: 24/40
- **Donor Access Multiplier**: 16/25
- **Dinner Ticket/Table Potential**: 15/20
- **Hawaii Connection**: 14/15
- **Total Fundraising Score**: 69/100
- **Score Breakdown**: Financial: 24/40 + Donor Access: 16/25 + Dinner: 15/20 + Hawaii: 14/15 = 69/100
- **Outreach Type**: TABLE_PURCHASE
- **Suggested Ask**: $2,500-$5,000

**Hawaii Connection**: Physical retail location at 3422 Waialae Ave, Honolulu (Kaimuki). Established neighborhood pet supply store.

**Financial Capacity**: TIER_B - Urban pet supply store in desirable Kaimuki location with 15.5K followers and 4,500+ posts indicates thriving, engaged business. Pet retail stores in affluent neighborhoods generate strong revenue from premium pet products. Active social media presence suggests effective marketing and loyal customer base.

**Donor Access**: MEDIUM - Pet store customers are dedicated pet owners who spend on their animals. Store serves as community gathering point for pet owners. Access to pet-owning demographic that naturally aligns with service dog mission. Events like "Paw Hana" indicate community-building orientation.

**Dinner Potential**: TABLE_BUYER - Established pet retail business with capacity for table purchase. Strong community presence and brand identity make dinner sponsorship a natural fit for visibility among pet-owning community.

**Hawaii Connection Detail**: LOCAL_STRONG - Kaimuki neighborhood fixture, active community engagement through events and social media. Deep roots in Honolulu's pet owner community.

**Outreach Strategy**: Visit store in person for relationship building. Propose table purchase with recognition as pet industry sponsor. Request in-store promotion (flyers, counter display) for FIDO dinner. Could host in-store adoption or awareness event. Their 15.5K follower Instagram is valuable for dinner promotion. Natural co-marketing partner for any pet-related FIDO campaign.

---

### 29. Julianne King (Heart of Kailua)

**Handle**: @heartofkailua

#### Profile
- **Followers**: 3,767
- **Following**: 2,213
- **Posts**: 627
- **Verified**: No
- **Business Account**: No
- **Website**: hawaiiautismfoundation.org
- **Bio**: Community
Let's change the understanding of autism! Mother, wife, friend.....taking action is my antidote.
hawaiiautismfoundation.org

#### AI Analysis
- **Hawaii-Based**: Yes
- **Entity Type**: member_organization
- **Financial Capacity**: 18/40
- **Donor Access Multiplier**: 22/25
- **Dinner Ticket/Table Potential**: 14/20
- **Hawaii Connection**: 14/15
- **Total Fundraising Score**: 68/100
- **Score Breakdown**: Financial: 18/40 + Donor Access: 22/25 + Dinner: 14/20 + Hawaii: 14/15 = 68/100
- **Outreach Type**: MEMBER_PRESENTATION
- **Suggested Ask**: $0 (access value)

**Hawaii Connection**: Kailua-based community leader, Hawaii Autism Foundation website linked. Deep roots in Windward Oahu community.

**Financial Capacity**: TIER_C - Nonprofit leader/community organizer. Personal financial capacity is moderate, but value lies entirely in network access. Hawaii Autism Foundation connects to disability advocacy community, donors, and government funding channels.

**Donor Access**: HIGH - Nonprofit founder/leader in the disability space has direct overlap with FIDO's mission (service dogs for people with disabilities). Access to Hawaii Autism Foundation donor base, disability advocacy network, government disability services contacts, and Kailua/Windward community leaders. One relationship opens doors to an entire parallel nonprofit ecosystem.

**Dinner Potential**: MULTI_TICKET - Could bring foundation board members or supporters. More valuable as a connector who introduces FIDO to her donor network and advocacy community.

**Hawaii Connection Detail**: LOCAL_STRONG - Kailua community leader with deep ties to Windward Oahu. Hawaii Autism Foundation indicates years of local nonprofit work and community building.

**Outreach Strategy**: Peer-to-peer nonprofit outreach. Connect as fellow disability-focused Hawaii nonprofit. Propose cross-promotion, shared events, or joint grant applications. Request introduction to Hawaii Autism Foundation donors and board members who may also support service dog mission. Invite to dinner as nonprofit partner. The disability advocacy overlap makes this a high-value strategic relationship, not just a fundraising target.

---

### 30. Haiku Veterinary Clinic

**Handle**: @haikuvet

#### Profile
- **Followers**: 1,003
- **Following**: 1,090
- **Posts**: 455
- **Verified**: No
- **Business Account**: No
- **Website**: www.kaneohevets.com
- **Bio**: Community
Providing life long care for your pet
Located on the beautiful Windward side of Oahu, HI
info@haikuvet.com | (808) 247-0608
45-773 Kamehameha Hwy, Kaneohe, Hawaii 96744
www.kaneohevets.com

#### AI Analysis
- **Hawaii-Based**: Yes
- **Entity Type**: established_business
- **Financial Capacity**: 24/40
- **Donor Access Multiplier**: 16/25
- **Dinner Ticket/Table Potential**: 14/20
- **Hawaii Connection**: 14/15
- **Total Fundraising Score**: 68/100
- **Score Breakdown**: Financial: 24/40 + Donor Access: 16/25 + Dinner: 14/20 + Hawaii: 14/15 = 68/100
- **Outreach Type**: TABLE_PURCHASE
- **Suggested Ask**: $2,000-$3,500

**Hawaii Connection**: Windward Oahu veterinary clinic at 45-773 Kamehameha Hwy, Kaneohe. Serves Kaneohe/Kailua pet community.

**Financial Capacity**: TIER_B - Established veterinary clinic on Windward Oahu. Veterinary practices have strong revenue from medical services, surgeries, preventive care. Windward location serves affluent Kailua/Kaneohe pet owners. Website and active social media indicate professional, well-run practice.

**Donor Access**: MEDIUM - Veterinary practice has client base of committed pet owners, many affluent. Connections to pet industry (suppliers, groomers, pet stores) and medical community. Windward Oahu pet owners are a tight-knit community.

**Dinner Potential**: MULTI_TICKET - Veterinary practice could purchase 2-3 tickets for veterinarians and staff. Direct mission alignment: vet clinic supporting service dog nonprofit is natural fit. Could display FIDO materials in waiting room.

**Hawaii Connection Detail**: LOCAL_STRONG - Established Windward Oahu vet practice. "Haiku" name references local geography. Serves Kaneohe/Kailua community with deep local roots.

**Outreach Strategy**: Contact clinic owner/lead veterinarian. Pitch table purchase emphasizing natural alignment: veterinary practice supporting service dog health and welfare. Propose veterinary partnership (discounted care for FIDO service dogs in training). Request waiting room promotional materials. Vet recommendation carries enormous weight with pet-owning donors.

---

### 31. HUMPHREY

**Handle**: @humphreysaccaro

#### Profile
- **Followers**: 64,300
- **Following**: 7,488
- **Posts**: 1,450
- **Verified**: No
- **Business Account**: No
- **Website**: linktr.ee/humphreysaccaro
- **Bio**: Honolulu, Hawaii
Mommy's boy @sammmysaccaro
Professional rock diver
linktr.ee/humphreysaccaro

#### AI Analysis
- **Hawaii-Based**: Yes
- **Entity Type**: established_business
- **Financial Capacity**: 22/40
- **Donor Access Multiplier**: 18/25
- **Dinner Ticket/Table Potential**: 12/20
- **Hawaii Connection**: 14/15
- **Total Fundraising Score**: 66/100
- **Score Breakdown**: Financial: 22/40 + Donor Access: 18/25 + Dinner: 12/20 + Hawaii: 14/15 = 66/100
- **Outreach Type**: DOOR_OPENER
- **Suggested Ask**: N/A (in-kind promo value)

**Hawaii Connection**: Honolulu-based pet influencer account (French Bulldog). 64.3K followers with strong Hawaii-focused content.

**Financial Capacity**: TIER_C - Pet influencer account monetized through brand partnerships, sponsored content, and merchandise (Linktree). 64K followers indicates meaningful sponsorship revenue. Owner @sammmysaccaro likely has additional income. Financial value is moderate for direct donation but high for in-kind promotional reach.

**Donor Access**: MEDIUM-HIGH - 64.3K followers is the largest pet-focused audience in FIDO's follower network. Access to engaged pet-lover demographic across Hawaii and beyond. Brand partnership connections to pet industry companies (Dr. Harvey's shown in highlights). Influencer network connections to other pet accounts.

**Dinner Potential**: UNLIKELY_DIRECT - Influencer value is promotional, not table purchase. One Instagram post or story about FIDO dinner reaches 64K followers, far exceeding the value of a single table purchase.

**Hawaii Connection Detail**: LOCAL_STRONG - Honolulu-based dog with Hawaii-themed content (beach, sunsets, rock diving). Strong local brand identity as Hawaii's celebrity French Bulldog.

**Outreach Strategy**: Approach owner @sammmysaccaro for promotional partnership. Request Instagram post/story promoting FIDO dinner or fundraising campaign in exchange for event tickets or recognition. One Humphrey post = 64K impressions to pet-loving audience. Could attend dinner as "celebrity guest" for photo ops. Propose ongoing brand ambassador relationship. The promotional reach (64K followers) is worth far more than any direct financial ask.

---
"""


def main():
    with open(AI_MD, encoding="utf-8") as f:
        full = f.read()

    # Extract fundraising section (everything before Marketing section)
    marker = "## Top 15 Marketing Campaign Partners"
    idx = full.find(marker)
    if idx == -1:
        raise RuntimeError("Could not find marketing section marker")
    fundraising_section = full[:idx].rstrip()

    # Update header: "Top 25" -> "Top 31 Combined"
    fundraising_section = fundraising_section.replace(
        "## Top 25 Fundraising Prospects",
        "## Top 31 Combined Fundraising Prospects",
    )

    # Update the subtitle
    fundraising_section = fundraising_section.replace(
        "High-value prospects for direct fundraising outreach. "
        "Ranked by fundraising capacity - ability to write checks, "
        "buy tables, and open doors to other donors.",
        "AI-generated top 25 (ranks 1-25) followed by 6 high-value "
        "prospects the AI model missed that were caught by database "
        "scoring (ranks 26-31). All scored on the 4-axis model: "
        "Financial Capacity, Donor Access, Dinner Potential, Hawaii Connection.",
    )

    # Update top-level title
    fundraising_section = fundraising_section.replace(
        "# Hawaii FIDO Fundraising & Marketing Analysis",
        "# Hawaii Fi-Do Combined Top 31 Follower Prospects",
    )

    # Update subtitle line
    fundraising_section = fundraising_section.replace(
        "> AI-driven analysis of 444 Instagram followers for fundraising prospects",
        "> Combined AI + database analysis of 444 Instagram followers — 31 best fundraising leads",
    )

    combined = fundraising_section + "\n" + NEW_ENTRIES.strip() + "\n"

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(combined)

    # Count entries
    count = len(re.findall(r"^### \d+\.", combined, re.MULTILINE))
    print(f"Wrote {count} entries to {OUT_MD}")


if __name__ == "__main__":
    main()
