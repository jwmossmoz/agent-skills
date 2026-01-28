#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "httpx"]
# ///
"""
Construct and execute mach try commands for OS integration testing.

This script loads preset configurations and builds mach try commands
with appropriate worker overrides for targeting specific Windows
testing environments.

Usage:
    uv run run_try.py win11-24h2
    uv run run_try.py win11-hw --rebuild 5
    uv run run_try.py win10-2009 --dry-run
    uv run run_try.py win11-amd --env MOZ_LOG=sync:5 --push
    uv run run_try.py b-win2022 --discover --dry-run

    # Filter to specific test types:
    uv run run_try.py win11-24h2 -t xpcshell -t mochitest-browser-chrome --push
    uv run run_try.py win11-24h2 -t mochitest-devtools-chrome --dry-run
"""

import argparse
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import yaml

from discover_tasks import fetch_task_graph, filter_by_worker_type


FIREFOX_DIR = Path.home() / "firefox"
SCRIPT_DIR = Path(__file__).parent.resolve()
PRESETS_FILE = SCRIPT_DIR.parent / "references" / "presets.yml"

VALID_PRESETS = [
    "win11-24h2",
    "win11-hw",
    "win10-2009",
    "win11-amd",
    "win11-source",
    "b-win2022",
    "win11-arm64",
]

PROTECTED_BRANCHES = ["main", "master", "central"]


def load_presets() -> dict | None:
    """Load preset configurations from presets.yml."""
    if not PRESETS_FILE.exists():
        print(f"Error: Presets file not found: {PRESETS_FILE}", file=sys.stderr)
        return None

    try:
        with open(PRESETS_FILE, "r") as f:
            data = yaml.safe_load(f)
            return data.get("presets", {})
    except yaml.YAMLError as e:
        print(f"Error parsing presets file: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error reading presets file: {e}", file=sys.stderr)
        return None


def get_current_branch(directory: Path) -> str | None:
    """Get the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=directory,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None
    except FileNotFoundError:
        print("Error: git is not installed or not in PATH", file=sys.stderr)
        return None


def create_temp_branch(preset_name: str) -> str | None:
    """Create a temporary branch for try push and return its name."""
    import time
    timestamp = int(time.time())
    branch_name = f"try-{preset_name}-{timestamp}"

    try:
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            capture_output=True,
            check=True,
            cwd=FIREFOX_DIR,
        )
        return branch_name
    except subprocess.CalledProcessError as e:
        print(f"Error creating temporary branch: {e.stderr.decode()}", file=sys.stderr)
        return None


def switch_branch(branch_name: str) -> bool:
    """Switch to the specified branch."""
    try:
        subprocess.run(
            ["git", "checkout", branch_name],
            capture_output=True,
            check=True,
            cwd=FIREFOX_DIR,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error switching to branch {branch_name}: {e.stderr.decode()}", file=sys.stderr)
        return False


def delete_branch(branch_name: str) -> bool:
    """Delete the specified branch."""
    try:
        subprocess.run(
            ["git", "branch", "-D", branch_name],
            capture_output=True,
            check=True,
            cwd=FIREFOX_DIR,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def preflight_check(preset_name: str) -> tuple[bool, str | None, str | None]:
    """
    Verify prerequisites before running mach try.

    Returns:
        Tuple of (success, original_branch, temp_branch)
        - success: Whether preflight passed
        - original_branch: The branch we were on (if we created a temp branch)
        - temp_branch: The temp branch name (if we created one)
    """
    # Check Firefox directory exists
    if not FIREFOX_DIR.exists():
        print(f"Error: Firefox directory not found: {FIREFOX_DIR}", file=sys.stderr)
        return False, None, None

    # Check if it's a git repository
    if not (FIREFOX_DIR / ".git").exists():
        # Could be a worktree or bare repo
        git_file = FIREFOX_DIR / ".git"
        if not git_file.exists():
            print(
                f"Error: {FIREFOX_DIR} does not appear to be a git repository",
                file=sys.stderr,
            )
            return False, None, None

    # Check current branch
    branch = get_current_branch(FIREFOX_DIR)
    if branch is None:
        print("Error: Could not determine current git branch", file=sys.stderr)
        return False, None, None

    original_branch = None
    temp_branch = None

    if branch in PROTECTED_BRANCHES:
        print(f"On protected branch '{branch}', creating temporary branch for try push...")
        original_branch = branch
        temp_branch = create_temp_branch(preset_name)
        if temp_branch is None:
            return False, None, None
        print(f"Created temporary branch: {temp_branch}\n")

    # Check mach exists
    mach_path = FIREFOX_DIR / "mach"
    if not mach_path.exists():
        print(f"Error: mach script not found at {mach_path}", file=sys.stderr)
        # Clean up temp branch if we created one
        if temp_branch and original_branch:
            switch_branch(original_branch)
            delete_branch(temp_branch)
        return False, None, None

    return True, original_branch, temp_branch


def build_command(
    preset_name: str,
    preset_config: dict,
    no_os_integration: bool = False,
    rebuild: int | None = None,
    env_vars: list[str] | None = None,
    query_override: str | None = None,
    tests: list[str] | None = None,
    push: bool = False,
) -> list[str]:
    """Build the mach try command from preset configuration."""
    cmd = ["./mach", "try", "fuzzy"]

    # Determine the platform query
    platform_query = query_override if query_override else preset_config.get("query", "")

    # If tests are specified, build an intersection query:
    # -xq "platform" -q "'test1 | 'test2 | 'test3"
    if tests:
        if platform_query:
            # Split platform query to handle "-xq 'foo'" style
            platform_parts = shlex.split(platform_query)
            # Check if it already has -x flag
            has_intersection = any(p.startswith("-x") for p in platform_parts)
            if has_intersection:
                cmd.extend(platform_parts)
            else:
                # Add -x for intersection and the platform query
                cmd.append("-xq")
                cmd.append(platform_parts[-1] if platform_parts else "")
        # Build OR query for test types using exact match syntax
        test_query = " | ".join(f"'{t}" for t in tests)
        cmd.extend(["-q", test_query])
    elif platform_query:
        # No tests filter, just use the platform query as-is
        platform_parts = shlex.split(platform_query)
        cmd.extend(platform_parts)

    # Add flags from preset
    flags = preset_config.get("flags", [])
    cmd.extend(flags)

    # Add os-integration preset unless disabled
    use_os_integration = preset_config.get("use_os_integration", True)
    if use_os_integration and not no_os_integration:
        cmd.extend(["--preset", "os-integration"])

    # Add worker overrides
    worker_overrides = preset_config.get("worker_overrides", [])
    for override in worker_overrides:
        cmd.extend(["--worker-override", override])

    # Add rebuild flag
    if rebuild is not None:
        cmd.extend(["--rebuild", str(rebuild)])

    # Add environment variables
    if env_vars:
        for env_var in env_vars:
            cmd.extend(["--env", env_var])

    # Handle push behavior:
    # - With --push: use default Lando push (no flag needed)
    # - Without --push: add --no-push to prevent pushing
    if not push:
        cmd.append("--no-push")

    return cmd


def parse_output(output: str) -> dict:
    """Parse mach try output to extract useful information."""
    result = {
        "task_count": None,
        "treeherder_url": None,
        "push_id": None,
    }

    # Look for task count patterns
    task_patterns = [
        r"(\d+)\s+tasks?\s+selected",
        r"Selected\s+(\d+)\s+tasks?",
        r"Scheduling\s+(\d+)\s+tasks?",
    ]
    for pattern in task_patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            result["task_count"] = int(match.group(1))
            break

    # Look for Treeherder URL
    th_patterns = [
        r"(https?://treeherder\.mozilla\.org[^\s]+)",
        r"Treeherder:\s+(https?://[^\s]+)",
    ]
    for pattern in th_patterns:
        match = re.search(pattern, output)
        if match:
            result["treeherder_url"] = match.group(1)
            break

    # Look for push ID
    push_pattern = r"push\s+id[:\s]+(\w+)"
    match = re.search(push_pattern, output, re.IGNORECASE)
    if match:
        result["push_id"] = match.group(1)

    return result


def display_summary(
    preset_name: str,
    preset_config: dict,
    cmd: list[str],
    parsed_output: dict | None = None,
    discovered_labels: list[str] | None = None,
) -> None:
    """Display a summary of the command and results."""
    print("\n" + "=" * 60)
    print(f"Preset: {preset_name}")
    print(f"Description: {preset_config.get('description', 'N/A')}")
    print("=" * 60)

    # Worker overrides summary
    worker_overrides = preset_config.get("worker_overrides", [])
    if worker_overrides:
        print("\nWorker Overrides:")
        for override in worker_overrides:
            print(f"  - {override}")

    # Discovered tasks summary
    if discovered_labels:
        print(f"\nDiscovered Tasks ({len(discovered_labels)} total):")
        for label in discovered_labels[:5]:  # Show first 5 in summary
            print(f"  - {label}")
        if len(discovered_labels) > 5:
            print(f"  ... and {len(discovered_labels) - 5} more")

    if parsed_output:
        print("\nResults:")
        if parsed_output.get("task_count") is not None:
            print(f"  Tasks selected: {parsed_output['task_count']}")
        if parsed_output.get("treeherder_url"):
            print(f"  Treeherder: {parsed_output['treeherder_url']}")
        if parsed_output.get("push_id"):
            print(f"  Push ID: {parsed_output['push_id']}")

    print("=" * 60 + "\n")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run mach try with OS integration presets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s win11-24h2              Run Windows 11 24H2 tests
  %(prog)s win11-hw --rebuild 5    Run hardware tests with 5 rebuilds
  %(prog)s win10-2009 --dry-run    Preview command without executing
  %(prog)s win11-amd --push        Run AMD tests and push to try

  # Filter to specific test types:
  %(prog)s win11-24h2 -t xpcshell -t mochitest-browser-chrome --push
  %(prog)s win11-24h2 -t mochitest-devtools-chrome -t mochitest-chrome-1proc --dry-run
        """,
    )

    parser.add_argument(
        "preset",
        choices=VALID_PRESETS,
        help="Preset configuration name",
    )
    parser.add_argument(
        "--no-os-integration",
        action="store_true",
        help="Skip the --preset os-integration flag",
    )
    parser.add_argument(
        "--rebuild",
        type=int,
        metavar="N",
        help="Add --rebuild N to run tasks multiple times",
    )
    parser.add_argument(
        "--env",
        action="append",
        metavar="KEY=VALUE",
        dest="env_vars",
        help="Add environment variable (can be specified multiple times)",
    )
    parser.add_argument(
        "-q",
        "--query",
        metavar="QUERY",
        help="Override the preset's query filter",
    )
    parser.add_argument(
        "-t",
        "--tests",
        action="append",
        metavar="TEST_TYPE",
        help="Filter to specific test types (can be repeated). "
        "Examples: mochitest-browser-chrome, xpcshell, mochitest-devtools-chrome",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push to try via Lando",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print command without executing",
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Auto-discover tasks for presets with worker_type defined",
    )
    parser.add_argument(
        "--branch",
        default="mozilla-central",
        metavar="BRANCH",
        help="Branch to fetch task graph from for discovery (default: mozilla-central)",
    )

    args = parser.parse_args()

    # Load presets
    presets = load_presets()
    if presets is None:
        return 1

    # Get preset configuration
    preset_config = presets.get(args.preset)
    if preset_config is None:
        print(
            f"Error: Preset '{args.preset}' not found in presets file", file=sys.stderr
        )
        print(f"Available presets: {', '.join(presets.keys())}", file=sys.stderr)
        return 1

    # Handle task discovery
    discovered_labels: list[str] = []
    discovered_query: str | None = None

    if args.discover:
        worker_type = preset_config.get("worker_type")
        if not worker_type:
            print(
                f"Error: Preset '{args.preset}' does not have a worker_type defined.\n"
                f"Add 'worker_type: <type>' to the preset in presets.yml to enable discovery.",
                file=sys.stderr,
            )
            return 1

        print(f"Discovering tasks for worker type '{worker_type}'...")
        task_graph = fetch_task_graph(branch=args.branch)
        if task_graph is None:
            print("Error: Failed to fetch task graph", file=sys.stderr)
            return 1

        discovered_labels = filter_by_worker_type(task_graph, worker_type)
        if not discovered_labels:
            print(f"Warning: No tasks found for worker type '{worker_type}'", file=sys.stderr)
        else:
            print(f"Found {len(discovered_labels)} task(s)\n")
            # Build query from discovered labels
            # Use multiple -q flags for mach try fuzzy union behavior
            discovered_query = " ".join(f"-q '{label}'" for label in discovered_labels)

    # Determine final query: explicit override > discovered > preset default
    final_query = args.query if args.query else discovered_query

    # Build command
    cmd = build_command(
        preset_name=args.preset,
        preset_config=preset_config,
        no_os_integration=args.no_os_integration,
        rebuild=args.rebuild,
        env_vars=args.env_vars,
        query_override=final_query,
        tests=args.tests,
        push=args.push,
    )

    # Display command
    cmd_str = " ".join(cmd)
    print(f"\nCommand: {cmd_str}")
    print(f"Directory: {FIREFOX_DIR}\n")

    # Show discovered tasks if any
    if discovered_labels:
        print(f"Discovered {len(discovered_labels)} task(s):")
        for label in discovered_labels[:10]:  # Show first 10
            print(f"  - {label}")
        if len(discovered_labels) > 10:
            print(f"  ... and {len(discovered_labels) - 10} more")
        print()

    if args.dry_run:
        print("[DRY RUN] Command not executed")
        display_summary(args.preset, preset_config, cmd, discovered_labels=discovered_labels)
        return 0

    # Run preflight checks (may create temp branch if on protected branch)
    success, original_branch, temp_branch = preflight_check(args.preset)
    if not success:
        return 1

    # Execute command
    print("Executing mach try...\n")
    process = None
    returncode = 1
    try:
        process = subprocess.Popen(
            cmd,
            cwd=FIREFOX_DIR,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )

        output_lines: list[str] = []
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="")
            output_lines.append(line)

        returncode = process.wait()
        parsed_output = parse_output("".join(output_lines))
        display_summary(args.preset, preset_config, cmd, parsed_output, discovered_labels)

    except FileNotFoundError:
        print("Error: Could not execute mach command", file=sys.stderr)
        returncode = 1
    except KeyboardInterrupt:
        if process and process.poll() is None:
            process.terminate()
        print("\nOperation cancelled by user")
        returncode = 130
    finally:
        # Clean up: switch back to original branch and delete temp branch
        if original_branch and temp_branch:
            print(f"\nCleaning up: switching back to '{original_branch}'...")
            if switch_branch(original_branch):
                delete_branch(temp_branch)
                print(f"Deleted temporary branch '{temp_branch}'")
            else:
                print(f"Warning: Could not switch back to '{original_branch}'", file=sys.stderr)
                print(f"You may need to manually delete branch '{temp_branch}'", file=sys.stderr)

    return returncode


if __name__ == "__main__":
    sys.exit(main())
