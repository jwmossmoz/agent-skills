#!/usr/bin/env python3
"""
Check Treeherder status for try pushes by landing job ID.

This script checks the status of a Lando landing job and queries Treeherder
for job results once the commit has landed.
"""

import requests
import sys
import json
from typing import Optional, Dict, Any


def check_lando_status(landing_job_id: str) -> Dict[str, Any]:
    """Check Lando landing job status."""
    url = f"https://api.lando.services.mozilla.com/landing_jobs/{landing_job_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def get_push_by_revision(repo: str, revision: str) -> Optional[Dict[str, Any]]:
    """Get push information from Treeherder by revision."""
    url = f"https://treeherder.mozilla.org/api/project/{repo}/push/"
    params = {"revision": revision}
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if data.get("results"):
        return data["results"][0]
    return None


def get_jobs_for_push(repo: str, push_id: int, filter_text: Optional[str] = None) -> list:
    """Get jobs for a specific push."""
    url = f"https://treeherder.mozilla.org/api/project/{repo}/jobs/"
    params = {"push_id": push_id}
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    jobs = data.get("results", [])

    # Filter by job type name if specified
    if filter_text:
        jobs = [j for j in jobs if filter_text in j.get("job_type_name", "")]

    return jobs


def format_job_status(job: Dict[str, Any]) -> str:
    """Format job information for display."""
    name = job.get("job_type_name", "Unknown")
    result = job.get("result", "unknown")
    state = job.get("state", "unknown")

    # Add emoji for result
    emoji = {
        "success": "✅",
        "testfailed": "❌",
        "busted": "💥",
        "retry": "🔄",
        "usercancel": "🚫",
        "running": "🏃",
        "pending": "⏳",
    }.get(result if result != "unknown" else state, "❓")

    return f"{emoji} {name} - {result} ({state})"


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_status.py <landing_job_id> [job_filter] [--repo REPO]")
        print("\nExamples:")
        print("  python check_status.py 173178")
        print("  python check_status.py 173178 marionette-integration")
        print("  python check_status.py 173178 --repo try")
        sys.exit(1)

    landing_job_id = sys.argv[1]
    job_filter = None
    repo = "try"

    # Parse optional arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--repo":
            repo = sys.argv[i + 1]
            i += 2
        else:
            job_filter = sys.argv[i]
            i += 1

    print(f"Checking landing job {landing_job_id}...")

    # Check Lando status
    try:
        lando_data = check_lando_status(landing_job_id)
        status = lando_data.get("status", "UNKNOWN")
        commit_id = lando_data.get("commit_id", "")

        print(f"Landing status: {status}")

        if status == "SUBMITTED":
            print("⏳ Landing job is still in progress. The commit hasn't landed yet.")
            print("Try again in a few moments.")
            sys.exit(0)

        if not commit_id:
            print(f"❌ Landing job status is {status} but no commit_id found.")
            print(f"Full response: {json.dumps(lando_data, indent=2)}")
            sys.exit(1)

        print(f"Commit ID: {commit_id}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error checking Lando status: {e}")
        sys.exit(1)

    # Get push from Treeherder
    print(f"\nQuerying Treeherder for push on {repo}...")
    try:
        push = get_push_by_revision(repo, commit_id)

        if not push:
            print(f"⚠️  Push not found yet on Treeherder. It may take a few moments to appear.")
            sys.exit(0)

        push_id = push.get("id")
        revision = push.get("revision")
        author = push.get("author", "unknown")

        print(f"Push ID: {push_id}")
        print(f"Revision: {revision}")
        print(f"Author: {author}")
        print(f"Treeherder URL: https://treeherder.mozilla.org/jobs?repo={repo}&revision={revision}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error querying Treeherder: {e}")
        sys.exit(1)

    # Get jobs
    print(f"\nFetching jobs{' matching ' + repr(job_filter) if job_filter else ''}...")
    try:
        jobs = get_jobs_for_push(repo, push_id, job_filter)

        if not jobs:
            print(f"⚠️  No jobs found yet. Jobs may still be scheduling.")
            sys.exit(0)

        print(f"\nFound {len(jobs)} job(s):\n")

        # Group by result
        by_result = {}
        for job in jobs:
            result = job.get("result", "unknown")
            if result not in by_result:
                by_result[result] = []
            by_result[result].append(job)

        # Print summary
        for result in sorted(by_result.keys()):
            print(f"{result.upper()}: {len(by_result[result])}")

        print("\nDetailed results:\n")
        for job in jobs:
            print(format_job_status(job))

        # Exit code based on results
        failed = len([j for j in jobs if j.get("result") in ["testfailed", "busted"]])
        if failed > 0:
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching jobs: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
