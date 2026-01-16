#!/usr/bin/env python3
"""
Simple wrapper for the taskcluster CLI.

This script provides a thin layer over the taskcluster CLI for common operations.
It primarily shells out to the `taskcluster` command and handles URL parsing.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


def extract_task_id(task_id_or_url: str) -> str:
    """
    Extract task ID from a Taskcluster URL or return the task ID as-is.

    Supports URLs like:
    - https://firefox-ci-tc.services.mozilla.com/tasks/<TASK_ID>
    - https://stage.taskcluster.nonprod.cloudops.mozgcp.net/tasks/<TASK_ID>
    - https://community-tc.services.mozilla.com/tasks/<TASK_ID>
    """
    # Match taskcluster URLs with /tasks/ or /task-group/ paths
    url_pattern = r'https?://[^/]+/(?:tasks|task-group)/([A-Za-z0-9_-]{22})'
    match = re.search(url_pattern, task_id_or_url)
    if match:
        return match.group(1)

    # If not a URL, assume it's already a task ID
    return task_id_or_url


def run_taskcluster_cmd(args: list[str], json_output: bool = True) -> int:
    """
    Execute a taskcluster CLI command and return the exit code.

    Args:
        args: Command arguments to pass to taskcluster CLI
        json_output: Whether to expect JSON output (for pretty printing)

    Returns:
        Exit code from the taskcluster command
    """
    cmd = ["taskcluster"] + args

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            return result.returncode

        # Pretty print JSON output
        if json_output and result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                print(json.dumps(data, indent=2))
            except json.JSONDecodeError:
                # Not JSON, print as-is
                print(result.stdout)
        else:
            print(result.stdout, end='')

        return 0

    except FileNotFoundError:
        print("Error: taskcluster CLI not found. Install with: brew install taskcluster", file=sys.stderr)
        return 127
    except Exception as e:
        print(f"Error running taskcluster command: {e}", file=sys.stderr)
        return 1


def cmd_status(task_id: str) -> int:
    """Get task status"""
    task_id = extract_task_id(task_id)
    print(f"# Task Status: {task_id}", file=sys.stderr)
    return run_taskcluster_cmd(["task", "status", task_id])


def cmd_log(task_id: str, run: Optional[int] = None) -> int:
    """Stream task log"""
    task_id = extract_task_id(task_id)
    print(f"# Task Log: {task_id}", file=sys.stderr)

    args = ["task", "log", task_id]
    if run is not None:
        args.extend(["--run", str(run)])

    return run_taskcluster_cmd(args, json_output=False)


def cmd_artifacts(task_id: str, run: Optional[int] = None) -> int:
    """List task artifacts"""
    task_id = extract_task_id(task_id)
    print(f"# Task Artifacts: {task_id}", file=sys.stderr)

    args = ["task", "artifacts", task_id]
    if run is not None:
        args.extend(["--run", str(run)])

    return run_taskcluster_cmd(args)


def cmd_definition(task_id: str) -> int:
    """Get full task definition"""
    task_id = extract_task_id(task_id)
    print(f"# Task Definition: {task_id}", file=sys.stderr)
    return run_taskcluster_cmd(["task", "def", task_id])


def cmd_retrigger(task_id: str) -> int:
    """Retrigger a task (new task ID)"""
    task_id = extract_task_id(task_id)
    print(f"# Retriggering Task: {task_id}", file=sys.stderr)
    return run_taskcluster_cmd(["task", "retrigger", task_id])


def cmd_rerun(task_id: str) -> int:
    """Rerun a task (same task ID)"""
    task_id = extract_task_id(task_id)
    print(f"# Rerunning Task: {task_id}", file=sys.stderr)
    return run_taskcluster_cmd(["task", "rerun", task_id])


def cmd_cancel(task_id: str) -> int:
    """Cancel a task"""
    task_id = extract_task_id(task_id)
    print(f"# Cancelling Task: {task_id}", file=sys.stderr)
    return run_taskcluster_cmd(["task", "cancel", task_id])


def cmd_group_list(group_id: str) -> int:
    """List tasks in a group"""
    group_id = extract_task_id(group_id)
    print(f"# Task Group List: {group_id}", file=sys.stderr)
    return run_taskcluster_cmd(["group", "list", group_id])


def cmd_group_status(group_id: str) -> int:
    """Get task group status"""
    group_id = extract_task_id(group_id)
    print(f"# Task Group Status: {group_id}", file=sys.stderr)
    return run_taskcluster_cmd(["group", "status", group_id])


def cmd_group_cancel(group_id: str) -> int:
    """Cancel a task group"""
    group_id = extract_task_id(group_id)
    print(f"# Cancelling Task Group: {group_id}", file=sys.stderr)
    return run_taskcluster_cmd(["group", "cancel", group_id])


def main():
    parser = argparse.ArgumentParser(
        description="Taskcluster CLI wrapper for common operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query task status
  %(prog)s status dtMnwBMHSc6kq5VGqJz0fw
  %(prog)s status https://firefox-ci-tc.services.mozilla.com/tasks/dtMnwBMHSc6kq5VGqJz0fw

  # Get task logs
  %(prog)s log dtMnwBMHSc6kq5VGqJz0fw

  # List artifacts
  %(prog)s artifacts dtMnwBMHSc6kq5VGqJz0fw

  # Retrigger a task
  %(prog)s retrigger dtMnwBMHSc6kq5VGqJz0fw

  # List tasks in a group
  %(prog)s group-list fuCPrKG2T62-4YH1tWYa7Q
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Task commands
    status_parser = subparsers.add_parser('status', help='Get task status')
    status_parser.add_argument('task_id', help='Task ID or Taskcluster URL')

    log_parser = subparsers.add_parser('log', help='Stream task log')
    log_parser.add_argument('task_id', help='Task ID or Taskcluster URL')
    log_parser.add_argument('--run', type=int, help='Specific run number')

    artifacts_parser = subparsers.add_parser('artifacts', help='List task artifacts')
    artifacts_parser.add_argument('task_id', help='Task ID or Taskcluster URL')
    artifacts_parser.add_argument('--run', type=int, help='Specific run number')

    def_parser = subparsers.add_parser('definition', help='Get full task definition')
    def_parser.add_argument('task_id', help='Task ID or Taskcluster URL')

    retrigger_parser = subparsers.add_parser('retrigger', help='Retrigger task (new task ID)')
    retrigger_parser.add_argument('task_id', help='Task ID or Taskcluster URL')

    rerun_parser = subparsers.add_parser('rerun', help='Rerun task (same task ID)')
    rerun_parser.add_argument('task_id', help='Task ID or Taskcluster URL')

    cancel_parser = subparsers.add_parser('cancel', help='Cancel a task')
    cancel_parser.add_argument('task_id', help='Task ID or Taskcluster URL')

    # Group commands
    group_list_parser = subparsers.add_parser('group-list', help='List tasks in a group')
    group_list_parser.add_argument('group_id', help='Task Group ID or URL')

    group_status_parser = subparsers.add_parser('group-status', help='Get task group status')
    group_status_parser.add_argument('group_id', help='Task Group ID or URL')

    group_cancel_parser = subparsers.add_parser('group-cancel', help='Cancel a task group')
    group_cancel_parser.add_argument('group_id', help='Task Group ID or URL')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch to command handlers
    if args.command == 'status':
        return cmd_status(args.task_id)
    elif args.command == 'log':
        return cmd_log(args.task_id, args.run)
    elif args.command == 'artifacts':
        return cmd_artifacts(args.task_id, args.run)
    elif args.command == 'definition':
        return cmd_definition(args.task_id)
    elif args.command == 'retrigger':
        return cmd_retrigger(args.task_id)
    elif args.command == 'rerun':
        return cmd_rerun(args.task_id)
    elif args.command == 'cancel':
        return cmd_cancel(args.task_id)
    elif args.command == 'group-list':
        return cmd_group_list(args.group_id)
    elif args.command == 'group-status':
        return cmd_group_status(args.group_id)
    elif args.command == 'group-cancel':
        return cmd_group_cancel(args.group_id)

    return 1


if __name__ == '__main__':
    sys.exit(main())
