#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""
Query Windows 11 24H2 update file information from SQLite database.

Database: ~/moz_artifacts/win11_24h2_files.db
Contains ~2M file entries across 45+ patches (build 26100.863 - 26100.7705+)

Columns: kb_number, release_date, build, update_type, file_name, file_version, date, time, file_size
"""

import argparse
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path.home() / "moz_artifacts" / "win11_24h2_files.db"


def get_connection():
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def cmd_search(args):
    """Search for files by name pattern."""
    conn = get_connection()
    cursor = conn.cursor()

    pattern = f"%{args.pattern}%" if not args.exact else args.pattern

    query = """
        SELECT DISTINCT file_name, file_version, kb_number, build, release_date
        FROM files
        WHERE file_name LIKE ?
        ORDER BY file_name, build
    """
    if args.limit:
        query += f" LIMIT {args.limit}"

    cursor.execute(query, (pattern,))
    rows = cursor.fetchall()

    if not rows:
        print(f"No files found matching '{args.pattern}'")
        return

    print(f"{'File Name':<50} {'Version':<25} {'KB':<12} {'Build':<15} {'Date'}")
    print("-" * 120)
    for row in rows:
        print(f"{row[0]:<50} {row[1]:<25} {row[2]:<12} {row[3]:<15} {row[4]}")

    print(f"\nTotal: {len(rows)} entries")
    conn.close()


def cmd_history(args):
    """Show version history for a specific file across all builds."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT kb_number, release_date, build, file_version, update_type
        FROM files
        WHERE file_name = ?
        ORDER BY release_date
    """, (args.file_name,))

    rows = cursor.fetchall()

    if not rows:
        print(f"No history found for '{args.file_name}'")
        return

    print(f"Version history for: {args.file_name}\n")
    print(f"{'KB':<12} {'Release Date':<15} {'Build':<15} {'File Version':<30} {'Type'}")
    print("-" * 100)

    prev_version = None
    for row in rows:
        marker = " *" if prev_version and row[3] != prev_version else ""
        print(f"{row[0]:<12} {row[1]:<15} {row[2]:<15} {row[3]:<30} {row[4]}{marker}")
        prev_version = row[3]

    print(f"\nTotal: {len(rows)} entries (* = version changed)")
    conn.close()


def cmd_diff(args):
    """Show files that changed between two builds."""
    conn = get_connection()
    cursor = conn.cursor()

    # Get files from build1
    cursor.execute("""
        SELECT file_name, file_version FROM files WHERE build = ?
    """, (args.build1,))
    build1_files = {row[0]: row[1] for row in cursor.fetchall()}

    # Get files from build2
    cursor.execute("""
        SELECT file_name, file_version FROM files WHERE build = ?
    """, (args.build2,))
    build2_files = {row[0]: row[1] for row in cursor.fetchall()}

    if not build1_files:
        print(f"No files found for build {args.build1}")
        return
    if not build2_files:
        print(f"No files found for build {args.build2}")
        return

    # Find changes
    changed = []
    added = []
    removed = []

    for name, ver in build2_files.items():
        if name not in build1_files:
            added.append((name, ver))
        elif build1_files[name] != ver:
            changed.append((name, build1_files[name], ver))

    for name, ver in build1_files.items():
        if name not in build2_files:
            removed.append((name, ver))

    print(f"Diff: {args.build1} → {args.build2}\n")

    if changed:
        print(f"CHANGED ({len(changed)}):")
        for name, old_ver, new_ver in sorted(changed)[:args.limit or len(changed)]:
            print(f"  {name}: {old_ver} → {new_ver}")
        if args.limit and len(changed) > args.limit:
            print(f"  ... and {len(changed) - args.limit} more")

    if added:
        print(f"\nADDED ({len(added)}):")
        for name, ver in sorted(added)[:args.limit or len(added)]:
            print(f"  {name}: {ver}")
        if args.limit and len(added) > args.limit:
            print(f"  ... and {len(added) - args.limit} more")

    if removed:
        print(f"\nREMOVED ({len(removed)}):")
        for name, ver in sorted(removed)[:args.limit or len(removed)]:
            print(f"  {name}: {ver}")
        if args.limit and len(removed) > args.limit:
            print(f"  ... and {len(removed) - args.limit} more")

    print(f"\nSummary: {len(changed)} changed, {len(added)} added, {len(removed)} removed")
    conn.close()


def cmd_builds(args):
    """List all available builds/patches."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT kb_number, release_date, build, update_type, COUNT(*) as file_count
        FROM files
        GROUP BY kb_number, release_date, build, update_type
        ORDER BY release_date
    """)

    rows = cursor.fetchall()

    print(f"{'KB':<12} {'Release Date':<15} {'Build':<15} {'Type':<12} {'Files'}")
    print("-" * 70)
    for row in rows:
        print(f"{row[0]:<12} {row[1]:<15} {row[2]:<15} {row[3]:<12} {row[4]:,}")

    print(f"\nTotal: {len(rows)} patches")
    conn.close()


def cmd_sql(args):
    """Run a custom SQL query."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(args.query)
        rows = cursor.fetchall()

        if cursor.description:
            headers = [d[0] for d in cursor.description]
            print("\t".join(headers))
            print("-" * 80)
            for row in rows:
                print("\t".join(str(v) for v in row))
            print(f"\nRows: {len(rows)}")
        else:
            print("Query executed successfully")
    except sqlite3.Error as e:
        print(f"SQL Error: {e}", file=sys.stderr)
        sys.exit(1)

    conn.close()


def cmd_stats(args):
    """Show database statistics."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM files")
    total_rows = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT kb_number) FROM files")
    total_patches = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT file_name) FROM files")
    unique_files = cursor.fetchone()[0]

    cursor.execute("SELECT MIN(build), MAX(build) FROM files")
    min_build, max_build = cursor.fetchone()

    cursor.execute("SELECT MIN(release_date), MAX(release_date) FROM files")
    min_date, max_date = cursor.fetchone()

    print("Windows 11 24H2 Files Database Statistics")
    print("=" * 45)
    print(f"Total file entries:    {total_rows:,}")
    print(f"Unique file names:     {unique_files:,}")
    print(f"Total patches:         {total_patches}")
    print(f"Build range:           {min_build} → {max_build}")
    print(f"Date range:            {min_date} → {max_date}")
    print(f"Database location:     {DB_PATH}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Query Windows 11 24H2 update file information"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search command
    p_search = subparsers.add_parser("search", help="Search files by name pattern")
    p_search.add_argument("pattern", help="File name pattern to search")
    p_search.add_argument("--exact", action="store_true", help="Exact match instead of contains")
    p_search.add_argument("--limit", type=int, help="Limit results")
    p_search.set_defaults(func=cmd_search)

    # history command
    p_history = subparsers.add_parser("history", help="Show version history for a file")
    p_history.add_argument("file_name", help="Exact file name")
    p_history.set_defaults(func=cmd_history)

    # diff command
    p_diff = subparsers.add_parser("diff", help="Compare files between two builds")
    p_diff.add_argument("build1", help="First build (e.g., 26100.2894)")
    p_diff.add_argument("build2", help="Second build (e.g., 26100.3037)")
    p_diff.add_argument("--limit", type=int, default=50, help="Limit results per category")
    p_diff.set_defaults(func=cmd_diff)

    # builds command
    p_builds = subparsers.add_parser("builds", help="List all available builds")
    p_builds.set_defaults(func=cmd_builds)

    # sql command
    p_sql = subparsers.add_parser("sql", help="Run custom SQL query")
    p_sql.add_argument("query", help="SQL query to execute")
    p_sql.set_defaults(func=cmd_sql)

    # stats command
    p_stats = subparsers.add_parser("stats", help="Show database statistics")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
