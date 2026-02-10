# AI-Driven Fundraising Analysis Implementation

## Overview

This implementation follows a pure AI-driven approach where:
- **Python**: Only handles data extraction and formatting (NO intelligence)
- **Claude AI**: Performs ALL analysis, classification, and evaluation
- **Subagents**: Analyze batches of 75 profiles in parallel
- **Review Agent**: Performs final ranking and selection

## Architecture

### Three-Layer System

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: Data Extraction (Python - NO intelligence) │
│  Extract raw Instagram data from database            │
│  Fetch website content for enrichment                │
│  Output: candidates_raw.json (444 profiles)          │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  Layer 2: AI Analysis (Claude - ALL intelligence)    │
│  6 subagents analyze batches of ~75 profiles         │
│  Each profile receives complete evaluation:          │
│    - Exclusion check (competitors, nonprofits, etc.) │
│    - Financial capacity scoring (0-40)               │
│    - Donor access multiplier (0-25)                  │
│    - Dinner ticket/table potential (0-20)            │
│    - Hawaii connection (0-15)                        │
│    - Total fundraising score (0-100)                 │
│    - Outreach type & suggested ask amount            │
│  1 agent performs final ranking                      │
│  Output: top_25_fundraising.json,                    │
│          top_15_marketing_partners.json              │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  Layer 3: Report Formatting (Python - NO intelligence)│
│  Convert JSON to CSV and Markdown formats            │
│  Output: 3 report files (CSV + comprehensive MD)     │
└─────────────────────────────────────────────────────┘


## Scoring System: 4 Factors (100 points)

| Factor | Max Points | Weight | Question |
|--------|-----------|--------|----------|
| Financial Capacity | 40 | 40% | Can they write a check? |
| Donor Access Multiplier | 25 | 25% | Can they get OTHERS to donate? |
| Dinner Ticket/Table Potential | 20 | 20% | Will they buy tickets/table? |
| Hawaii Connection | 15 | 15% | Are they local and reachable? |

### Hard Exclusion Rules (Score = 0, Auto-SKIP)
- **Competitors**: Other service/assistance/guide dog organizations
- **ALL Nonprofits**: 501(c)(3), charities, foundations - NO EXCEPTIONS
- **Pet Micro-Businesses**: Solo trainers, groomers, pet influencers
- **Personal Accounts**: No business or wealth signals

### Entity Types
**Scoreable**: corporation, established_business, member_organization, bank_financial, government_official, wealthy_individual, media_event_org, small_business

**Auto-Exclude**: EXCLUDE_competitor, EXCLUDE_nonprofit, EXCLUDE_pet_micro, EXCLUDE_personal

### Outreach Types
- `CORPORATE_SPONSORSHIP` ($5K-$25K)
- `TABLE_PURCHASE` ($2K-$5K)
- `MEMBER_PRESENTATION` (access to member network)
- `INDIVIDUAL_DONOR` ($200-$2K)
- `DOOR_OPENER` (introductions to decision-makers)
- `SKIP` (excluded entities)

## Implementation Plan

### Step 1: Extract Raw Data

**Script**: `scripts/extract_raw_candidates.py`

**Output**: `data/candidates_raw.json`
- 444 candidates extracted (complete list)
- 132 with website content fetched and cached
- Fields: id, handle, display_name, bio, profile_url, follower_count, following_count, post_count, is_business, is_verified, website, website_content

**Key Points**:
- NO classification logic in Python
- NO intelligence applied - raw data only
- Website content cached for AI analysis
- No category, subcategory, is_hawaii, priority_score fields

### Step 2: Parallel AI Analysis

**Model**: Sonnet 4.5 (`model: "sonnet"` in Task tool)
- Framework is well-structured with clear rubrics — Sonnet follows structured instructions well
- 75 profiles per batch is manageable context
- 6x Sonnet is significantly cheaper/faster than 6x Opus

**Batch Distribution**:
- Batch 1: 75 profiles
- Batch 2: 75 profiles
- Batch 3: 75 profiles
- Batch 4: 75 profiles
- Batch 5: 75 profiles
- Batch 6: 69 profiles

**Total**: 444 profiles analyzed in parallel

**Analysis Framework**: `data/AI_ANALYSIS_FRAMEWORK.md`
- 4-factor scoring system (Financial Capacity, Donor Access, Dinner Potential, Hawaii Connection)
- Hard exclusion rules applied FIRST (competitors, nonprofits, pet micro, personal)
- Fundraising-capacity focused - mission alignment is NOT a factor
- Calibration examples ensure score consistency
- Every prospect gets a suggested ask amount

**Execution**: Launch 6 Task subagents in a single message (6 parallel tool calls). Each subagent:
1. Reads its assigned batch file (`data/analysis_batches/batch_N.json`)
2. Reads the framework (`data/AI_ANALYSIS_FRAMEWORK.md`)
3. For each profile, applies hard exclusion rules FIRST (competitors, nonprofits, pet micro, personal → score=0, outreach=SKIP)
4. For scoreable entities, evaluates 4 factors: Financial Capacity (0-40), Donor Access (0-25), Dinner Potential (0-20), Hawaii Connection (0-15)
5. Assigns entity_type, outreach_type, suggested_ask_amount
6. Writes results as JSON array to `data/analysis_results/batch_N_results.json`

**Subagent Output Schema**:
Each subagent produces JSON array with complete analysis:
```json
{
  "handle": "...",
  "display_name": "...",
  "bio": "...",
  "hawaii_based": true/false,
  "reasoning_hawaii": "...",
  "entity_type": "...",
  "entity_type_reasoning": "...",
  "financial_capacity": 0-40,
  "financial_capacity_reasoning": "...",
  "donor_access": 0-25,
  "donor_access_reasoning": "...",
  "dinner_potential": 0-20,
  "dinner_potential_reasoning": "...",
  "hawaii_connection": 0-15,
  "hawaii_connection_reasoning": "...",
  "score": 0-100,
  "score_breakdown": "Financial: X/40 + Access: Y/25 + Dinner: Z/20 + Hawaii: W/15 = Total",
  "outreach_type": "CORPORATE_SPONSORSHIP|TABLE_PURCHASE|MEMBER_PRESENTATION|INDIVIDUAL_DONOR|DOOR_OPENER|SKIP",
  "suggested_ask_amount": "$X-$Y",
  "outreach_strategy": "..."
}
```

### Step 3: Aggregate Results

**Script**: `scripts/aggregate_and_rank.py` (MUST CREATE — does not exist yet)

**Purpose**: Pure data aggregation — NO intelligence, NO re-scoring, NO filtering.

**Implementation**:
1. Glob `data/analysis_results/batch_*_results.json` to find all result files
2. Load and parse each JSON file (handle both raw array and `{"candidates": [...]}` wrapper formats — match the pattern in `format_reports.py:load_json()`)
3. Merge all profiles into a single list
4. Validate: assert no duplicate handles, assert all excluded entities (entity_type starts with `EXCLUDE_`) have score=0
5. Sort by score descending
6. Print summary stats: total profiles, excluded count, scored count, score distribution
7. Save to `data/all_analyzed_profiles.json`

**Style**: Match existing scripts — use `pathlib.Path`, `json` stdlib, print progress with checkmarks, `sys.exit(1)` on errors

**Can run in parallel with Step 2** — write the script while subagents analyze.

### Step 4: Final Ranking

**Model**: Opus 4.6 (`model: "opus"` in Task tool)
- Holistic reasoning across all 444 profiles benefits from the strongest model
- Cross-comparing scores, ensuring diversity of entity types, strategic selection

**Process**:
1. Read `data/all_analyzed_profiles.json` (aggregated from Step 3)
2. Use Opus 4.6 thinking subagent to:
   - Verify all excluded entities have score = 0
   - Review all scored profiles and validate scores
   - Select top 25 for fundraising (diverse mix of entity types)
   - Select top 15 for marketing (high-follower accounts, 5K+ followers)
   - Provide strategic reasoning for each selection
3. Write results to JSON files

**Output Files**:
- `data/top_25_fundraising.json` - Top 25 fundraising prospects
- `data/top_15_marketing_partners.json` - Top 15 marketing partners

### Step 5: Format Reports

**Script**: `scripts/format_reports.py` (COMPLETE — ready to run)

**Outputs**:
1. `output/fundraising_recommendations.md` - Comprehensive report with top 25 + marketing partners
2. `output/fundraising_outreach.csv` - Spreadsheet for top 25
3. `output/marketing_partners.csv` - Spreadsheet for top 15

## Design Decisions

### Why This Approach?

1. **Pure AI Intelligence**: Claude's reasoning is more sophisticated than any Python heuristic
   - Reads context and nuance from bios
   - Understands entity types and relationships
   - Applies domain-specific evaluation criteria
   - Makes holistic judgments about fundraising capacity

2. **Parallel Processing**: 6 subagents for speed
   - 75 profiles per agent is manageable
   - Parallel execution reduces total time

3. **Website Content Enhancement**: Fetched and cached upfront
   - Provides additional context for AI analysis
   - Enriches profile understanding beyond bio
   - Demonstrates legitimacy and professionalism

4. **Mixture of Experts**: Different evaluation per entity type
   - Corporations → focus on CSR capacity and corporate giving
   - Member organizations → focus on multiplier effect (one relationship = many donors)
   - Banks → focus on CRA obligations and community investment
   - Government officials → focus on door-opening and budget authority
   - Established businesses → focus on revenue signals and owner wealth

### Key Design Change: No Mission Alignment Factor

The previous framework included "Strategic Alignment & Mission Fit" which rewarded overlap with service dogs. This caused competitors, other nonprofits, pet micro-businesses, and special needs orgs to fill the top 50 - entities with ZERO fundraising value. The new framework eliminates this factor entirely and focuses purely on fundraising capacity.

### Key Design Change: Hard Exclusion Rules

Instead of scoring nonprofits and competitors low, they are now auto-excluded with score = 0. This prevents any possibility of mission-aligned but financially worthless entities from appearing in results.

## Task Execution Plan

Use TaskCreate to create these 7 tasks in order. Tasks 3 and 4 can run in parallel; all others are sequential.

```
Task 1 → Task 2 → Task 3 (Sonnet) ──┐
                   Task 4 (write) ───┤→ Task 5 (Opus) → Task 6 → Task 7
```

| Task | Description | Model/Tool | Depends On |
|------|-------------|------------|------------|
| 1 | Run `extract_raw_candidates.py` → `data/candidates_raw.json` | Bash (python3) | — |
| 2 | Run `ai_analysis_orchestrator.py` → `data/analysis_batches/` | Bash (python3) | Task 1 |
| 3 | Launch 6 Sonnet subagents to analyze batches → `data/analysis_results/` | Task (Sonnet 4.5) | Task 2 |
| 4 | Create `scripts/aggregate_and_rank.py` | Write tool | — (parallel with 3) |
| 5 | Run aggregation, then launch Opus ranking agent → `data/top_25_fundraising.json`, `data/top_15_marketing_partners.json` | Bash + Task (Opus 4.6) | Tasks 3 + 4 |
| 6 | Run `format_reports.py` → `output/` reports | Bash (python3) | Task 5 |
| 7 | Verify results against expected outcomes | Read tool | Task 6 |

## Verification Checklist

- [ ] Raw data extracted (NO intelligence in Python)
- [ ] Website content fetched and cached
- [ ] 6 Sonnet 4.5 subagents launched with framework
- [ ] Analysis framework applied with exclusion rules
- [ ] Each profile gets 4-factor scoring + exclusion check
- [ ] All subagents complete
- [ ] `aggregate_and_rank.py` created and working
- [ ] Results aggregated into `data/all_analyzed_profiles.json`
- [ ] Opus 4.6 performs final ranking
- [ ] Top 25 fundraising selected (quality over quantity)
- [ ] Top 15 marketing partners selected (5K+ followers)
- [ ] Format reports script runs successfully
- [ ] Final reports generated in `output/`
- [ ] Expected good rankings present, expected exclusions absent

### Expected Good Rankings (MUST be in top 10-25):
- Hawaiian Electric (corporation, ~90)
- Rotary E-Club of Hawaii (member org, ~88)
- Rotary Club of East Honolulu (member org)
- North Shore Chamber of Commerce (member org, ~83)
- Sony Open in Hawaii (media/event, ~74)
- Government officials (Rep. Branco, Councilmember Tulba)
- Banks/financial institutions
- Established local businesses with real revenue

### Expected Exclusions (MUST NOT appear):
- Assistance Dogs of Hawaii (EXCLUDE_competitor)
- Guide Dogs of Hawaii (EXCLUDE_competitor)
- IADA (EXCLUDE_competitor)
- Oahu SPCA (EXCLUDE_nonprofit)
- K9 Kokua (EXCLUDE_nonprofit)
- Never Quit Dreaming (EXCLUDE_nonprofit)
- CAMO (EXCLUDE_nonprofit)
- AUW Society of Young Leaders (EXCLUDE_nonprofit)
- Friends of Hawaii Charities (EXCLUDE_nonprofit)
- Combined Federal Campaign (EXCLUDE_nonprofit)
- Hawaii Autism Foundation (EXCLUDE_nonprofit)
- Disability Advocates (EXCLUDE_nonprofit)
- Aloha Independent Living (EXCLUDE_nonprofit)
- Hawaii Disability Legal Services (EXCLUDE_nonprofit)
- Individual dog trainers/groomers (EXCLUDE_pet_micro)

## Files

### Python Scripts
- `scripts/extract_raw_candidates.py` - Data extraction (EXISTS, ready to run)
- `scripts/ai_analysis_orchestrator.py` - Batch preparation (EXISTS, ready to run)
- `scripts/aggregate_and_rank.py` - Results aggregation (MUST CREATE in Task 4)
- `scripts/format_reports.py` - Report formatting (EXISTS, ready to run)
- `scripts/finalize_analysis.sh` - Runs aggregate + format in sequence (EXISTS)

### Data Files
- `data/followers.db` - Source SQLite database (MUST EXIST before Task 1)
- `data/AI_ANALYSIS_FRAMEWORK.md` - Analysis guidelines for subagents (EXISTS)
- `data/candidates_raw.json` - Raw candidates, ~444 (created by Task 1)
- `data/analysis_batches/batch_1.json` through `batch_6.json` - Batch files (created by Task 2)
- `data/analysis_results/batch_1_results.json` through `batch_6_results.json` - Subagent outputs (created by Task 3)
- `data/all_analyzed_profiles.json` - Aggregated analyses (created by Tasks 4+5)
- `data/top_25_fundraising.json` - Final top 25 selection (created by Task 5)
- `data/top_15_marketing_partners.json` - Final marketing selection (created by Task 5)

### Output Reports
- `output/fundraising_recommendations.md` - Full report with top 25 + marketing (created by Task 6)
- `output/fundraising_outreach.csv` - Outreach list for top 25 (created by Task 6)
- `output/marketing_partners.csv` - Campaign list for top 15 (created by Task 6)
