#!/usr/bin/env python3
"""Merge fundraising_outreach.csv with 6 missed high-value prospects from
db_fundraising_outreach.csv into a combined 31-row CSV ranked by 4-axis score."""

import csv
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_CSV = os.path.join(BASE, "output", "fundraising_outreach.csv")
DB_CSV = os.path.join(BASE, "output", "db_fundraising_outreach.csv")
OUT_CSV = os.path.join(BASE, "output", "combined_top_followers.csv")

FIELDNAMES = [
    "Rank", "Handle", "Display Name", "Followers", "Entity Type",
    "Hawaii-Based", "Financial Capacity", "Donor Access",
    "Dinner Potential", "Hawaii Connection", "Total Score",
    "Outreach Type", "Suggested Ask", "Website", "Bio",
]

# 6 DB-only prospects that the AI model missed, scored on the 4-axis model
MISSES = {
    "fishcakehawaii": {
        "Financial Capacity": 22, "Donor Access": 20,
        "Dinner Potential": 16, "Hawaii Connection": 14,
        "Total Score": 72,
        "Entity Type": "member_organization",
        "Outreach Type": "MEMBER_PRESENTATION",
        "Suggested Ask": "$0 (access value)",
    },
    "hawaiidoggiebakery": {
        "Financial Capacity": 24, "Donor Access": 18,
        "Dinner Potential": 15, "Hawaii Connection": 14,
        "Total Score": 71,
        "Entity Type": "established_business",
        "Outreach Type": "TABLE_PURCHASE",
        "Suggested Ask": "$2,500-$5,000",
    },
    "thepublicpet": {
        "Financial Capacity": 24, "Donor Access": 16,
        "Dinner Potential": 15, "Hawaii Connection": 14,
        "Total Score": 69,
        "Entity Type": "established_business",
        "Outreach Type": "TABLE_PURCHASE",
        "Suggested Ask": "$2,500-$5,000",
    },
    "heartofkailua": {
        "Financial Capacity": 18, "Donor Access": 22,
        "Dinner Potential": 14, "Hawaii Connection": 14,
        "Total Score": 68,
        "Entity Type": "member_organization",
        "Outreach Type": "MEMBER_PRESENTATION",
        "Suggested Ask": "$0 (access value)",
    },
    "haikuvet": {
        "Financial Capacity": 24, "Donor Access": 16,
        "Dinner Potential": 14, "Hawaii Connection": 14,
        "Total Score": 68,
        "Entity Type": "established_business",
        "Outreach Type": "TABLE_PURCHASE",
        "Suggested Ask": "$2,000-$3,500",
    },
    "humphreysaccaro": {
        "Financial Capacity": 22, "Donor Access": 18,
        "Dinner Potential": 12, "Hawaii Connection": 14,
        "Total Score": 66,
        "Entity Type": "established_business",
        "Outreach Type": "DOOR_OPENER",
        "Suggested Ask": "N/A (in-kind promo value)",
    },
}


def main():
    # Read AI-generated top 25
    with open(AI_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Read DB version to pull bio/website/follower data for the 6 misses
    db_lookup = {}
    with open(DB_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            db_lookup[row["Handle"]] = row

    # Build rows for the 6 missed prospects
    for handle, scores in MISSES.items():
        db = db_lookup[handle]
        new_row = {
            "Handle": handle,
            "Display Name": db["Display Name"],
            "Followers": db["Followers"],
            "Entity Type": scores["Entity Type"],
            "Hawaii-Based": "Yes",
            "Financial Capacity": scores["Financial Capacity"],
            "Donor Access": scores["Donor Access"],
            "Dinner Potential": scores["Dinner Potential"],
            "Hawaii Connection": scores["Hawaii Connection"],
            "Total Score": scores["Total Score"],
            "Outreach Type": scores["Outreach Type"],
            "Suggested Ask": scores["Suggested Ask"],
            "Website": db.get("Website", ""),
            "Bio": db.get("Bio", ""),
        }
        rows.append(new_row)

    # Sort descending by Total Score
    rows.sort(key=lambda r: int(r["Total Score"]), reverse=True)

    # Re-rank
    for i, row in enumerate(rows, 1):
        row["Rank"] = i

    # Write combined CSV
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUT_CSV}")


if __name__ == "__main__":
    main()
