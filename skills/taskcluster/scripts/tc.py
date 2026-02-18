#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Taskcluster helper for operations not covered by the native CLI.

For basic operations, use the taskcluster CLI directly:
  taskcluster task status <taskId>
  taskcluster task log <taskId>
  taskcluster task def <taskId>
  taskcluster task rerun <taskId>
  taskcluster task cancel <taskId>
  taskcluster group list --all <groupId>
  taskcluster group status <groupId>
  taskcluster group cancel --force <groupId>

This script handles what the native CLI cannot:
  artifacts     Full artifact listing as JSON (URLs, content types, expiry)
  group-status  Structured state count summary (JSON)
  retrigger     In-tree action retrigger (preserves task graph dependencies)
  retrigger-multiple  Retrigger N times via in-tree action
  confirm-failures    Re-run failing tests to check intermittent vs regression
  backfill      Run test on previous pushes to find regression range
  action-list   List all available in-tree actions for a task
  action        Trigger any in-tree action by name with optional JSON input
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
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
    url_pattern = r'https?://[^/]+/(?:tasks|task-group)/([A-Za-z0-9_-]{22})'
    match = re.search(url_pattern, task_id_or_url)
    if match:
        return match.group(1)
    return task_id_or_url


def run_taskcluster_cmd(
    args: list[str], expect_json: bool = True
) -> tuple[int, dict[str, Any] | list[Any] | str | None]:
    """
    Execute a taskcluster CLI command and return parsed output.

    Args:
        args: Command arguments to pass to taskcluster CLI.
        expect_json: Whether command output must be valid JSON.

    Returns:
        Tuple of (exit_code, parsed_output).
    """
    cmd = ["taskcluster"] + args

    env = os.environ.copy()
    if "TASKCLUSTER_ROOT_URL" not in env:
        env["TASKCLUSTER_ROOT_URL"] = DEFAULT_TASKCLUSTER_ROOT_URL

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)

        if result.returncode != 0:
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            return result.returncode, None

        if expect_json:
            if not result.stdout.strip():
                print("Error: Command returned empty output; expected JSON", file=sys.stderr)
                return 1, None
            try:
                return 0, json.loads(result.stdout)
            except json.JSONDecodeError:
                print("Error: Command returned non-JSON output; expected JSON", file=sys.stderr)
                print(result.stdout.strip(), file=sys.stderr)
                return 1, None

        return 0, result.stdout

    except FileNotFoundError:
        print("Error: taskcluster CLI not found. Install with: brew install taskcluster", file=sys.stderr)
        return 127, None
    except Exception as e:
        print(f"Error running taskcluster command: {e}", file=sys.stderr)
        return 1, None


def fetch_paginated_queue(
    method: str,
    method_args: list[str],
    items_key: str,
) -> tuple[int, dict[str, Any] | None]:
    """
    Fetch all pages for queue endpoints that return continuationToken.

    Returns a merged response where `items_key` contains all items.
    """
    continuation: Optional[str] = None
    merged_items: list[Any] = []
    last_page: Optional[dict[str, Any]] = None

    while True:
        args = ["api", "queue", method, *method_args]
        if continuation:
            args.extend(["--continuationToken", continuation])

        code, data = run_taskcluster_cmd(args, expect_json=True)
        if code != 0:
            return code, None
        if not isinstance(data, dict):
            print(f"Error: Unexpected response type from queue {method}", file=sys.stderr)
            return 1, None

        page_items = data.get(items_key, [])
        if not isinstance(page_items, list):
            print(f"Error: Expected '{items_key}' to be a list in queue {method} response", file=sys.stderr)
            return 1, None
        merged_items.extend(page_items)

        continuation = data.get("continuationToken")
        last_page = data
        if not continuation:
            break

    if last_page is None:
        return 1, None

    merged = {k: v for k, v in last_page.items() if k not in {items_key, "continuationToken"}}
    merged[items_key] = merged_items
    return 0, merged


def get_task_definition(task_id: str) -> Optional[dict[str, Any]]:
    """Get task definition as JSON."""
    task_id = extract_task_id(task_id)
    code, data = run_taskcluster_cmd(["api", "queue", "task", task_id], expect_json=True)
    if code != 0 or not isinstance(data, dict):
        return None
    return data


def get_actions_json(task_group_id: str) -> Optional[dict[str, Any]]:
    """
    Fetch actions.json from the decision task of a task group.

    The actions.json artifact contains all available in-tree actions
    like confirm-failures, retrigger-multiple, backfill, etc.
    """
    root_url = os.environ.get("TASKCLUSTER_ROOT_URL", DEFAULT_TASKCLUSTER_ROOT_URL).rstrip("/")
    url = f"{root_url}/api/queue/v1/task/{task_group_id}/artifacts/public/actions.json"

    try:
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

    task_def = get_task_definition(task_id)
    if not task_def:
        print(f"Error: Could not get task definition for {task_id}", file=sys.stderr)
        return 1

    task_group_id = task_def.get("taskGroupId")
    if not task_group_id:
        print("Error: Could not determine task group ID", file=sys.stderr)
        return 1

    actions_json = get_actions_json(task_group_id)
    if not actions_json:
        print(f"Error: Could not fetch actions.json for task group {task_group_id}", file=sys.stderr)
        return 1

    action = find_action(actions_json, action_name)
    if not action:
        print(f"Error: Action '{action_name}' not found in actions.json", file=sys.stderr)
        print("Available actions:", file=sys.stderr)
        for a in actions_json.get("actions", []):
            print(f"  - {a.get('name')}: {a.get('title')}", file=sys.stderr)
        return 1

    hook_group_id = action.get("hookGroupId")
    hook_id = action.get("hookId")
    hook_payload = action.get("hookPayload", {})

    if not hook_group_id or not hook_id:
        print(f"Error: Action '{action_name}' is missing hook configuration", file=sys.stderr)
        return 1

    payload = {
        "decision": hook_payload.get("decision", {}),
        "user": {
            "input": input_data or {},
            "taskId": task_id,
            "taskGroupId": task_group_id,
        },
    }

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

        cmd = ["taskcluster", "api", "hooks", "triggerHook", hook_group_id, hook_id]

        with open(payload_file) as f:
            result = subprocess.run(
                cmd, stdin=f, capture_output=True, text=True, check=False, env=env
            )

        if result.returncode != 0:
            print(f"Error triggering hook: {result.stderr}", file=sys.stderr)
            return result.returncode

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
                print("Error: Hook response was not valid JSON", file=sys.stderr)
                print(result.stdout.strip(), file=sys.stderr)
                return 1

        return 0

    finally:
        os.unlink(payload_file)


def cmd_artifacts(task_id: str, run: Optional[int] = None) -> int:
    """List task artifacts as full JSON (names, URLs, content types, expiry)."""
    task_id = extract_task_id(task_id)
    print(f"# Task Artifacts: {task_id}", file=sys.stderr)

    if run is not None:
        code, data = fetch_paginated_queue("listArtifacts", [task_id, str(run)], "artifacts")
    else:
        code, data = fetch_paginated_queue("listLatestArtifacts", [task_id], "artifacts")
    if code != 0 or data is None:
        return code if code != 0 else 1
    print(json.dumps(data, indent=2))
    return 0


def cmd_group_status(group_id: str) -> int:
    """Get task group status with structured state count summary."""
    group_id = extract_task_id(group_id)
    print(f"# Task Group Status: {group_id}", file=sys.stderr)
    meta_code, meta = run_taskcluster_cmd(["api", "queue", "getTaskGroup", group_id], expect_json=True)
    if meta_code != 0 or not isinstance(meta, dict):
        return meta_code if meta_code != 0 else 1

    list_code, tasks_data = fetch_paginated_queue("listTaskGroup", [group_id], "tasks")
    if list_code != 0 or tasks_data is None:
        return list_code if list_code != 0 else 1

    tasks = tasks_data.get("tasks", [])
    state_counts: dict[str, int] = {}
    if isinstance(tasks, list):
        for task in tasks:
            state = "unknown"
            if isinstance(task, dict):
                status = task.get("status", {})
                if isinstance(status, dict):
                    state = status.get("state", "unknown")
            state_counts[state] = state_counts.get(state, 0) + 1

    result = {
        "taskGroupId": group_id,
        "taskGroup": meta,
        "taskSummary": {
            "totalTasks": len(tasks) if isinstance(tasks, list) else 0,
            "stateCounts": state_counts,
        },
    }
    print(json.dumps(result, indent=2))
    return 0


def cmd_action_list(task_id: str) -> int:
    """List available in-tree actions for a task."""
    task_id = extract_task_id(task_id)

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

    actions_list = [
        {
            "name": action.get("name"),
            "title": action.get("title"),
            "description": action.get("description", ""),
            "kind": action.get("kind"),
        }
        for action in actions_json.get("actions", [])
    ]
    print(json.dumps(actions_list, indent=2))
    return 0


def cmd_retrigger(task_id: str) -> int:
    """
    Retrigger a task using the in-tree action API.

    Uses the Firefox taskgraph's retrigger hook, which recreates the task
    within the task graph context with correct dependencies.

    Note: `taskcluster task retrigger` clears dependencies, breaking Firefox CI
    tasks that depend on upstream artifacts (e.g., signing tasks needing builds).
    """
    return trigger_action(task_id, "retrigger")


def cmd_confirm_failures(task_id: str) -> int:
    """Re-run failing tests to determine if intermittent or regression."""
    return trigger_action(task_id, "confirm-failures")


def cmd_backfill(task_id: str) -> int:
    """Run test on previous pushes to find regression range."""
    return trigger_action(task_id, "backfill")


def cmd_retrigger_multiple(task_id: str, times: int = 5) -> int:
    """Retrigger a task N times via in-tree action."""
    return trigger_action(task_id, "retrigger-multiple", {"requests": [{"times": times}]})


def cmd_action(task_id: str, action_name: str, input_json: Optional[str] = None) -> int:
    """Trigger any in-tree action by name with optional JSON input."""
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
        description="Taskcluster helper for operations not covered by the native CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
For basic operations use the native taskcluster CLI:
  taskcluster task status <taskId>       # task status
  taskcluster task log <taskId>          # stream log
  taskcluster task def <taskId>          # full task definition
  taskcluster task rerun <taskId>        # rerun (same task ID)
  taskcluster task cancel <taskId>       # cancel
  taskcluster group list --all <groupId> # list all tasks in group
  taskcluster group status <groupId>     # group status
  taskcluster group cancel --force <groupId>  # cancel group

This script handles the rest:
  %(prog)s artifacts <taskId>                     # full JSON with URLs
  %(prog)s group-status <groupId>                 # structured state counts
  %(prog)s retrigger <taskId>                     # in-tree retrigger
  %(prog)s retrigger-multiple <taskId> --times 5  # retrigger N times
  %(prog)s confirm-failures <taskId>              # confirm intermittent
  %(prog)s backfill <taskId>                      # find regression range
  %(prog)s action-list <taskId>                   # list available actions
  %(prog)s action <taskId> <name> --input '{}'    # trigger any action
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    artifacts_parser = subparsers.add_parser(
        'artifacts', help='List task artifacts as full JSON (includes URLs, content types, expiry)'
    )
    artifacts_parser.add_argument('task_id', help='Task ID or Taskcluster URL')
    artifacts_parser.add_argument('--run', type=int, help='Specific run number')

    group_status_parser = subparsers.add_parser(
        'group-status', help='Get task group status with structured state count summary'
    )
    group_status_parser.add_argument('group_id', help='Task Group ID or URL')

    retrigger_parser = subparsers.add_parser(
        'retrigger', help='Retrigger task via in-tree action (preserves dependencies)'
    )
    retrigger_parser.add_argument('task_id', help='Task ID or Taskcluster URL')

    retrigger_multiple_parser = subparsers.add_parser(
        'retrigger-multiple', help='Retrigger a task N times via in-tree action'
    )
    retrigger_multiple_parser.add_argument('task_id', help='Task ID or Taskcluster URL')
    retrigger_multiple_parser.add_argument(
        '--times', '-n', type=int, default=5,
        help='Number of times to retrigger (default: 5)'
    )

    confirm_failures_parser = subparsers.add_parser(
        'confirm-failures', help='Re-run failing tests to confirm intermittent or regression'
    )
    confirm_failures_parser.add_argument('task_id', help='Task ID or Taskcluster URL')

    backfill_parser = subparsers.add_parser(
        'backfill', help='Run test on previous pushes to find regression range'
    )
    backfill_parser.add_argument('task_id', help='Task ID or Taskcluster URL')

    action_list_parser = subparsers.add_parser(
        'action-list', help='List available in-tree actions for a task'
    )
    action_list_parser.add_argument('task_id', help='Task ID or Taskcluster URL')

    action_parser = subparsers.add_parser(
        'action', help='Trigger any in-tree action by name'
    )
    action_parser.add_argument('task_id', help='Task ID or Taskcluster URL')
    action_parser.add_argument('action_name', help='Name of the action to trigger')
    action_parser.add_argument('--input', help='JSON input for the action')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == 'artifacts':
        return cmd_artifacts(args.task_id, args.run)
    elif args.command == 'group-status':
        return cmd_group_status(args.group_id)
    elif args.command == 'retrigger':
        return cmd_retrigger(args.task_id)
    elif args.command == 'retrigger-multiple':
        return cmd_retrigger_multiple(args.task_id, args.times)
    elif args.command == 'confirm-failures':
        return cmd_confirm_failures(args.task_id)
    elif args.command == 'backfill':
        return cmd_backfill(args.task_id)
    elif args.command == 'action-list':
        return cmd_action_list(args.task_id)
    elif args.command == 'action':
        return cmd_action(args.task_id, args.action_name, args.input)

    return 1


if __name__ == '__main__':
    sys.exit(main())
