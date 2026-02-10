# AI Analysis Framework for Hawaii FIDO Fundraising

## Task Overview

You are analyzing Instagram profiles to identify **high-value fundraising prospects** for Hawaii FIDO's annual fundraising dinner. The goal is to find 25 people/organizations who will:
- Write checks or make donations
- Buy tables or tickets at the annual dinner ($200-$5,000)
- Give access to members/networks who will donate

**Key Principle**: Fundraising capacity is ALL that matters. Mission alignment with service dogs is irrelevant to scoring. A utility company with a $50K CSR budget and zero knowledge of service dogs is worth 10x a sister nonprofit with perfect mission alignment but no money.

---

## Hard Exclusion Rules (Auto-SKIP, Score = 0)

**BEFORE scoring any profile, check these exclusion rules first. If ANY rule matches, set score = 0, entity_type = EXCLUDE_*, outreach_type = SKIP, and move on.**

### EXCLUDE: Competitors
- Other service/assistance/guide dog organizations
- Other therapy dog programs
- Any entity that trains, places, or advocates for service/assistance dogs
- Examples: Assistance Dogs of Hawaii, Guide Dogs of Hawaii, IADA, Canine Companions

### EXCLUDE: ALL Nonprofits / 501(c)(3) / Charities - NO EXCEPTIONS
- Animal welfare nonprofits (SPCA, Humane Society, animal rescue)
- Disability/special needs organizations (autism foundations, disability legal services, independent living centers)
- Grantmaking foundations (Friends of Hawaii Charities, etc.)
- United Way, community foundations, any charitable organization
- Combined Federal Campaign, government charity programs
- If it says nonprofit, 501(c)(3), charity, or foundation: score = 0, SKIP
- **ONLY EXCEPTION**: Member-based organizations (Rotary, Chamber of Commerce, professional associations) are classified as `member_organization`, NOT as nonprofits. These exist to serve their members (who are business owners/professionals with money) and are HIGH VALUE fundraising targets.

### EXCLUDE: Pet Industry Micro-Businesses
- Individual dog trainers, groomers, walkers
- Pet influencer accounts (dogs with their own Instagram)
- Solo pet photographers, pet sitters
- **EXCEPTION**: Established pet businesses with 5+ years, physical location, multiple employees/services get scored normally as `established_business`. The test: could this business realistically buy a $200 dinner ticket?

### EXCLUDE: Personal/Irrelevant Accounts
- Personal accounts with no business or wealth signals
- Empty bios, spam/bot accounts
- Hobby accounts, meme pages

---

## Scoring System: 4 Factors (100 points total)

### Factor 1: Financial Capacity (0-40 points, 40% weight)
**Question**: Can they write a check?

| Tier | Points | Description | Examples |
|------|--------|-------------|----------|
| TIER_A | 35-40 | Major corporation with CSR budget, significant revenue | Hawaiian Electric, banks, utilities, major employers |
| TIER_B | 25-34 | Established business with significant revenue | Law firms, real estate agencies, medical groups, hotel chains |
| TIER_C | 15-24 | Medium business or wealthy individual | Successful restaurant, dental practice, established consulting firm |
| TIER_D | 8-14 | Small business with moderate income | Single-location retail, small professional practice |
| TIER_E | 1-7 | Micro business with limited financial signals | Freelancer with business account, small online shop |
| TIER_F | 0 | Other nonprofits, charities, competitors | ZERO capacity - these entities need money themselves |

**Output**: `financial_capacity: 0-40` + `financial_capacity_reasoning: "specific evidence"`

### Factor 2: Donor Access Multiplier (0-25 points, 25% weight)
**Question**: Can they get OTHERS to donate? One relationship with a Rotary club president = access to 50+ wealthy business owners.

| Level | Points | Description | Examples |
|-------|--------|-------------|----------|
| HIGH | 20-25 | Organization with 50+ members who are business owners/professionals | Rotary clubs, Chamber of Commerce, professional associations |
| MEDIUM | 12-19 | Organization with members or large employee base | Churches, business networking groups, corporate employee programs |
| LOW | 5-11 | Business owner who knows other business owners | Restaurant owner, real estate agent, attorney |
| NONE | 0-4 | Individual account, sole proprietor, no network signals | Personal accounts, solo freelancers |

**Output**: `donor_access: 0-25` + `donor_access_reasoning: "specific evidence"`

### Factor 3: Dinner Ticket/Table Potential (0-20 points, 20% weight)
**Question**: Will they buy tickets or a table at the annual fundraising dinner?

| Level | Points | Description | Examples |
|-------|--------|-------------|----------|
| TABLE_BUYER | 16-20 | Will buy a full table ($2K-$5K) | Corporations, banks, law firms, major businesses |
| MULTI_TICKET | 10-15 | Will buy 2-4 tickets ($400-$800) | Business owners bringing partners/employees |
| SINGLE_TICKET | 5-9 | Might buy 1 ticket ($200) | Community members, small business owners |
| UNLIKELY | 0-4 | Won't buy tickets | Nonprofits, out-of-state, no financial signals |

**Output**: `dinner_potential: 0-20` + `dinner_potential_reasoning: "specific evidence"`

### Factor 4: Hawaii Connection (0-15 points, 15% weight)
**Question**: Are they local and reachable for an in-person dinner event?

| Level | Points | Description | Examples |
|-------|--------|-------------|----------|
| LOCAL_STRONG | 12-15 | Confirmed Hawaii-based, physical presence, long history | 20+ year Hawaii business, "Est. 1891", multiple Hawaii locations |
| LOCAL_MODERATE | 8-11 | Hawaii-based but newer or smaller presence | Newer Hawaii business, Hawaii address in bio |
| NATIONAL_HI_PRESENCE | 4-7 | National entity with Hawaii office/presence | National chain with Hawaii location, mainland company with HI office |
| NO_CONNECTION | 0-3 | No Hawaii signals, mainland/international | No geographic indicators, clearly out-of-state |

**Output**: `hawaii_connection: 0-15` + `hawaii_connection_reasoning: "specific evidence"`

### Total Score Calculation
```
total_score = financial_capacity + donor_access + dinner_potential + hawaii_connection
```
Maximum: 100 points

---

## Entity Type Classification

Classify each profile into one of these fundraising-oriented types:

### Scoreable Entity Types
- `corporation` - Major company with CSR budget (Hawaiian Electric, banks, utilities)
- `established_business` - Real revenue, employees, physical location (law firms, restaurants, medical groups)
- `member_organization` - Rotary, Chamber, professional associations (HIGH VALUE for donor access)
- `bank_financial` - Banks, credit unions, financial services
- `government_official` - Elected official with budget authority or door-opening ability
- `wealthy_individual` - Business owner, executive, professional with clear wealth signals
- `media_event_org` - Major event with corporate sponsors (Sony Open, charity galas)
- `small_business` - Single-location, limited revenue but real business

### Auto-Exclude Entity Types (Score = 0)
- `EXCLUDE_competitor` - Other service/assistance/guide dog organizations
- `EXCLUDE_nonprofit` - Any nonprofit, 501(c)(3), charity, foundation
- `EXCLUDE_pet_micro` - Individual dog trainers, groomers, pet influencer accounts
- `EXCLUDE_personal` - Personal accounts with no business or wealth signals

**Output**: `entity_type: "type"` + `entity_type_reasoning: "why this classification"`

---

## Outreach Type & Suggested Ask

Based on entity type and score, recommend the specific fundraising approach:

| Outreach Type | Description | Typical Ask Range |
|---------------|-------------|-------------------|
| `CORPORATE_SPONSORSHIP` | Event sponsorship with branding/recognition | $5,000-$25,000 |
| `TABLE_PURCHASE` | Buy a table at the annual dinner | $2,000-$5,000 |
| `MEMBER_PRESENTATION` | Request speaking slot to pitch their members | N/A (access value) |
| `INDIVIDUAL_DONOR` | Personal relationship and direct ask | $200-$2,000 |
| `DOOR_OPENER` | Can introduce FIDO to decision-makers | N/A (connection value) |
| `SKIP` | Not a fundraising target | $0 |

**Output**: `outreach_type: "type"` + `suggested_ask_amount: "$X-$Y"` + `outreach_strategy: "specific recommended approach"`

---

## Mixture of Experts: Entity-Specific Evaluation

### Corporations
- Look for CSR programs, community giving history, "community" in bio
- Scale and longevity = stability and budget
- Hawaii-based corporations have stronger local commitment
- TABLE_BUYER or CORPORATE_SPONSORSHIP ask
- Example reasoning: "Hawaiian Electric, established 1891, major Hawaii utility serving all islands. CSR budget is certain. 130+ year community presence. Corporate sponsorship ask $10K-$25K."

### Member-Based Organizations (HIGHEST MULTIPLIER VALUE)
- Estimate membership size if possible
- One presentation = access to entire membership of business owners
- Rotary members are affluent business professionals by definition
- Chamber members are local business owners
- MEMBER_PRESENTATION outreach, then individual asks to members
- Example reasoning: "Rotary E-Club of Hawaii, service organization whose members are affluent business owners. One speaking slot = pitch to 50+ potential donors. Multiplier effect makes this top-tier."

### Banks & Financial Institutions
- Community banks are especially engaged locally
- CRA (Community Reinvestment Act) obligations mean they MUST give locally
- TABLE_BUYER or CORPORATE_SPONSORSHIP
- Example reasoning: "First Hawaiian Bank, oldest bank in Hawaii. CRA obligations require local community investment. Table purchase or sponsorship ask $5K-$10K."

### Government Officials
- They control budgets and open doors to government funding
- Public endorsement adds credibility
- DOOR_OPENER outreach
- Example reasoning: "State Representative with committee influence. Can advocate for government funding, open doors to other officials. Door-opener value, not direct donation target."

### Established Businesses
- Look for years in operation, multiple locations, employee count
- Professional services (law, medical, real estate) have high-income owners
- TABLE_PURCHASE or INDIVIDUAL_DONOR
- Example reasoning: "Law firm with 20+ years in Honolulu. Partners are high-income professionals. Table purchase ask $2K-$5K."

### Wealthy Individuals
- Look for executive titles, business ownership, luxury lifestyle signals
- Real estate, medical, legal professionals = high income
- INDIVIDUAL_DONOR outreach
- Example reasoning: "Real estate broker with luxury property portfolio. High personal income likely. Individual donor ask $500-$2,000."

### Media/Event Organizations
- Value is in their sponsor networks and attendee lists
- Sony Open = access to corporate sponsors and wealthy golf community
- DOOR_OPENER to their sponsor/donor networks
- Example reasoning: "Sony Open in Hawaii, major PGA event. Value is access to corporate sponsors (Sony, Lexus, etc.) and wealthy golf community. Door-opener to high-net-worth network."

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
  "reasoning_hawaii": "Major Hawaii utility, established 1891, serves Oahu, Maui, and Hawaii Island",

  "entity_type": "corporation",
  "entity_type_reasoning": "Major utility company with CSR programs and significant corporate infrastructure",

  "financial_capacity": 38,
  "financial_capacity_reasoning": "TIER_A - Major Hawaii utility established 1891, serves hundreds of thousands of customers, CSR budget certain",

  "donor_access": 20,
  "donor_access_reasoning": "HIGH - Employee giving programs, corporate partner network, board connections to other major Hawaii businesses",

  "dinner_potential": 18,
  "dinner_potential_reasoning": "TABLE_BUYER - Corporations of this scale routinely buy tables at charity dinners for $2K-$5K",

  "hawaii_connection": 14,
  "hawaii_connection_reasoning": "LOCAL_STRONG - 130+ year Hawaii institution, physical presence on multiple islands",

  "score": 90,
  "score_breakdown": "Financial: 38/40 + Donor Access: 20/25 + Dinner: 18/20 + Hawaii: 14/15 = 90/100",

  "outreach_type": "CORPORATE_SPONSORSHIP",
  "suggested_ask_amount": "$10,000-$25,000",
  "outreach_strategy": "Contact CSR department. Propose event sponsorship with corporate branding at annual dinner. Hawaiian Electric logo on materials, reserved corporate table, recognition in program."
}
```

### Excluded Entity Output Format

```json
{
  "handle": "assistancedogshawaii",
  "display_name": "Assistance Dogs of Hawaii",
  "follower_count": 1200,
  "bio": "Training assistance dogs...",

  "hawaii_based": true,
  "reasoning_hawaii": "Hawaii-based organization",

  "entity_type": "EXCLUDE_competitor",
  "entity_type_reasoning": "Competitor - trains and places assistance dogs in Hawaii",

  "financial_capacity": 0,
  "financial_capacity_reasoning": "EXCLUDED - competitor organization",
  "donor_access": 0,
  "donor_access_reasoning": "EXCLUDED - competitor organization",
  "dinner_potential": 0,
  "dinner_potential_reasoning": "EXCLUDED - competitor organization",
  "hawaii_connection": 0,
  "hawaii_connection_reasoning": "EXCLUDED - competitor organization",

  "score": 0,
  "score_breakdown": "EXCLUDED - competitor",
  "outreach_type": "SKIP",
  "suggested_ask_amount": "$0",
  "outreach_strategy": "SKIP - competitor organization, do not contact for fundraising"
}
```

---

## Critical Rules

1. **Check exclusion rules FIRST** - before any scoring
2. **Financial capacity is 40% of the score** - money is what matters
3. **Member organizations are gold** - one relationship = dozens of donors (Rotary, Chamber)
4. **ALL nonprofits are excluded** - no exceptions, they need money themselves
5. **Mission alignment is NOT a factor** - do not boost scores for service dog connection
6. **Be specific in reasoning** - cite what in the bio/website led to your conclusion
7. **Include score breakdown** - show the math: "Financial: X/40 + Access: Y/25 + Dinner: Z/20 + Hawaii: W/15 = Total"
8. **Include suggested ask amount** - every prospect needs a dollar range
9. **Top 25 only** - quality over quantity, only the best fundraising prospects make the cut
10. **Read the bio carefully** - it's your primary source of truth
