#!/usr/bin/env python3
"""
Main build orchestrator for Hawaii Fi-Do dashboard.

This script coordinates the entire build process:
1. Convert CSVs to JavaScript (csv-to-js.py)
2. Generate self-contained HTML (generate-html.py)
3. Validate output

Usage:
    python3 build-dashboard.py
"""

import subprocess
import sys
from pathlib import Path


def run_script(script_name, description):
    """
    Run a Python script and handle errors.

    Args:
        script_name: Name of script file
        description: Human-readable description

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}\n")

    script_path = Path(__file__).parent / script_name

    if not script_path.exists():
        print(f"❌ ERROR: Script not found: {script_path}", file=sys.stderr)
        return False

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            capture_output=False
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ ERROR: {description} failed with exit code {e.returncode}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {description} failed: {e}", file=sys.stderr)
        return False


def validate_output():
    """Validate generated output files."""
    print(f"\n{'='*60}")
    print("Validating Output")
    print(f"{'='*60}\n")

    project_root = Path(__file__).parent.parent.parent
    index_path = project_root / 'dashboard' / 'dist' / 'index.html'

    if not index_path.exists():
        print(f"❌ ERROR: Output file not found: {index_path}", file=sys.stderr)
        return False

    file_size = index_path.stat().st_size
    print(f"✓ index.html exists ({file_size:,} bytes / {file_size/1024:.1f} KB)")

    # Check file size
    if file_size < 1000:
        print("⚠️  WARNING: Output file seems too small", file=sys.stderr)
        return False

    if file_size > 5_000_000:  # > 5MB
        print("⚠️  WARNING: Output file is very large (> 5MB)", file=sys.stderr)

    # Check content
    content = index_path.read_text(encoding='utf-8')

    checks = {
        'DASHBOARD_DATA': '✓ Dashboard data embedded',
        'DASHBOARD_CONFIG': '✓ Dashboard config embedded',
        'class Dashboard': '✓ Dashboard application code present',
        '<html': '✓ Valid HTML structure',
    }

    all_passed = True
    for check_str, message in checks.items():
        if check_str in content:
            print(message)
        else:
            print(f"❌ {message.replace('✓', 'MISSING:')}", file=sys.stderr)
            all_passed = False

    # Check for unreplaced placeholders
    if '{{' in content or '$' in content:
        print("⚠️  WARNING: Possible unreplaced placeholders in output", file=sys.stderr)

    return all_passed


def main():
    """Main entry point."""
    print("\n🏗️  Hawaii Fi-Do Dashboard - Build System")
    print("=" * 60)

    # Step 1: Convert CSVs to JavaScript
    if not run_script('csv-to-js.py', 'Step 1/3: Converting CSVs to JavaScript'):
        sys.exit(1)

    # Step 2: Generate HTML
    if not run_script('generate-html.py', 'Step 2/3: Generating self-contained HTML'):
        sys.exit(1)

    # Step 3: Validate
    if not validate_output():
        print("\n❌ Build validation failed", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*60}")
    print("✅ BUILD SUCCESSFUL")
    print(f"{'='*60}\n")
    print("📁 Output: dashboard/dist/index.html")
    print("\n💡 Next steps:")
    print("   • Open dashboard/dist/index.html in browser to test locally")
    print("   • Run deployment script to publish to Cloudflare Pages")
    print()


if __name__ == '__main__':
    main()
