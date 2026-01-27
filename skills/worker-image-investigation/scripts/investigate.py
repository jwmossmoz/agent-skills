#!/usr/bin/env python3
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


def run_tc_cmd(args: list[str], root_url: str = DEFAULT_TASKCLUSTER_ROOT_URL) -> dict | str | None:
    """Run taskcluster CLI command and return parsed JSON or raw output."""
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
            return result.stdout.strip()
    except FileNotFoundError:
        print("Error: taskcluster CLI not found. Install with: brew install taskcluster", file=sys.stderr)
        return None


def run_az_cmd(args: list[str]) -> dict | str | None:
    """Run Azure CLI command and return parsed JSON or raw output."""
    cmd = ["az"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(f"Error: {result.stderr}", file=sys.stderr)
            return None

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return result.stdout.strip()
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

    if not pool_config:
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

    if not workers:
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
        if values:
            return values[0].get("message", "")

    return str(result)


def get_vm_info(vm_name: str, resource_group: str) -> dict | None:
    """Get Windows build and GenericWorker version from a VM."""
    # Get Windows version
    win_version_cmd = "(Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion').CurrentBuild"
    win_version = run_vm_command(vm_name, resource_group, win_version_cmd)

    # Get GenericWorker version
    gw_version_cmd = "Get-Content C:\\generic-worker\\generic-worker-info.json | ConvertFrom-Json | Select-Object -ExpandProperty version"
    gw_version = run_vm_command(vm_name, resource_group, gw_version_cmd)

    # Get installed hotfixes
    hotfix_cmd = "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 5 HotFixID, InstalledOn | ConvertTo-Json"
    hotfixes = run_vm_command(vm_name, resource_group, hotfix_cmd)

    return {
        "vmName": vm_name,
        "resourceGroup": resource_group,
        "windowsBuild": win_version.strip() if win_version else None,
        "genericWorkerVersion": gw_version.strip() if gw_version else None,
        "recentHotfixes": hotfixes,
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

    result = {
        "taskId": task_id,
        "taskLabel": worker_info["taskLabel"],
        "workerPool": worker_info["workerPool"],
        "workerId": worker_info["workerId"],
        "workerGroup": worker_info["workerGroup"],
        "imageVersion": sbom.get("imageVersion") if sbom else None,
        "sbomUrl": sbom.get("sbomUrl") if sbom else None,
        "status": task_info["status"].get("status", {}).get("state"),
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

    result = {
        "task1": {
            "taskId": extract_task_id(task_id1),
            "label": worker1["taskLabel"],
            "workerPool": worker1["workerPool"],
            "imageVersion": sbom1.get("imageVersion") if sbom1 else None,
            "sbomUrl": sbom1.get("sbomUrl") if sbom1 else None,
            "status": task1["status"].get("status", {}).get("state"),
        },
        "task2": {
            "taskId": extract_task_id(task_id2),
            "label": worker2["taskLabel"],
            "workerPool": worker2["workerPool"],
            "imageVersion": sbom2.get("imageVersion") if sbom2 else None,
            "sbomUrl": sbom2.get("sbomUrl") if sbom2 else None,
            "status": task2["status"].get("status", {}).get("state"),
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


def get_task_group_tasks(task_group_id: str, root_url: str = DEFAULT_TASKCLUSTER_ROOT_URL) -> list:
    """Get all tasks in a task group."""
    task_group_id = extract_task_id(task_group_id)

    result = run_tc_cmd(
        ["api", "queue", "listTaskGroup", task_group_id],
        root_url,
    )

    if not result:
        return []

    return result.get("tasks", [])


def get_production_pool_for_alpha(alpha_pool: str) -> str:
    """
    Map an alpha worker pool to its production equivalent.

    Example: gecko-t/win11-64-24h2-alpha -> gecko-t/win11-64-24h2
    """
    # Common alpha pool suffixes to strip
    alpha_suffixes = ["-alpha", "-staging", "-test", "-beta"]

    for suffix in alpha_suffixes:
        if alpha_pool.endswith(suffix):
            return alpha_pool[: -len(suffix)]

    # If no suffix found, return as-is
    return alpha_pool


def cmd_batch_compare(
    task_group_id: str,
    production_pool: str | None,
    alpha_pool: str | None,
    root_url: str = DEFAULT_TASKCLUSTER_ROOT_URL,
) -> int:
    """
    Compare all failed tasks in a task group.

    Identifies tasks that failed on alpha but might pass on production,
    which indicates an image regression rather than a code regression.
    """
    print(f"# Batch Compare: {task_group_id}", file=sys.stderr)

    tasks = get_task_group_tasks(task_group_id, root_url)
    if not tasks:
        print("No tasks found in task group", file=sys.stderr)
        return 1

    print(f"Found {len(tasks)} tasks in group", file=sys.stderr)

    # Find failed tasks
    failed_tasks = []
    for task_entry in tasks:
        task = task_entry.get("task", {})
        status = task_entry.get("status", {})
        state = status.get("state")

        if state in ["failed", "exception"]:
            task_id = status.get("taskId")
            worker_pool = f"{task.get('provisionerId', 'unknown')}/{task.get('workerType', 'unknown')}"
            task_label = task.get("metadata", {}).get("name", "unknown")

            # Filter by alpha pool if specified
            if alpha_pool and worker_pool != alpha_pool:
                continue

            failed_tasks.append({
                "taskId": task_id,
                "taskLabel": task_label,
                "workerPool": worker_pool,
                "state": state,
            })

    if not failed_tasks:
        print("No failed tasks found", file=sys.stderr)
        result = {"taskGroupId": task_group_id, "failedTasks": [], "summary": "No failures"}
        print(json.dumps(result, indent=2))
        return 0

    print(f"Found {len(failed_tasks)} failed tasks", file=sys.stderr)

    # Get SBOM info for each unique worker pool
    pool_sboms = {}
    for task in failed_tasks:
        pool = task["workerPool"]
        if pool not in pool_sboms:
            sbom = get_worker_sbom(pool, root_url)
            pool_sboms[pool] = sbom

        task["imageVersion"] = pool_sboms[pool].get("imageVersion") if pool_sboms[pool] else None
        task["sbomUrl"] = pool_sboms[pool].get("sbomUrl") if pool_sboms[pool] else None

        # Get production pool equivalent
        prod_pool = production_pool or get_production_pool_for_alpha(pool)
        if prod_pool != pool and prod_pool not in pool_sboms:
            prod_sbom = get_worker_sbom(prod_pool, root_url)
            pool_sboms[prod_pool] = prod_sbom

        task["productionPool"] = prod_pool
        task["productionImageVersion"] = pool_sboms.get(prod_pool, {}).get("imageVersion") if pool_sboms.get(prod_pool) else None

    # Group by worker pool
    by_pool = {}
    for task in failed_tasks:
        pool = task["workerPool"]
        by_pool.setdefault(pool, []).append(task)

    result = {
        "taskGroupId": task_group_id,
        "totalTasks": len(tasks),
        "failedTasks": len(failed_tasks),
        "byPool": {
            pool: {
                "count": len(tasks),
                "imageVersion": pool_sboms.get(pool, {}).get("imageVersion") if pool_sboms.get(pool) else None,
                "productionPool": get_production_pool_for_alpha(pool),
                "productionImageVersion": pool_sboms.get(get_production_pool_for_alpha(pool), {}).get("imageVersion") if pool_sboms.get(get_production_pool_for_alpha(pool)) else None,
                "tasks": tasks,
            }
            for pool, tasks in by_pool.items()
        },
    }

    print(json.dumps(result, indent=2))
    return 0


def cmd_find_image_regressions(
    task_group_id: str,
    root_url: str = DEFAULT_TASKCLUSTER_ROOT_URL,
) -> int:
    """
    Find tasks that likely failed due to image changes.

    An image regression is indicated when:
    - Task failed on an alpha/staging pool
    - The equivalent production pool has a different image version
    - The failure pattern suggests image-specific issues
    """
    print(f"# Finding Image Regressions: {task_group_id}", file=sys.stderr)

    tasks = get_task_group_tasks(task_group_id, root_url)
    if not tasks:
        print("No tasks found in task group", file=sys.stderr)
        return 1

    # Analyze each task
    potential_regressions = []
    pool_cache = {}

    for task_entry in tasks:
        task = task_entry.get("task", {})
        status = task_entry.get("status", {})
        state = status.get("state")

        if state not in ["failed", "exception"]:
            continue

        task_id = status.get("taskId")
        worker_pool = f"{task.get('provisionerId', 'unknown')}/{task.get('workerType', 'unknown')}"
        task_label = task.get("metadata", {}).get("name", "unknown")

        # Check if this is an alpha/staging pool
        is_alpha = any(suffix in worker_pool for suffix in ["-alpha", "-staging", "-test", "-beta"])

        if not is_alpha:
            continue

        # Get SBOM for alpha pool
        if worker_pool not in pool_cache:
            pool_cache[worker_pool] = get_worker_sbom(worker_pool, root_url)

        alpha_sbom = pool_cache[worker_pool]
        alpha_version = alpha_sbom.get("imageVersion") if alpha_sbom else None

        # Get SBOM for production pool
        prod_pool = get_production_pool_for_alpha(worker_pool)
        if prod_pool not in pool_cache:
            pool_cache[prod_pool] = get_worker_sbom(prod_pool, root_url)

        prod_sbom = pool_cache[prod_pool]
        prod_version = prod_sbom.get("imageVersion") if prod_sbom else None

        # Check for version difference
        version_differs = alpha_version != prod_version

        potential_regressions.append({
            "taskId": task_id,
            "taskLabel": task_label,
            "alphaPool": worker_pool,
            "alphaImageVersion": alpha_version,
            "productionPool": prod_pool,
            "productionImageVersion": prod_version,
            "versionDiffers": version_differs,
            "likelyImageRegression": version_differs,
            "taskclusterUrl": f"{root_url}/tasks/{task_id}",
        })

    # Summary
    likely_regressions = [r for r in potential_regressions if r["likelyImageRegression"]]

    result = {
        "taskGroupId": task_group_id,
        "totalAlphaFailures": len(potential_regressions),
        "likelyImageRegressions": len(likely_regressions),
        "regressions": likely_regressions,
        "allAlphaFailures": potential_regressions,
    }

    print(json.dumps(result, indent=2))
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

  # Batch compare all failed tasks in a task group
  %(prog)s batch-compare U0vOaaW-T-i5nN79edugYA

  # Filter batch compare to specific alpha pool
  %(prog)s batch-compare U0vOaaW-T-i5nN79edugYA --alpha-pool gecko-t/win11-64-24h2-alpha

  # Find tasks that likely failed due to image changes
  %(prog)s find-image-regressions U0vOaaW-T-i5nN79edugYA
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

    # batch-compare command
    batch_parser = subparsers.add_parser(
        "batch-compare",
        help="Compare all failed tasks in a task group",
    )
    batch_parser.add_argument("task_group_id", help="Task group ID or Taskcluster URL")
    batch_parser.add_argument(
        "--production-pool",
        help="Production worker pool to compare against (auto-detected if not specified)",
    )
    batch_parser.add_argument(
        "--alpha-pool",
        help="Filter to only tasks from this alpha pool",
    )

    # find-image-regressions command
    regress_parser = subparsers.add_parser(
        "find-image-regressions",
        help="Find tasks that likely failed due to image changes",
    )
    regress_parser.add_argument("task_group_id", help="Task group ID or Taskcluster URL")

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
    elif args.command == "batch-compare":
        return cmd_batch_compare(
            args.task_group_id,
            args.production_pool,
            args.alpha_pool,
            args.root_url,
        )
    elif args.command == "find-image-regressions":
        return cmd_find_image_regressions(args.task_group_id, args.root_url)

    return 1


if __name__ == "__main__":
    sys.exit(main())
