# Classification Audit System Guide

## Overview

The classification audit system provides a three-tier approach to review and correct the Instagram follower classifications:

1. **Automated Analysis** - Detect suspicious patterns automatically
2. **Semi-Automated Review Queue** - Prioritized list with context for human review
3. **Interactive Audit Tool** - Terminal UI for human reviewers to approve or correct classifications
4. **Application** - Apply corrections to database with audit trail
5. **Reporting** - Generate metrics and recommendations

## Quick Start

### Step 1: Run Automated Analysis

```bash
python3 scripts/audit_analyze.py --db data/followers.db --output-dir output
```

This generates `output/audit_analysis.json` with flagged accounts.

**What it detects:**
- Rule conflicts (account classified by lower-priority rule when higher-priority keywords present)
- Confidence mismatches (low confidence on high-value categories)
- Keyword cross-contamination (keywords from multiple categories)
- Priority score anomalies
- Business flag inconsistencies
- Engagement boundary cases

### Step 2: Generate Review Queue

```bash
python3 scripts/audit_queue.py --db data/followers.db --output-dir output --sample-size 20
```

This generates:
- `output/audit_queue.json` - Machine-readable queue with full context
- `output/audit_queue.csv` - Spreadsheet-friendly format

**Queue prioritization:**
- **P1**: High-value categories with low confidence or rule conflicts
- **P2**: Known problematic categories (corporate, charity, org, pet_industry)
- **P3**: Boundary cases (influencer/engagement thresholds)
- **P4**: Low-confidence classifications
- **P5**: Random sample for baseline accuracy

### Step 3: Interactive Review

```bash
python3 scripts/audit_interactive.py --queue output/audit_queue.json --output-dir output
```

**In the interactive tool:**

For each account, choose an action:
- `a` - Approve current classification
- `r` - Reclassify to a different category
- `s` - Skip (review later)
- `n` - Add note without changing category
- `q` - Quit (saves progress)

The tool generates `output/audit_corrections.jsonl` - an append-only log of all decisions.

**To resume from where you left off:**
```bash
python3 scripts/audit_interactive.py --queue output/audit_queue.json --resume output/audit_corrections.jsonl
```

### Step 4: Preview Changes (Dry Run)

```bash
python3 scripts/audit_apply.py --corrections output/audit_corrections.jsonl --db data/followers.db --dry-run
```

This shows what will be changed without modifying the database.

### Step 5: Apply Corrections to Database

```bash
python3 scripts/audit_apply.py --corrections output/audit_corrections.jsonl --db data/followers.db
```

This applies all corrections with an audit trail:
- Updates `category`, `subcategory`, `priority_score`
- Sets `audit_status='corrected'`, `audit_note`, `audited_at`
- Recalculates priority scores automatically

### Step 6: Generate Report

```bash
python3 scripts/audit_report.py --corrections output/audit_corrections.jsonl --queue output/audit_queue.json --output-dir output
```

This generates:
- `output/audit_report.json` - Machine-readable metrics
- `output/audit_report.md` - Human-readable report

**Report includes:**
- Overall accuracy percentage
- Category-level misclassification breakdown
- Confidence calibration analysis
- Rule improvement recommendations with test cases

## Workflow Example

### Scenario: Audit first 50 accounts

```bash
# 1. Analyze
python3 scripts/audit_analyze.py --db data/followers.db --output-dir output

# 2. Generate queue (sample 20 random accounts + 30 priority accounts)
python3 scripts/audit_queue.py --db data/followers.db --output-dir output --sample-size 20

# 3. Review queue in CSV before interactive review
open output/audit_queue.csv

# 4. Run interactive audit (about 30-45 min for 50 accounts)
python3 scripts/audit_interactive.py --queue output/audit_queue.json --output-dir output

# 5. Preview changes
python3 scripts/audit_apply.py --corrections output/audit_corrections.jsonl --db data/followers.db --dry-run

# 6. Apply corrections
python3 scripts/audit_apply.py --corrections output/audit_corrections.jsonl --db data/followers.db

# 7. Generate final report
python3 scripts/audit_report.py --corrections output/audit_corrections.jsonl --queue output/audit_queue.json --output-dir output
```

## Understanding the Interactive Review UI

### Profile Display

```
[1/50] @amypetersyoga
┌──────────────────────────────────────────────────────────────────┐
│ @amypetersyoga                                                   │
│ Display Name: Amy Peters                                         │
│ Yoga/Meditation classes✨                                        │
│ Privates✨Corporate✨ Special Events✨                           │
│                                                                  │
│ Metrics: 1,459 followers | 298 posts | Personal | Public       │
│                                                                  │
│ CURRENT CLASSIFICATION:                                         │
│   Category: corporate (0.8 conf) | Score: 40 (Tier 3)          │
│                                                                  │
│ REVIEW REASON: Corporate classification needs review for        │
│                keyword ambiguity                                 │
│                                                                  │
│ Priority Queue: P2_corporate_keyword_review                     │
└──────────────────────────────────────────────────────────────────┘

Action [a=approve, r=reclassify, s=skip, n=note, q=quit]:
```

### Category Selection

```
Select category:
   1. service_dog_aligned - Service dog org / therapy
   2. bank_financial - Bank or financial
   3. corporate - Large corporation
   4. pet_industry - Pet service/business
   5. organization - Non-profit org / club
   6. charity - Rescue / charity
   ...
```

### Subcategory Selection

```
Select subcategory for business_local:
  1. Restaurant/cafe
  2. Hotel/resort
  3. Real estate
  4. Legal
  5. Retail
  6. Service (yoga, haircut, cleaning, etc)
  7. General
```

## Understanding Corrections File Format

`output/audit_corrections.jsonl` contains one JSON object per line:

```json
{"handle": "amypetersyoga", "decision": "reclassified", "old_category": "corporate", "old_subcategory": "general", "new_category": "business_local", "new_subcategory": "service", "note": "Corporate refers to service offering", "timestamp": "2026-02-08T10:30:00Z", "auditor": "human"}
{"handle": "hawaiianelectric", "decision": "approved", "old_category": "corporate", "timestamp": "2026-02-08T10:31:00Z", "auditor": "human"}
```

**Decision types:**
- `approved` - Auditor approved the current classification
- `reclassified` - Auditor changed the category/subcategory
- `noted` - Auditor added a note without changing category

## Interpreting the Report

### Accuracy Metric

- `Accuracy: 85%` = 85% of reviewed accounts were classified correctly
- Used as baseline for future improvements

### Category Misclassification Summary

Shows where accounts were being misclassified:

```
### corporate
- Reclassified: 4 accounts
  - → business_local: 3 (75%)
  - → business_national: 1 (25%)
```

This suggests the "corporate" keyword is triggering false positives - should either be more restrictive or add exclusions.

### Recommendations

**High Impact:**
- `Rule Priority Issue`: Corporate triggering when business_local is correct
  - Recommendation: Add context-aware keyword analysis
  - Test: Create test case for "corporate yoga" vs actual corporations

**Medium Impact:**
- `Confidence Calibration`: Multiple low-confidence classifications need review
  - Recommendation: Tighten keyword matching or reduce confidence thresholds

## Database Changes After Apply

### New Columns (if using schema extension)

```sql
SELECT handle, category, subcategory, audit_status, audit_note, audited_at
FROM followers
WHERE audit_status = 'corrected'
LIMIT 5;
```

Example output:
```
handle                 | category        | subcategory | audit_status | audit_note                    | audited_at
-----------------------+-----------------+-------------+--------------+-------------------------------+-------------------
amypetersyoga          | business_local  | service     | corrected    | Corporate refers to service   | 2026-02-08T10:30:00Z
hawaiianelectric       | corporate       | general     | approved     | NULL                          | 2026-02-08T10:31:00Z
```

## Batch Audit Workflow

For large-scale audits (200+ accounts):

1. **Split into batches**: Process 50 accounts at a time
2. **Run analysis separately for each batch**: Identify priority issues per batch
3. **Conduct interactive review**: 1-2 hours per batch
4. **Apply corrections**: After each batch
5. **Generate incremental reports**: Track improvement across batches

### Example: Three-batch audit

```bash
# Batch 1: P1 and P2 priority accounts (highest impact)
python3 scripts/audit_queue.py --db data/followers.db --output-dir output --sample-size 0
# (generates mostly P1/P2 accounts)
python3 scripts/audit_interactive.py --queue output/audit_queue.json --output-dir output
python3 scripts/audit_apply.py --corrections output/audit_corrections.jsonl --db data/followers.db

# Batch 2: Boundary cases (P3 and P4)
# ... repeat with next batch

# Final report across all batches
python3 scripts/audit_report.py --corrections output/audit_corrections.jsonl --queue output/audit_queue.json --output-dir output
```

## Troubleshooting

### "Queue file not found"

Generate the queue first:
```bash
python3 scripts/audit_queue.py --db data/followers.db --output-dir output
```

### Confidence is None in CSV export

Fixed in latest version - ensure you're using the latest `audit_queue.py`.

### Database locked error

Another process is using the database. Check:
```bash
lsof | grep followers.db
```

### Want to start over?

Delete corrections file and start fresh:
```bash
rm output/audit_corrections.jsonl
python3 scripts/audit_interactive.py --queue output/audit_queue.json --output-dir output
```

## Performance Tips

- **Fastest audit**: 30-45 seconds per account average
- **Full 50-account audit**: ~30-45 minutes
- **Large batch (200+)**: Break into 4-5 sessions, 1-2 per session per day
- **Keyboard shortcuts**: Use single letter + Enter instead of full words
- **CSV review**: Screen accounts in CSV before interactive audit to batch similar reviews

## Next Steps After Audit

1. Review `audit_report.md` for high-impact recommendations
2. Apply recommendations to `src/classifier.py`
3. Run tests to validate changes: `python3 -m pytest tests/`
4. Re-run audit on new accounts after each improvement
5. Track accuracy improvement over time

## Files Created/Modified

### Created
- `scripts/audit_analyze.py` - Automated analysis
- `scripts/audit_queue.py` - Queue generation
- `scripts/audit_interactive.py` - Interactive review tool
- `scripts/audit_apply.py` - Apply corrections
- `scripts/audit_report.py` - Generate reports

### Modified
- `data/followers.db` - Updated during `audit_apply.py` (optional columns added)

### Generated
- `output/audit_analysis.json`
- `output/audit_queue.json`
- `output/audit_queue.csv`
- `output/audit_corrections.jsonl`
- `output/audit_apply_report.json`
- `output/audit_report.json`
- `output/audit_report.md`

## Support

For questions or issues:

1. Check this guide first
2. Review the `--help` output: `python3 scripts/audit_analyze.py --help`
3. Check the JSON output files for debugging information
4. See `output/audit_report.md` for detailed findings

## Key Concepts

### Confidence Levels

- `0.95`: Very high confidence (service_dog_aligned)
- `0.85-0.90`: High confidence (pet_industry, charity, org)
- `0.75-0.80`: Medium confidence (media_event, organization, elected_official)
- `0.70`: Lower confidence (business, influencer)
- `0.60`: Low confidence (personal_engaged)
- `0.50`: Very low confidence (personal_passive)
- `0.30`: Fallback (unknown)

### Priority Scoring (0-100)

- **Tier 1 (80-100)**: High priority for outreach
- **Tier 2 (60-79)**: Medium priority
- **Tier 3 (40-59)**: Low priority
- **Tier 4 (0-39)**: Skip

Scores combine base category score + bonuses for location, reach, engagement, etc.

### Rule Priority Order

1. service_dog_aligned (highest)
2. bank_financial
3. corporate
4. pet_industry
5. organization (government)
6. organization (other)
7. charity
8. elected_official
9. media_event
10. business_local
11. business_national
12. influencer
13. spam_bot
14. personal_engaged
15. personal_passive
16. unknown (fallback)

First rule to match wins. No fallthrough.
