# Classification Audit Report

## Executive Summary

- **Total Accounts Reviewed:** 3
- **Accuracy Rate:** 33.3%
- **Approved:** 1
- **Reclassified:** 2
- **Noted:** 0

### Key Findings
- 2 misclassifications detected
- 1 low-confidence classification issues
- 0 rule conflict issues

## Category Misclassification Summary

### corporate
- Reclassified: 1 accounts
  - → business_local: 1 (100%)

### organization
- Reclassified: 1 accounts
  - → business_local: 1 (100%)

## Recommendations

Prioritized by impact:

### MEDIUM Impact

1. **Rule_Priority**
   - Issue: Category corporate triggered 1 reclassifications
   - Recommendation: Review rule priority - corporate may be triggering when business_local is more appropriate
   - Test: Create test case: profiles that match corporate but should be business_local

2. **Rule_Priority**
   - Issue: Category organization triggered 1 reclassifications
   - Recommendation: Review rule priority - organization may be triggering when business_local is more appropriate
   - Test: Create test case: profiles that match organization but should be business_local

3. **Confidence_Calibration**
   - Issue: Found 1 corrections for low-confidence classifications
   - Recommendation: Review confidence thresholds - consider lowering minimum confidence requirements or tightening keyword matching

## Next Steps

1. Review high-impact recommendations
2. Create test cases for rule improvements
3. Apply changes to classifier.py
4. Re-run audit_queue.py to verify improvements
5. Re-run audit on newly enriched accounts
