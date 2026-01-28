#!/usr/bin/env python3
"""
Simple wrapper for the taskcluster CLI.

This script provides a thin layer over the taskcluster CLI for common operations.
It primarily shells out to the `taskcluster` command and handles URL parsing.
Includes support for triggering in-tree actions like confirm-failures and backfill.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Optional

# Default Taskcluster root URL for Firefox CI
DEFAULT_TASKCLUSTER_ROOT_URL = "https://firefox-ci-tc.services.mozilla.com"


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

    # Set default TASKCLUSTER_ROOT_URL if not already set
    env = os.environ.copy()
    if "TASKCLUSTER_ROOT_URL" not in env:
        env["TASKCLUSTER_ROOT_URL"] = DEFAULT_TASKCLUSTER_ROOT_URL

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)

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


def get_task_definition(task_id: str) -> Optional[dict[str, Any]]:
    """Get task definition as JSON."""
    task_id = extract_task_id(task_id)
    env = os.environ.copy()
    if "TASKCLUSTER_ROOT_URL" not in env:
        env["TASKCLUSTER_ROOT_URL"] = DEFAULT_TASKCLUSTER_ROOT_URL

    cmd = ["taskcluster", "task", "def", task_id]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def get_actions_json(task_group_id: str) -> Optional[dict[str, Any]]:
    """
    Fetch actions.json from the decision task of a task group.

    The actions.json artifact contains all available in-tree actions
    like confirm-failures, retrigger-multiple, backfill, etc.
    """
    root_url = os.environ.get("TASKCLUSTER_ROOT_URL", DEFAULT_TASKCLUSTER_ROOT_URL).rstrip("/")
    url = f"{root_url}/api/queue/v1/task/{task_group_id}/artifacts/public/actions.json"

    try:
        # Use curl for more reliable redirect handling
        result = subprocess.run(
            ["curl", "-sL", url],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            print(f"Error fetching actions.json: {result.stderr}", file=sys.stderr)
            return None
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        print("Error: Timeout fetching actions.json", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing actions.json: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error fetching actions.json: {e}", file=sys.stderr)
        return None


def find_action(actions_json: dict[str, Any], action_name: str) -> Optional[dict[str, Any]]:
    """Find a specific action by name in actions.json."""
    for action in actions_json.get("actions", []):
        if action.get("name") == action_name:
            return action
    return None


def trigger_action(
    task_id: str,
    action_name: str,
    input_data: Optional[dict[str, Any]] = None,
) -> int:
    """
    Trigger an in-tree action for a task.

    Args:
        task_id: The task ID to run the action on
        action_name: Name of the action (e.g., "confirm-failures", "backfill")
        input_data: Optional input parameters for the action

    Returns:
        Exit code (0 for success)
    """
    task_id = extract_task_id(task_id)

    # Get task definition to find task group ID
    task_def = get_task_definition(task_id)
    if not task_def:
        print(f"Error: Could not get task definition for {task_id}", file=sys.stderr)
        return 1

    task_group_id = task_def.get("taskGroupId")
    if not task_group_id:
        print("Error: Could not determine task group ID", file=sys.stderr)
        return 1

    # Get actions.json from the decision task (task group ID is the decision task)
    actions_json = get_actions_json(task_group_id)
    if not actions_json:
        print(f"Error: Could not fetch actions.json for task group {task_group_id}", file=sys.stderr)
        return 1

    # Find the requested action
    action = find_action(actions_json, action_name)
    if not action:
        print(f"Error: Action '{action_name}' not found in actions.json", file=sys.stderr)
        print("Available actions:", file=sys.stderr)
        for a in actions_json.get("actions", []):
            print(f"  - {a.get('name')}: {a.get('title')}", file=sys.stderr)
        return 1

    # Build the hook payload
    hook_group_id = action.get("hookGroupId")
    hook_id = action.get("hookId")
    hook_payload = action.get("hookPayload", {})

    if not hook_group_id or not hook_id:
        print(f"Error: Action '{action_name}' is missing hook configuration", file=sys.stderr)
        return 1

    # Construct the payload by substituting variables
    # The hookPayload uses JSON-e expressions like {$eval: "input"}
    payload = {
        "decision": hook_payload.get("decision", {}),
        "user": {
            "input": input_data or {},
            "taskId": task_id,
            "taskGroupId": task_group_id,
        },
    }

    # Write payload to temp file for taskcluster CLI
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        payload_file = f.name

    try:
        print(f"# Triggering action: {action_name}", file=sys.stderr)
        print(f"# Hook: {hook_group_id}/{hook_id}", file=sys.stderr)
        print(f"# Task: {task_id}", file=sys.stderr)
        print(f"# Task Group: {task_group_id}", file=sys.stderr)

        env = os.environ.copy()
        if "TASKCLUSTER_ROOT_URL" not in env:
            env["TASKCLUSTER_ROOT_URL"] = DEFAULT_TASKCLUSTER_ROOT_URL

        cmd = [
            "taskcluster",
            "api",
            "hooks",
            "triggerHook",
            hook_group_id,
            hook_id,
        ]

        # Read payload from stdin
        with open(payload_file) as f:
            result = subprocess.run(
                cmd, stdin=f, capture_output=True, text=True, check=False, env=env
            )

        if result.returncode != 0:
            print(f"Error triggering hook: {result.stderr}", file=sys.stderr)
            return result.returncode

        # Pretty print the response
        if result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                print(json.dumps(data, indent=2))
                new_task_id = data.get("status", {}).get("taskId") or data.get("taskId")
                if new_task_id:
                    print(f"\n# New task created: {new_task_id}", file=sys.stderr)
                    root_url = env.get("TASKCLUSTER_ROOT_URL", DEFAULT_TASKCLUSTER_ROOT_URL).rstrip("/")
                    print(f"# URL: {root_url}/tasks/{new_task_id}", file=sys.stderr)
            except json.JSONDecodeError:
                print(result.stdout)

        return 0

    finally:
        os.unlink(payload_file)


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


# -------------------------------------------------------------------------
# Action commands
# -------------------------------------------------------------------------


def cmd_action_list(task_id: str) -> int:
    """List available actions for a task"""
    task_id = extract_task_id(task_id)

    # Get task definition to find task group ID
    task_def = get_task_definition(task_id)
    if not task_def:
        print(f"Error: Could not get task definition for {task_id}", file=sys.stderr)
        return 1

    task_group_id = task_def.get("taskGroupId")
    if not task_group_id:
        print("Error: Could not determine task group ID", file=sys.stderr)
        return 1

    print(f"# Actions for task {task_id}", file=sys.stderr)
    print(f"# Task Group: {task_group_id}", file=sys.stderr)

    actions_json = get_actions_json(task_group_id)
    if not actions_json:
        print(f"Error: Could not fetch actions.json for task group {task_group_id}", file=sys.stderr)
        return 1

    # Format actions as JSON
    actions_list = []
    for action in actions_json.get("actions", []):
        actions_list.append({
            "name": action.get("name"),
            "title": action.get("title"),
            "description": action.get("description", ""),
            "kind": action.get("kind"),
        })

    print(json.dumps(actions_list, indent=2))
    return 0


def cmd_confirm_failures(task_id: str) -> int:
    """
    Trigger confirm-failures action for a task.

    This action re-runs the failing tests multiple times to determine
    if they are intermittent failures or real regressions.
    """
    return trigger_action(task_id, "confirm-failures")


def cmd_backfill(task_id: str) -> int:
    """
    Trigger backfill action for a task.

    This action runs the same test on previous pushes to help identify
    when a regression was introduced.
    """
    return trigger_action(task_id, "backfill")


def cmd_retrigger_multiple(task_id: str, times: int = 5) -> int:
    """
    Trigger retrigger-multiple action for a task.

    This action retriggers the task multiple times, useful for
    confirming intermittent failures.
    """
    return trigger_action(task_id, "retrigger-multiple", {"requests": [{"times": times}]})


def cmd_action(task_id: str, action_name: str, input_json: Optional[str] = None) -> int:
    """Trigger any action by name with optional input"""
    input_data = None
    if input_json:
        try:
            input_data = json.loads(input_json)
        except json.JSONDecodeError as e:
            print(f"Error parsing input JSON: {e}", file=sys.stderr)
            return 1

    return trigger_action(task_id, action_name, input_data)


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

    # Action commands
    action_list_parser = subparsers.add_parser('action-list', help='List available actions for a task')
    action_list_parser.add_argument('task_id', help='Task ID or Taskcluster URL')

    confirm_failures_parser = subparsers.add_parser(
        'confirm-failures',
        help='Re-run failing tests to confirm if intermittent or regression'
    )
    confirm_failures_parser.add_argument('task_id', help='Task ID or Taskcluster URL')

    backfill_parser = subparsers.add_parser(
        'backfill',
        help='Run test on previous pushes to find regression range'
    )
    backfill_parser.add_argument('task_id', help='Task ID or Taskcluster URL')

    retrigger_multiple_parser = subparsers.add_parser(
        'retrigger-multiple',
        help='Retrigger a task multiple times'
    )
    retrigger_multiple_parser.add_argument('task_id', help='Task ID or Taskcluster URL')
    retrigger_multiple_parser.add_argument(
        '--times', '-n', type=int, default=5,
        help='Number of times to retrigger (default: 5)'
    )

    action_parser = subparsers.add_parser(
        'action',
        help='Trigger any action by name'
    )
    action_parser.add_argument('task_id', help='Task ID or Taskcluster URL')
    action_parser.add_argument('action_name', help='Name of the action to trigger')
    action_parser.add_argument('--input', help='JSON input for the action')

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
    elif args.command == 'action-list':
        return cmd_action_list(args.task_id)
    elif args.command == 'confirm-failures':
        return cmd_confirm_failures(args.task_id)
    elif args.command == 'backfill':
        return cmd_backfill(args.task_id)
    elif args.command == 'retrigger-multiple':
        return cmd_retrigger_multiple(args.task_id, args.times)
    elif args.command == 'action':
        return cmd_action(args.task_id, args.action_name, args.input)

    return 1


if __name__ == '__main__':
    sys.exit(main())
