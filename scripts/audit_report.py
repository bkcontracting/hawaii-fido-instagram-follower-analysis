#!/usr/bin/env python3
"""Generate comprehensive audit report with metrics and recommendations.

Analyzes corrections to provide:
- Overall classification accuracy metrics
- Category-level performance analysis
- Rule improvement recommendations
- Confidence calibration analysis
- Test cases for proposed improvements

Usage:
    python3 scripts/audit_report.py [--corrections output/audit_corrections.jsonl] [--queue output/audit_queue.json] [--output-dir output]
"""
import argparse
import json
import os
import sys
from typing import List, Dict, Any
from collections import defaultdict

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_corrections(corrections_path: str) -> List[Dict]:
    """Load corrections from JSONL file."""
    corrections = []
    if not os.path.exists(corrections_path):
        return []

    with open(corrections_path, "r") as f:
        for line in f:
            if line.strip():
                corrections.append(json.loads(line))

    return corrections


def _load_queue(queue_path: str) -> List[Dict]:
    """Load audit queue from JSON file."""
    if not os.path.exists(queue_path):
        return []

    with open(queue_path, "r") as f:
        data = json.load(f)
    return data.get("queue", [])


def analyze_corrections(corrections: List[Dict], queue: List[Dict]) -> Dict[str, Any]:
    """Analyze corrections to generate metrics and recommendations."""

    # Build lookup of queue entries by handle
    queue_by_handle = {entry["handle"]: entry for entry in queue}

    # Separate corrections by type
    approved = [c for c in corrections if c.get("decision") == "approved"]
    reclassified = [c for c in corrections if c.get("decision") == "reclassified"]
    noted = [c for c in corrections if c.get("decision") == "noted"]

    # Calculate accuracy
    total_reviewed = len(approved) + len(reclassified) + len(noted)
    accuracy = (len(approved) / total_reviewed * 100) if total_reviewed > 0 else 0

    # Analyze reclassifications for patterns
    category_changes = defaultdict(lambda: {"count": 0, "to": defaultdict(int)})
    keyword_patterns = defaultdict(int)
    confidence_issues = []
    rule_conflicts = []

    for correction in reclassified:
        handle = correction["handle"]
        old_cat = correction.get("old_category")
        old_subcat = correction.get("old_subcategory")
        new_cat = correction.get("new_category")
        new_subcat = correction.get("new_subcategory")
        note = correction.get("note", "")

        # Track category changes
        category_changes[old_cat]["count"] += 1
        category_changes[old_cat]["to"][new_cat] += 1

        # Extract keywords from notes for pattern detection
        if note:
            keyword_patterns[note.lower()] += 1

        # Get queue entry for context
        queue_entry = queue_by_handle.get(handle)
        if queue_entry:
            audit_ctx = queue_entry.get("audit_context", {})
            audit_ctx_reason = audit_ctx.get("review_reason", "")

            # Track confidence issues
            if "low confidence" in audit_ctx_reason.lower():
                confidence_issues.append({
                    "handle": handle,
                    "old_category": old_cat,
                    "new_category": new_cat,
                    "reason": audit_ctx_reason
                })

            # Track rule conflicts
            if "rule_conflict" in audit_ctx_reason.lower() or "rule conflict" in audit_ctx_reason.lower():
                rule_conflicts.append({
                    "handle": handle,
                    "old_category": old_cat,
                    "new_category": new_cat,
                    "reason": audit_ctx_reason
                })

    # Build recommendations
    recommendations = []

    # Top category misclassifications
    top_misclassified = sorted(
        category_changes.items(),
        key=lambda x: x[1]["count"],
        reverse=True
    )[:3]

    for old_cat, change_data in top_misclassified:
        if change_data["count"] > 0:
            most_common_new = max(change_data["to"].items(), key=lambda x: x[1])
            recommendations.append({
                "type": "rule_priority",
                "category": old_cat,
                "issue": f"Category {old_cat} triggered {change_data['count']} reclassifications",
                "most_common_target": most_common_new[0],
                "recommendation": f"Review rule priority - {old_cat} may be triggering when {most_common_new[0]} is more appropriate",
                "impact": "high" if change_data["count"] > 3 else "medium",
                "test_case": f"Create test case: profiles that match {old_cat} but should be {most_common_new[0]}"
            })

    # Confidence calibration issues
    if confidence_issues:
        recommendations.append({
            "type": "confidence_calibration",
            "issue": f"Found {len(confidence_issues)} corrections for low-confidence classifications",
            "recommendation": "Review confidence thresholds - consider lowering minimum confidence requirements or tightening keyword matching",
            "impact": "medium",
            "affected_count": len(confidence_issues)
        })

    # Rule conflict issues
    if rule_conflicts:
        recommendations.append({
            "type": "rule_conflict",
            "issue": f"Found {len(rule_conflicts)} corrections for rule conflicts",
            "recommendation": "Audit rule priority ordering - some categories may need reordering",
            "impact": "high" if len(rule_conflicts) > 2 else "medium",
            "affected_count": len(rule_conflicts)
        })

    # Keyword ambiguity patterns
    if keyword_patterns:
        top_keywords = sorted(keyword_patterns.items(), key=lambda x: x[1], reverse=True)[:3]
        for keyword, count in top_keywords:
            if count > 1 and len(keyword) > 10:
                recommendations.append({
                    "type": "keyword_ambiguity",
                    "issue": f"Keyword pattern '{keyword}' appears in {count} corrections",
                    "recommendation": f"Add context-aware exclusion or confirmation rule for this pattern",
                    "impact": "low",
                    "keyword": keyword,
                    "occurrences": count
                })

    return {
        "total_reviewed": total_reviewed,
        "accuracy": accuracy,
        "approved": len(approved),
        "reclassified": len(reclassified),
        "noted": len(noted),
        "category_misclassifications": dict(category_changes),
        "recommendations": recommendations,
        "confidence_issues": len(confidence_issues),
        "rule_conflicts": len(rule_conflicts),
    }


def generate_markdown_report(analysis: Dict) -> str:
    """Generate markdown format report."""
    lines = []

    lines.append("# Classification Audit Report\n")

    # Executive Summary
    lines.append("## Executive Summary\n")
    lines.append(f"- **Total Accounts Reviewed:** {analysis['total_reviewed']}")
    lines.append(f"- **Accuracy Rate:** {analysis['accuracy']:.1f}%")
    lines.append(f"- **Approved:** {analysis['approved']}")
    lines.append(f"- **Reclassified:** {analysis['reclassified']}")
    lines.append(f"- **Noted:** {analysis['noted']}\n")

    lines.append("### Key Findings")
    lines.append(f"- {analysis['reclassified']} misclassifications detected")
    lines.append(f"- {analysis['confidence_issues']} low-confidence classification issues")
    lines.append(f"- {analysis['rule_conflicts']} rule conflict issues\n")

    # Category Performance
    if analysis["category_misclassifications"]:
        lines.append("## Category Misclassification Summary\n")

        cat_changes = analysis["category_misclassifications"]
        for old_cat in sorted(cat_changes.keys()):
            change_data = cat_changes[old_cat]
            if change_data["count"] > 0:
                lines.append(f"### {old_cat}")
                lines.append(f"- Reclassified: {change_data['count']} accounts")

                # Show destination categories
                destinations = sorted(change_data["to"].items(), key=lambda x: -x[1])
                for new_cat, count in destinations:
                    if count > 0:
                        pct = count / change_data["count"] * 100
                        lines.append(f"  - → {new_cat}: {count} ({pct:.0f}%)")
                lines.append("")

    # Recommendations
    if analysis["recommendations"]:
        lines.append("## Recommendations\n")
        lines.append("Prioritized by impact:\n")

        high_impact = [r for r in analysis["recommendations"] if r.get("impact") == "high"]
        medium_impact = [r for r in analysis["recommendations"] if r.get("impact") == "medium"]
        low_impact = [r for r in analysis["recommendations"] if r.get("impact") == "low"]

        for impact_group, recommendations in [
            ("HIGH", high_impact),
            ("MEDIUM", medium_impact),
            ("LOW", low_impact)
        ]:
            if not recommendations:
                continue

            lines.append(f"### {impact_group} Impact\n")
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. **{rec.get('type', 'Unknown').title()}**")
                lines.append(f"   - Issue: {rec.get('issue', 'Unknown')}")
                lines.append(f"   - Recommendation: {rec.get('recommendation', 'Unknown')}")

                if rec.get("test_case"):
                    lines.append(f"   - Test: {rec.get('test_case')}")
                lines.append("")

    # Next Steps
    lines.append("## Next Steps\n")
    lines.append("1. Review high-impact recommendations")
    lines.append("2. Create test cases for rule improvements")
    lines.append("3. Apply changes to classifier.py")
    lines.append("4. Re-run audit_queue.py to verify improvements")
    lines.append("5. Re-run audit on newly enriched accounts\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate audit report with metrics and recommendations"
    )
    parser.add_argument(
        "--corrections",
        default="output/audit_corrections.jsonl",
        help="Path to corrections JSONL file (default: output/audit_corrections.jsonl)"
    )
    parser.add_argument(
        "--queue",
        default="output/audit_queue.json",
        help="Path to audit queue JSON file (default: output/audit_queue.json)"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory to save report (default: output)"
    )

    args = parser.parse_args()

    # Load data
    corrections = _load_corrections(args.corrections)
    queue = _load_queue(args.queue)

    if not corrections:
        print("No corrections found. Run the interactive audit tool first.")
        return

    print(f"Analyzing {len(corrections)} corrections...")

    # Generate analysis
    analysis = analyze_corrections(corrections, queue)

    # Create markdown report
    markdown_report = generate_markdown_report(analysis)

    # Save reports
    os.makedirs(args.output_dir, exist_ok=True)

    # Save JSON analysis
    json_path = os.path.join(args.output_dir, "audit_report.json")
    with open(json_path, "w") as f:
        json.dump(analysis, f, indent=2)

    # Save markdown report
    md_path = os.path.join(args.output_dir, "audit_report.md")
    with open(md_path, "w") as f:
        f.write(markdown_report)

    # Print summary
    print("\n" + "=" * 70)
    print("AUDIT REPORT - SUMMARY")
    print("=" * 70)
    print(f"\nAccuracy: {analysis['accuracy']:.1f}%")
    print(f"Approved: {analysis['approved']}")
    print(f"Reclassified: {analysis['reclassified']}")
    print(f"Recommendations: {len(analysis['recommendations'])}\n")

    print(markdown_report)

    print(f"\n✓ JSON report saved to {json_path}")
    print(f"✓ Markdown report saved to {md_path}")


if __name__ == "__main__":
    main()
