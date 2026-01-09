#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""
Fetch and parse alpha worker pools from mozilla-releng/fxci-config.

This script uses the GitHub CLI (gh) to fetch the worker-pools.yml file
from the fxci-config repository and extracts all alpha worker pools,
grouping them by category.

Usage:
    uv run fetch_worker_pools.py
"""

import subprocess
import sys

import yaml


REPO = "mozilla-releng/fxci-config"
FILE_PATH = "worker-pools.yml"
CATEGORIES = ["gecko-t", "releng-hardware", "gecko-1"]


def check_gh_installed() -> bool:
    """Check if the GitHub CLI is installed and available."""
    try:
        subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            check=True,
        )
        return True
    except FileNotFoundError:
        return False
    except subprocess.CalledProcessError:
        return False


def fetch_worker_pools_yaml() -> str | None:
    """Fetch the worker-pools.yml content from GitHub using gh api."""
    try:
        result = subprocess.run(
            [
                "gh",
                "api",
                f"/repos/{REPO}/contents/{FILE_PATH}",
                "-H",
                "Accept: application/vnd.github.raw+json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error fetching worker pools: {e.stderr}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return None


def parse_alpha_pools(yaml_content: str) -> dict[str, list[str]]:
    """Parse YAML content and extract alpha worker pools grouped by category."""
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}", file=sys.stderr)
        return {}

    if not isinstance(data, dict):
        print("Unexpected YAML structure: expected a dictionary", file=sys.stderr)
        return {}

    alpha_pools: dict[str, list[str]] = {cat: [] for cat in CATEGORIES}
    alpha_pools["other"] = []

    for pool_name in data.keys():
        if not pool_name.endswith("-alpha"):
            continue

        categorized = False
        for category in CATEGORIES:
            if pool_name.startswith(category):
                alpha_pools[category].append(pool_name)
                categorized = True
                break

        if not categorized:
            alpha_pools["other"].append(pool_name)

    # Sort pools within each category
    for category in alpha_pools:
        alpha_pools[category].sort()

    return alpha_pools


def display_pools(pools: dict[str, list[str]]) -> None:
    """Display the alpha pools grouped by category."""
    total_count = sum(len(p) for p in pools.values())

    if total_count == 0:
        print("No alpha worker pools found.")
        return

    print(f"Found {total_count} alpha worker pool(s):\n")

    for category in CATEGORIES + ["other"]:
        category_pools = pools.get(category, [])
        if not category_pools:
            continue

        display_name = category if category != "other" else "Other"
        print(f"[{display_name}] ({len(category_pools)} pool(s))")
        for pool in category_pools:
            print(f"  - {pool}")
        print()


def main() -> int:
    """Main entry point."""
    if not check_gh_installed():
        print(
            "Error: GitHub CLI (gh) is not installed or not in PATH.\n"
            "Install it from: https://cli.github.com/",
            file=sys.stderr,
        )
        return 1

    print(f"Fetching worker pools from {REPO}...\n")

    yaml_content = fetch_worker_pools_yaml()
    if yaml_content is None:
        return 1

    pools = parse_alpha_pools(yaml_content)
    display_pools(pools)

    return 0


if __name__ == "__main__":
    sys.exit(main())
