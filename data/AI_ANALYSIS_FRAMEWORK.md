# AI Analysis Framework for Hawaii FIDO Fundraising

## Task Overview

You are analyzing Instagram profiles to identify high-value fundraising prospects and marketing partners for Hawaii FIDO, a nonprofit focused on service dog accessibility and training in Hawaii.

**Key Principle**: All analysis is driven by AI reasoning from bio content, website information, and profile context. Do NOT make assumptions beyond what you can read.

---

## Analysis Evaluation Factors

### 1. Hawaii-Based Assessment
Read the bio for indicators of Hawaii location:
- Geographic references (Honolulu, Oahu, Maui, 808, Hawaii)
- Local business language ("local", "island", "aloha")
- Hawaiian words or cultural references
- Explicit mentions of Hawaii in description
- If website is available, check for Hawaii address/references

**Output**: `hawaii_based: true/false` + `reasoning_hawaii: "specific evidence"`

### 2. Entity Type Classification
Determine what type of entity this is:
- **Government official** - Mayor, councilmember, representative, bureaucrat
- **Corporation** - Major company (Hawaiian Electric, Honda, Sony)
- **Local business** - Small/medium Hawaii business (restaurant, brewery, shop)
- **Member-based org** - Rotary, professional association, club, church
- **Pet industry** - Dog trainer, vet, pet store, dog-related business
- **Nonprofit** - Charitable org, community organization
- **Influencer** - Content creator, social media personality
- **Professional** - Consultant, coach, artist, photographer
- **Individual** - Regular person

**Output**: `entity_type: "classification"` + `reasoning_type: "why"`

### 3. Business Capacity & Resources (HIGH/MEDIUM/LOW)
Can they actually donate or fund something?
- Years in operation (longevity = stability)
- Scale of operation (employees, locations)
- Website professionalism
- Revenue indicators (if apparent)
- Organizational stability
- Decision-making authority

**For Government Officials**: Authority matters more than personal wealth
**For Member Orgs**: Access to member donations matters

**Output**: `capacity: "HIGH/MEDIUM/LOW"` + `reasoning_capacity: "evidence"`

### 4. Strategic Alignment & Mission Fit (HIGH/MEDIUM/LOW/NONE)
Do they connect with service dogs, disability accessibility, or Hawaii FIDO's mission?
- Service dog mentions (trainers, handlers, orgs)
- Disability/accessibility focus
- Community service orientation
- Animal welfare focus
- Hawaii local pride/community involvement
- Any overlap with target audience

**Output**: `alignment: "HIGH/MEDIUM/LOW/NONE"` + `reasoning_alignment: "evidence"`

### 5. Relationship Potential (HIGH/MEDIUM/LOW)
How reachable and approachable are they?
- Local presence (Hawaii-based is a plus)
- Community engagement (do they respond to community outreach)
- Business type (some are more open to partnerships than others)
- Verified/professional profile
- Bio suggests openness or professional network
- Website shows contact info or collaboration interest

**Output**: `relationship: "HIGH/MEDIUM/LOW"` + `reasoning_relationship: "evidence"`

### 6. Impact Potential (HIGH/MEDIUM/LOW)
Can they open doors beyond themselves?
- Credibility and reputation
- Network access (members, employees, partners)
- Multiplier effect potential
- Media reach
- Influence over others
- Long-term partnership potential vs one-time donation

**Special Note on Member Organizations**:
- Rotary Club → direct access to dozens of wealthy business owners
- Professional Association → access to industry members
- Chamber of Commerce → access to local business community
- Church/Religious Org → access to congregation members
- Alumni Association → access to former students
- **These are HIGH impact because one presentation = many potential donors**

**Output**: `impact: "HIGH/MEDIUM/LOW"` + `reasoning_impact: "evidence"`

### 7. Fundraising Score (0-100 for Fundraising Prospects)
Synthesize above factors into an overall score:

**90-100**: Top tier - perfect fit
- HIGH capacity + HIGH alignment + HIGH impact
- E.g., Hawaiian Electric CSR department

**75-89**: Excellent prospect
- HIGH capacity + MEDIUM+ alignment, OR
- HIGH capacity + HIGH impact but MEDIUM alignment

**60-74**: Good prospect
- MEDIUM+ capacity + MEDIUM+ alignment, OR
- HIGH capacity but LOW alignment

**40-59**: Possible prospect
- MEDIUM capacity, MEDIUM+ alignment, OR
- HIGH capacity but NONE alignment (still worth trying)

**20-39**: Low prospect
- LOW capacity OR NONE alignment

**0-19**: Not suitable

**Reasoning**: Explain how the score combines the factors

**Output**: `score: number` + `outreach_type: "DIRECT_FUNDING/PARTNERSHIP/DOOR_OPENER/MARKETING_PARTNER"`

### 8. Recommended Outreach Strategy
Based on all factors, what's the specific approach?
- **DIRECT_FUNDING**: Ask for money, sponsor program, donate
- **PARTNERSHIP**: Collaborate (venue, co-training, joint events)
- **DOOR_OPENER**: Use to open access to larger organizations or networks
- **MARKETING_PARTNER**: Collaborate on reaching shared audiences
- **SKIP**: Not worth time to contact

**Output**: `outreach_strategy: "specific recommended approach"`

---

## Mixture of Experts Strategies

Apply different reasoning based on entity type:

### Government Officials
- Focus on policy influence and legitimacy benefit
- They can open doors with city/state resources
- Public sector credibility
- Example: "Councilmember can advocate at city council meetings"

### Member-Based Organizations (HIGH VALUE)
- Estimate membership size if possible
- Research known membership demographics
- One presentation = access to entire membership
- Multiplier effect is the main value
- Example: "Rotary Club of Honolulu likely has 100+ affluent business owners as members"

### Corporations
- Look for CSR programs or community giving history
- Scale and longevity matter
- Hawaii-based corporations show stronger local commitment
- Example: "Hawaiian Electric has 130+ year history, major Hawaii institution"

### Local Businesses
- Partnership potential (venue, pro-bono services)
- Community integration = authentic local relationships
- Smaller but more accessible than corporations
- Example: "Brewery can host events, engage local community"

### Pet Industry
- Mission alignment is key strength
- Already aware of service dog value
- Shared customer base potential
- Example: "Dog trainer has immediate understanding of service dog importance"

### Nonprofits
- Understand mission-based giving
- Network with other nonprofits
- May have grant funding or donor networks
- Example: "Animal rescue org understands animal welfare mission alignment"

### High-Follower Influencers (For Marketing)
- Audience demographics matter more than follower count
- Pet-related influencers = more relevant
- Engagement rate > raw followers
- Authenticity > sponsored content history

---

## Critical Notes

1. **Read the bio carefully** - it's your primary source of truth
2. **Use website content** if available to deepen understanding
3. **Hawaii-based is a strong signal** but not required
4. **Follower count alone is not the score** - capacity and alignment matter more
5. **Member organizations are valuable** - one relationship = many donors
6. **Be specific in reasoning** - explain what in the bio/website led to your conclusion
7. **Score conservatively** - only HIGH scores should be in top 50

---

## Output Format (JSON)

```json
{
  "handle": "hawaiianelectric",
  "display_name": "Hawaiian Electric",
  "follower_count": 33400,
  "bio": "Established in 1891...",
  "website": "hawaiianelectric.com",
  "website_content": "[first 1500 chars of website content]",

  "hawaii_based": true,
  "reasoning_hawaii": "...",

  "entity_type": "corporation",
  "reasoning_type": "...",

  "capacity": "HIGH",
  "reasoning_capacity": "...",

  "alignment": "MEDIUM",
  "reasoning_alignment": "...",

  "relationship": "MEDIUM",
  "reasoning_relationship": "...",

  "impact": "HIGH",
  "reasoning_impact": "...",

  "score": 78,
  "outreach_type": "DIRECT_FUNDING",
  "outreach_strategy": "..."
}
```

---

## Examples of Good Analysis

**Hawaiian Electric** (High Score)
- hawaii_based: true (major Hawaii utility)
- entity_type: corporation
- capacity: HIGH (established 1891, major utility, significant resources)
- alignment: MEDIUM (CSR programs likely, community-focused)
- relationship: MEDIUM (professional, reachable via CSR)
- impact: HIGH (major Hawaii institution, credibility, can open doors)
- score: 78
- reasoning: "Major Hawaii corporation with 130+ year history, CSR programs, and significant institutional credibility. Can open doors to corporate partnerships and provide major funding. Slightly lower alignment (utility vs service dogs) but high capacity and impact compensate."

**Rotary E-Club Hawaii** (Very High Score)
- hawaii_based: true
- entity_type: member_org
- capacity: HIGH (Rotary members are affluent business owners)
- alignment: HIGH (Rotary focuses on community service, vocational service)
- relationship: HIGH (service organizations welcome presentations)
- impact: HIGH (one presentation = access to dozens of wealthy business owners)
- score: 92
- reasoning: "Member-based service organization with direct access to affluent Hawaii business community. Perfect mission alignment and multiplier effect. One presentation reaches entire club."

**Local Dog Trainer** (Medium Score)
- hawaii_based: true
- entity_type: pet_industry
- capacity: MEDIUM (local business, moderate resources)
- alignment: HIGH (direct service dog expertise)
- relationship: HIGH (local, professional, aligned)
- impact: MEDIUM (can refer clients, limited broader reach)
- score: 68
- reasoning: "Local Hawaii dog trainer with direct mission alignment and accessibility. Good for partnership and referrals, but limited broader impact. Still valuable for grassroots relationships."
