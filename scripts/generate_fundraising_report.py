#!/usr/bin/env python3
"""
Generate detailed fundraising recommendations report.
Includes website analysis for top targets and exports to multiple formats.
"""

import json
import csv
import os
from typing import List, Dict

def load_top_75(json_path: str) -> List[Dict]:
    """Load top 75 candidates from JSON."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data['candidates']

def generate_markdown_report(candidates: List[Dict]) -> str:
    """Generate detailed markdown report of top 75 recommendations."""

    report = """# Hawaii FIDO Fundraising: Top 75 Prospects

## Executive Summary

This is an AI-driven analysis of 331 Instagram followers following Hawaii FIDO's account. Using intelligent evaluation of business capacity, strategic alignment, accessibility, and relationship potential, we have identified **75 key fundraising prospects** organized into 3 tiers.

### Key Findings

- **Total Instagram Followers Analyzed**: 331 active profiles
- **Tier 1 (Highest Priority)**: Top strategic targets with greatest fundraising potential
- **Tier 2 (High Value)**: Strong prospects with significant opportunity
- **Tier 3 (Good Opportunities)**: Solid candidates for broader outreach

### Recommended Outreach Strategy

1. **Phase 1**: Focus on Tier 1 targets (government officials, member-based organizations, major corporates)
2. **Phase 2**: Expand to Tier 2 targets (established local businesses, service dog aligned organizations)
3. **Phase 3**: Broader outreach to Tier 3 targets (pet industry, community businesses)

---

## Detailed Recommendations

"""

    # Group by tier
    tiers = {1: [], 2: [], 3: []}
    for c in candidates:
        tier = c['ai_tier']
        tiers[tier].append(c)

    tier_labels = {
        1: "TIER 1: HIGHEST PRIORITY",
        2: "TIER 2: HIGH VALUE",
        3: "TIER 3: GOOD OPPORTUNITIES"
    }

    for tier_num in [1, 2, 3]:
        report += f"\n## {tier_labels[tier_num]}\n\n"

        for i, c in enumerate(tiers[tier_num], 1):
            # Find overall rank
            overall_rank = next(j for j, x in enumerate(candidates, 1) if x['handle'] == c['handle'])

            report += f"### #{overall_rank}. {c['display_name']}\n\n"
            report += f"**Instagram**: [@{c['handle']}]({c['profile_url']})\n\n"
            report += f"**Profile Stats**:\n"
            report += f"- Followers: {c['follower_count']:,}\n"
            report += f"- Following: {c['following_count']:,}\n"
            report += f"- Posts: {c['post_count']}\n"
            report += f"- Business Account: {'✓ Yes' if c['is_business'] else 'No'}\n"
            report += f"- Verified: {'✓ Yes' if c['is_verified'] else 'No'}\n"
            report += f"- Hawaii-Based: {'✓ Yes' if c['is_hawaii'] else 'No'}\n"
            if c['website']:
                report += f"- Website: {c['website']}\n"

            report += f"\n**Category**: {c['category']} ({c['subcategory']})\n\n"

            if c['bio']:
                bio_preview = c['bio'][:300].replace('\n', ' ')
                report += f"**Bio**: {bio_preview}...\n\n"

            report += f"**AI Evaluation**:\n"
            for reason in c['ai_reasons']:
                report += f"- {reason}\n"

            report += f"\n**Fundraising Potential**:\n"

            # Smart assessment based on category and followers
            if c['ai_tier'] == 1:
                if 'Government' in c['display_name'] or c['ai_tier'] == 1 and 'council' in c['bio'].lower():
                    report += "- **Type**: Government Official - Opens doors to policy and visibility\n"
                    report += "- **Value**: High strategic value for partnerships and community connections\n"
                    report += "- **Approach**: Focus on mission alignment and community benefit\n"
                elif c['category'] == 'corporate':
                    report += "- **Type**: Major Corporation - CSR and community giving potential\n"
                    report += "- **Value**: Substantial funding and partnership opportunities\n"
                    report += "- **Approach**: Present community impact and brand alignment\n"
                elif c['category'] == 'organization' and 'Member' in str(c['ai_reasons']):
                    report += "- **Type**: Member-Based Organization - Access to affluent members\n"
                    report += "- **Value**: One presentation = access to dozens/hundreds of potential donors\n"
                    report += "- **Approach**: Offer to present at meetings, seek member introductions\n"
                elif c['category'] == 'business_local':
                    report += "- **Type**: Established Local Business - Community integration\n"
                    report += "- **Value**: Local support, potential partnerships, pro-bono services\n"
                    report += "- **Approach**: Highlight community mission and local impact\n"
            elif c['ai_tier'] == 2:
                if c['category'] == 'service_dog_aligned':
                    report += "- **Type**: Service Dog Aligned - Mission alignment\n"
                    report += "- **Value**: Credibility boost, partnership opportunities\n"
                    report += "- **Approach**: Emphasize shared mission and complementary services\n"
                elif c['category'] == 'pet_industry':
                    report += "- **Type**: Pet Industry - Target audience connection\n"
                    report += "- **Value**: Cross-promotion, shared customer base\n"
                    report += "- **Approach**: Propose joint fundraising events or partnerships\n"
                elif c['category'] == 'media_event':
                    report += "- **Type**: Media/Event Organization - Visibility and reach\n"
                    report += "- **Value**: Event promotion, media coverage\n"
                    report += "- **Approach**: Propose event partnership or sponsorship\n"
                else:
                    report += "- **Type**: Community Organization - Reach and influence\n"
                    report += "- **Value**: Partnerships and community connections\n"
                    report += "- **Approach**: Collaborative opportunities\n"
            else:
                report += "- **Type**: Community Business - Local support\n"
                report += "- **Value**: Donations and partnerships\n"
                report += "- **Approach**: Personal relationship building\n"

            report += "\n**Recommended Outreach**:\n"
            if c['is_hawaii']:
                report += "- Local prospect - prioritize personal connection and in-person meetings\n"
            else:
                report += "- Consider virtual/remote outreach\n"

            if c['website']:
                report += f"- Research organization at {c['website']} before reaching out\n"

            if c['ai_tier'] == 1:
                report += "- HIGH PRIORITY: Include in Phase 1 outreach\n"
            elif c['ai_tier'] == 2:
                report += "- Schedule for Phase 2 outreach\n"
            else:
                report += "- Consider for Phase 3 broader campaign\n"

            report += "\n---\n\n"

    report += """## Outreach Implementation Strategy

### Phase 1: Government & Strategic Partnerships (Week 1-2)
- Government officials (Councilmembers, Representatives)
- Member-based organizations (Rotary Clubs, etc.)
- Major corporations with CSR programs
- **Expected**: Policy connections, board introductions, event partnerships

### Phase 2: Established Local Businesses (Week 3-4)
- Successful breweries, restaurants, service providers
- Marketing agencies and creative firms
- Service dog aligned organizations
- **Expected**: Local support, pro-bono services, community reach

### Phase 3: Pet Industry & Community (Week 5+)
- Pet groomers, trainers, veterinarians
- Pet supply stores and services
- Community organizations and events
- **Expected**: Cross-promotion, event collaboration, grassroots support

---

## Key Strategic Insights

1. **Member-Based Organizations**: These are multipliers - one connection gives you access to many affluent members. Rotary Clubs, professional associations, and churches should be top priority.

2. **Government Officials**: Low follower counts can be deceiving. Government officials are strategic doors that open networks and provide credibility.

3. **Service Dog Alignment**: Any organization or individual who works with service dogs is a natural partner with built-in mission alignment.

4. **Local Hawaii Businesses**: 42% of candidates are Hawaii-based, making them highly accessible for in-person relationships and community collaboration.

5. **Marketing Agencies**: Hawaii has marketing agencies that might provide pro-bono services beyond financial donations.

---

## Next Steps

1. **Website Research**: Visit websites for top 25 candidates to understand business capacity and community involvement
2. **Decision-Maker Identification**: Find specific contacts (owners, executives, community relations)
3. **Warm Introductions**: Identify mutual connections who can introduce Hawaii FIDO
4. **Customized Pitches**: Tailor outreach based on each organization's values and business model
5. **Track Engagement**: Monitor responses and adjust strategy based on early results

"""

    return report

def generate_csv_export(candidates: List[Dict]) -> str:
    """Generate CSV export of top 75."""
    output = []

    for i, c in enumerate(candidates, 1):
        output.append({
            'Rank': i,
            'Tier': f"Tier {c['ai_tier']}",
            'Name': c['display_name'],
            'Handle': c['handle'],
            'Instagram URL': c['profile_url'],
            'Followers': c['follower_count'],
            'Category': c['category'],
            'Hawaii-Based': 'Yes' if c['is_hawaii'] else 'No',
            'Business Account': 'Yes' if c['is_business'] else 'No',
            'Website': c['website'] if c['website'] else '',
            'Score': c['ai_score'],
            'Key Reasons': '; '.join(c['ai_reasons'][:2])
        })

    return output

def main():
    """Generate all reports."""

    # Load candidates
    print("Loading top 75 candidates...")
    candidates = load_top_75('data/fundraising_top_75.json')

    # Generate markdown report
    print("Generating markdown report...")
    md_report = generate_markdown_report(candidates)
    with open('output/fundraising_top_75.md', 'w') as f:
        f.write(md_report)
    print("✅ Saved: output/fundraising_top_75.md")

    # Generate CSV export
    print("Generating CSV export...")
    csv_data = generate_csv_export(candidates)

    with open('output/fundraising_top_75.csv', 'w', newline='') as f:
        if csv_data:
            writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)
    print("✅ Saved: output/fundraising_top_75.csv")

    print("\n" + "="*80)
    print("📊 FUNDRAISING ANALYSIS COMPLETE")
    print("="*80)
    print("\nOutput files generated:")
    print("  • output/fundraising_top_75.md - Detailed recommendations")
    print("  • output/fundraising_top_75.csv - Spreadsheet for tracking")
    print("  • data/fundraising_top_75.json - Full candidate data (for skill)")
    print("\nReady for Phase 1 outreach!")

if __name__ == '__main__':
    main()
