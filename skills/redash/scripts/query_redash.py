#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""
Wrapper around Mozilla's Redash API (sql.telemetry.mozilla.org).

Handles authentication, job polling, and result retrieval for BigQuery
telemetry data via Redash.

Requires REDASH_API_KEY environment variable.

Usage:
    export REDASH_API_KEY="your-api-key"
    uv run query_redash.py --sql "SELECT * FROM telemetry.main LIMIT 10"
    uv run query_redash.py --query-id 65967
    uv run query_redash.py --sql "SELECT 1" --output ~/moz_artifacts/data.json
"""

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

BASE_URL = "https://sql.telemetry.mozilla.org"
DATA_SOURCE_ID = 63  # Telemetry (BigQuery)


def get_api_key() -> str:
    """Retrieve API key from REDASH_API_KEY environment variable."""
    api_key = os.environ.get("REDASH_API_KEY")
    if not api_key:
        print("Error: REDASH_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    return api_key


def run_query(api_key: str, sql: str, max_wait: int = 300) -> dict:
    """
    Execute a SQL query against Redash and wait for results.

    Args:
        api_key: Redash API key
        sql: SQL query to execute
        max_wait: Maximum seconds to wait for query completion

    Returns:
        Query result data
    """
    data = json.dumps({
        "data_source_id": DATA_SOURCE_ID,
        "query": sql,
        "max_age": 0,
    }).encode()

    req = urllib.request.Request(
        f"{BASE_URL}/api/query_results",
        data=data,
        headers={
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode())

    job_id = result.get("job", {}).get("id")
    if not job_id:
        raise RuntimeError(f"No job ID returned: {result}")

    # Poll for completion
    start_time = time.time()
    while time.time() - start_time < max_wait:
        req = urllib.request.Request(
            f"{BASE_URL}/api/jobs/{job_id}",
            headers={"Authorization": f"Key {api_key}"},
        )

        with urllib.request.urlopen(req) as resp:
            job_result = json.loads(resp.read().decode())

        status = job_result.get("job", {}).get("status")

        if status == 3:  # Completed
            query_result_id = job_result.get("job", {}).get("query_result_id")
            req = urllib.request.Request(
                f"{BASE_URL}/api/query_results/{query_result_id}",
                headers={"Authorization": f"Key {api_key}"},
            )
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode())

        elif status == 4:  # Failed
            error = job_result.get("job", {}).get("error", "Unknown error")
            raise RuntimeError(f"Query failed: {error}")

        time.sleep(2)

    raise TimeoutError(f"Query did not complete within {max_wait} seconds")


def get_existing_query_results(api_key: str, query_id: int) -> dict:
    """Fetch cached results from an existing Redash query."""
    # First get query metadata to find latest_query_data_id
    req = urllib.request.Request(
        f"{BASE_URL}/api/queries/{query_id}",
        headers={"Authorization": f"Key {api_key}"},
    )

    with urllib.request.urlopen(req) as resp:
        query_info = json.loads(resp.read().decode())

    result_id = query_info.get("latest_query_data_id")
    if not result_id:
        raise RuntimeError(f"Query {query_id} has no cached results")

    req = urllib.request.Request(
        f"{BASE_URL}/api/query_results/{result_id}",
        headers={"Authorization": f"Key {api_key}"},
    )

    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def main():
    parser = argparse.ArgumentParser(
        description="Query Mozilla Redash for telemetry data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run custom SQL
  %(prog)s --sql "SELECT * FROM telemetry.main LIMIT 10"

  # Fetch cached results from an existing Redash query
  %(prog)s --query-id 65967

  # Run SQL and save to file
  %(prog)s --sql "SELECT 1" --output ~/data/result.json
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--sql",
        help="SQL query to execute against BigQuery via Redash",
    )
    group.add_argument(
        "--query-id",
        type=int,
        help="Fetch cached results from existing Redash query ID",
    )

    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Save results to JSON file",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "csv", "table"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of rows displayed (not applied to saved file)",
    )

    args = parser.parse_args()

    api_key = get_api_key()

    if args.query_id:
        print(f"Fetching cached results for query {args.query_id}...", file=sys.stderr)
        result = get_existing_query_results(api_key, args.query_id)
    else:
        print(f"Executing query...", file=sys.stderr)
        result = run_query(api_key, args.sql)

    rows = result["query_result"]["data"]["rows"]
    columns = [c["name"] for c in result["query_result"]["data"]["columns"]]

    print(f"Retrieved {len(rows)} rows", file=sys.stderr)

    # Save to file if requested
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(rows, f, indent=2)
        print(f"Saved to {args.output}", file=sys.stderr)

    # Display results
    display_rows = rows[:args.limit] if args.limit else rows

    if args.format == "json":
        print(json.dumps(display_rows, indent=2))

    elif args.format == "csv":
        print(",".join(columns))
        for row in display_rows:
            print(",".join(str(row.get(c, "")) for c in columns))

    else:  # table
        # Calculate column widths
        widths = {c: len(c) for c in columns}
        for row in display_rows:
            for c in columns:
                widths[c] = max(widths[c], len(str(row.get(c, ""))))

        # Print header
        header = " | ".join(c.ljust(widths[c]) for c in columns)
        print(header)
        print("-" * len(header))

        # Print rows
        for row in display_rows:
            print(" | ".join(str(row.get(c, "")).ljust(widths[c]) for c in columns))


if __name__ == "__main__":
    main()
