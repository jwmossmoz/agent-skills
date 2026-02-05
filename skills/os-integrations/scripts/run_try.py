#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "httpx", "taskcluster", "requests"]
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

    # Quick validation (skip Firefox build):
    uv run run_try.py win11-24h2 --use-existing-tasks -t xpcshell --push
    uv run run_try.py win11-24h2 --task-id ABC123 -t mochitest --push

    # Named query sets (specific suites, reuses builds):
    uv run run_try.py win11-24h2 --query-set targeted --push
    uv run run_try.py win11-24h2 --query-set targeted --watch

    # Watch test results:
    uv run run_try.py win11-24h2 -t xpcshell --watch
    uv run run_try.py win11-24h2 --use-existing-tasks --watch --watch-filter "xpcshell"
"""

import argparse
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

import requests
import taskcluster
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

# Taskcluster root URL for Firefox CI
TASKCLUSTER_ROOT_URL = "https://firefox-ci-tc.services.mozilla.com"

# Lando API URL
LANDO_API_URL = "https://lando.services.mozilla.com/api/v1"

# Default interval for checking Lando job status (in seconds)
DEFAULT_LANDO_CHECK_INTERVAL = 90


def get_latest_central_decision_task() -> str | None:
    """Get the latest mozilla-central decision task ID from Taskcluster index."""
    try:
        options = taskcluster.optionsFromEnvironment()
        options.setdefault("rootUrl", TASKCLUSTER_ROOT_URL)
        index = taskcluster.Index(options)
        result = index.findTask("gecko.v2.mozilla-central.latest.taskgraph.decision")
        return result.get("taskId")
    except Exception as e:
        print(f"Warning: Could not fetch latest decision task: {e}", file=sys.stderr)
        return None


def extract_push_id_from_output(output: str) -> str | None:
    """Extract push ID from mach try output."""
    # Look for patterns like "push-id/1234567" or "push-id: 1234567"
    match = re.search(r"push-id[/=:]?\s*(\d+)", output, re.IGNORECASE)
    if match:
        return match.group(1)

    # Also try Treeherder URL pattern
    match = re.search(r"treeherder\.mozilla\.org.*push-id[/=]?(\d+)", output)
    if match:
        return match.group(1)

    return None


def extract_lando_job_id_from_output(output: str) -> str | None:
    """Extract Lando job ID from mach try output."""
    # Look for patterns like "Lando job ID: 12345" or "landing_jobs/12345"
    patterns = [
        r"[Ll]ando\s+job\s+(?:ID|id)?[:\s]+(\d+)",
        r"landing_jobs/(\d+)",
        r"Job\s+ID[:\s]+(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            return match.group(1)
    return None


def check_lando_job_status(job_id: str) -> dict | None:
    """Check the status of a Lando landing job."""
    url = f"{LANDO_API_URL}/landing_jobs/{job_id}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error checking Lando job status: {e}", file=sys.stderr)
        return None


def poll_lando_job(job_id: str, interval: int = DEFAULT_LANDO_CHECK_INTERVAL) -> str | None:
    """Poll Lando job status until it reaches a terminal state."""
    terminal_statuses = {"landed", "failed"}
    print(f"\nPolling Lando job {job_id} every {interval} seconds...")
    print(f"API: {LANDO_API_URL}/landing_jobs/{job_id}\n")

    while True:
        job_data = check_lando_job_status(job_id)
        if job_data is None:
            print("Warning: Could not fetch job status, retrying...")
            time.sleep(interval)
            continue

        status = job_data.get("status", "unknown")
        updated_at = job_data.get("updated_at", "")
        print(f"[{time.strftime('%H:%M:%S')}] Status: {status}", end="")
        if updated_at:
            print(f" (updated: {updated_at})", end="")
        print()

        if status in terminal_statuses:
            if status == "landed":
                commit_id = job_data.get("landed_commit_id", "")
                print(f"\nLanded successfully! Commit: {commit_id}")
            elif status == "failed":
                error = job_data.get("error", "Unknown error")
                print(f"\nLanding failed: {error}", file=sys.stderr)
            return status

        time.sleep(interval)


def run_lumberjackth_watch(push_id: str, filter_regex: str | None = None) -> None:
    """Run lumberjackth to watch test results."""
    cmd = [
        "uvx", "--from", "lumberjackth",
        "lj", "jobs", "try",
        "--push-id", push_id,
        "--watch",
    ]
    if filter_regex:
        cmd.extend(["-f", filter_regex])

    print(f"\nWatching tests with lumberjackth...")
    if filter_regex:
        print(f"Filter: {filter_regex}")
    print(f"Command: {' '.join(cmd)}\n")
    subprocess.run(cmd)


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
    queries_override: list[str] | None = None,
    tests: list[str] | None = None,
    push: bool = False,
    use_existing_tasks: bool = False,
    task_id: str | None = None,
) -> list[str]:
    """Build the mach try command from preset configuration."""
    cmd = ["./mach", "try", "fuzzy"]

    # Add existing tasks option to skip rebuilding Firefox
    if use_existing_tasks:
        if task_id:
            cmd.extend(["--use-existing-tasks", f"task-id={task_id}"])
        else:
            latest_task = get_latest_central_decision_task()
            if latest_task:
                print(f"Using latest mozilla-central decision task: {latest_task}")
                cmd.extend(["--use-existing-tasks", f"task-id={latest_task}"])
            else:
                print("Warning: Could not find latest decision task, will use most recent try push")
                cmd.append("--use-existing-tasks")

    # Handle query selection:
    # 1. If queries_override provided, use those directly (multiple -q flags)
    # 2. Otherwise use preset query with optional -t test filtering
    if queries_override:
        # Multiple explicit queries - add each as -q flag
        for query in queries_override:
            cmd.extend(["-q", query])
    else:
        # Use preset's default query
        platform_query = preset_config.get("query", "")

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

  # Named query sets (reuse builds, specific suites):
  %(prog)s win11-24h2 --query-set targeted --push
  %(prog)s win11-24h2 --query-set targeted --watch
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
        action="append",
        dest="queries",
        metavar="QUERY",
        help="Query filter (can be repeated). Overrides preset's default query.",
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
        "--use-existing-tasks",
        action="store_true",
        help="Skip rebuilding Firefox by reusing builds from latest mozilla-central decision task",
    )
    parser.add_argument(
        "--task-id",
        metavar="TASK_ID",
        help="Specific decision task ID to use with --use-existing-tasks",
    )
    parser.add_argument(
        "--fresh-build",
        action="store_true",
        help="Force a fresh Firefox build (overrides --use-existing-tasks)",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch test results with lumberjackth after push (implies --push)",
    )
    parser.add_argument(
        "--watch-filter",
        metavar="REGEX",
        help="Regex filter for lumberjackth watch (e.g., 'xpcshell|mochitest')",
    )
    parser.add_argument(
        "--watch-lando",
        action="store_true",
        help="Poll Lando job status until landed or failed (implies --push)",
    )
    parser.add_argument(
        "--lando-interval",
        type=int,
        default=DEFAULT_LANDO_CHECK_INTERVAL,
        metavar="SECONDS",
        help=f"Interval between Lando status checks (default: {DEFAULT_LANDO_CHECK_INTERVAL}s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print command without executing",
    )
    parser.add_argument(
        "--query-set",
        metavar="NAME",
        help="Use a named query set from the preset config (e.g., 'targeted'). "
        "Query sets define specific test suites with their own settings for "
        "use_existing_tasks, skip_os_integration, and watch_filter.",
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

    # --watch and --watch-lando imply --push
    if args.watch or args.watch_lando:
        args.push = True

    # --query-set may imply --use-existing-tasks and --no-os-integration
    # (validated later after preset is loaded)

    # --fresh-build overrides --use-existing-tasks
    use_existing = args.use_existing_tasks and not args.fresh_build

    # --task-id implies --use-existing-tasks
    if args.task_id:
        use_existing = True

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

    # Determine final queries: explicit override > query-set > discovered > preset default
    final_queries = None
    if args.queries:
        final_queries = args.queries
    elif args.query_set:
        query_sets = preset_config.get("query_sets", {})
        if args.query_set not in query_sets:
            available = ", ".join(query_sets.keys()) if query_sets else "(none)"
            print(
                f"Error: Query set '{args.query_set}' not found in preset '{args.preset}'.\n"
                f"Available query sets: {available}",
                file=sys.stderr,
            )
            return 1
        qs = query_sets[args.query_set]
        qs_queries = qs.get("queries", [])
        if not qs_queries:
            print(
                f"Error: Query set '{args.query_set}' has no queries defined.",
                file=sys.stderr,
            )
            return 1
        final_queries = qs_queries
        qs_desc = qs.get("description", "")
        print(f"Using query set '{args.query_set}': {qs_desc}")
        print(f"{len(qs_queries)} queries:")
        for q in qs_queries:
            print(f"  - {q}")
        print()
        # Apply query set settings
        if qs.get("use_existing_tasks"):
            use_existing = True
        if qs.get("skip_os_integration"):
            args.no_os_integration = True
        # Use query set watch filter if --watch and no explicit --watch-filter
        if args.watch and not args.watch_filter:
            args.watch_filter = qs.get("watch_filter")
    elif discovered_labels:
        final_queries = discovered_labels

    # Build command
    cmd = build_command(
        preset_name=args.preset,
        preset_config=preset_config,
        no_os_integration=args.no_os_integration,
        rebuild=args.rebuild,
        env_vars=args.env_vars,
        queries_override=final_queries,
        tests=args.tests,
        push=args.push,
        use_existing_tasks=use_existing,
        task_id=args.task_id,
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
        full_output = "".join(output_lines)
        parsed_output = parse_output(full_output)
        display_summary(args.preset, preset_config, cmd, parsed_output, discovered_labels)

        # Handle --watch-lando: poll Lando job status until terminal state
        if args.watch_lando and returncode == 0:
            lando_job_id = extract_lando_job_id_from_output(full_output)
            if lando_job_id:
                poll_lando_job(lando_job_id, args.lando_interval)
            else:
                print("Warning: Could not extract Lando job ID from output", file=sys.stderr)
                print("Check manually: curl -s 'https://lando.services.mozilla.com/api/v1/landing_jobs/<ID>' | jq")

        # Handle --watch: launch lumberjackth to monitor test results
        if args.watch and returncode == 0:
            push_id = extract_push_id_from_output(full_output)
            if push_id:
                run_lumberjackth_watch(push_id, args.watch_filter)
            else:
                print("Warning: Could not extract push ID from output", file=sys.stderr)
                print("Run manually: uvx --from lumberjackth lj jobs try --push-id <ID> --watch")

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
