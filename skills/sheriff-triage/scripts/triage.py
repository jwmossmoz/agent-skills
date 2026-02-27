#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["treeherder-client", "requests"]
# ///
"""
Sheriff Triage Tool

Comprehensive failure triage that automatically determines the likely cause
of CI failures by combining data from Taskcluster, Treeherder, and worker
image analysis.

Verdicts:
- CODE_REGRESSION: Likely caused by code change
- IMAGE_REGRESSION: Likely caused by image change
- INTERMITTENT: Known flaky test
- INFRA: Infrastructure issue
- NEEDS_INVESTIGATION: Unclear cause
"""

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Optional

from thclient import TreeherderClient


# Treeherder classification IDs
CLASSIFICATION_NAMES = {
    1: "not classified",
    2: "fixed by commit",
    3: "expected fail",
    4: "intermittent",
    5: "infra",
    6: "intermittent needs filing",
    7: "autoclassified intermittent",
}

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
            return None
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return result.stdout.strip()
    except FileNotFoundError:
        print("Error: taskcluster CLI not found. Install with: brew install taskcluster", file=sys.stderr)
        return None


def get_task_info(task_id: str, root_url: str) -> dict | None:
    """Get task definition and status from Taskcluster."""
    definition = run_tc_cmd(["api", "queue", "task", task_id], root_url)
    status = run_tc_cmd(["api", "queue", "status", task_id], root_url)

    if not definition:
        return None

    return {
        "taskId": task_id,
        "definition": definition,
        "status": status or {},
    }


def get_worker_sbom(worker_pool: str, root_url: str) -> dict | None:
    """Get SBOM (Software Bill of Materials) for a worker pool."""
    parts = worker_pool.split("/")
    if len(parts) != 2:
        return None

    provisioner, worker_type = parts
    pool_config = run_tc_cmd(
        ["api", "workerManager", "workerPool", f"{provisioner}/{worker_type}"],
        root_url,
    )

    if not pool_config:
        return None

    config = pool_config.get("config", {})
    launch_configs = config.get("launchConfigs", [])

    sbom_url = None
    image_version = None

    for lc in launch_configs:
        worker_config = lc.get("workerConfig", {})
        gw_config = worker_config.get("genericWorker", {}).get("config", {})
        metadata = gw_config.get("workerTypeMetaData", {})

        if metadata.get("sbom") and not sbom_url:
            sbom_url = metadata.get("sbom")
            version_match = re.search(r"-(\d+\.\d+\.\d+)\.md$", sbom_url)
            if version_match:
                image_version = version_match.group(1)

    return {
        "workerPool": worker_pool,
        "imageVersion": image_version,
        "sbomUrl": sbom_url,
    }


def get_production_pool(alpha_pool: str) -> str:
    """Map alpha pool to production equivalent."""
    alpha_suffixes = ["-alpha", "-staging", "-test", "-beta"]
    for suffix in alpha_suffixes:
        if alpha_pool.endswith(suffix):
            return alpha_pool[: -len(suffix)]
    return alpha_pool


def find_similar_failures_treeherder(
    job_name: str,
    repos: list[str],
    limit: int = 50,
) -> dict:
    """Search for similar failures on Treeherder."""
    client = TreeherderClient()
    results = {"autoland": [], "mozilla-central": []}

    for repo in repos:
        try:
            data = client._get_json(client.PUSH_ENDPOINT, project=repo, count=limit)
            pushes = data.get("results", [])

            for push in pushes:
                push_id = push["id"]
                jobs_data = client._get_json(client.JOBS_ENDPOINT, project=repo, push_id=push_id)
                jobs = jobs_data.get("results", [])

                matching_failures = [
                    j for j in jobs
                    if job_name.lower() in j.get("job_type_name", "").lower()
                    and j.get("result") in ["testfailed", "busted"]
                ]

                for job in matching_failures:
                    results[repo].append({
                        "job_id": job.get("id"),
                        "job_type_name": job.get("job_type_name"),
                        "result": job.get("result"),
                        "failure_classification_id": job.get("failure_classification_id"),
                        "revision": push.get("revision", "")[:12],
                        "treeherder_url": f"https://treeherder.mozilla.org/jobs?repo={repo}&revision={push['revision']}&selectedJobId={job.get('id')}",
                    })
        except Exception as e:
            print(f"Warning: Could not search {repo}: {e}", file=sys.stderr)

    return results


def get_treeherder_classification(task_id: str) -> dict | None:
    """Get classification for a job from Treeherder by task ID."""
    client = TreeherderClient()

    # Search across repos
    for repo in ["autoland", "mozilla-central", "try"]:
        try:
            data = client._get_json(client.JOBS_ENDPOINT, project=repo, task_id=task_id)
            jobs = data.get("results", [])
            if jobs:
                job = jobs[0]
                class_id = job.get("failure_classification_id", 1)
                return {
                    "classification_id": class_id,
                    "classification_name": CLASSIFICATION_NAMES.get(class_id, f"unknown ({class_id})"),
                    "repo": repo,
                }
        except Exception:
            continue

    return None


def determine_verdict(signals: dict) -> tuple[str, str, str]:
    """
    Determine the verdict based on collected signals.

    Returns: (verdict, confidence, rationale)
    """
    is_alpha = signals.get("is_alpha", False)
    version_differs = signals.get("version_differs", False)
    autoland_failures = signals.get("autoland_failures", 0)
    central_failures = signals.get("central_failures", 0)
    classification_id = signals.get("classification_id", 1)

    # Check for known classifications first
    if classification_id == 4 or classification_id == 7:
        return (
            "INTERMITTENT",
            "High",
            "Already classified as intermittent in Treeherder",
        )

    if classification_id == 5:
        return (
            "INFRA",
            "High",
            "Already classified as infrastructure issue in Treeherder",
        )

    if classification_id == 2:
        return (
            "CODE_REGRESSION",
            "High",
            "Classified as fixed by commit - was a real regression",
        )

    # Check for image regression signals
    if is_alpha and version_differs:
        if autoland_failures == 0 and central_failures == 0:
            return (
                "IMAGE_REGRESSION",
                "High",
                "Failed on alpha pool with different image version, no similar failures on production branches",
            )
        elif autoland_failures + central_failures < 3:
            return (
                "IMAGE_REGRESSION",
                "Medium",
                "Failed on alpha pool with different image version, few similar failures on production (may be newly exposed)",
            )

    # Check for code regression signals
    if autoland_failures >= 3 or central_failures >= 3:
        return (
            "CODE_REGRESSION",
            "High",
            f"Multiple similar failures found on production branches (autoland: {autoland_failures}, mozilla-central: {central_failures})",
        )

    if autoland_failures > 0 or central_failures > 0:
        return (
            "CODE_REGRESSION",
            "Medium",
            f"Similar failures found on production branches (autoland: {autoland_failures}, mozilla-central: {central_failures})",
        )

    # No strong signals
    if is_alpha and not version_differs:
        return (
            "NEEDS_INVESTIGATION",
            "Low",
            "Failed on alpha pool but same image version as production - could be code or intermittent",
        )

    return (
        "NEEDS_INVESTIGATION",
        "Low",
        "Insufficient signals to determine cause - manual investigation needed",
    )


def triage(
    task_id: str,
    root_url: str = DEFAULT_TASKCLUSTER_ROOT_URL,
    skip_treeherder: bool = False,
    json_output: bool = False,
) -> int:
    """Perform comprehensive triage on a failing task."""
    task_id = extract_task_id(task_id)

    if not json_output:
        print(f"Triaging task: {task_id}", file=sys.stderr)

    # Step 1: Get task info
    if not json_output:
        print("  [1/5] Getting task info...", file=sys.stderr)
    task_info = get_task_info(task_id, root_url)
    if not task_info:
        print("Error: Could not get task information", file=sys.stderr)
        return 1

    definition = task_info.get("definition", {})
    status = task_info.get("status", {})
    state = status.get("status", {}).get("state", "unknown")

    worker_pool = f"{definition.get('provisionerId', 'unknown')}/{definition.get('workerType', 'unknown')}"
    task_label = definition.get("metadata", {}).get("name", "unknown")

    # Step 2: Check if alpha pool and get image versions
    if not json_output:
        print("  [2/5] Comparing image versions...", file=sys.stderr)

    is_alpha = any(suffix in worker_pool for suffix in ["-alpha", "-staging", "-test", "-beta"])
    failing_sbom = get_worker_sbom(worker_pool, root_url)
    failing_version = failing_sbom.get("imageVersion") if failing_sbom else None

    production_pool = get_production_pool(worker_pool)
    production_version = None
    version_differs = False

    if is_alpha:
        production_sbom = get_worker_sbom(production_pool, root_url)
        production_version = production_sbom.get("imageVersion") if production_sbom else None
        version_differs = failing_version != production_version

    # Step 3: Search for similar failures on Treeherder
    autoland_failures = 0
    central_failures = 0
    similar_failures = {"autoland": [], "mozilla-central": []}

    if not skip_treeherder:
        if not json_output:
            print("  [3/5] Searching for similar failures...", file=sys.stderr)

        # Extract test name from task label for searching
        test_name = task_label.split("/")[-1] if "/" in task_label else task_label
        similar_failures = find_similar_failures_treeherder(
            test_name,
            ["autoland", "mozilla-central"],
            limit=50,
        )
        autoland_failures = len(similar_failures.get("autoland", []))
        central_failures = len(similar_failures.get("mozilla-central", []))
    else:
        if not json_output:
            print("  [3/5] Skipping Treeherder search...", file=sys.stderr)

    # Step 4: Get classification from Treeherder
    if not json_output:
        print("  [4/5] Checking Treeherder classification...", file=sys.stderr)

    classification = get_treeherder_classification(task_id)
    classification_id = classification.get("classification_id", 1) if classification else 1
    classification_name = classification.get("classification_name", "not classified") if classification else "not classified"

    # Step 5: Determine verdict
    if not json_output:
        print("  [5/5] Determining verdict...", file=sys.stderr)

    signals = {
        "is_alpha": is_alpha,
        "version_differs": version_differs,
        "autoland_failures": autoland_failures,
        "central_failures": central_failures,
        "classification_id": classification_id,
    }

    verdict, confidence, rationale = determine_verdict(signals)

    # Build result
    result = {
        "taskId": task_id,
        "taskLabel": task_label,
        "state": state,
        "workerPool": worker_pool,
        "isAlpha": is_alpha,
        "failingImageVersion": failing_version,
        "productionPool": production_pool if is_alpha else None,
        "productionImageVersion": production_version,
        "versionDiffers": version_differs,
        "autolandFailures": autoland_failures,
        "mozillaCentralFailures": central_failures,
        "classificationId": classification_id,
        "classificationName": classification_name,
        "verdict": verdict,
        "confidence": confidence,
        "rationale": rationale,
        "taskclusterUrl": f"{root_url}/tasks/{task_id}",
        "sbomUrl": failing_sbom.get("sbomUrl") if failing_sbom else None,
    }

    if json_output:
        print(json.dumps(result, indent=2))
    else:
        # Print markdown report
        print(f"\n## Triage Report: {task_id}\n")
        print(f"**Test**: {task_label}")
        print(f"**Status**: {state}")
        print()
        print("### Signals")
        print()
        print("| Signal | Value | Implication |")
        print("|--------|-------|-------------|")
        print(f"| Alpha Pool | {'Yes' if is_alpha else 'No'} | {'Using new/staging image' if is_alpha else 'Production pool'} |")

        if is_alpha:
            print(f"| Image Version Differs | {'Yes' if version_differs else 'No'} ({failing_version} vs {production_version}) | {'Image change detected' if version_differs else 'Same image'} |")

        if not skip_treeherder:
            print(f"| Similar Failures on autoland | {autoland_failures} | {'Failing on production' if autoland_failures > 0 else 'Not failing on production'} |")
            print(f"| Similar Failures on mozilla-central | {central_failures} | {'Failing on production' if central_failures > 0 else 'Not failing on production'} |")

        print(f"| Treeherder Classification | {classification_name} | {'Already triaged' if classification_id != 1 else 'No prior triage'} |")
        print()
        print(f"### Verdict: **{verdict}**")
        print()
        print(f"**Confidence**: {confidence}")
        print(f"**Rationale**: {rationale}")
        print()
        print("### Recommended Actions")
        print()

        if verdict == "IMAGE_REGRESSION":
            print("1. Notify image maintainer")
            print("2. Check SBOM for image changes")
            print("3. Consider rolling back image or fixing the issue")
        elif verdict == "CODE_REGRESSION":
            print("1. Identify the regressing commit")
            print("2. Consider backout or fix")
            print("3. Star/classify the failures in Treeherder")
        elif verdict == "INTERMITTENT":
            print("1. No action needed if already filed")
            print("2. Check if failure rate is increasing")
        elif verdict == "INFRA":
            print("1. Check infrastructure status")
            print("2. Report to RelOps if persistent")
        else:
            print("1. Manual investigation needed")
            print("2. Check task logs for more details")
            print("3. Compare with similar tasks")

        print()
        print("### Links")
        print()
        print(f"- **Taskcluster**: {result['taskclusterUrl']}")
        if result["sbomUrl"]:
            print(f"- **SBOM**: {result['sbomUrl']}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Sheriff Triage Tool - Determine likely cause of CI failures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Verdicts:
  CODE_REGRESSION      Likely caused by code change
  IMAGE_REGRESSION     Likely caused by image change
  INTERMITTENT         Known flaky test
  INFRA                Infrastructure issue
  NEEDS_INVESTIGATION  Unclear cause

Examples:
  # Full triage
  %(prog)s Xcac5C8gRqiOT13YsVRX8A

  # With Taskcluster URL
  %(prog)s https://firefox-ci-tc.services.mozilla.com/tasks/Xcac5C8gRqiOT13YsVRX8A

  # JSON output
  %(prog)s Xcac5C8gRqiOT13YsVRX8A --json

  # Skip Treeherder search (faster)
  %(prog)s Xcac5C8gRqiOT13YsVRX8A --skip-treeherder
        """,
    )

    parser.add_argument("task_id", help="Task ID or Taskcluster URL")
    parser.add_argument(
        "--root-url",
        default=DEFAULT_TASKCLUSTER_ROOT_URL,
        help="Taskcluster root URL (default: firefox-ci-tc)",
    )
    parser.add_argument(
        "--skip-treeherder",
        action="store_true",
        help="Skip Treeherder search (faster but less accurate)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args()

    return triage(
        args.task_id,
        root_url=args.root_url,
        skip_treeherder=args.skip_treeherder,
        json_output=args.json,
    )


if __name__ == "__main__":
    sys.exit(main())
