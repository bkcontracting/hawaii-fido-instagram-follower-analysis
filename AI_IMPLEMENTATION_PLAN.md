# AI-Driven Fundraising Analysis Implementation

## Overview

This implementation follows a pure AI-driven approach where:
- **Python**: Only handles data extraction and formatting (NO intelligence)
- **Claude AI**: Performs ALL analysis, classification, and evaluation
- **Subagents**: Analyze batches of 50 profiles in parallel
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
│  9 subagents analyze batches of ~50 profiles   │
│  Each profile receives complete evaluation:          │
│    - Hawaii-based assessment                        │
│    - Entity type classification                      │
│    - Business capacity evaluation                    │
│    - Strategic alignment scoring                     │
│    - Relationship potential assessment               │
│    - Impact potential rating                         │
│    - Fundraising score (0-100)                       │
│    - Outreach strategy recommendation                │
│  1 agent performs final ranking             │
│  Output: top_50_fundraising.json, top_15_marketing.json │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  Layer 3: Report Formatting (Python - NO intelligence)│
│  Convert JSON to CSV and Markdown formats            │
│  Output: 3 report files (CSV + comprehensive MD)     │
└─────────────────────────────────────────────────────┘


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

**Architecture**: Opus 4.6 thinking agents

**Batch Distribution**:
- Batch 1: 50 profiles
- Batch 2: 50 profiles
- Batch 3: 50 profiles
- Batch 4: 50 profiles
- Batch 5: 50 profiles
- Batch 6: 50 profiles
- Batch 7: 50 profiles
- Batch 8: 50 profiles
- Batch 9: 44 profiles

**Total**: 444 profiles analyzed in parallel

**Analysis Framework**: `data/AI_ANALYSIS_FRAMEWORK.md`
- Comprehensive evaluation criteria
- Mixture of experts approaches per entity type
- Specific scoring methodology
- Reasoning templates

** Subagent Outputs**:
Each subagent produces JSON array with complete analysis:
```json
{
  "handle": "...",
  "display_name": "...",
  "bio": "...",
  "hawaii_based": true/false,
  "reasoning_hawaii": "...",
  "entity_type": "...",
  "reasoning_type": "...",
  "capacity": "HIGH/MEDIUM/LOW",
  "reasoning_capacity": "...",
  "alignment": "HIGH/MEDIUM/LOW/NONE",
  "reasoning_alignment": "...",
  "relationship": "HIGH/MEDIUM/LOW",
  "reasoning_relationship": "...",
  "impact": "HIGH/MEDIUM/LOW",
  "reasoning_impact": "...",
  "score": 0-100,
  "outreach_type": "DIRECT_FUNDING|PARTNERSHIP|DOOR_OPENER|MARKETING_PARTNER|SKIP",
  "outreach_strategy": "..."
}
```

### Step 3: Final Ranking

**Process**:
1. Aggregate all 444 analyzed profiles
2. Use Opus 4.6 thinking subagent to:
   - Review all profiles and their scores
   - Select top 50 for fundraising (diverse mix of entity types)
   - Select top 15 for marketing (high-follower accounts)
   - Provide strategic reasoning for each selection

**Output Files** (to be created):
- `data/top_50_fundraising.json` - Top 50 fundraising prospects
- `data/top_15_marketing_partners.json` - Top 15 marketing partners

### Step 4: Format Reports ✓ READY

**Script**: `scripts/format_reports.py` (ready to execute)

**Outputs**:
1. `output/fundraising_recommendations.md` - Comprehensive report with all candidates
2. `output/fundraising_outreach.csv` - Spreadsheet for top 50
3. `output/marketing_partners.csv` - Spreadsheet for top 15

## Design Decisions

### Why This Approach?

1. **Pure AI Intelligence**: Claude's reasoning is more sophisticated than any Python heuristic
   - Reads context and nuance from bios
   - Understands entity types and relationships
   - Applies domain-specific evaluation criteria
   - Makes holistic judgments about capacity, alignment, and impact

2. **Parallel Processing**: 9 subagents for speed
   - 50 profiles per agent is manageable
   - Parallel execution reduces total time
   - model is fast and cost-effective
   - Opus 4.6 used only for final ranking (strategic thinking required)

3. **Website Content Enhancement**: Fetched and cached upfront
   - Provides additional context for AI analysis
   - Enriches profile understanding beyond bio
   - Demonstrates legitimacy and professionalism
   - Enables more accurate capacity and alignment assessment

4. **Mixture of Experts**: Different evaluation per entity type
   - Government officials → focus on doors and credibility
   - Corporations → focus on CSR capacity and Hawaii connection
   - Member organizations → focus on multiplier effect
   - Pet industry → focus on mission alignment
   - Influencers → focus on audience demographics

### Key Differences from Deterministic Approach

| Aspect | Deterministic | AI-Driven |
|--------|---------------|-----------|
| Classification | Keyword matching | Bio reading + context understanding |
| Scoring | Formula-based | AI reasoning + holistic evaluation |
| Entity type | Keyword lookup | Contextual understanding |
| Capacity assessment | Follower count | Resources, authority, stability |
| Alignment assessment | Service dog mention | Full mission understanding |
| Impact potential | Follower count | Network, credibility, doors opened |
| Special cases | Missed nuance | Understood and handled |
| Member orgs | No recognition | HIGH value multiplier effect |

## Verification Checklist

- [x] Raw data extracted (NO intelligence in Python)
- [x] Website content fetched and cached
- [x] 9 subagents launched in parallel
- [x] Analysis framework provided to agents
- [x] Each profile gets complete structured analysis
- [ ] All subagents complete (in progress)
- [ ] Results aggregated into single JSON
- [ ] Opus 4.6 performs final ranking
- [ ] Top 50 fundraising selected with diversity
- [ ] Top 15 marketing partners selected (5K+ followers)
- [ ] Format reports script ready
- [ ] Final reports generated

## Expected Output Quality

**Top 50 Fundraising Candidates**:
- Diverse mix of entity types (not just high follower counts)
- Hawaii-based candidates prioritized
- Member organizations identified (multiplier effect)
- Government officials recognized for strategic doors
- Service dog-aligned businesses highest rated
- Capacity + alignment + impact combination scores

**Top 15 Marketing Partners**:
- 5K+ follower accounts
- Pet-related content preference
- Hawaii-based preferred
- Engagement-focused (not just followers)
- Audience demographic alignment
- Campaign potential assessed

## Timeline

1. **Data Extraction** (Step 1): ~2 minutes
   - 444 candidates
   - 132 websites fetched
   - Raw data cached

2. **Parallel Analysis** (Step 2): ~10-15 minutes
   - 9 subagents in parallel
   - Each analyzes 44-50 profiles

3. **Final Ranking** (Step 3): ~3-5 minutes
   - Opus 4.6 thinking
   - Strategic selection
   - Top 50 + Top 15

4. **Report Formatting** (Step 4): ~1 minute
   - Python script formats results
   - CSV + Markdown outputs

**Total Expected Time**: ~20-25 minutes

## Files Created

### Python Scripts
- `scripts/extract_raw_candidates.py` - Data extraction
- `scripts/ai_analysis_orchestrator.py` - Batch preparation
- `scripts/aggregate_and_rank.py` - Results aggregation
- `scripts/format_reports.py` - Report formatting

### Data Files
- `data/candidates_raw.json` - Raw candidates (444)
- `data/analysis_batches/batch_1.json` through `batch_9.json` - Batch files
- `data/AI_ANALYSIS_FRAMEWORK.md` - Analysis guidelines
- `data/all_analyzed_profiles.json` - (to be created) Aggregated analyses
- `data/top_50_fundraising.json` - (to be created) Final selection
- `data/top_15_marketing_partners.json` - (to be created) Final selection

### Output Reports
- `output/fundraising_recommendations.md` - Full report
- `output/fundraising_outreach.csv` - Outreach list
- `output/marketing_partners.csv` - Campaign list

## Next Steps

1. Wait for all 9 subagents to complete
2. Run `scripts/aggregate_and_rank.py` to combine results
3. Launch final Opus 4.6 thinking subagent for ranking
4. Run `scripts/format_reports.py` to generate outputs
5. Review results and refine if needed

## Key Learnings

- **Pure AI is better than heuristics** for nuanced evaluation
- **Parallel processing** dramatically reduces analysis time
- **Website content** significantly improves analysis accuracy
- **Member organizations** are a high-value opportunity class often missed
- **Mixture of experts** approach respects entity-specific differences

