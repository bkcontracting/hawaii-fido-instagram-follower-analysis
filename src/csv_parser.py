"""CSV parser for Instagram follower export files.

Reads a CSV with at least {handle, display_name, profile_url} columns,
deduplicates by handle, normalises whitespace, and returns clean dicts.
"""
import csv
import os


class ParseError(Exception):
    """Raised when the CSV structure is invalid (e.g. missing required columns)."""


def parse_followers(filepath: str) -> list[dict]:
    """Parse CSV and return list of {handle, display_name, profile_url}.

    Rules
    -----
    - Reads by column headers (not positional); extra columns are ignored.
    - Deduplicates by handle — first occurrence wins.
    - If display_name is empty/whitespace, falls back to handle.
    - Strips leading/trailing whitespace from handle and display_name.

    Raises
    ------
    FileNotFoundError
        If *filepath* does not point to an existing file.
    ParseError
        If the CSV is missing the required ``handle`` column.
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)

        # Validate required column exists
        if reader.fieldnames is None or "handle" not in reader.fieldnames:
            raise ParseError(
                f"CSV is missing required 'handle' column. "
                f"Found columns: {reader.fieldnames}"
            )

        seen: set[str] = set()
        results: list[dict] = []

        for row in reader:
            handle = row.get("handle", "").strip()
            if not handle or handle in seen:
                continue
            seen.add(handle)

            display_name = row.get("display_name", "").strip()
            if not display_name:
                display_name = handle

            profile_url = row.get("profile_url", "").strip()

            results.append(
                {
                    "handle": handle,
                    "display_name": display_name,
                    "profile_url": profile_url,
                }
            )

    return results
