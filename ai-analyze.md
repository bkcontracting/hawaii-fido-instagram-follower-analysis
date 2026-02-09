# AI-Driven Fundraising Analysis: Pure Intelligence Approach

## Context

Hawaii FIDO needs to identify fundraising prospects from their 331+ Instagram followers. Previous approach incorrectly used deterministic Python logic. This plan implements a **pure AI-driven analysis** where:

- **Python**: Only extracts raw data and formats output (NO intelligence)
- **Claude AI**: Performs ALL analysis, classification, and evaluation
- **Subagents**: Enable parallel processing for performance
- **Web Fetch**: Enriches analysis with website context
- **Mixture of Experts**: Different analysis strategies per profile type

**Target outputs**:
1. Top 50 candidates for direct fundraising/outreach
2. 10-15 high-follower accounts for shared marketing campaigns

## Implementation Steps

### Step 1: Extract Raw Data + Fetch Websites (Simple Python)

**Script**: `scripts/extract_raw_candidates.py`

**Purpose**:
1. Extract ONLY raw Instagram fields from database (no classification logic)
2. Fetch website content for profiles with websites

**SQL Query**:
```sql
SELECT id, handle, display_name, bio, profile_url,
       follower_count, following_count, post_count,
       is_business, is_verified, website
FROM followers
WHERE status = 'completed'
ORDER BY follower_count DESC
```

**CRITICAL - Do NOT extract**:
- ❌ category
- ❌ subcategory
- ❌ is_hawaii
- ❌ location
- ❌ priority_score
- ❌ priority_reason

**Website Fetching**:
- For each profile with a `website` field
- Use WebFetch tool or HTTP requests
- Store website content summary (first 1000 chars or key sections)
- Add to profile data as `website_content` field

**Output**: `data/candidates_raw.json` with ~331 profiles including website content

---

### Step 2: Claude AI Analysis (Pure Intelligence with Haiku)

This is where ALL the intelligence happens. No Python logic - only Claude reasoning.

#### Phase A: Batch Profile Analysis with Subagents (Haiku)

Launch multiple **subagents in parallel** to analyze candidate batches.
Each subagent should use **Haiku** model:

- Subagent 1: Candidates 1-50
- Subagent 2: Candidates 51-100
- Subagent 3: Candidates 101-150
- Subagent 4: Candidates 151-200
- Subagent 5: Candidates 201-250
- Subagent 6: Candidates 251-331

**Each subagent will** (using Haiku model):

For each profile, Claude AI will determine from bio/name/context + website content:

1. **Hawaii-based?** (read bio for Honolulu, Oahu, 808, Hawaiian words, etc.)
2. **Entity type?** (government official, corporate, local business, member org, pet industry, nonprofit, influencer)
3. **Business capacity?** (HIGH/MEDIUM/LOW - do they have resources and authority?)
4. **Strategic alignment?** (service dog connection, mission fit, community involvement)
5. **Relationship potential?** (reachable, local advantage, approachable)
6. **Impact potential?** (can they open doors, influence others, multiplier effect)
7. **Fundraising score** (0-100 based on above factors)
8. **Outreach type** (DIRECT_FUNDING, MARKETING_PARTNER, PARTNERSHIP, DOOR_OPENER)

**Example analysis** (done by Claude, not code):
```json
{
  "handle": "hawaiianelectric",
  "display_name": "Hawaiian Electric",
  "follower_count": 33400,
  "bio": "Established in 1891, we are committed to empowering our customers...",

  "hawaii_based": true,
  "reasoning_hawaii": "Bio mentions Hawaii, company is Hawaiian Electric",

  "entity_type": "corporation",
  "reasoning_type": "Major utility company, established 1891, corporate entity",

  "capacity": "HIGH",
  "reasoning_capacity": "Major corporation with significant resources, 130+ years established",

  "alignment": "MODERATE",
  "reasoning_alignment": "Community-focused utility, CSR likely, Hawaii-based advantage",

  "relationship": "MEDIUM",
  "reasoning_relationship": "Large corporation, professional channels, local presence",

  "impact": "HIGH",
  "reasoning_impact": "Major Hawaii institution, credibility, could open doors to corporate partners",

  "score": 78,
  "outreach_type": "DIRECT_FUNDING",
  "outreach_strategy": "Target CSR/community relations department, emphasize local mission and accessibility impact"
}
```

#### Phase B: Strategic Ranking & Selection

***important*** use Opus 4.6 thinking for subagent

Launch final Opus 4.6 thinking **subagent to analyze all profiles** and make selections:

**Task**: Review all analyzed profiles and select:

1. **Top 50 for Direct Fundraising** based on:
   - Fundraising capacity + accessibility
   - Strategic alignment or impact potential
   - Mixture across types (government, corporate, local business, member orgs)
   - Priority: Hawaii-based, high capacity, strategic value

2. **Top 10-15 for Marketing Campaigns** based on:
   - Very high follower count (5K-70K+)
   - Audience alignment with Hawaii FIDO mission
   - Engagement potential
   - Interest in social causes

**Output**:
- `top_50_fundraising.json`
- `top_15_marketing_partners.json`

---

### Step 3: Format Reports (Simple Python)

**Script**: `scripts/format_reports.py`

**Purpose**: Take Claude's analysis and format into usable reports (NO intelligence)

**Inputs**:
- `top_50_fundraising.json`
- `top_15_marketing_partners.json`

**Outputs**:
1. `output/fundraising_recommendations.md` - Complete report with:
   - All top 50 fundraising candidates (full details)
   - All 10-15 marketing partners (full details)
   - Same data as both CSV files, in markdown format
2. `output/fundraising_outreach.csv` - Spreadsheet with top 50
3. `output/marketing_partners.csv` - High-follower campaign opportunities

**Note**: The markdown report contains ALL the data from both CSV files in readable format

---

## AI Analysis Framework (For Claude)

When analyzing each profile, Claude will evaluate:

### Fundraising Evaluation Factors

**1. Business Capacity & Resources**
- Do they have money? (established business, corporate entity, successful operation)
- Do they have decision-making authority? (owner, executive, government official)
- Are they stable and legitimate? (years in operation, professional presence, website)
- What's their revenue potential? (reading between the lines of their bio and following)

**2. Strategic Alignment & Connection Potential**
- Do they align with Hawaii FIDO's mission? (service dogs, community service, accessibility)
- Could they be a partner beyond just funding? (event space, promotional channels, connections)
- Do they have reach that could amplify Hawaii FIDO's message?
- Would they care about this cause? (community-minded, local pride, pet-friendly)

**3. Accessibility & Relationship Potential**
- Are they local and reachable? (Hawaii-based is ideal)
- Do they engage with community causes? (reading their content themes)
- Is there a clear "in" or connection point? (mutual interests, service dog connection)
- What's their communication style? (professional, approachable, community-focused)

**4. Impact Potential**
- Can they open doors beyond themselves? (government, corporate partnerships, media)
- Do they have credibility and reputation? (verified, established, respected)
- Could this be a long-term relationship? (not just a one-time donation)
- What's the multiplier effect? (could lead to more connections)

**5. Member-Based Organization Potential (HIGH VALUE)**
- **Organizations with affluent membership bases**: Rotary Clubs, churches, professional associations, chambers of commerce, yacht clubs, country clubs
- **Why these are strategic**:
  - One presentation to the organization = access to dozens/hundreds of potential donors
  - Members often include business owners, professionals, and affluent individuals
  - Organizations may provide institutional support AND member donations
  - Built-in credibility (if the organization endorses you, members trust you)
  - Recurring opportunity (annual meetings, newsletters, events)
- **What to look for**:
  - Mentions of "members", "club", "association", "society", "congregation"
  - Organizations known for community service and charitable giving
  - Professional networks and business associations
  - Service organizations (Rotary, Lions, Kiwanis, etc.)
  - Religious organizations with active communities
  - Alumni associations, chambers of commerce

### AI Reasoning Process (Mixture of Experts)

Claude will apply different analysis strategies based on profile type:

**For Government Officials**:
- Focus on policy influence and door-opening potential
- Look for community service background
- Assess visibility and credibility benefits
- Example: "Councilmember" → opens policy doors, provides legitimacy

**For Member-Based Organizations** (HIGH VALUE):
- Identify membership indicators (Rotary, clubs, associations, chambers)
- ONE presentation = access to dozens/hundreds of affluent members
- Multiplier effect - institutional support + member donations
- Example: "Rotary Club" → access to business owners and professionals

**For Corporations**:
- Assess scale and stability
- Look for CSR programs or community giving
- Hawaii-based = stronger connection
- Example: "Established 1891" → massive institutional stability

**For Local Businesses**:
- Community integration and local pride
- Partnership potential (event space, pro-bono services)
- Direct relationship building opportunity
- Example: "Brewery + community events" → venue + visibility

**For Pet Industry**:
- Mission alignment (service dogs, pet care)
- Shared customer base
- Cross-promotion opportunities
- Example: "Dog trainer" → direct mission alignment

**For High-Follower Accounts** (Marketing):
- Audience demographics
- Engagement patterns
- Social cause affinity
- Example: "70K followers + pet content" → shared campaign potential

**Strategic Insights Claude Will Make**:
- Brewery with 15K followers > Bank with 2K (community presence matters)
- Government official with 5K > Influencer with 50K (doors > popularity)
- Member org with 1K > Business with 10K (multiplier effect)
- Service dog connection > Generic pet industry (perfect vs moderate alignment)

---

## Performance Optimization

**Step 1 (Data Extraction)**:
- Website fetching done upfront (all websites fetched before AI analysis)
- Websites stored with profile data for AI context

**Step 2 (AI Analysis with Haiku)**:
- 6 Haiku subagents analyze batches of ~50 profiles simultaneously
- 1 Opus 4.6 thinking subagent performs final ranking and selection

**Context Management**:
- Each subagent has focused scope (batch of profiles)
- Website content already fetched and available in profile data
- Results aggregated efficiently

**Total Time Estimate**: ~10-15 minutes for 331 profiles

## Critical Files

**Existing**:
- `data/followers.db` - SQLite database with 447 completed profiles
- `src/database.py` - Database module with `_connect()` function

**To Create**:
1. `scripts/extract_raw_candidates.py` - Simple data extraction (NO intelligence)
2. `scripts/format_reports.py` - Simple report formatting (NO intelligence)
3. `data/candidates_raw.json` - Raw Instagram data for Claude
4. `data/top_50_fundraising.json` - Claude's fundraising analysis
5. `data/top_15_marketing_partners.json` - Claude's marketing partner analysis
6. `output/fundraising_recommendations.md` - Detailed report
7. `output/fundraising_outreach.csv` - Outreach spreadsheet
8. `output/marketing_partners.csv` - Marketing campaign opportunities

## Verification

After implementation, verify:

**Step 1 (Extract + Fetch)**:
- ✅ Python script ONLY queries database and saves JSON
- ✅ Website content fetched and added to JSON
- ✅ NO classification logic in Python
- ✅ NO evaluation or scoring in Python
- ✅ Only 11 fields extracted (no category, is_hawaii, priority_score, etc.)

**Step 2 (AI Analysis with Haiku)**:
- ✅ 6 Haiku subagents launched in parallel for batches
- ✅ 1 Opus 4.6 thinking subagent for final ranking
- ✅ Website content available in profile data for analysis
- ✅ All classification done by Claude reading bios + websites
- ✅ All scoring done by Claude AI reasoning
- ✅ Mixture of experts approach applied per profile type

**Step 3 (Format)**:
- ✅ Python script ONLY formats Claude's results
- ✅ NO intelligence or classification in formatting
- ✅ Markdown report includes ALL data from both CSV files
- ✅ Outputs: MD report (complete), CSV outreach list, CSV marketing partners

**Quality Checks**:
- Top 50 includes diverse entity types (not just high follower counts)
- Member-based organizations identified (Rotary, professional associations)
- Government officials recognized for strategic value (not follower count)
- Service dog aligned businesses scored highest
- Marketing partners list includes 5K+ follower accounts
- Each recommendation has tailored outreach strategy

**Expected Top Results**:
- Hawaiian Electric (major corporate - CSR potential)
- Councilmember Augie Tulba (government - doors + credibility)
- Hana Koa Brewing (local business - venue + community reach)
- Rotary E-Club Hawaii (member org - multiplier effect)
