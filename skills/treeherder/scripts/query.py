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

API Documentation: https://treeherder.readthedocs.io/accessing_data.html
"""

import argparse
import json
import sys
from typing import Any

import requests
from thclient import TreeherderClient

# User-Agent is required by Treeherder API
USER_AGENT = "Mozilla-Agent-Skills/1.0"
BASE_URL = "https://treeherder.mozilla.org"


def get_session() -> requests.Session:
    """Create a session with required headers."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def format_job_status(job: dict) -> str:
    """Format job information for display."""
    name = job.get("job_type_name", "Unknown")
    result = job.get("result", "unknown")
    state = job.get("state", "unknown")
    platform = job.get("platform", "")
    task_id = job.get("task_id", "")

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

    task_link = f" [task:{task_id}]" if task_id else ""
    return f"{emoji} {name} - {result} ({state}) [{platform}]{task_link}"


def cmd_jobs(args: argparse.Namespace) -> int:
    """Query jobs for a push."""
    client = TreeherderClient()

    # Get push if querying by revision
    if args.revision:
        print(f"Querying push for revision {args.revision}...")
        data = client._get_json(
            client.PUSH_ENDPOINT, project=args.repo, revision=args.revision
        )
        if not data.get("results"):
            print("❌ No push found for this revision")
            return 1
        push = data["results"][0]
        push_id = push["id"]
        print(f"Found push ID: {push_id}")
        print(f"Author: {push.get('author', 'unknown')}")
        print(
            f"Treeherder: https://treeherder.mozilla.org/jobs?repo={args.repo}&revision={args.revision}\n"
        )
    else:
        push_id = args.push_id

    # Build query params
    params: dict[str, Any] = {"push_id": push_id}
    if args.result:
        params["result"] = args.result
    if args.tier:
        params["tier"] = args.tier
    if args.count:
        params["count"] = args.count

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
            print(format_job_status(job))

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

    print(f"Log URLs for job:\n")
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


def main():
    parser = argparse.ArgumentParser(
        description="Query Treeherder API for CI job results and data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  jobs           Query jobs for a specific push
  pushes         List recent pushes for a repository
  repos          List available repositories
  classifications List failure classification types
  logs           Get log URLs for a job
  perf-frameworks List performance testing frameworks
  perf-alerts    Query performance alert summaries
  job-details    Get detailed job information

Examples:
  # Query jobs by revision
  %(prog)s jobs --revision abc123def456 --repo try

  # Query jobs by push ID with filters
  %(prog)s jobs --push-id 12345 --repo autoland --result testfailed

  # List recent pushes
  %(prog)s pushes --repo autoland --count 5

  # Get log URLs for a job
  %(prog)s logs --job-id 545634438 --repo autoland

  # Query performance alerts
  %(prog)s perf-alerts --framework 1 --limit 5

  # List repositories
  %(prog)s repos
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
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
