#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Worker Image Investigation Tool

Investigates Taskcluster task failures by comparing worker images,
extracting SBOM information, and finding relevant workers for debugging.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Optional


DEFAULT_TASKCLUSTER_ROOT_URL = "https://firefox-ci-tc.services.mozilla.com"


def extract_task_id(task_id_or_url: str) -> str:
    """Extract task ID from a Taskcluster URL or return as-is."""
    url_pattern = r"https?://[^/]+/(?:tasks|task-group)/([A-Za-z0-9_-]{22})"
    match = re.search(url_pattern, task_id_or_url)
    if match:
        return match.group(1)
    return task_id_or_url


def run_tc_cmd(args: list[str], root_url: str = DEFAULT_TASKCLUSTER_ROOT_URL) -> dict | None:
    """Run taskcluster CLI command and return parsed JSON."""
    env = os.environ.copy()
    env["TASKCLUSTER_ROOT_URL"] = root_url

    cmd = ["taskcluster"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
        if result.returncode != 0:
            print(f"Error: {result.stderr}", file=sys.stderr)
            return None

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            print("Error: taskcluster command returned non-JSON output", file=sys.stderr)
            print(result.stdout.strip(), file=sys.stderr)
            return None
    except FileNotFoundError:
        print("Error: taskcluster CLI not found. Install with: brew install taskcluster", file=sys.stderr)
        return None


def run_az_cmd(args: list[str]) -> dict | None:
    """Run Azure CLI command and return parsed JSON."""
    cmd = ["az"] + args + ["--output", "json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(f"Error: {result.stderr}", file=sys.stderr)
            return None

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            print("Error: az command returned non-JSON output", file=sys.stderr)
            print(result.stdout.strip(), file=sys.stderr)
            return None
    except FileNotFoundError:
        print("Error: az CLI not found. Install Azure CLI first.", file=sys.stderr)
        return None


def get_task_info(task_id: str, root_url: str = DEFAULT_TASKCLUSTER_ROOT_URL) -> dict | None:
    """Get task definition and status."""
    task_id = extract_task_id(task_id)

    # Use API to get full task info (returns JSON)
    definition = run_tc_cmd(["api", "queue", "task", task_id], root_url)
    status = run_tc_cmd(["api", "queue", "status", task_id], root_url)

    if not definition:
        return None

    return {
        "taskId": task_id,
        "definition": definition,
        "status": status or {},
    }


def extract_worker_info(task_info: dict) -> dict:
    """Extract worker pool and image information from task."""
    definition = task_info.get("definition", {})
    status = task_info.get("status", {})
    payload = definition.get("payload", {})

    # Get worker pool from task definition
    worker_pool = f"{definition.get('provisionerId', 'unknown')}/{definition.get('workerType', 'unknown')}"

    # Try to get image from runs
    runs = status.get("status", {}).get("runs", [])
    worker_id = None
    worker_group = None

    if runs:
        last_run = runs[-1]
        worker_id = last_run.get("workerId")
        worker_group = last_run.get("workerGroup")

    return {
        "workerPool": worker_pool,
        "workerId": worker_id,
        "workerGroup": worker_group,
        "taskLabel": definition.get("metadata", {}).get("name", "unknown"),
    }


def get_worker_sbom(worker_pool: str, root_url: str = DEFAULT_TASKCLUSTER_ROOT_URL) -> dict | None:
    """Get SBOM (Software Bill of Materials) for a worker pool."""
    # Extract provisioner and worker type
    parts = worker_pool.split("/")
    if len(parts) != 2:
        print(f"Invalid worker pool format: {worker_pool}", file=sys.stderr)
        return None

    provisioner, worker_type = parts

    # Get worker pool configuration
    pool_config = run_tc_cmd(
        ["api", "workerManager", "workerPool", f"{provisioner}/{worker_type}"],
        root_url,
    )

    if not pool_config or not isinstance(pool_config, dict):
        return None

    # Extract image information from pool config
    config = pool_config.get("config", {})
    launch_configs = config.get("launchConfigs", [])

    sbom_url = None
    image_version = None
    locations = []

    for lc in launch_configs:
        # Get location
        location = lc.get("location")
        if location and location not in locations:
            locations.append(location)

        # Get SBOM from workerConfig.genericWorker.config.workerTypeMetaData
        worker_config = lc.get("workerConfig", {})
        gw_config = worker_config.get("genericWorker", {}).get("config", {})
        metadata = gw_config.get("workerTypeMetaData", {})

        if metadata.get("sbom") and not sbom_url:
            sbom_url = metadata.get("sbom")
            # Extract version from SBOM URL (e.g., win11-64-24h2-1.0.8.md -> 1.0.8)
            import re
            version_match = re.search(r"-(\d+\.\d+\.\d+)\.md$", sbom_url)
            if version_match:
                image_version = version_match.group(1)

    return {
        "workerPool": worker_pool,
        "imageVersion": image_version,
        "sbomUrl": sbom_url,
        "locations": locations,
        "provider": pool_config.get("providerId"),
    }


def find_running_workers(worker_pool: str, root_url: str = DEFAULT_TASKCLUSTER_ROOT_URL) -> list:
    """Find currently running workers in a pool."""
    parts = worker_pool.split("/")
    if len(parts) != 2:
        return []

    provisioner, worker_type = parts

    workers = run_tc_cmd(
        ["api", "workerManager", "listWorkersForWorkerPool", f"{provisioner}/{worker_type}"],
        root_url,
    )

    if not workers or not isinstance(workers, dict):
        return []

    running = []
    for worker in workers.get("workers", []):
        if worker.get("state") == "running":
            running.append({
                "workerId": worker.get("workerId"),
                "workerGroup": worker.get("workerGroup"),
                "providerId": worker.get("providerId"),
            })

    return running


def run_vm_command(vm_name: str, resource_group: str, command: str) -> str | None:
    """Run a PowerShell command on an Azure VM."""
    result = run_az_cmd([
        "vm", "run-command", "invoke",
        "--resource-group", resource_group,
        "--name", vm_name,
        "--command-id", "RunPowerShellScript",
        "--scripts", command,
    ])

    if not result:
        return None

    # Extract output from Azure response
    if isinstance(result, dict):
        values = result.get("value", [])
        if isinstance(values, list) and values:
            messages = []
            for value in values:
                if isinstance(value, dict):
                    message = value.get("message")
                    if isinstance(message, str) and message:
                        messages.append(message)
            merged_message = "\n".join(messages).strip()
            if merged_message:
                # Azure run-command returns a wrapper with [stdout]/[stderr] sections.
                match = re.search(
                    r"\[stdout\]\s*(.*?)(?:\r?\n\[stderr\]|\Z)",
                    merged_message,
                    flags=re.DOTALL | re.IGNORECASE,
                )
                if match:
                    return match.group(1).strip()
                return merged_message

    return str(result)


def get_vm_info(vm_name: str, resource_group: str) -> dict | None:
    """Get Windows build and GenericWorker version from a VM."""
    # Validate VM exists first so we fail once instead of repeating the same error.
    vm_check = run_az_cmd(["vm", "show", "--resource-group", resource_group, "--name", vm_name])
    if not vm_check:
        return None

    # Get Windows version
    win_version_cmd = "(Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion').CurrentBuild"
    win_version = run_vm_command(vm_name, resource_group, win_version_cmd)

    # Get GenericWorker version
    gw_version_cmd = (
        "if (Test-Path 'C:\\generic-worker\\generic-worker-info.json') { "
        "(Get-Content C:\\generic-worker\\generic-worker-info.json | ConvertFrom-Json).version "
        "} else { 'not-found' }"
    )
    gw_version = run_vm_command(vm_name, resource_group, gw_version_cmd)

    # Get installed hotfixes
    hotfix_cmd = (
        "Get-HotFix | Sort-Object InstalledOn -Descending | "
        "Select-Object -First 5 HotFixID, InstalledOn | ConvertTo-Json -Depth 3"
    )
    hotfixes = run_vm_command(vm_name, resource_group, hotfix_cmd)

    parsed_hotfixes: list[dict] | dict | str | None = None
    if hotfixes:
        try:
            parsed_hotfixes = json.loads(hotfixes)
        except json.JSONDecodeError:
            parsed_hotfixes = hotfixes.strip()

    if not win_version and not gw_version and not hotfixes:
        return None

    return {
        "vmName": vm_name,
        "resourceGroup": resource_group,
        "windowsBuild": win_version.strip() if win_version else None,
        "genericWorkerVersion": gw_version.strip() if gw_version else None,
        "recentHotfixes": parsed_hotfixes,
    }


def cmd_investigate(task_id: str, root_url: str = DEFAULT_TASKCLUSTER_ROOT_URL) -> int:
    """Investigate a failing task."""
    task_id = extract_task_id(task_id)
    print(f"# Investigating Task: {task_id}", file=sys.stderr)

    # Get task info
    task_info = get_task_info(task_id, root_url)
    if not task_info:
        print("Failed to get task information", file=sys.stderr)
        return 1

    worker_info = extract_worker_info(task_info)

    # Get worker pool SBOM
    sbom = get_worker_sbom(worker_info["workerPool"], root_url)

    status = task_info.get("status", {})
    status_state = None
    if isinstance(status, dict):
        nested_status = status.get("status", {})
        if isinstance(nested_status, dict):
            status_state = nested_status.get("state")

    result = {
        "taskId": task_id,
        "taskLabel": worker_info["taskLabel"],
        "workerPool": worker_info["workerPool"],
        "workerId": worker_info["workerId"],
        "workerGroup": worker_info["workerGroup"],
        "imageVersion": sbom.get("imageVersion") if sbom else None,
        "sbomUrl": sbom.get("sbomUrl") if sbom else None,
        "status": status_state,
    }

    print(json.dumps(result, indent=2))
    return 0


def cmd_compare(task_id1: str, task_id2: str, root_url: str = DEFAULT_TASKCLUSTER_ROOT_URL) -> int:
    """Compare two tasks to find image differences."""
    print(f"# Comparing Tasks", file=sys.stderr)

    task1 = get_task_info(extract_task_id(task_id1), root_url)
    task2 = get_task_info(extract_task_id(task_id2), root_url)

    if not task1 or not task2:
        print("Failed to get task information", file=sys.stderr)
        return 1

    worker1 = extract_worker_info(task1)
    worker2 = extract_worker_info(task2)

    sbom1 = get_worker_sbom(worker1["workerPool"], root_url)
    sbom2 = get_worker_sbom(worker2["workerPool"], root_url)

    task1_status = task1.get("status", {}) if isinstance(task1, dict) else {}
    task2_status = task2.get("status", {}) if isinstance(task2, dict) else {}
    task1_state = None
    task2_state = None
    if isinstance(task1_status, dict):
        s1 = task1_status.get("status", {})
        if isinstance(s1, dict):
            task1_state = s1.get("state")
    if isinstance(task2_status, dict):
        s2 = task2_status.get("status", {})
        if isinstance(s2, dict):
            task2_state = s2.get("state")

    result = {
        "task1": {
            "taskId": extract_task_id(task_id1),
            "label": worker1["taskLabel"],
            "workerPool": worker1["workerPool"],
            "imageVersion": sbom1.get("imageVersion") if sbom1 else None,
            "sbomUrl": sbom1.get("sbomUrl") if sbom1 else None,
            "status": task1_state,
        },
        "task2": {
            "taskId": extract_task_id(task_id2),
            "label": worker2["taskLabel"],
            "workerPool": worker2["workerPool"],
            "imageVersion": sbom2.get("imageVersion") if sbom2 else None,
            "sbomUrl": sbom2.get("sbomUrl") if sbom2 else None,
            "status": task2_state,
        },
    }

    print(json.dumps(result, indent=2))
    return 0


def cmd_workers(worker_pool: str, root_url: str = DEFAULT_TASKCLUSTER_ROOT_URL) -> int:
    """List running workers in a pool."""
    print(f"# Running Workers: {worker_pool}", file=sys.stderr)

    workers = find_running_workers(worker_pool, root_url)

    print(json.dumps({"workers": workers, "count": len(workers)}, indent=2))
    return 0


def cmd_sbom(worker_pool: str, root_url: str = DEFAULT_TASKCLUSTER_ROOT_URL) -> int:
    """Get SBOM for a worker pool."""
    print(f"# SBOM: {worker_pool}", file=sys.stderr)

    sbom = get_worker_sbom(worker_pool, root_url)
    if not sbom:
        return 1

    print(json.dumps(sbom, indent=2))
    return 0


def cmd_vm_info(vm_name: str, resource_group: str) -> int:
    """Get information from an Azure VM."""
    print(f"# VM Info: {vm_name}", file=sys.stderr)

    info = get_vm_info(vm_name, resource_group)
    if not info:
        return 1

    print(json.dumps(info, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Investigate Taskcluster worker image issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Investigate a failing task
  %(prog)s investigate Axmr36nCRCmF2AmnVJgjVA

  # Compare two tasks (passing vs failing)
  %(prog)s compare <passing-task-id> <failing-task-id>

  # List running workers in a pool
  %(prog)s workers gecko-t/win11-64-24h2

  # Get SBOM for a worker pool
  %(prog)s sbom gecko-t/win11-64-24h2

  # Get VM info (requires Azure CLI)
  %(prog)s vm-info <vm-name> <resource-group>
        """,
    )

    parser.add_argument(
        "--root-url",
        default=DEFAULT_TASKCLUSTER_ROOT_URL,
        help="Taskcluster root URL (default: firefox-ci-tc)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # investigate command
    inv_parser = subparsers.add_parser("investigate", help="Investigate a failing task")
    inv_parser.add_argument("task_id", help="Task ID or Taskcluster URL")

    # compare command
    cmp_parser = subparsers.add_parser("compare", help="Compare two tasks")
    cmp_parser.add_argument("task_id1", help="First task ID (e.g., passing)")
    cmp_parser.add_argument("task_id2", help="Second task ID (e.g., failing)")

    # workers command
    wrk_parser = subparsers.add_parser("workers", help="List running workers")
    wrk_parser.add_argument("worker_pool", help="Worker pool (e.g., gecko-t/win11-64-24h2)")

    # sbom command
    sbom_parser = subparsers.add_parser("sbom", help="Get SBOM for worker pool")
    sbom_parser.add_argument("worker_pool", help="Worker pool (e.g., gecko-t/win11-64-24h2)")

    # vm-info command
    vm_parser = subparsers.add_parser("vm-info", help="Get Azure VM info")
    vm_parser.add_argument("vm_name", help="Azure VM name")
    vm_parser.add_argument("resource_group", help="Azure resource group")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "investigate":
        return cmd_investigate(args.task_id, args.root_url)
    elif args.command == "compare":
        return cmd_compare(args.task_id1, args.task_id2, args.root_url)
    elif args.command == "workers":
        return cmd_workers(args.worker_pool, args.root_url)
    elif args.command == "sbom":
        return cmd_sbom(args.worker_pool, args.root_url)
    elif args.command == "vm-info":
        return cmd_vm_info(args.vm_name, args.resource_group)

    return 1


if __name__ == "__main__":
    sys.exit(main())
