#!/usr/bin/env python3
"""Format Claude's AI analysis results into usable reports.

This script ONLY formats Claude's results - NO intelligence or evaluation.
Takes JSON outputs from Claude analysis and produces markdown and CSV reports.
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any


def load_json(filepath: str) -> List[Dict[str, Any]]:
    """Load JSON data from file. Handles both wrapped and unwrapped formats."""
    if not Path(filepath).exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    with open(filepath, "r") as f:
        data = json.load(f)

    # Handle wrapped format {"top_50_fundraising": [...]} or {"top_15_marketing_partners": [...]}
    if isinstance(data, dict):
        if "top_50_fundraising" in data:
            return data["top_50_fundraising"]
        elif "top_15_marketing_partners" in data:
            return data["top_15_marketing_partners"]
        elif "candidates" in data:
            return data["candidates"]
        elif "partners" in data:
            return data["partners"]

    # Otherwise assume it's already the array
    return data if isinstance(data, list) else [data]


def format_fundraising_recommendations(
    top_50: List[Dict[str, Any]],
    top_15: List[Dict[str, Any]],
    output_path: str
) -> None:
    """Format all analysis into comprehensive markdown report.

    Includes all data from both top 50 fundraising and top 15 marketing partners.
    """
    with open(output_path, "w") as f:
        f.write("# Hawaii FIDO Fundraising & Marketing Analysis\n\n")
        f.write("> AI-driven analysis of 331+ Instagram followers for fundraising prospects\n\n")

        # Top 50 Fundraising Candidates
        f.write("## Top 50 Fundraising Candidates\n\n")
        f.write("High-value prospects for direct fundraising outreach, partnership opportunities, and strategic relationships.\n\n")

        for i, candidate in enumerate(top_50, 1):
            f.write(f"### {i}. {candidate.get('display_name', candidate.get('handle'))}\n\n")
            f.write(f"**Handle**: @{candidate['handle']}\n\n")

            # Profile basics
            f.write("#### Profile\n")
            followers = candidate.get('follower_count') or candidate.get('followers', 'N/A')
            following = candidate.get('following_count') or candidate.get('following', 'N/A')
            posts = candidate.get('post_count') or candidate.get('posts', 'N/A')

            # Format numbers with commas if they're numeric
            if isinstance(followers, int):
                f.write(f"- **Followers**: {followers:,}\n")
            else:
                f.write(f"- **Followers**: {followers}\n")

            if isinstance(following, int):
                f.write(f"- **Following**: {following:,}\n")
            else:
                f.write(f"- **Following**: {following}\n")

            if isinstance(posts, int):
                f.write(f"- **Posts**: {posts:,}\n")
            else:
                f.write(f"- **Posts**: {posts}\n")

            f.write(f"- **Verified**: {'Yes' if candidate.get('is_verified') else 'No'}\n")
            f.write(f"- **Business Account**: {'Yes' if candidate.get('is_business') else 'No'}\n")
            if candidate.get("website"):
                f.write(f"- **Website**: {candidate['website']}\n")
            f.write(f"- **Bio**: {candidate.get('bio', 'N/A')}\n\n")

            # AI Analysis
            f.write("#### AI Analysis\n")
            f.write(f"- **Hawaii-Based**: {'Yes' if candidate.get('hawaii_based') else 'No'}\n")
            f.write(f"- **Entity Type**: {candidate.get('entity_type', 'N/A')}\n")
            f.write(f"- **Business Capacity**: {candidate.get('capacity', 'UNKNOWN')}\n")
            f.write(f"- **Strategic Alignment**: {candidate.get('alignment', 'UNKNOWN')}\n")
            f.write(f"- **Relationship Potential**: {candidate.get('relationship', 'UNKNOWN')}\n")
            f.write(f"- **Impact Potential**: {candidate.get('impact', 'UNKNOWN')}\n")
            f.write(f"- **Fundraising Score**: {candidate.get('score', 0)}/100\n")
            f.write(f"- **Recommended Outreach**: {candidate.get('outreach_type', 'UNKNOWN')}\n\n")

            # Reasoning
            if candidate.get("reasoning_hawaii"):
                f.write(f"**Hawaii Connection**: {candidate['reasoning_hawaii']}\n\n")
            if candidate.get("reasoning_capacity"):
                f.write(f"**Capacity**: {candidate['reasoning_capacity']}\n\n")
            if candidate.get("reasoning_alignment"):
                f.write(f"**Alignment**: {candidate['reasoning_alignment']}\n\n")
            if candidate.get("reasoning_impact"):
                f.write(f"**Impact**: {candidate['reasoning_impact']}\n\n")
            if candidate.get("outreach_strategy"):
                f.write(f"**Outreach Strategy**: {candidate['outreach_strategy']}\n\n")

            f.write("---\n\n")

        # Top 15 Marketing Partners
        f.write("## Top 15 Marketing Campaign Partners\n\n")
        f.write("High-follower accounts for shared marketing campaigns and audience reach.\n\n")

        for i, partner in enumerate(top_15, 1):
            f.write(f"### {i}. {partner.get('display_name', partner.get('handle'))}\n\n")
            f.write(f"**Handle**: @{partner['handle']}\n\n")

            # Profile basics
            f.write("#### Profile\n")
            followers = partner.get('follower_count') or partner.get('followers', 'N/A')
            following = partner.get('following_count') or partner.get('following', 'N/A')
            posts = partner.get('post_count') or partner.get('posts', 'N/A')

            # Format numbers with commas if they're numeric
            if isinstance(followers, int):
                f.write(f"- **Followers**: {followers:,}\n")
            else:
                f.write(f"- **Followers**: {followers}\n")

            if isinstance(following, int):
                f.write(f"- **Following**: {following:,}\n")
            else:
                f.write(f"- **Following**: {following}\n")

            if isinstance(posts, int):
                f.write(f"- **Posts**: {posts:,}\n")
            else:
                f.write(f"- **Posts**: {posts}\n")

            f.write(f"- **Verified**: {'Yes' if partner.get('is_verified') else 'No'}\n")
            f.write(f"- **Business Account**: {'Yes' if partner.get('is_business') else 'No'}\n")
            if partner.get("website"):
                f.write(f"- **Website**: {partner['website']}\n")
            f.write(f"- **Bio**: {partner.get('bio', 'N/A')}\n\n")

            # AI Analysis
            f.write("#### AI Analysis\n")
            f.write(f"- **Hawaii-Based**: {'Yes' if partner.get('hawaii_based') else 'No'}\n")
            f.write(f"- **Entity Type**: {partner.get('entity_type', 'N/A')}\n")
            f.write(f"- **Audience Alignment**: {partner.get('audience_alignment', 'N/A')}\n")
            f.write(f"- **Campaign Fit**: {partner.get('campaign_fit', 'N/A')}\n")
            f.write(f"- **Marketing Score**: {partner.get('score', 0)}/100\n\n")

            # Reasoning
            if partner.get("reasoning"):
                f.write(f"**Why This Partner**: {partner['reasoning']}\n\n")
            if partner.get("campaign_ideas"):
                f.write(f"**Campaign Ideas**: {partner['campaign_ideas']}\n\n")

            f.write("---\n\n")


def format_fundraising_outreach_csv(
    top_50: List[Dict[str, Any]],
    output_path: str
) -> None:
    """Format top 50 fundraising candidates as CSV for outreach."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "Rank",
            "Handle",
            "Display Name",
            "Followers",
            "Entity Type",
            "Hawaii-Based",
            "Capacity",
            "Score",
            "Outreach Type",
            "Website",
            "Bio",
        ])
        writer.writeheader()

        for i, candidate in enumerate(top_50, 1):
            writer.writerow({
                "Rank": i,
                "Handle": candidate.get("handle", ""),
                "Display Name": candidate.get("display_name", ""),
                "Followers": candidate.get("follower_count", ""),
                "Entity Type": candidate.get("entity_type", ""),
                "Hawaii-Based": "Yes" if candidate.get("hawaii_based") else "No",
                "Capacity": candidate.get("capacity", ""),
                "Score": candidate.get("score", ""),
                "Outreach Type": candidate.get("outreach_type", ""),
                "Website": candidate.get("website", ""),
                "Bio": candidate.get("bio", ""),
            })


def format_marketing_partners_csv(
    top_15: List[Dict[str, Any]],
    output_path: str
) -> None:
    """Format top 15 marketing partners as CSV."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "Rank",
            "Handle",
            "Display Name",
            "Followers",
            "Entity Type",
            "Hawaii-Based",
            "Score",
            "Website",
            "Bio",
        ])
        writer.writeheader()

        for i, partner in enumerate(top_15, 1):
            writer.writerow({
                "Rank": i,
                "Handle": partner.get("handle", ""),
                "Display Name": partner.get("display_name", ""),
                "Followers": partner.get("follower_count", ""),
                "Entity Type": partner.get("entity_type", ""),
                "Hawaii-Based": "Yes" if partner.get("hawaii_based") else "No",
                "Score": partner.get("score", ""),
                "Website": partner.get("website", ""),
                "Bio": partner.get("bio", ""),
            })


def format_reports(
    fundraising_json: str,
    marketing_json: str,
    md_output: str,
    csv_outreach: str,
    csv_marketing: str
) -> None:
    """Format all Claude analysis results into reports."""
    print("Loading analysis results...")
    top_50 = load_json(fundraising_json)
    top_15 = load_json(marketing_json)

    print(f"Formatting {len(top_50)} fundraising candidates...")
    format_fundraising_outreach_csv(top_50, csv_outreach)
    print(f"✓ Saved to {csv_outreach}")

    print(f"Formatting {len(top_15)} marketing partners...")
    format_marketing_partners_csv(top_15, csv_marketing)
    print(f"✓ Saved to {csv_marketing}")

    print("Formatting comprehensive markdown report...")
    format_fundraising_recommendations(top_50, top_15, md_output)
    print(f"✓ Saved to {md_output}")

    print("\n✓ All reports formatted successfully!")


if __name__ == "__main__":
    base_path = Path(__file__).parent.parent

    fundraising_json = base_path / "data" / "top_50_fundraising.json"
    marketing_json = base_path / "data" / "top_15_marketing_partners.json"
    md_output = base_path / "output" / "fundraising_recommendations.md"
    csv_outreach = base_path / "output" / "fundraising_outreach.csv"
    csv_marketing = base_path / "output" / "marketing_partners.csv"

    # Check that input files exist
    if not fundraising_json.exists():
        print(f"Error: {fundraising_json} not found")
        exit(1)
    if not marketing_json.exists():
        print(f"Error: {marketing_json} not found")
        exit(1)

    format_reports(
        str(fundraising_json),
        str(marketing_json),
        str(md_output),
        str(csv_outreach),
        str(csv_marketing)
    )
