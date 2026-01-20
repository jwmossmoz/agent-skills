#!/usr/bin/env python3
"""
Extract, create, and modify JIRA stories from Mozilla JIRA (Atlassian Cloud).

Uses 1Password CLI to retrieve the API token securely.
Fetches stories and saves them to JSON, creates new stories, or modifies existing stories.

Usage:
    # Extract stories
    uv run extract_jira.py                              # Default: RELOPS project
    uv run extract_jira.py --project FOO                # Specific project
    uv run extract_jira.py --epics                      # List all epics
    uv run extract_jira.py --epic-key RELOPS-123        # Stories in an epic
    uv run extract_jira.py --status "In Progress"       # Filter by status
    uv run extract_jira.py --assignee "John Doe"        # Filter by assignee
    uv run extract_jira.py --created-after 2025-01-01   # Filter by date
    uv run extract_jira.py --jql "custom query"         # Custom JQL
    uv run extract_jira.py --list-projects              # List available projects
    uv run extract_jira.py --my-issues                  # Your issues only

    # Create stories
    uv run extract_jira.py --create --create-summary "Story title"
    uv run extract_jira.py --create --create-summary "Story title" --description "Details here"
    uv run extract_jira.py --create --create-summary "Story title" --epic-create RELOPS-2028
    uv run extract_jira.py --create --create-summary "Story title" --assignee-create me --priority-create Medium
    uv run extract_jira.py --create --create-summary "Story title" --sprint-create "Sprint 2026.01"

    # Modify stories
    uv run extract_jira.py --modify RELOPS-123 --set-status "Backlog"
    uv run extract_jira.py --modify RELOPS-123 --remove-sprint
    uv run extract_jira.py --modify RELOPS-123 --set-epic RELOPS-456
    uv run extract_jira.py --modify RELOPS-123 --remove-epic
    uv run extract_jira.py --modify RELOPS-123,RELOPS-124 --set-status "Backlog" --remove-sprint
"""

import argparse
import json
import subprocess
import sys
import os
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any

from jira import JIRA
from jira.exceptions import JIRAError


def load_config() -> dict[str, Any]:
    """Load configuration from config.toml if it exists, otherwise use defaults."""
    config_path = Path(__file__).parent / "config.toml"

    if config_path.exists():
        with open(config_path, "rb") as f:
            return tomllib.load(f)

    # Return defaults if no config file
    return {
        "jira": {
            "base_url": "https://mozilla-hub.atlassian.net",
            "default_project": "RELOPS",
        },
        "onepassword": {
            "item_name": "JiraMozillaToken",
            "vault": "Private",
            "credential_field": "credential",
            "username_field": "username",
        },
        "output": {
            "output_dir": str(Path.home() / "moz_artifacts"),
        },
    }


# Load configuration
CONFIG = load_config()

JIRA_BASE_URL = CONFIG["jira"]["base_url"]
OP_ITEM_NAME = CONFIG["onepassword"]["item_name"]
OP_VAULT = CONFIG["onepassword"]["vault"]
OP_CREDENTIAL_FIELD = CONFIG["onepassword"].get("credential_field", "credential")
OP_USERNAME_FIELD = CONFIG["onepassword"].get("username_field", "username")
DEFAULT_PROJECT = CONFIG["jira"]["default_project"]
DEFAULT_OUTPUT_DIR = Path(CONFIG["output"]["output_dir"]).expanduser()


def build_jira_client(email: str, token: str) -> JIRA:
    """Create a Jira client for the configured Jira Cloud instance."""
    try:
        # Use API v3 for Atlassian Document Format (ADF) support in descriptions/comments
        return JIRA(
            server=JIRA_BASE_URL,
            basic_auth=(email, token),
            options={"rest_api_version": "3"},
        )
    except JIRAError as exc:
        print(f"Error: Failed to connect to JIRA: {exc}", file=sys.stderr)
        sys.exit(1)


# --- Markdown to ADF Converter ---
import re


def markdown_to_adf(text: str) -> dict[str, Any]:
    """
    Convert Markdown text to Atlassian Document Format (ADF).

    Supports: headings, bullet/numbered lists, code blocks, inline code,
    links, bold, italic, and plain paragraphs.
    """
    if not text or not text.strip():
        return {"type": "doc", "version": 1, "content": []}

    content: list[dict[str, Any]] = []
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Code block (```)
        if line.startswith("```"):
            language = line[3:].strip() or None
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code_text = "\n".join(code_lines)
            node: dict[str, Any] = {
                "type": "codeBlock",
                "content": [{"type": "text", "text": code_text}],
            }
            if language:
                node["attrs"] = {"language": language}
            content.append(node)
            i += 1
            continue

        # Heading (# ## ### etc.)
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2)
            content.append(
                {
                    "type": "heading",
                    "attrs": {"level": level},
                    "content": _parse_inline(heading_text),
                }
            )
            i += 1
            continue

        # Bullet list (- or *)
        if re.match(r"^\s*[-*]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                item_text = re.sub(r"^\s*[-*]\s+", "", lines[i])
                items.append(
                    {
                        "type": "listItem",
                        "content": [
                            {"type": "paragraph", "content": _parse_inline(item_text)}
                        ],
                    }
                )
                i += 1
            content.append({"type": "bulletList", "content": items})
            continue

        # Numbered list (1. 2. etc.)
        if re.match(r"^\s*\d+\.\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                item_text = re.sub(r"^\s*\d+\.\s+", "", lines[i])
                items.append(
                    {
                        "type": "listItem",
                        "content": [
                            {"type": "paragraph", "content": _parse_inline(item_text)}
                        ],
                    }
                )
                i += 1
            content.append({"type": "orderedList", "content": items})
            continue

        # Markdown table (| col | col |)
        if re.match(r"^\s*\|.+\|\s*$", line):
            table_rows: list[dict[str, Any]] = []
            is_first_row = True
            has_header = False

            while i < len(lines) and re.match(r"^\s*\|.+\|\s*$", lines[i]):
                row_line = lines[i].strip()

                # Check if this is a separator row (|---|---|)
                # Remove all spaces and check if it only contains |, -, and :
                stripped = row_line.replace(" ", "")
                if re.match(r"^\|[-:|]+\|$", stripped) and "-" in stripped:
                    has_header = True
                    i += 1
                    is_first_row = False
                    continue

                # Parse cells from the row
                # Remove leading/trailing pipes and split by |
                cells_text = row_line[1:-1].split("|")
                cells = [cell.strip() for cell in cells_text]

                # Determine cell type based on position
                if is_first_row:
                    # First row - will be header if followed by separator
                    cell_type = "tableHeader"
                else:
                    cell_type = "tableCell"

                row_content = []
                for cell in cells:
                    row_content.append(
                        {
                            "type": cell_type,
                            "attrs": {},
                            "content": [
                                {"type": "paragraph", "content": _parse_inline(cell)}
                            ],
                        }
                    )

                table_rows.append({"type": "tableRow", "content": row_content})
                i += 1
                is_first_row = False

            # If we detected a header separator, the first row cells should be headers
            # They already are set as tableHeader, so no change needed.
            # If no separator was found, convert first row to regular cells
            if not has_header and table_rows:
                for cell in table_rows[0]["content"]:
                    cell["type"] = "tableCell"

            content.append(
                {
                    "type": "table",
                    "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
                    "content": table_rows,
                }
            )
            continue

        # Empty line - skip
        if not line.strip():
            i += 1
            continue

        # Regular paragraph - collect consecutive non-empty lines
        para_lines = []
        while i < len(lines) and lines[i].strip() and not _is_special_line(lines[i]):
            para_lines.append(lines[i])
            i += 1
        if para_lines:
            para_text = " ".join(para_lines)
            content.append({"type": "paragraph", "content": _parse_inline(para_text)})

    return {"type": "doc", "version": 1, "content": content}


def _is_special_line(line: str) -> bool:
    """Check if a line starts a special block (heading, list, code, table)."""
    if line.startswith("```"):
        return True
    if re.match(r"^#{1,6}\s+", line):
        return True
    if re.match(r"^\s*[-*]\s+", line):
        return True
    if re.match(r"^\s*\d+\.\s+", line):
        return True
    if re.match(r"^\s*\|.+\|\s*$", line):
        return True
    return False


def _parse_inline(text: str) -> list[dict[str, Any]]:
    """Parse inline formatting: bold, italic, code, links."""
    result: list[dict[str, Any]] = []

    # Pattern to match inline elements
    # Order matters: links first, then bold, italic, code
    pattern = re.compile(
        r"(\[([^\]]+)\]\(([^)]+)\))"  # [text](url)
        r"|(\*\*([^*]+)\*\*)"  # **bold**
        r"|(\*([^*]+)\*)"  # *italic*
        r"|(`([^`]+)`)"  # `code`
    )

    last_end = 0
    for match in pattern.finditer(text):
        # Add text before match
        if match.start() > last_end:
            plain = text[last_end : match.start()]
            if plain:
                result.append({"type": "text", "text": plain})

        if match.group(1):  # Link
            link_text = match.group(2)
            link_url = match.group(3)
            result.append(
                {
                    "type": "text",
                    "text": link_text,
                    "marks": [{"type": "link", "attrs": {"href": link_url}}],
                }
            )
        elif match.group(4):  # Bold
            bold_text = match.group(5)
            result.append(
                {
                    "type": "text",
                    "text": bold_text,
                    "marks": [{"type": "strong"}],
                }
            )
        elif match.group(6):  # Italic
            italic_text = match.group(7)
            result.append(
                {
                    "type": "text",
                    "text": italic_text,
                    "marks": [{"type": "em"}],
                }
            )
        elif match.group(8):  # Inline code
            code_text = match.group(9)
            result.append(
                {
                    "type": "text",
                    "text": code_text,
                    "marks": [{"type": "code"}],
                }
            )

        last_end = match.end()

    # Add remaining text
    if last_end < len(text):
        remaining = text[last_end:]
        if remaining:
            result.append({"type": "text", "text": remaining})

    # If no matches, return plain text
    if not result and text:
        result.append({"type": "text", "text": text})

    return result


# Essential fields to extract
ESSENTIAL_FIELDS = [
    "key",
    "summary",
    "status",
    "assignee",
    "reporter",
    "created",
    "updated",
    "resolved",
    "resolutiondate",
    "description",
    "issuetype",
    "priority",
    "project",
    "labels",
    "fixVersions",
    "components",
    "parent",  # For epic link
    "customfield_10014",  # Epic Link (common custom field)
    "customfield_10020",  # Sprint field (common in Jira Cloud)
]


def get_token_from_1password() -> str:
    """Retrieve JIRA API token from 1Password CLI."""
    try:
        result = subprocess.run(
            [
                "op",
                "item",
                "get",
                OP_ITEM_NAME,
                "--vault",
                OP_VAULT,
                "--fields",
                OP_CREDENTIAL_FIELD,
                "--reveal",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        token = result.stdout.strip()
        if not token:
            print("Error: Empty token retrieved from 1Password", file=sys.stderr)
            sys.exit(1)
        return token
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving token from 1Password: {e.stderr}", file=sys.stderr)
        print("Make sure you're signed in to 1Password CLI: op signin", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(
            "Error: 1Password CLI (op) not found. Please install it.", file=sys.stderr
        )
        sys.exit(1)


def get_email_from_1password() -> str | None:
    """Try to retrieve email from 1Password item."""
    try:
        result = subprocess.run(
            [
                "op",
                "item",
                "get",
                OP_ITEM_NAME,
                "--vault",
                OP_VAULT,
                "--fields",
                OP_USERNAME_FIELD,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_board_id_for_project(client: JIRA, project_key: str) -> int | None:
    """Get the board ID for a project (needed for sprint operations)."""
    try:
        boards = client.boards(projectKeyOrID=project_key)
    except JIRAError:
        return None

    for board in boards:
        board_id = getattr(board, "id", None)
        if board_id:
            try:
                client.sprints(board_id, maxResults=1)
                return int(board_id)
            except JIRAError:
                continue

    if boards:
        board_id = getattr(boards[0], "id", None)
        return int(board_id) if board_id else None
    return None


def get_sprint_id_by_name(client: JIRA, board_id: int, sprint_name: str) -> int | None:
    """Get sprint ID by name."""
    try:
        sprints = client.sprints(board_id)
    except JIRAError:
        return None

    for sprint in sprints:
        if getattr(sprint, "name", None) == sprint_name:
            sprint_id = getattr(sprint, "id", None)
            return int(sprint_id) if sprint_id else None
    return None


def get_current_user_account_id(client: JIRA) -> str | None:
    """Get the account ID for the current user."""
    try:
        account_id = client.current_user()
    except JIRAError:
        return None
    return account_id or None


def find_user_account_id(client: JIRA, query: str) -> str | None:
    """
    Find a user's account ID by email or display name.

    Args:
        client: Jira client
        query: Email address or display name to search for

    Returns:
        Account ID if found, None otherwise
    """
    try:
        users = client.search_users(query=query)
    except JIRAError:
        return None

    if not users:
        return None

    if "@" in query:
        for user in users:
            email = getattr(user, "emailAddress", None)
            if email and email.lower() == query.lower():
                return getattr(user, "accountId", None)

    return getattr(users[0], "accountId", None)


def create_issue(
    client: JIRA,
    project_key: str,
    summary: str,
    description: str | None = None,
    issue_type: str = "Story",
    priority: str | None = None,
    assignee: str | None = None,
    reporter: str | None = None,
    epic_key: str | None = None,
    sprint_name: str | None = None,
    labels: list[str] | None = None,
    fix_versions: list[str] | None = None,
) -> tuple[bool, str, str | None]:
    """
    Create a new JIRA issue.

    Returns (success, message, issue_key) tuple.
    """
    # Build the fields payload
    fields: dict[str, Any] = {
        "project": {"key": project_key},
        "summary": summary,
        "issuetype": {"name": issue_type},
    }

    # Add description if provided (supports Markdown)
    if description:
        fields["description"] = markdown_to_adf(description)

    # Add priority if provided
    if priority:
        fields["priority"] = {"name": priority}

    # Add assignee if provided
    if assignee:
        if assignee.lower() in ("me", "currentuser", "current"):
            # Get the current user's account ID
            account_id = get_current_user_account_id(client)
            if account_id:
                fields["assignee"] = {"accountId": account_id}
            else:
                return False, "Failed to get current user account ID", None
        else:
            account_id = find_user_account_id(client, assignee)
            if account_id:
                fields["assignee"] = {"accountId": account_id}
            elif "@" in assignee:
                return False, f"Could not find user: {assignee}", None
            else:
                fields["assignee"] = {"accountId": assignee}

    # Add reporter if provided
    if reporter:
        if reporter.lower() in ("me", "currentuser", "current"):
            # Get the current user's account ID
            account_id = get_current_user_account_id(client)
            if account_id:
                fields["reporter"] = {"accountId": account_id}
            else:
                return False, "Failed to get current user account ID", None
        else:
            # Search for user by email or display name
            account_id = find_user_account_id(client, reporter)
            if account_id:
                fields["reporter"] = {"accountId": account_id}
            else:
                return False, f"Could not find user: {reporter}", None

    epic_id = None
    # Add epic link if provided
    if epic_key:
        try:
            epic_id = client.issue(epic_key).id
        except JIRAError:
            epic_id = None

        fields["customfield_10014"] = epic_key
        if not epic_id:
            fields["parent"] = {"key": epic_key}

    # Add labels if provided
    if labels:
        fields["labels"] = labels

    # Add fix versions if provided
    if fix_versions:
        fields["fixVersions"] = [{"name": version} for version in fix_versions]

    # Create the issue
    try:
        issue = client.create_issue(fields=fields)
    except JIRAError as exc:
        return False, f"Failed to create issue: {exc}", None

    issue_key = getattr(issue, "key", None)
    issue_url = f"{JIRA_BASE_URL}/browse/{issue_key}" if issue_key else None

    messages = [f"Created {issue_key}: {issue_url}"]

    if issue_key and epic_id:
        try:
            client.add_issues_to_epic(epic_id, [issue_key])
            messages.append(f"Linked to epic {epic_key}")
        except JIRAError as exc:
            messages.append(f"Warning: Failed to set epic: {exc}")

    # If sprint is specified, add to sprint (requires a separate API call)
    if sprint_name and issue_key:
        board_id = get_board_id_for_project(client, project_key)
        if board_id:
            sprint_id = get_sprint_id_by_name(client, board_id, sprint_name)
            if sprint_id:
                try:
                    client.add_issues_to_sprint(sprint_id, [issue_key])
                    messages.append(f"Added to sprint '{sprint_name}'")
                except JIRAError as exc:
                    messages.append(f"Warning: Failed to add to sprint: {exc}")
            else:
                messages.append(f"Warning: Sprint '{sprint_name}' not found")
        else:
            messages.append(f"Warning: Could not find board for project {project_key}")

    return True, "; ".join(messages), issue_key


def modify_issue(
    client: JIRA,
    issue_key: str,
    set_status: str | None = None,
    remove_sprint: bool = False,
    set_sprint: str | None = None,
    set_epic: str | None = None,
    remove_epic: bool = False,
    set_fix_versions: list[str] | None = None,
    set_summary: str | None = None,
    set_description: str | None = None,
    set_reporter: str | None = None,
    set_assignee: str | None = None,
) -> tuple[bool, str]:
    """
    Modify a JIRA issue.

    Returns (success, message) tuple.
    """
    messages = []

    # Handle status change via transitions
    if set_status:
        success, msg = transition_issue(client, issue_key, set_status)
        messages.append(msg)
        if not success:
            return False, msg

    # Build the update payload for other fields
    update_payload: dict = {"fields": {}}

    # Handle sprint changes
    if remove_sprint:
        try:
            client.move_to_backlog([issue_key])
            messages.append("Removed from sprint")
        except JIRAError as exc:
            return False, f"Failed to remove from sprint: {exc}"
    elif set_sprint:
        # Need to get sprint ID first
        # Extract project key from issue key
        project_key = issue_key.split("-")[0]
        board_id = get_board_id_for_project(client, project_key)
        if board_id:
            sprint_id = get_sprint_id_by_name(client, board_id, set_sprint)
            if sprint_id:
                update_payload["fields"]["customfield_10020"] = sprint_id
                messages.append(f"Set sprint to '{set_sprint}'")
            else:
                return False, f"Sprint '{set_sprint}' not found"
        else:
            return False, f"Could not find board for project {project_key}"

    # Handle epic changes
    if remove_epic:
        update_payload["fields"]["parent"] = None
        update_payload["fields"]["customfield_10014"] = None
        messages.append("Removed from epic")
    elif set_epic:
        try:
            epic_id = client.issue(set_epic).id
        except JIRAError:
            epic_id = None

        if epic_id:
            try:
                client.add_issues_to_epic(epic_id, [issue_key])
                messages.append(f"Set epic to {set_epic}")
            except JIRAError as exc:
                return False, f"Failed to set epic {set_epic}: {exc}"
        else:
            update_payload["fields"]["customfield_10014"] = set_epic
            messages.append(f"Set epic to {set_epic}")

    # Handle fix versions
    if set_fix_versions:
        update_payload["fields"]["fixVersions"] = [
            {"name": version} for version in set_fix_versions
        ]
        messages.append(f"Set fix versions to {', '.join(set_fix_versions)}")

    # Handle summary/title change
    if set_summary:
        update_payload["fields"]["summary"] = set_summary
        messages.append(f"Updated summary to '{set_summary}'")

    # Handle description change (supports Markdown)
    if set_description:
        update_payload["fields"]["description"] = markdown_to_adf(set_description)
        messages.append("Updated description")

    # Handle reporter change
    if set_reporter:
        if set_reporter.lower() in ("me", "currentuser", "current"):
            account_id = get_current_user_account_id(client)
            if account_id:
                update_payload["fields"]["reporter"] = {"accountId": account_id}
                messages.append("Set reporter to current user")
            else:
                return False, "Failed to get current user account ID"
        else:
            account_id = find_user_account_id(client, set_reporter)
            if account_id:
                update_payload["fields"]["reporter"] = {"accountId": account_id}
                messages.append(f"Set reporter to '{set_reporter}'")
            else:
                return False, f"Could not find user: {set_reporter}"

    # Handle assignee change
    if set_assignee:
        if set_assignee.lower() in ("me", "currentuser", "current"):
            account_id = get_current_user_account_id(client)
            if account_id:
                update_payload["fields"]["assignee"] = {"accountId": account_id}
                messages.append("Set assignee to current user")
            else:
                return False, "Failed to get current user account ID"
        else:
            account_id = find_user_account_id(client, set_assignee)
            if account_id:
                update_payload["fields"]["assignee"] = {"accountId": account_id}
                messages.append(f"Set assignee to '{set_assignee}'")
            else:
                return False, f"Could not find user: {set_assignee}"

    # Only make the update request if we have field changes
    if update_payload["fields"]:
        try:
            issue = client.issue(issue_key)
            issue.update(fields=update_payload["fields"])
        except JIRAError as exc:
            return False, f"Failed to update {issue_key}: {exc}"

    return True, "; ".join(messages) if messages else "No changes made"


def link_issues(
    client: JIRA,
    inward_issue: str,
    outward_issue: str,
    link_type: str = "Relates",
) -> tuple[bool, str]:
    """
    Create a link between two JIRA issues.

    Args:
        inward_issue: The source issue key (e.g., RELOPS-123)
        outward_issue: The target issue key to link to (e.g., RELOPS-456)
        link_type: The type of link (e.g., "Relates", "Blocks", "Clones", "Duplicate")

    Returns (success, message) tuple.
    """
    try:
        client.create_issue_link(link_type, inward_issue, outward_issue)
    except JIRAError as exc:
        return False, f"Failed to link {inward_issue} to {outward_issue}: {exc}"

    return True, f"Linked {inward_issue} to {outward_issue} ({link_type})"


def add_comment(
    client: JIRA,
    issue_key: str,
    comment_text: str,
) -> tuple[bool, str]:
    """
    Add a comment to a JIRA issue.

    Returns (success, message) tuple.
    """
    try:
        client.add_comment(issue_key, markdown_to_adf(comment_text))
    except JIRAError as exc:
        return False, f"Failed to add comment to {issue_key}: {exc}"

    return True, "Added comment"


def transition_issue(
    client: JIRA, issue_key: str, target_status: str
) -> tuple[bool, str]:
    """
    Transition an issue to a new status.

    Returns (success, message) tuple.
    """
    try:
        transitions = client.transitions(issue_key)
    except JIRAError as exc:
        return False, f"Failed to get transitions for {issue_key}: {exc}"

    target_transition = None
    available_statuses = []
    for transition in transitions:
        status_name = transition.get("to", {}).get("name", "")
        available_statuses.append(status_name)
        if status_name.lower() == target_status.lower():
            target_transition = transition
            break

    if not target_transition:
        return (
            False,
            f"Cannot transition to '{target_status}'. Available: {', '.join(available_statuses)}",
        )

    try:
        client.transition_issue(issue_key, target_transition["id"])
    except JIRAError as exc:
        return False, f"Failed to transition {issue_key} to {target_status}: {exc}"

    return True, f"Status changed to '{target_status}'"


def list_projects(client: JIRA) -> None:
    """List all accessible JIRA projects."""
    try:
        projects = client.projects()
    except JIRAError as exc:
        print(f"Error: Failed to fetch projects: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"\nAvailable projects ({len(projects)}):\n")
    print(f"{'KEY':<15} {'NAME'}")
    print("-" * 60)
    for project in sorted(projects, key=lambda p: getattr(p, "key", "")):
        key = getattr(project, "key", "")
        name = getattr(project, "name", "")
        print(f"{key:<15} {name}")


def build_jql_query(args) -> str:
    """Build JQL query from command line arguments."""
    conditions = []

    # Custom JQL takes precedence
    if args.jql:
        return args.jql

    # Project filter
    project = args.project or DEFAULT_PROJECT
    conditions.append(f"project = {project}")

    # Epic-related filters
    if args.epics:
        conditions.append("issuetype = Epic")
    elif args.epic_key:
        # Stories belonging to a specific epic
        conditions.append(f"'Epic Link' = {args.epic_key} OR parent = {args.epic_key}")

    # Issue type filter
    if args.issue_type:
        conditions.append(f"issuetype = '{args.issue_type}'")

    # Status filter
    if args.status:
        conditions.append(f"status = '{args.status}'")

    # Assignee filter
    if args.my_issues:
        conditions.append(
            "(assignee = currentUser() OR reporter = currentUser() OR watcher = currentUser())"
        )
    elif args.assignee:
        conditions.append(f"assignee = '{args.assignee}'")

    # Reporter filter
    if args.reporter:
        conditions.append(f"reporter = '{args.reporter}'")

    # Date filters
    if args.created_after:
        conditions.append(f"created >= '{args.created_after}'")
    if args.created_before:
        conditions.append(f"created <= '{args.created_before}'")
    if args.updated_after:
        conditions.append(f"updated >= '{args.updated_after}'")
    if args.updated_before:
        conditions.append(f"updated <= '{args.updated_before}'")

    # Resolution filter
    if args.resolved:
        conditions.append("resolution is not EMPTY")
    if args.unresolved:
        conditions.append("resolution is EMPTY")

    # Label filter
    if args.label:
        conditions.append(f"labels = '{args.label}'")

    # Component filter
    if args.component:
        conditions.append(f"component = '{args.component}'")

    # Text search
    if args.search:
        conditions.append(f"text ~ '{args.search}'")

    # Sprint filters
    if args.current_sprint:
        conditions.append("Sprint in openSprints()")
    elif args.sprint:
        conditions.append(f"Sprint = '{args.sprint}'")

    # Build the final query
    jql = " AND ".join(conditions)

    # Add ordering
    order_by = args.order_by or "created DESC"
    jql += f" ORDER BY {order_by}"

    return jql


def fetch_all_stories(client: JIRA, jql: str) -> list[dict]:
    """Fetch JIRA stories with pagination."""
    all_issues = []
    max_results = 100
    start_at = 0

    print(f"Fetching stories from {JIRA_BASE_URL}...")
    print(f"JQL: {jql}\n")

    while True:
        try:
            issues = client.search_issues(
                jql,
                startAt=start_at,
                maxResults=max_results,
                fields=ESSENTIAL_FIELDS,
            )
        except JIRAError as exc:
            print(f"Error: API request failed: {exc}", file=sys.stderr)
            sys.exit(1)

        if not issues:
            break

        all_issues.extend([issue.raw for issue in issues])

        fetched = len(all_issues)
        total = getattr(issues, "total", None)
        if total:
            print(f"  Fetched {fetched}/{total} stories...")
        else:
            print(f"  Fetched {fetched} stories...")

        start_at += len(issues)
        if total is not None and start_at >= total:
            break
        if len(issues) < max_results:
            break

    print(f"Total stories fetched: {len(all_issues)}")
    return all_issues


def extract_essential_data(issues: list[dict]) -> list[dict]:
    """Extract essential fields from raw JIRA issues."""
    extracted = []

    for issue in issues:
        fields = issue.get("fields", {})

        # Extract epic information
        epic_key = None
        epic_name = None

        # Check parent field (for next-gen projects)
        parent = fields.get("parent")
        if parent:
            parent_type = get_nested(parent, "fields", "issuetype", "name")
            if parent_type == "Epic":
                epic_key = parent.get("key")
                epic_name = get_nested(parent, "fields", "summary")

        # Check customfield_10014 (Epic Link for classic projects)
        if not epic_key:
            epic_link = fields.get("customfield_10014")
            if epic_link:
                epic_key = epic_link

        # Extract sprint information
        sprint_names = []
        sprint_data = fields.get("customfield_10020")
        if sprint_data:
            if isinstance(sprint_data, list):
                # Sprint data is typically a list of sprint objects or strings
                for sprint in sprint_data:
                    if isinstance(sprint, dict):
                        sprint_names.append(sprint.get("name", ""))
                    elif isinstance(sprint, str):
                        # Sometimes it's a string representation
                        import re

                        match = re.search(r"name=([^,\]]+)", sprint)
                        if match:
                            sprint_names.append(match.group(1))

        # Extract nested values safely
        story = {
            "key": issue.get("key"),
            "url": f"{JIRA_BASE_URL}/browse/{issue.get('key')}",
            "summary": fields.get("summary"),
            "description": extract_description(fields.get("description")),
            "status": get_nested(fields, "status", "name"),
            "issue_type": get_nested(fields, "issuetype", "name"),
            "priority": get_nested(fields, "priority", "name"),
            "project_key": get_nested(fields, "project", "key"),
            "project_name": get_nested(fields, "project", "name"),
            "assignee": get_nested(fields, "assignee", "displayName"),
            "assignee_email": get_nested(fields, "assignee", "emailAddress"),
            "reporter": get_nested(fields, "reporter", "displayName"),
            "reporter_email": get_nested(fields, "reporter", "emailAddress"),
            "epic_key": epic_key,
            "epic_name": epic_name,
            "sprints": sprint_names,
            "created": fields.get("created"),
            "updated": fields.get("updated"),
            "resolved": fields.get("resolutiondate"),
            "labels": fields.get("labels", []),
            "components": [c.get("name") for c in fields.get("components", [])],
            "fix_versions": [v.get("name") for v in fields.get("fixVersions", [])],
        }

        extracted.append(story)

    return extracted


def get_nested(data: dict[str, Any], *keys: str) -> Any:
    """Safely get nested dictionary values."""
    current: Any = data
    for key in keys:
        if current is None:
            return None
        current = current.get(key) if isinstance(current, dict) else None
    return current


def extract_description(description: dict | None) -> str | None:
    """Extract plain text from Atlassian Document Format (ADF)."""
    if description is None:
        return None

    if isinstance(description, str):
        return description

    # Handle ADF format
    def extract_text(node: dict) -> str:
        if node.get("type") == "text":
            return node.get("text", "")

        content = node.get("content", [])
        return "".join(extract_text(child) for child in content)

    try:
        return extract_text(description).strip() or None
    except (TypeError, AttributeError):
        return None


def save_to_json(data: list[dict], output_path: Path, jql: str) -> None:
    """Save extracted data to JSON file."""
    output = {
        "extracted_at": datetime.now().isoformat(),
        "source": JIRA_BASE_URL,
        "jql_query": jql,
        "total_stories": len(data),
        "stories": data,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(data)} stories to {output_path}")


def print_summary(stories: list[dict]) -> None:
    """Print a summary of extracted stories."""
    if not stories:
        return

    # Count by status
    status_counts = {}
    type_counts = {}
    assignee_counts = {}

    for story in stories:
        status = story.get("status") or "Unknown"
        status_counts[status] = status_counts.get(status, 0) + 1

        issue_type = story.get("issue_type") or "Unknown"
        type_counts[issue_type] = type_counts.get(issue_type, 0) + 1

        assignee = story.get("assignee") or "Unassigned"
        assignee_counts[assignee] = assignee_counts.get(assignee, 0) + 1

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    print("\nBy Status:")
    for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        print(f"  {status}: {count}")

    print("\nBy Type:")
    for issue_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {issue_type}: {count}")

    print("\nTop Assignees:")
    for assignee, count in sorted(assignee_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {assignee}: {count}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract JIRA stories from Mozilla JIRA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # All RELOPS stories
  %(prog)s --epics                            # All RELOPS epics
  %(prog)s --epic-key RELOPS-123              # Stories in epic RELOPS-123
  %(prog)s --status "In Progress"             # In Progress stories
  %(prog)s --my-issues                        # Your assigned/reported stories
  %(prog)s --current-sprint                   # Stories in current active sprint
  %(prog)s --current-sprint --assignee currentUser()  # Your sprint stories
  %(prog)s --created-after 2025-01-01         # Stories created in 2025
  %(prog)s --assignee "John Doe" --resolved   # John's resolved stories
        """,
    )

    # Output options
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="jira_stories.json",
        help="Output JSON filename (default: jira_stories.json)",
    )
    parser.add_argument(
        "--output-dir",
        "-d",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for JSON files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print summary statistics after extraction",
    )

    # Authentication
    parser.add_argument(
        "--email",
        "-e",
        type=str,
        help="Your JIRA email address (tries 1Password if not provided)",
    )

    # Project and issue filters
    parser.add_argument(
        "--project",
        "-p",
        type=str,
        help=f"JIRA project key (default: {DEFAULT_PROJECT})",
    )
    parser.add_argument(
        "--list-projects",
        action="store_true",
        help="List all accessible projects and exit",
    )

    # Epic filters
    parser.add_argument(
        "--epics",
        action="store_true",
        help="Only fetch Epic issue types",
    )
    parser.add_argument(
        "--epic-key",
        type=str,
        help="Fetch stories belonging to a specific epic",
    )

    # Issue type and status
    parser.add_argument(
        "--issue-type",
        "-t",
        type=str,
        help="Filter by issue type (Story, Task, Bug, Epic, etc.)",
    )
    parser.add_argument(
        "--status",
        "-s",
        type=str,
        help="Filter by status (e.g., 'In Progress', 'Done', 'Backlog')",
    )

    # People filters
    parser.add_argument(
        "--my-issues",
        action="store_true",
        help="Only fetch issues where you are assignee, reporter, or watcher",
    )
    parser.add_argument(
        "--assignee",
        "-a",
        type=str,
        help="Filter by assignee display name",
    )
    parser.add_argument(
        "--reporter",
        type=str,
        help="Filter by reporter display name",
    )

    # Date filters
    parser.add_argument(
        "--created-after",
        type=str,
        help="Filter by created date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--created-before",
        type=str,
        help="Filter by created date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--updated-after",
        type=str,
        help="Filter by updated date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--updated-before",
        type=str,
        help="Filter by updated date (YYYY-MM-DD)",
    )

    # Resolution filters
    parser.add_argument(
        "--resolved",
        action="store_true",
        help="Only resolved issues",
    )
    parser.add_argument(
        "--unresolved",
        action="store_true",
        help="Only unresolved issues",
    )

    # Other filters
    parser.add_argument(
        "--label",
        type=str,
        help="Filter by label",
    )
    parser.add_argument(
        "--component",
        type=str,
        help="Filter by component",
    )
    parser.add_argument(
        "--search",
        type=str,
        help="Full-text search in summary and description",
    )

    # Sprint filters
    parser.add_argument(
        "--current-sprint",
        action="store_true",
        help="Only issues in the current active sprint",
    )
    parser.add_argument(
        "--sprint",
        type=str,
        help="Filter by specific sprint name",
    )

    # Ordering
    parser.add_argument(
        "--order-by",
        type=str,
        help="Order by field (default: 'created DESC')",
    )

    # Custom JQL (overrides all other filters)
    parser.add_argument(
        "--jql",
        "-q",
        type=str,
        help="Custom JQL query (overrides all other filters)",
    )

    # Create operations
    create_group = parser.add_argument_group(
        "create options", "Options for creating new issues"
    )
    create_group.add_argument(
        "--create",
        "-c",
        action="store_true",
        help="Create a new issue",
    )
    create_group.add_argument(
        "--create-summary",
        type=str,
        help="Summary/title for the new issue (required with --create)",
    )
    create_group.add_argument(
        "--description",
        type=str,
        help="Description for the new issue",
    )
    create_group.add_argument(
        "--issue-type-create",
        type=str,
        default="Story",
        help="Issue type for new issue (default: Story)",
    )
    create_group.add_argument(
        "--priority-create",
        type=str,
        help="Priority for new issue (e.g., 'High', 'Medium', 'Low')",
    )
    create_group.add_argument(
        "--assignee-create",
        type=str,
        help="Assignee for new issue (email, 'me', or account ID)",
    )
    create_group.add_argument(
        "--reporter-create",
        type=str,
        help="Reporter for new issue (email, display name, 'me', or account ID)",
    )
    create_group.add_argument(
        "--epic-create",
        type=str,
        help="Epic key to link new issue to (e.g., RELOPS-2028)",
    )
    create_group.add_argument(
        "--sprint-create",
        type=str,
        help="Sprint name to add new issue to",
    )
    create_group.add_argument(
        "--labels-create",
        type=str,
        help="Comma-separated labels for new issue",
    )
    create_group.add_argument(
        "--fix-versions-create",
        type=str,
        help="Comma-separated fix versions for new issue (e.g., '2026 Q1')",
    )
    create_group.add_argument(
        "--project-create",
        type=str,
        help=f"Project key for new issue (default: {DEFAULT_PROJECT})",
    )

    # Modify operations
    modify_group = parser.add_argument_group(
        "modify options", "Options for modifying issues"
    )
    modify_group.add_argument(
        "--modify",
        "-m",
        type=str,
        help="Issue key(s) to modify (comma-separated, e.g., RELOPS-123 or RELOPS-123,RELOPS-124)",
    )
    modify_group.add_argument(
        "--set-status",
        type=str,
        help="Set the status (e.g., 'Backlog', 'In Progress', 'Done')",
    )
    modify_group.add_argument(
        "--remove-sprint",
        action="store_true",
        help="Remove issue(s) from their current sprint",
    )
    modify_group.add_argument(
        "--set-sprint",
        type=str,
        help="Move issue(s) to a specific sprint by name",
    )
    modify_group.add_argument(
        "--set-epic",
        type=str,
        help="Set the epic link (e.g., RELOPS-456)",
    )
    modify_group.add_argument(
        "--remove-epic",
        action="store_true",
        help="Remove issue(s) from their current epic",
    )
    modify_group.add_argument(
        "--set-fix-versions",
        type=str,
        help="Set fix versions (comma-separated, e.g., '2026 Q1')",
    )
    modify_group.add_argument(
        "--set-summary",
        type=str,
        help="Set the issue summary/title",
    )
    modify_group.add_argument(
        "--set-description",
        type=str,
        help="Set the issue description",
    )
    modify_group.add_argument(
        "--set-reporter",
        type=str,
        help="Set the reporter (email, display name, 'me', or account ID)",
    )
    modify_group.add_argument(
        "--set-assignee",
        type=str,
        help="Set the assignee (email, display name, 'me', or account ID)",
    )
    modify_group.add_argument(
        "--add-comment",
        type=str,
        help="Add a comment to the issue",
    )
    modify_group.add_argument(
        "--link-issue",
        type=str,
        help="Link to another issue (e.g., RELOPS-456)",
    )
    modify_group.add_argument(
        "--link-type",
        type=str,
        default="Relates",
        help="Type of link: Relates (default), Blocks, Clones, Duplicate",
    )
    modify_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )

    args = parser.parse_args()

    # Check for environment variables first (bypass 1Password)
    env_token = os.environ.get("JIRA_API_TOKEN")
    env_email = os.environ.get("JIRA_EMAIL")

    if env_token:
        print("Using API token from JIRA_API_TOKEN environment variable")
        token = env_token
    else:
        print("Retrieving API token from 1Password...")
        token = get_token_from_1password()

    # Get email from args, env var, or 1Password (in that order)
    email: str | None = args.email
    if email:
        pass  # Use provided --email arg
    elif env_email:
        print("Using email from JIRA_EMAIL environment variable")
        email = env_email
    else:
        email = get_email_from_1password()

    if not email:
        print(
            "Error: Email not provided via --email, JIRA_EMAIL env var, or 1Password.",
            file=sys.stderr,
        )
        print("Please provide your email with --email YOUR_EMAIL", file=sys.stderr)
        print("Or set the JIRA_EMAIL environment variable", file=sys.stderr)
        sys.exit(1)

    # Type narrowing: email is guaranteed to be str after the check above
    assert email is not None
    print(f"Using email: {email}")

    client = build_jira_client(email, token)

    # List projects mode
    if args.list_projects:
        list_projects(client)
        return

    # Create mode
    if args.create:
        # Validate required fields
        if not args.create_summary:
            print(
                "Error: --create requires --create-summary to be provided",
                file=sys.stderr,
            )
            sys.exit(1)

        # Get project key
        project_key = args.project_create or DEFAULT_PROJECT

        # Parse labels if provided
        labels = None
        if args.labels_create:
            labels = [label.strip() for label in args.labels_create.split(",")]

        # Parse fix versions if provided
        fix_versions = None
        if args.fix_versions_create:
            fix_versions = [
                version.strip() for version in args.fix_versions_create.split(",")
            ]

        print(f"\nCreating new issue in project {project_key}...")
        if args.dry_run:
            print("(DRY RUN - no changes will be made)\n")
            print(f"  Project: {project_key}")
            print(f"  Type: {args.issue_type_create}")
            print(f"  Summary: {args.create_summary}")
            if args.description:
                print(f"  Description: {args.description[:100]}...")
            if args.priority_create:
                print(f"  Priority: {args.priority_create}")
            if args.assignee_create:
                print(f"  Assignee: {args.assignee_create}")
            if args.reporter_create:
                print(f"  Reporter: {args.reporter_create}")
            if args.epic_create:
                print(f"  Epic: {args.epic_create}")
            if args.sprint_create:
                print(f"  Sprint: {args.sprint_create}")
            if labels:
                print(f"  Labels: {', '.join(labels)}")
            if fix_versions:
                print(f"  Fix Versions: {', '.join(fix_versions)}")
            print("\nWould create this issue (dry run)")
        else:
            success, message, issue_key = create_issue(
                client=client,
                project_key=project_key,
                summary=args.create_summary,
                description=args.description,
                issue_type=args.issue_type_create,
                priority=args.priority_create,
                assignee=args.assignee_create,
                reporter=args.reporter_create,
                epic_key=args.epic_create,
                sprint_name=args.sprint_create,
                labels=labels,
                fix_versions=fix_versions,
            )
            status_icon = "✓" if success else "✗"
            print(f"  {status_icon} {message}")

        print("\nDone!")
        return

    # Modify mode
    if args.modify:
        issue_keys = [k.strip() for k in args.modify.split(",")]

        # Validate that at least one modify option is provided
        if not any(
            [
                args.set_status,
                args.remove_sprint,
                args.set_sprint,
                args.set_epic,
                args.remove_epic,
                args.set_fix_versions,
                args.set_summary,
                args.set_description,
                args.set_reporter,
                args.set_assignee,
                args.add_comment,
                args.link_issue,
            ]
        ):
            print(
                "Error: --modify requires at least one of: --set-status, --remove-sprint, --set-sprint, --set-epic, --remove-epic, --set-fix-versions, --set-summary, --set-description, --set-reporter, --set-assignee, --add-comment, --link-issue",
                file=sys.stderr,
            )
            sys.exit(1)

        # Parse fix versions if provided
        fix_versions = None
        if args.set_fix_versions:
            fix_versions = [
                version.strip() for version in args.set_fix_versions.split(",")
            ]

        print(f"\nModifying {len(issue_keys)} issue(s)...")
        if args.dry_run:
            print("(DRY RUN - no changes will be made)\n")

        for issue_key in issue_keys:
            if args.dry_run:
                changes = []
                if args.set_status:
                    changes.append(f"set status to '{args.set_status}'")
                if args.remove_sprint:
                    changes.append("remove from sprint")
                if args.set_sprint:
                    changes.append(f"move to sprint '{args.set_sprint}'")
                if args.set_epic:
                    changes.append(f"set epic to {args.set_epic}")
                if args.remove_epic:
                    changes.append("remove from epic")
                if fix_versions:
                    changes.append(f"set fix versions to {', '.join(fix_versions)}")
                if args.set_summary:
                    changes.append(f"set summary to '{args.set_summary}'")
                if args.set_description:
                    changes.append("update description")
                if args.set_reporter:
                    changes.append(f"set reporter to '{args.set_reporter}'")
                if args.set_assignee:
                    changes.append(f"set assignee to '{args.set_assignee}'")
                if args.add_comment:
                    changes.append("add comment")
                if args.link_issue:
                    changes.append(f"link to {args.link_issue} ({args.link_type})")
                print(f"  {issue_key}: Would {', '.join(changes)}")
            else:
                messages = []
                success = True
                # Handle field modifications
                if any(
                    [
                        args.set_status,
                        args.remove_sprint,
                        args.set_sprint,
                        args.set_epic,
                        args.remove_epic,
                        fix_versions,
                        args.set_summary,
                        args.set_description,
                        args.set_reporter,
                        args.set_assignee,
                    ]
                ):
                    success, message = modify_issue(
                        client=client,
                        issue_key=issue_key,
                        set_status=args.set_status,
                        remove_sprint=args.remove_sprint,
                        set_sprint=args.set_sprint,
                        set_epic=args.set_epic,
                        remove_epic=args.remove_epic,
                        set_fix_versions=fix_versions,
                        set_summary=args.set_summary,
                        set_description=args.set_description,
                        set_reporter=args.set_reporter,
                        set_assignee=args.set_assignee,
                    )
                    messages.append(message)
                    if not success:
                        print(f"  ✗ {issue_key}: {message}")
                        continue

                # Handle comment separately
                if args.add_comment:
                    success, message = add_comment(
                        client=client,
                        issue_key=issue_key,
                        comment_text=args.add_comment,
                    )
                    messages.append(message)

                # Handle issue linking
                if args.link_issue:
                    success, message = link_issues(
                        client=client,
                        inward_issue=issue_key,
                        outward_issue=args.link_issue,
                        link_type=args.link_type,
                    )
                    messages.append(message)

                status_icon = "✓" if success else "✗"
                print(f"  {status_icon} {issue_key}: {'; '.join(messages)}")

        print("\nDone!")
        return

    # Ensure output directory exists
    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build full output path
    output_path = output_dir / args.output
    print(f"Output directory: {output_dir}")

    # Build JQL query
    jql = build_jql_query(args)

    # Fetch all stories
    raw_issues = fetch_all_stories(client, jql)

    # Extract essential data
    stories = extract_essential_data(raw_issues)

    # Save to JSON
    save_to_json(stories, output_path, jql)

    # Print summary if requested
    if args.summary:
        print_summary(stories)

    print("\nDone!")


if __name__ == "__main__":
    main()
