#!/usr/bin/env python3
"""
Interact with Mozilla Bugzilla (bugzilla.mozilla.org) via REST API.

Supports searching, viewing, creating, updating bugs, and adding comments/attachments.

Usage:
    # Search bugs
    uv run bz.py search --product Firefox --component "Developer Tools"
    uv run bz.py search --assignee user@example.com --status OPEN
    uv run bz.py search --quicksearch "crash startup"

    # Get bug details
    uv run bz.py get 1234567
    uv run bz.py get 1234567 --include-comments --include-history

    # Create a bug
    uv run bz.py create --product Firefox --component General --summary "Bug title" --version "unspecified"

    # Update a bug
    uv run bz.py update 1234567 --status RESOLVED --resolution FIXED
    uv run bz.py update 1234567 --add-comment "This is fixed in changeset abc123"

    # Add comment
    uv run bz.py comment 1234567 "Comment text here"

    # Who am I (verify auth)
    uv run bz.py whoami
"""

import argparse
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests

BUGZILLA_URL = "https://bugzilla.mozilla.org"
REST_BASE = f"{BUGZILLA_URL}/rest"


def get_api_key() -> str | None:
    """Get API key from environment variable."""
    return os.environ.get("BUGZILLA_API_KEY")


def make_request(
    method: str,
    endpoint: str,
    params: dict | None = None,
    data: dict | None = None,
    api_key: str | None = None,
) -> dict:
    """Make a request to the Bugzilla REST API."""
    url = f"{REST_BASE}/{endpoint}"
    headers = {}

    if api_key:
        headers["X-BUGZILLA-API-KEY"] = api_key

    if method == "GET":
        response = requests.get(url, params=params, headers=headers)
    elif method == "POST":
        headers["Content-Type"] = "application/json"
        response = requests.post(url, params=params, json=data, headers=headers)
    elif method == "PUT":
        headers["Content-Type"] = "application/json"
        response = requests.put(url, params=params, json=data, headers=headers)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")

    if response.status_code >= 400:
        try:
            error_data = response.json()
            error_msg = error_data.get("message", response.text)
        except json.JSONDecodeError:
            error_msg = response.text
        print(f"Error {response.status_code}: {error_msg}", file=sys.stderr)
        sys.exit(1)

    return response.json()


def cmd_whoami(args) -> None:
    """Verify authentication and show current user info."""
    api_key = get_api_key()
    if not api_key:
        print("Error: BUGZILLA_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    result = make_request("GET", "whoami", api_key=api_key)
    print(f"Logged in as: {result.get('real_name', 'Unknown')} <{result.get('name', 'Unknown')}>")
    print(f"ID: {result.get('id')}")


def cmd_get(args) -> None:
    """Get details for one or more bugs."""
    api_key = get_api_key()
    bug_ids = args.bug_ids

    params = {}
    if args.include_comments:
        # Comments are fetched separately
        pass
    if args.include_history:
        params["include_fields"] = "_all"

    for bug_id in bug_ids:
        result = make_request("GET", f"bug/{bug_id}", params=params, api_key=api_key)
        bugs = result.get("bugs", [])

        if not bugs:
            print(f"Bug {bug_id} not found", file=sys.stderr)
            continue

        bug = bugs[0]
        print_bug(bug, verbose=args.verbose)

        if args.include_comments:
            comments_result = make_request(
                "GET", f"bug/{bug_id}/comment", api_key=api_key
            )
            comments = comments_result.get("bugs", {}).get(str(bug_id), {}).get("comments", [])
            if comments:
                print(f"\n  Comments ({len(comments)}):")
                for i, comment in enumerate(comments):
                    author = comment.get("creator", "Unknown")
                    time = comment.get("creation_time", "")
                    text = comment.get("text", "")[:200]
                    if len(comment.get("text", "")) > 200:
                        text += "..."
                    print(f"    [{i}] {author} ({time}):")
                    for line in text.split("\n")[:5]:
                        print(f"        {line}")

        if args.include_history:
            history_result = make_request(
                "GET", f"bug/{bug_id}/history", api_key=api_key
            )
            history = history_result.get("bugs", [{}])[0].get("history", [])
            if history:
                print(f"\n  History ({len(history)} changes):")
                for change in history[-5:]:  # Last 5 changes
                    who = change.get("who", "Unknown")
                    when = change.get("when", "")
                    changes = change.get("changes", [])
                    print(f"    {who} ({when}):")
                    for c in changes:
                        print(f"      {c.get('field_name')}: {c.get('removed', '')} -> {c.get('added', '')}")

        print()


def print_bug(bug: dict, verbose: bool = False) -> None:
    """Print bug details."""
    bug_id = bug.get("id")
    summary = bug.get("summary", "No summary")
    status = bug.get("status", "Unknown")
    resolution = bug.get("resolution", "")
    product = bug.get("product", "Unknown")
    component = bug.get("component", "Unknown")
    assignee = bug.get("assigned_to", "Nobody")
    priority = bug.get("priority", "")
    severity = bug.get("severity", "")

    status_str = f"{status}"
    if resolution:
        status_str += f" {resolution}"

    print(f"Bug {bug_id}: {summary}")
    print(f"  URL: {BUGZILLA_URL}/show_bug.cgi?id={bug_id}")
    print(f"  Status: {status_str}")
    print(f"  Product/Component: {product} :: {component}")
    print(f"  Assignee: {assignee}")

    if verbose:
        print(f"  Priority: {priority}")
        print(f"  Severity: {severity}")
        print(f"  Creator: {bug.get('creator', 'Unknown')}")
        print(f"  Created: {bug.get('creation_time', '')}")
        print(f"  Modified: {bug.get('last_change_time', '')}")
        keywords = bug.get("keywords", [])
        if keywords:
            print(f"  Keywords: {', '.join(keywords)}")
        depends_on = bug.get("depends_on", [])
        if depends_on:
            print(f"  Depends on: {', '.join(map(str, depends_on))}")
        blocks = bug.get("blocks", [])
        if blocks:
            print(f"  Blocks: {', '.join(map(str, blocks))}")
        see_also = bug.get("see_also", [])
        if see_also:
            print(f"  See also: {', '.join(see_also)}")


def cmd_search(args) -> None:
    """Search for bugs."""
    api_key = get_api_key()
    params = {}

    # Quick search (simple text search)
    if args.quicksearch:
        params["quicksearch"] = args.quicksearch
    else:
        # Build search parameters
        if args.product:
            params["product"] = args.product
        if args.component:
            params["component"] = args.component
        if args.status:
            params["status"] = args.status
        if args.resolution:
            params["resolution"] = args.resolution
        if args.assignee:
            params["assigned_to"] = args.assignee
        if args.reporter:
            params["reporter"] = args.reporter
        if args.priority:
            params["priority"] = args.priority
        if args.severity:
            params["severity"] = args.severity
        if args.keywords:
            params["keywords"] = args.keywords
        if args.whiteboard:
            params["status_whiteboard"] = args.whiteboard
        if args.created_after:
            params["creation_time"] = args.created_after
        if args.changed_after:
            params["last_change_time"] = args.changed_after
        if args.summary:
            params["summary"] = args.summary

    # Limit results
    params["limit"] = args.limit

    result = make_request("GET", "bug", params=params, api_key=api_key)
    bugs = result.get("bugs", [])

    if not bugs:
        print("No bugs found matching criteria")
        return

    print(f"Found {len(bugs)} bug(s):\n")

    if args.format == "json":
        print(json.dumps(bugs, indent=2))
    else:
        for bug in bugs:
            print_bug(bug, verbose=args.verbose)
            print()


def cmd_create(args) -> None:
    """Create a new bug."""
    api_key = get_api_key()
    if not api_key:
        print("Error: BUGZILLA_API_KEY environment variable required for creating bugs", file=sys.stderr)
        sys.exit(1)

    data = {
        "product": args.product,
        "component": args.component,
        "summary": args.summary,
        "version": args.version,
    }

    if args.description:
        data["description"] = args.description
    if args.severity:
        data["severity"] = args.severity
    if args.priority:
        data["priority"] = args.priority
    if args.assignee:
        data["assigned_to"] = args.assignee
    if args.cc:
        data["cc"] = args.cc.split(",")
    if args.keywords:
        data["keywords"] = args.keywords.split(",")
    if args.blocks:
        data["blocks"] = [int(b) for b in args.blocks.split(",")]
    if args.depends_on:
        data["depends_on"] = [int(d) for d in args.depends_on.split(",")]
    if args.see_also:
        data["see_also"] = args.see_also.split(",")

    if args.dry_run:
        print("Would create bug with:")
        print(json.dumps(data, indent=2))
        return

    result = make_request("POST", "bug", data=data, api_key=api_key)
    bug_id = result.get("id")
    print(f"Created bug {bug_id}")
    print(f"URL: {BUGZILLA_URL}/show_bug.cgi?id={bug_id}")


def cmd_update(args) -> None:
    """Update an existing bug."""
    api_key = get_api_key()
    if not api_key:
        print("Error: BUGZILLA_API_KEY environment variable required for updating bugs", file=sys.stderr)
        sys.exit(1)

    bug_id = args.bug_id
    data = {}

    if args.status:
        data["status"] = args.status
    if args.resolution:
        data["resolution"] = args.resolution
    if args.assignee:
        data["assigned_to"] = args.assignee
    if args.priority:
        data["priority"] = args.priority
    if args.severity:
        data["severity"] = args.severity
    if args.summary:
        data["summary"] = args.summary
    if args.add_cc:
        data["cc"] = {"add": args.add_cc.split(",")}
    if args.remove_cc:
        data["cc"] = {"remove": args.remove_cc.split(",")}
    if args.add_keywords:
        data["keywords"] = {"add": args.add_keywords.split(",")}
    if args.remove_keywords:
        data["keywords"] = {"remove": args.remove_keywords.split(",")}
    if args.add_blocks:
        data["blocks"] = {"add": [int(b) for b in args.add_blocks.split(",")]}
    if args.remove_blocks:
        data["blocks"] = {"remove": [int(b) for b in args.remove_blocks.split(",")]}
    if args.add_depends_on:
        data["depends_on"] = {"add": [int(d) for d in args.add_depends_on.split(",")]}
    if args.remove_depends_on:
        data["depends_on"] = {"remove": [int(d) for d in args.remove_depends_on.split(",")]}
    if args.whiteboard:
        data["whiteboard"] = args.whiteboard

    # Handle comment as part of update
    if args.add_comment:
        data["comment"] = {"body": args.add_comment}
        if args.comment_private:
            data["comment"]["is_private"] = True

    if not data:
        print("Error: No update fields specified", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"Would update bug {bug_id} with:")
        print(json.dumps(data, indent=2))
        return

    result = make_request("PUT", f"bug/{bug_id}", data=data, api_key=api_key)
    changes = result.get("bugs", [{}])[0].get("changes", {})
    if changes:
        print(f"Updated bug {bug_id}:")
        for field, change in changes.items():
            print(f"  {field}: {change.get('removed', '')} -> {change.get('added', '')}")
    else:
        print(f"Bug {bug_id} updated (no field changes)")


def cmd_comment(args) -> None:
    """Add a comment to a bug."""
    api_key = get_api_key()
    if not api_key:
        print("Error: BUGZILLA_API_KEY environment variable required for adding comments", file=sys.stderr)
        sys.exit(1)

    bug_id = args.bug_id
    data = {
        "comment": args.text,
    }

    if args.private:
        data["is_private"] = True

    if args.dry_run:
        print(f"Would add comment to bug {bug_id}:")
        print(f"  Text: {args.text[:100]}{'...' if len(args.text) > 100 else ''}")
        print(f"  Private: {args.private}")
        return

    result = make_request("POST", f"bug/{bug_id}/comment", data=data, api_key=api_key)
    comment_id = result.get("id")
    print(f"Added comment {comment_id} to bug {bug_id}")


def cmd_attachment(args) -> None:
    """Add an attachment to a bug."""
    api_key = get_api_key()
    if not api_key:
        print("Error: BUGZILLA_API_KEY environment variable required for attachments", file=sys.stderr)
        sys.exit(1)

    bug_id = args.bug_id
    file_path = Path(args.file)

    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    with open(file_path, "rb") as f:
        file_data = base64.b64encode(f.read()).decode("ascii")

    data = {
        "ids": [bug_id],
        "data": file_data,
        "file_name": file_path.name,
        "summary": args.summary or file_path.name,
        "content_type": args.content_type or "application/octet-stream",
    }

    if args.comment:
        data["comment"] = args.comment
    if args.is_patch:
        data["is_patch"] = True

    if args.dry_run:
        print(f"Would attach to bug {bug_id}:")
        print(f"  File: {file_path.name}")
        print(f"  Summary: {data['summary']}")
        print(f"  Content-Type: {data['content_type']}")
        return

    result = make_request("POST", f"bug/{bug_id}/attachment", data=data, api_key=api_key)
    attachment_ids = result.get("ids", [])
    if attachment_ids:
        print(f"Created attachment {attachment_ids[0]} on bug {bug_id}")


def cmd_products(args) -> None:
    """List available products or get product details."""
    api_key = get_api_key()

    if args.product:
        result = make_request("GET", f"product/{args.product}", api_key=api_key)
        products = result.get("products", [])
        if not products:
            print(f"Product '{args.product}' not found")
            return
        product = products[0]
        print(f"Product: {product.get('name')}")
        print(f"Description: {product.get('description', 'No description')}")
        print(f"\nComponents:")
        for comp in product.get("components", []):
            print(f"  - {comp.get('name')}")
            if args.verbose:
                print(f"    Description: {comp.get('description', 'No description')[:80]}")
    else:
        result = make_request("GET", "product_accessible", api_key=api_key)
        product_ids = result.get("ids", [])
        if product_ids:
            # Fetch product names
            params = {"ids": ",".join(map(str, product_ids))}
            products_result = make_request("GET", "product", params=params, api_key=api_key)
            products = products_result.get("products", [])
            print(f"Accessible products ({len(products)}):\n")
            for product in sorted(products, key=lambda p: p.get("name", "")):
                print(f"  {product.get('name')}")


def main():
    parser = argparse.ArgumentParser(
        description="Interact with Mozilla Bugzilla (bugzilla.mozilla.org)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # whoami
    whoami_parser = subparsers.add_parser("whoami", help="Verify authentication")

    # get
    get_parser = subparsers.add_parser("get", help="Get bug details")
    get_parser.add_argument("bug_ids", nargs="+", help="Bug ID(s) to fetch")
    get_parser.add_argument("-c", "--include-comments", action="store_true", help="Include comments")
    get_parser.add_argument("-H", "--include-history", action="store_true", help="Include history")
    get_parser.add_argument("-v", "--verbose", action="store_true", help="Show all fields")

    # search
    search_parser = subparsers.add_parser("search", help="Search for bugs")
    search_parser.add_argument("-q", "--quicksearch", help="Quick search text")
    search_parser.add_argument("-p", "--product", help="Product name")
    search_parser.add_argument("-c", "--component", help="Component name")
    search_parser.add_argument("-s", "--status", help="Bug status (NEW, ASSIGNED, RESOLVED, etc.)")
    search_parser.add_argument("-r", "--resolution", help="Resolution (FIXED, INVALID, WONTFIX, etc.)")
    search_parser.add_argument("-a", "--assignee", help="Assigned to (email)")
    search_parser.add_argument("--reporter", help="Reporter (email)")
    search_parser.add_argument("--priority", help="Priority (P1, P2, P3, P4, P5, --)")
    search_parser.add_argument("--severity", help="Severity (blocker, critical, major, normal, minor, trivial, enhancement)")
    search_parser.add_argument("-k", "--keywords", help="Keywords")
    search_parser.add_argument("-w", "--whiteboard", help="Status whiteboard contains")
    search_parser.add_argument("--summary", help="Summary contains")
    search_parser.add_argument("--created-after", help="Created after (YYYY-MM-DD)")
    search_parser.add_argument("--changed-after", help="Changed after (YYYY-MM-DD)")
    search_parser.add_argument("-l", "--limit", type=int, default=20, help="Max results (default: 20)")
    search_parser.add_argument("-v", "--verbose", action="store_true", help="Show all fields")
    search_parser.add_argument("-f", "--format", choices=["text", "json"], default="text", help="Output format")

    # create
    create_parser = subparsers.add_parser("create", help="Create a new bug")
    create_parser.add_argument("-p", "--product", required=True, help="Product name")
    create_parser.add_argument("-c", "--component", required=True, help="Component name")
    create_parser.add_argument("-s", "--summary", required=True, help="Bug summary/title")
    create_parser.add_argument("-V", "--version", required=True, help="Product version")
    create_parser.add_argument("-d", "--description", help="Bug description")
    create_parser.add_argument("--severity", help="Severity")
    create_parser.add_argument("--priority", help="Priority")
    create_parser.add_argument("-a", "--assignee", help="Assign to (email)")
    create_parser.add_argument("--cc", help="CC list (comma-separated emails)")
    create_parser.add_argument("-k", "--keywords", help="Keywords (comma-separated)")
    create_parser.add_argument("--blocks", help="Bug IDs this blocks (comma-separated)")
    create_parser.add_argument("--depends-on", help="Bug IDs this depends on (comma-separated)")
    create_parser.add_argument("--see-also", help="See also URLs (comma-separated)")
    create_parser.add_argument("--dry-run", action="store_true", help="Show what would be created")

    # update
    update_parser = subparsers.add_parser("update", help="Update an existing bug")
    update_parser.add_argument("bug_id", help="Bug ID to update")
    update_parser.add_argument("-s", "--status", help="New status")
    update_parser.add_argument("-r", "--resolution", help="New resolution")
    update_parser.add_argument("-a", "--assignee", help="New assignee (email)")
    update_parser.add_argument("--priority", help="New priority")
    update_parser.add_argument("--severity", help="New severity")
    update_parser.add_argument("--summary", help="New summary")
    update_parser.add_argument("--add-cc", help="Add to CC (comma-separated)")
    update_parser.add_argument("--remove-cc", help="Remove from CC (comma-separated)")
    update_parser.add_argument("--add-keywords", help="Add keywords (comma-separated)")
    update_parser.add_argument("--remove-keywords", help="Remove keywords (comma-separated)")
    update_parser.add_argument("--add-blocks", help="Add blocks (comma-separated bug IDs)")
    update_parser.add_argument("--remove-blocks", help="Remove blocks (comma-separated bug IDs)")
    update_parser.add_argument("--add-depends-on", help="Add depends on (comma-separated bug IDs)")
    update_parser.add_argument("--remove-depends-on", help="Remove depends on (comma-separated bug IDs)")
    update_parser.add_argument("-w", "--whiteboard", help="Set status whiteboard")
    update_parser.add_argument("--add-comment", help="Add comment with update")
    update_parser.add_argument("--comment-private", action="store_true", help="Make comment private")
    update_parser.add_argument("--dry-run", action="store_true", help="Show what would be updated")

    # comment
    comment_parser = subparsers.add_parser("comment", help="Add a comment to a bug")
    comment_parser.add_argument("bug_id", help="Bug ID")
    comment_parser.add_argument("text", help="Comment text")
    comment_parser.add_argument("--private", action="store_true", help="Make comment private")
    comment_parser.add_argument("--dry-run", action="store_true", help="Show what would be added")

    # attachment
    attach_parser = subparsers.add_parser("attachment", help="Add an attachment to a bug")
    attach_parser.add_argument("bug_id", help="Bug ID")
    attach_parser.add_argument("file", help="File to attach")
    attach_parser.add_argument("-s", "--summary", help="Attachment summary")
    attach_parser.add_argument("-t", "--content-type", help="MIME content type")
    attach_parser.add_argument("-c", "--comment", help="Comment for attachment")
    attach_parser.add_argument("--is-patch", action="store_true", help="Mark as patch")
    attach_parser.add_argument("--dry-run", action="store_true", help="Show what would be attached")

    # products
    products_parser = subparsers.add_parser("products", help="List products or get product details")
    products_parser.add_argument("product", nargs="?", help="Product name to get details for")
    products_parser.add_argument("-v", "--verbose", action="store_true", help="Show component descriptions")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "whoami": cmd_whoami,
        "get": cmd_get,
        "search": cmd_search,
        "create": cmd_create,
        "update": cmd_update,
        "comment": cmd_comment,
        "attachment": cmd_attachment,
        "products": cmd_products,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
