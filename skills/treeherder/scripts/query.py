#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["treeherder-client", "requests"]
# ///
"""
Query Treeherder for job results, pushes, and other CI data.

This script provides comprehensive access to the Treeherder REST API,
wrapping the treeherder-client library with additional direct API calls
for endpoints not covered by the library.

Designed to support sheriff workflows including:
- Checking push health status
- Finding unclassified failures
- Getting bug suggestions for failed jobs
- Viewing error lines from job logs
- Checking job classification history

API Documentation: https://treeherder.readthedocs.io/accessing_data.html
Sheriff Guide: https://wiki.mozilla.org/Sheriffing/How_To/Treeherder
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Any

import requests
from thclient import TreeherderClient

# User-Agent is required by Treeherder API
USER_AGENT = "Mozilla-Agent-Skills/1.0"
BASE_URL = "https://treeherder.mozilla.org"

# Failure classification IDs
CLASSIFICATION_NOT_CLASSIFIED = 1
CLASSIFICATION_FIXED_BY_COMMIT = 2
CLASSIFICATION_EXPECTED_FAIL = 3
CLASSIFICATION_INTERMITTENT = 4
CLASSIFICATION_INFRA = 5
CLASSIFICATION_NEW_FAILURE = 6
CLASSIFICATION_AUTOCLASSIFIED = 7
CLASSIFICATION_INTERMITTENT_NEEDS_BUG = 8


def get_session() -> requests.Session:
    """Create a session with required headers."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def format_job_status(job: dict, verbose: bool = False) -> str:
    """Format job information for display."""
    name = job.get("job_type_name", "Unknown")
    result = job.get("result", "unknown")
    state = job.get("state", "unknown")
    platform = job.get("platform", "")
    task_id = job.get("task_id", "")
    job_id = job.get("id", "")
    classification_id = job.get("failure_classification_id", 1)

    emoji = {
        "success": "✅",
        "testfailed": "❌",
        "busted": "💥",
        "retry": "🔄",
        "usercancel": "🚫",
        "running": "🏃",
        "pending": "⏳",
        "unknown": "❓",
    }.get(result if result != "unknown" else state, "❓")

    # Classification indicator
    class_indicator = ""
    if classification_id == CLASSIFICATION_NOT_CLASSIFIED:
        class_indicator = " [UNCLASSIFIED]"
    elif classification_id == CLASSIFICATION_INTERMITTENT:
        class_indicator = " [intermittent]"
    elif classification_id == CLASSIFICATION_INFRA:
        class_indicator = " [infra]"

    task_link = f" [task:{task_id}]" if task_id and verbose else ""
    job_link = f" (job:{job_id})" if job_id and verbose else ""
    return f"{emoji} {name} - {result} ({state}) [{platform}]{class_indicator}{task_link}{job_link}"


def get_push_id_for_revision(client: TreeherderClient, repo: str, revision: str) -> int | None:
    """Get push ID for a revision, with helpful output."""
    print(f"Querying push for revision {revision}...")
    data = client._get_json(client.PUSH_ENDPOINT, project=repo, revision=revision)
    if not data.get("results"):
        print("❌ No push found for this revision")
        return None
    push = data["results"][0]
    push_id = push["id"]
    print(f"Found push ID: {push_id}")
    print(f"Author: {push.get('author', 'unknown')}")
    print(f"Treeherder: https://treeherder.mozilla.org/jobs?repo={repo}&revision={revision}\n")
    return push_id


def cmd_jobs(args: argparse.Namespace) -> int:
    """Query jobs for a push."""
    client = TreeherderClient()

    # Get push if querying by revision
    if args.revision:
        push_id = get_push_id_for_revision(client, args.repo, args.revision)
        if push_id is None:
            return 1
    else:
        push_id = args.push_id

    if not push_id:
        print("Error: Either --revision or --push-id must be specified")
        return 1

    # Build query params
    params: dict[str, Any] = {"push_id": push_id}
    if args.result:
        params["result"] = args.result
    if args.tier:
        params["tier"] = args.tier
    if args.count:
        params["count"] = args.count
    if args.unclassified:
        params["failure_classification_id"] = CLASSIFICATION_NOT_CLASSIFIED

    # Get jobs
    print(f"Fetching jobs for push {push_id}...")
    data = client._get_json(client.JOBS_ENDPOINT, project=args.repo, **params)
    jobs = data.get("results", [])

    # Apply filters
    if args.filter:
        jobs = [j for j in jobs if args.filter.lower() in j.get("job_type_name", "").lower()]
        print(f"Filter (name): '{args.filter}'")
    if args.platform:
        jobs = [j for j in jobs if args.platform.lower() in j.get("platform", "").lower()]
        print(f"Filter (platform): '{args.platform}'")
    if args.unclassified:
        print("Filter: unclassified failures only")

    if not jobs:
        print("⚠️  No jobs found")
        return 0

    print(f"\nFound {len(jobs)} job(s):\n")

    # Summary by result
    by_result: dict[str, list] = {}
    for job in jobs:
        result = job.get("result", "unknown")
        by_result.setdefault(result, []).append(job)

    for result in sorted(by_result.keys()):
        print(f"{result.upper()}: {len(by_result[result])}")

    if not args.summary_only:
        print("\nDetailed results:\n")
        for job in jobs:
            print(format_job_status(job, verbose=args.verbose))

    # Exit code based on failures
    failed = sum(1 for j in jobs if j.get("result") in ["testfailed", "busted"])
    return 1 if failed > 0 else 0


def cmd_pushes(args: argparse.Namespace) -> int:
    """List recent pushes."""
    client = TreeherderClient()

    params: dict[str, Any] = {}
    if args.count:
        params["count"] = args.count
    if args.author:
        params["author"] = args.author

    pushes = client.get_pushes(args.repo, **params)

    if not pushes:
        print("No pushes found")
        return 0

    print(f"Found {len(pushes)} push(es) for {args.repo}:\n")
    for push in pushes:
        rev = push.get("revision", "unknown")[:12]
        author = push.get("author", "unknown")
        push_id = push.get("id")
        revisions = push.get("revisions", [])
        msg = revisions[0].get("comments", "").split("\n")[0][:60] if revisions else ""

        print(f"  {push_id}: {rev} by {author}")
        if msg:
            print(f"         {msg}")
        print()

    return 0


def cmd_repos(args: argparse.Namespace) -> int:
    """List available repositories."""
    client = TreeherderClient()
    repos = client.get_repositories()

    if args.json:
        print(json.dumps(repos, indent=2))
        return 0

    print("Available Treeherder repositories:\n")
    for repo in sorted(repos, key=lambda r: r.get("name", "")):
        name = repo.get("name", "unknown")
        url = repo.get("url", "")
        active = "active" if repo.get("active_status") == "active" else "inactive"
        print(f"  {name:<30} ({active}) {url}")

    return 0


def cmd_classifications(args: argparse.Namespace) -> int:
    """List failure classification types."""
    client = TreeherderClient()
    classifications = client.get_failure_classifications()

    if args.json:
        print(json.dumps(classifications, indent=2))
        return 0

    print("Failure classifications:\n")
    for c in classifications:
        print(f"  {c['id']}: {c['name']}")

    return 0


def cmd_logs(args: argparse.Namespace) -> int:
    """Get log URLs for a job."""
    session = get_session()

    # Can query by job_id or job_guid
    params = {}
    if args.job_id:
        params["job_id"] = args.job_id
    elif args.job_guid:
        params["job_guid"] = args.job_guid
    else:
        print("Error: Either --job-id or --job-guid required")
        return 1

    url = f"{BASE_URL}/api/project/{args.repo}/job-log-url/"
    resp = session.get(url, params=params)
    resp.raise_for_status()
    logs = resp.json()

    if args.json:
        print(json.dumps(logs, indent=2))
        return 0

    if not logs:
        print("No logs found for this job")
        return 0

    print("Log URLs for job:\n")
    for log in logs:
        name = log.get("name", "unknown")
        log_url = log.get("url", "")
        status = log.get("parse_status", "")
        print(f"  {name} ({status}):")
        print(f"    {log_url}\n")

    return 0


def cmd_perf_frameworks(args: argparse.Namespace) -> int:
    """List performance testing frameworks."""
    session = get_session()
    url = f"{BASE_URL}/api/performance/framework/"
    resp = session.get(url)
    resp.raise_for_status()
    frameworks = resp.json()

    if args.json:
        print(json.dumps(frameworks, indent=2))
        return 0

    print("Performance frameworks:\n")
    for f in frameworks:
        print(f"  {f['id']}: {f['name']}")

    return 0


def cmd_perf_alerts(args: argparse.Namespace) -> int:
    """Query performance alerts."""
    session = get_session()

    params: dict[str, Any] = {"limit": args.limit or 10}
    if args.framework:
        params["framework"] = args.framework
    if args.repo:
        params["repository"] = args.repo
    if args.status:
        # 0=untriaged, 1=downstream, 2=reassigned, 3=invalid, 4=acknowledged, 5=investigating, 6=wontfix, 7=fixed, 8=backedout
        status_map = {
            "untriaged": 0,
            "downstream": 1,
            "reassigned": 2,
            "invalid": 3,
            "acknowledged": 4,
            "investigating": 5,
            "wontfix": 6,
            "fixed": 7,
            "backedout": 8,
        }
        params["status"] = status_map.get(args.status.lower(), args.status)

    url = f"{BASE_URL}/api/performance/alertsummary/"
    resp = session.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    results = data.get("results", [])
    print(f"Found {data.get('count', len(results))} alert summaries (showing {len(results)}):\n")

    for summary in results:
        summary_id = summary.get("id")
        repo = summary.get("repository", "unknown")
        revision = summary.get("original_revision", "")[:12]
        created = summary.get("created", "")[:10]
        alerts = summary.get("alerts", [])

        regressions = sum(1 for a in alerts if a.get("is_regression"))
        improvements = len(alerts) - regressions

        print(f"  #{summary_id} ({repo}) {revision} - {created}")
        print(f"    Alerts: {len(alerts)} ({regressions} regressions, {improvements} improvements)")

        # Show first few alerts
        for alert in alerts[:3]:
            sig = alert.get("series_signature", {})
            suite = sig.get("suite", "")
            test = sig.get("test", "")
            pct = alert.get("amount_pct", 0)
            direction = "↑" if alert.get("is_regression") else "↓"
            print(f"      {direction} {suite}/{test}: {pct:.1f}%")
        if len(alerts) > 3:
            print(f"      ... and {len(alerts) - 3} more")
        print()

    return 0


def cmd_job_details(args: argparse.Namespace) -> int:
    """Get detailed information about a specific job."""
    client = TreeherderClient()

    if args.job_guid:
        details = client.get_job_details(job_guid=args.job_guid)
    else:
        print("Error: --job-guid required")
        return 1

    if args.json:
        print(json.dumps(details, indent=2))
        return 0

    if not details:
        print("No job details found")
        return 0

    print(f"Job details for {args.job_guid}:\n")
    for detail in details:
        title = detail.get("title", "")
        value = detail.get("value", "")
        url = detail.get("url", "")
        print(f"  {title}: {value}")
        if url:
            print(f"    URL: {url}")

    return 0


# =============================================================================
# Sheriff-focused commands
# =============================================================================


def cmd_push_health(args: argparse.Namespace) -> int:
    """Get push health summary (pass/fail status for tests, builds, linting)."""
    session = get_session()
    client = TreeherderClient()

    # Get push ID if revision provided
    if args.revision:
        push_id = get_push_id_for_revision(client, args.repo, args.revision)
        if push_id is None:
            return 1
        revision = args.revision
    else:
        # Need to get revision from push_id
        data = client._get_json(client.PUSH_ENDPOINT, project=args.repo, id=args.push_id)
        if not data.get("results"):
            print(f"❌ No push found with ID {args.push_id}")
            return 1
        revision = data["results"][0]["revision"]
        push_id = args.push_id
        print(f"Push ID: {push_id}, Revision: {revision[:12]}")

    # Get push health
    url = f"{BASE_URL}/api/project/{args.repo}/push/health/"
    resp = session.get(url, params={"revision": revision})
    resp.raise_for_status()
    health = resp.json()

    if args.json:
        print(json.dumps(health, indent=2))
        return 0

    # Display health summary
    result_emoji = {"pass": "✅", "fail": "❌", "indeterminate": "⚠️", "none": "➖"}

    print(f"\nPush Health for {revision[:12]}:\n")
    print(f"  Overall: {result_emoji.get(health.get('result', 'none'), '❓')} {health.get('result', 'unknown').upper()}\n")

    metrics = health.get("metrics", {})

    # Commit history
    commit_history = metrics.get("commitHistory", {})
    if commit_history:
        ch_result = commit_history.get("result", "none")
        print(f"  Commit History: {result_emoji.get(ch_result, '❓')} {ch_result}")
        details = commit_history.get("details", {})
        if details.get("jobCounts"):
            counts = details["jobCounts"]
            print(f"    Parent push: {counts.get('success', 0)} passed, {counts.get('testfailed', 0)} failed")

    # Tests
    tests = metrics.get("tests", {})
    if tests:
        t_result = tests.get("result", "none")
        print(f"  Tests: {result_emoji.get(t_result, '❓')} {t_result}")
        details = tests.get("details", {})
        if details.get("needInvestigation"):
            print(f"    Need investigation: {len(details['needInvestigation'])}")
            for item in details["needInvestigation"][:5]:
                print(f"      - {item.get('testName', 'unknown')}")

    # Builds
    builds = metrics.get("builds", {})
    if builds:
        b_result = builds.get("result", "none")
        print(f"  Builds: {result_emoji.get(b_result, '❓')} {b_result}")

    # Linting
    linting = metrics.get("linting", {})
    if linting:
        l_result = linting.get("result", "none")
        print(f"  Linting: {result_emoji.get(l_result, '❓')} {l_result}")

    # Jobs summary
    jobs = health.get("jobs", {})
    if jobs:
        print(f"\n  Job counts:")
        for status, count in sorted(jobs.items()):
            if count > 0:
                print(f"    {status}: {count}")

    return 0


def cmd_push_health_summary(args: argparse.Namespace) -> int:
    """Get quick push health summary for multiple pushes."""
    session = get_session()
    client = TreeherderClient()

    # Get recent pushes
    pushes = client.get_pushes(args.repo, count=args.count)

    if not pushes:
        print("No pushes found")
        return 0

    if args.json:
        # Fetch health for all and return JSON
        results = []
        for push in pushes:
            url = f"{BASE_URL}/api/project/{args.repo}/push/health_summary/"
            resp = session.get(url, params={"revision": push["revision"]})
            if resp.ok:
                results.extend(resp.json())
        print(json.dumps(results, indent=2))
        return 0

    print(f"Push health summary for {args.repo} (last {len(pushes)}):\n")

    result_emoji = {"pass": "✅", "fail": "❌", "indeterminate": "⚠️", "none": "➖"}

    for push in pushes:
        revision = push["revision"]
        url = f"{BASE_URL}/api/project/{args.repo}/push/health_summary/"
        resp = session.get(url, params={"revision": revision})

        if not resp.ok:
            print(f"  {revision[:12]}: ❓ (failed to fetch)")
            continue

        summaries = resp.json()
        if not summaries:
            print(f"  {revision[:12]}: ➖ (no data)")
            continue

        summary = summaries[0]
        status = summary.get("status", {})
        metrics = summary.get("metrics", {})

        tests_result = metrics.get("tests", {}).get("result", "none")
        builds_result = metrics.get("builds", {}).get("result", "none")
        lint_result = metrics.get("linting", {}).get("result", "none")

        need_investigation = summary.get("needInvestigation", 0)
        test_failures = summary.get("testFailureCount", 0)
        build_failures = summary.get("buildFailureCount", 0)

        author = push.get("author", "unknown")

        # Status line
        status_icons = f"T:{result_emoji.get(tests_result, '❓')} B:{result_emoji.get(builds_result, '❓')} L:{result_emoji.get(lint_result, '❓')}"

        print(f"  {revision[:12]} {status_icons}  ({author})")
        if need_investigation > 0 or test_failures > 0 or build_failures > 0:
            print(f"    Failures: {test_failures} test, {build_failures} build | Need investigation: {need_investigation}")

    return 0


def cmd_bug_suggestions(args: argparse.Namespace) -> int:
    """Get bug suggestions for a failed job (helps with classification)."""
    session = get_session()

    if not args.job_id:
        print("Error: --job-id required")
        return 1

    url = f"{BASE_URL}/api/project/{args.repo}/jobs/{args.job_id}/bug_suggestions/"
    resp = session.get(url)
    resp.raise_for_status()
    suggestions = resp.json()

    if args.json:
        print(json.dumps(suggestions, indent=2))
        return 0

    if not suggestions:
        print("No bug suggestions found for this job")
        return 0

    print(f"Bug suggestions for job {args.job_id}:\n")

    for item in suggestions:
        search = item.get("search", "")[:80]
        line_num = item.get("line_number", "?")
        is_new = item.get("failure_new_in_rev", False)
        bugs = item.get("bugs", {})

        new_marker = " [NEW IN REV]" if is_new else ""
        print(f"  Line {line_num}{new_marker}:")
        print(f"    {search}...")

        open_bugs = bugs.get("open_recent", [])
        other_bugs = bugs.get("all_others", [])

        if open_bugs:
            print(f"    Open bugs ({len(open_bugs)}):")
            for bug in open_bugs[:3]:
                bug_id = bug.get("id", "?")
                summary = bug.get("summary", "")[:60]
                if bug_id:
                    print(f"      Bug {bug_id}: {summary}")
                else:
                    print(f"      {summary}")

        if other_bugs and args.verbose:
            print(f"    Other bugs ({len(other_bugs)}):")
            for bug in other_bugs[:2]:
                bug_id = bug.get("id", "?")
                summary = bug.get("summary", "")[:60]
                print(f"      Bug {bug_id}: {summary}")

        print()

    return 0


def cmd_errors(args: argparse.Namespace) -> int:
    """Get parsed error lines from a job's log (text_log_errors)."""
    session = get_session()

    if not args.job_id:
        print("Error: --job-id required")
        return 1

    url = f"{BASE_URL}/api/project/{args.repo}/jobs/{args.job_id}/text_log_errors/"
    resp = session.get(url)
    resp.raise_for_status()
    errors = resp.json()

    if args.json:
        print(json.dumps(errors, indent=2))
        return 0

    if not errors:
        print("No errors found in job log")
        return 0

    print(f"Error lines for job {args.job_id}:\n")

    for error in errors:
        line = error.get("line", "")
        line_num = error.get("line_number", "?")
        is_new = error.get("new_failure", False)

        new_marker = " ← NEW FAILURE" if is_new else ""
        print(f"  [{line_num}]{new_marker}")
        # Truncate long lines
        if len(line) > 120:
            print(f"    {line[:120]}...")
        else:
            print(f"    {line}")
        print()

    # Summary
    new_failures = sum(1 for e in errors if e.get("new_failure"))
    if new_failures > 0:
        print(f"⚠️  {new_failures} new failure(s) detected in this revision")

    return 0


def cmd_notes(args: argparse.Namespace) -> int:
    """Get classification notes/annotations for a job."""
    session = get_session()

    if not args.job_id:
        print("Error: --job-id required")
        return 1

    url = f"{BASE_URL}/api/project/{args.repo}/note/"
    resp = session.get(url, params={"job_id": args.job_id})
    resp.raise_for_status()
    notes = resp.json()

    if args.json:
        print(json.dumps(notes, indent=2))
        return 0

    if not notes:
        print(f"No classification notes for job {args.job_id}")
        return 0

    # Get classification names
    client = TreeherderClient()
    classifications = {c["id"]: c["name"] for c in client.get_failure_classifications()}

    print(f"Classification notes for job {args.job_id}:\n")

    for note in notes:
        who = note.get("who", "unknown")
        created = note.get("created", "")[:19]
        class_id = note.get("failure_classification_id", 1)
        class_name = classifications.get(class_id, f"unknown ({class_id})")
        text = note.get("text", "")

        print(f"  {created} by {who}")
        print(f"    Classification: {class_name}")
        if text:
            print(f"    Note: {text}")
        print()

    return 0


def cmd_platforms(args: argparse.Namespace) -> int:
    """List available machine platforms."""
    session = get_session()

    url = f"{BASE_URL}/api/machineplatforms/"
    resp = session.get(url)
    resp.raise_for_status()
    platforms = resp.json()

    if args.json:
        print(json.dumps(platforms, indent=2))
        return 0

    print("Available machine platforms:\n")

    # Group by OS
    by_os: dict[str, list] = {}
    for p in platforms:
        os_name = p.get("os_name", "unknown")
        by_os.setdefault(os_name, []).append(p)

    for os_name in sorted(by_os.keys()):
        print(f"  {os_name}:")
        for p in sorted(by_os[os_name], key=lambda x: x.get("platform", "")):
            platform = p.get("platform", "unknown")
            arch = p.get("architecture", "")
            print(f"    {platform} ({arch})")
        print()

    return 0


def cmd_unclassified(args: argparse.Namespace) -> int:
    """Find unclassified failures across recent pushes (sheriff workflow)."""
    session = get_session()
    client = TreeherderClient()

    # Get recent pushes
    pushes = client.get_pushes(args.repo, count=args.push_count)

    if not pushes:
        print("No pushes found")
        return 0

    print(f"Scanning {len(pushes)} recent pushes for unclassified failures...\n")

    total_unclassified = 0
    results_by_push: list[tuple[dict, list]] = []

    for push in pushes:
        push_id = push["id"]
        revision = push["revision"]

        # Get unclassified failed jobs
        params = {
            "push_id": push_id,
            "failure_classification_id": CLASSIFICATION_NOT_CLASSIFIED,
        }
        data = client._get_json(client.JOBS_ENDPOINT, project=args.repo, **params)
        jobs = data.get("results", [])

        # Filter to only actual failures
        failed_jobs = [j for j in jobs if j.get("result") in ["testfailed", "busted"]]

        if failed_jobs:
            results_by_push.append((push, failed_jobs))
            total_unclassified += len(failed_jobs)

    if args.json:
        output = []
        for push, jobs in results_by_push:
            output.append({
                "push_id": push["id"],
                "revision": push["revision"],
                "author": push.get("author"),
                "unclassified_failures": len(jobs),
                "jobs": jobs if args.verbose else [{"id": j["id"], "job_type_name": j["job_type_name"]} for j in jobs],
            })
        print(json.dumps(output, indent=2))
        return 0

    if total_unclassified == 0:
        print("✅ No unclassified failures found!")
        return 0

    print(f"Found {total_unclassified} unclassified failure(s):\n")

    for push, jobs in results_by_push:
        revision = push["revision"][:12]
        author = push.get("author", "unknown")
        push_id = push["id"]

        print(f"  Push {push_id} ({revision}) by {author}:")
        print(f"    Treeherder: https://treeherder.mozilla.org/jobs?repo={args.repo}&revision={push['revision']}")

        for job in jobs[:5]:  # Limit display
            name = job.get("job_type_name", "Unknown")
            result = job.get("result", "unknown")
            platform = job.get("platform", "")
            job_id = job.get("id")
            print(f"    ❌ {name} [{platform}] (job:{job_id})")

        if len(jobs) > 5:
            print(f"    ... and {len(jobs) - 5} more")
        print()

    return 1 if total_unclassified > 0 else 0


def main():
    parser = argparse.ArgumentParser(
        description="Query Treeherder API for CI job results and data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  jobs              Query jobs for a specific push
  pushes            List recent pushes for a repository
  repos             List available repositories
  classifications   List failure classification types
  logs              Get log URLs for a job
  perf-frameworks   List performance testing frameworks
  perf-alerts       Query performance alert summaries
  job-details       Get detailed job information

Sheriff Commands:
  push-health       Get detailed push health (tests/builds/linting status)
  health-summary    Quick health overview for recent pushes
  bug-suggestions   Get suggested bugs for a failed job
  errors            Get parsed error lines from a job log
  notes             Get classification history for a job
  platforms         List available machine platforms
  unclassified      Find unclassified failures across recent pushes

Examples:
  # Query jobs by revision
  %(prog)s jobs --revision abc123def456 --repo try

  # Find unclassified failures (sheriff workflow)
  %(prog)s jobs --revision abc123 --repo autoland --unclassified

  # Get push health status
  %(prog)s push-health --revision abc123 --repo autoland

  # Get bug suggestions for a failed job
  %(prog)s bug-suggestions --job-id 545634438 --repo autoland

  # Get error lines from a job
  %(prog)s errors --job-id 545634438 --repo autoland

  # Scan for unclassified failures
  %(prog)s unclassified --repo autoland --push-count 10
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Jobs command
    jobs_parser = subparsers.add_parser("jobs", help="Query jobs for a push")
    jobs_parser.add_argument("--revision", help="Commit revision to query")
    jobs_parser.add_argument("--push-id", type=int, help="Push ID to query")
    jobs_parser.add_argument("--repo", default="try", help="Repository name (default: try)")
    jobs_parser.add_argument("--filter", help="Filter jobs by name substring")
    jobs_parser.add_argument("--platform", help="Filter jobs by platform substring")
    jobs_parser.add_argument(
        "--result",
        choices=["success", "testfailed", "busted", "retry", "usercancel", "running", "pending"],
        help="Filter by result status",
    )
    jobs_parser.add_argument("--tier", type=int, choices=[1, 2, 3], help="Filter by tier")
    jobs_parser.add_argument("--count", type=int, help="Maximum number of jobs to return")
    jobs_parser.add_argument(
        "--summary-only", action="store_true", help="Only show summary, not individual jobs"
    )
    jobs_parser.add_argument(
        "--unclassified", action="store_true", help="Only show unclassified failures"
    )
    jobs_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show additional details (task IDs, job IDs)"
    )

    # Pushes command
    pushes_parser = subparsers.add_parser("pushes", help="List recent pushes")
    pushes_parser.add_argument("--repo", default="autoland", help="Repository name (default: autoland)")
    pushes_parser.add_argument("--count", type=int, default=10, help="Number of pushes (default: 10)")
    pushes_parser.add_argument("--author", help="Filter by author email")

    # Repos command
    repos_parser = subparsers.add_parser("repos", help="List available repositories")
    repos_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Classifications command
    class_parser = subparsers.add_parser("classifications", help="List failure classification types")
    class_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Logs command
    logs_parser = subparsers.add_parser("logs", help="Get log URLs for a job")
    logs_parser.add_argument("--job-id", type=int, help="Job ID")
    logs_parser.add_argument("--job-guid", help="Job GUID")
    logs_parser.add_argument("--repo", default="autoland", help="Repository name (default: autoland)")
    logs_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Performance frameworks command
    perf_fw_parser = subparsers.add_parser("perf-frameworks", help="List performance frameworks")
    perf_fw_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Performance alerts command
    perf_alerts_parser = subparsers.add_parser("perf-alerts", help="Query performance alerts")
    perf_alerts_parser.add_argument("--framework", type=int, help="Framework ID (1=talos, 10=raptor, 13=browsertime)")
    perf_alerts_parser.add_argument("--repo", help="Filter by repository")
    perf_alerts_parser.add_argument(
        "--status",
        choices=["untriaged", "downstream", "reassigned", "invalid", "acknowledged", "investigating", "wontfix", "fixed", "backedout"],
        help="Filter by alert status",
    )
    perf_alerts_parser.add_argument("--limit", type=int, default=10, help="Number of results (default: 10)")
    perf_alerts_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Job details command
    details_parser = subparsers.add_parser("job-details", help="Get detailed job information")
    details_parser.add_argument("--job-guid", required=True, help="Job GUID")
    details_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # ==========================================================================
    # Sheriff-focused commands
    # ==========================================================================

    # Push health command
    health_parser = subparsers.add_parser("push-health", help="Get push health status")
    health_parser.add_argument("--revision", help="Commit revision to query")
    health_parser.add_argument("--push-id", type=int, help="Push ID to query")
    health_parser.add_argument("--repo", default="autoland", help="Repository name (default: autoland)")
    health_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Health summary command
    health_summary_parser = subparsers.add_parser("health-summary", help="Quick health overview for recent pushes")
    health_summary_parser.add_argument("--repo", default="autoland", help="Repository name (default: autoland)")
    health_summary_parser.add_argument("--count", type=int, default=10, help="Number of pushes (default: 10)")
    health_summary_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Bug suggestions command
    bug_parser = subparsers.add_parser("bug-suggestions", help="Get bug suggestions for a failed job")
    bug_parser.add_argument("--job-id", type=int, required=True, help="Job ID")
    bug_parser.add_argument("--repo", default="autoland", help="Repository name (default: autoland)")
    bug_parser.add_argument("--verbose", "-v", action="store_true", help="Show all bug matches")
    bug_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Errors command
    errors_parser = subparsers.add_parser("errors", help="Get parsed error lines from a job log")
    errors_parser.add_argument("--job-id", type=int, required=True, help="Job ID")
    errors_parser.add_argument("--repo", default="autoland", help="Repository name (default: autoland)")
    errors_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Notes command
    notes_parser = subparsers.add_parser("notes", help="Get classification history for a job")
    notes_parser.add_argument("--job-id", type=int, required=True, help="Job ID")
    notes_parser.add_argument("--repo", default="autoland", help="Repository name (default: autoland)")
    notes_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Platforms command
    platforms_parser = subparsers.add_parser("platforms", help="List available machine platforms")
    platforms_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Unclassified command
    unclass_parser = subparsers.add_parser("unclassified", help="Find unclassified failures across recent pushes")
    unclass_parser.add_argument("--repo", default="autoland", help="Repository name (default: autoland)")
    unclass_parser.add_argument("--push-count", type=int, default=10, help="Number of pushes to scan (default: 10)")
    unclass_parser.add_argument("--verbose", "-v", action="store_true", help="Include full job details")
    unclass_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Legacy support: if no command given but --revision/--push-id provided, assume 'jobs'
    # Check before parsing if first arg looks like a legacy flag
    if len(sys.argv) > 1 and sys.argv[1].startswith("--"):
        # Legacy mode: insert 'jobs' command
        args = parser.parse_args(["jobs"] + sys.argv[1:])
    else:
        args = parser.parse_args()
        if not args.command:
            parser.print_help()
            return 0

    # Dispatch to command handler
    commands = {
        "jobs": cmd_jobs,
        "pushes": cmd_pushes,
        "repos": cmd_repos,
        "classifications": cmd_classifications,
        "logs": cmd_logs,
        "perf-frameworks": cmd_perf_frameworks,
        "perf-alerts": cmd_perf_alerts,
        "job-details": cmd_job_details,
        # Sheriff commands
        "push-health": cmd_push_health,
        "health-summary": cmd_push_health_summary,
        "bug-suggestions": cmd_bug_suggestions,
        "errors": cmd_errors,
        "notes": cmd_notes,
        "platforms": cmd_platforms,
        "unclassified": cmd_unclassified,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
