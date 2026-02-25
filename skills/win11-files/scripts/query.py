#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""
Query Windows 11 update file information from SQLite database.

Supports both the combined database (win11_files.db with version column)
and the legacy 24H2-only database (win11_24h2_files.db).
"""

import argparse
import sqlite3
import sys
from pathlib import Path

DB_PATHS = [
    Path.home() / "moz_artifacts" / "win11_files.db",
    Path.home() / "moz_artifacts" / "win11_24h2_files.db",
]


def get_connection():
    for db_path in DB_PATHS:
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            has_version = _has_version_column(conn)
            return conn, db_path, has_version

    paths = "\n  ".join(str(p) for p in DB_PATHS)
    print(f"Error: No database found. Checked:\n  {paths}", file=sys.stderr)
    sys.exit(1)


def _has_version_column(conn):
    cursor = conn.execute("PRAGMA table_info(files)")
    columns = {row[1] for row in cursor.fetchall()}
    return "version" in columns


def _version_filter(has_version, version, prefix="AND"):
    if not has_version or not version:
        return "", []
    return f"{prefix} version = ?", [version]


def cmd_search(args):
    """Search for files by name pattern."""
    conn, db_path, has_version = get_connection()
    cursor = conn.cursor()

    pattern = f"%{args.pattern}%" if not args.exact else args.pattern
    ver_clause, ver_params = _version_filter(has_version, args.version)

    query = f"""
        SELECT DISTINCT file_name, file_version, kb_number, build, release_date
        FROM files
        WHERE file_name LIKE ? {ver_clause}
        ORDER BY file_name, build
    """
    if args.limit:
        query += f" LIMIT {args.limit}"

    cursor.execute(query, [pattern] + ver_params)
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
    conn, db_path, has_version = get_connection()
    cursor = conn.cursor()
    ver_clause, ver_params = _version_filter(has_version, args.version)

    cursor.execute(f"""
        SELECT kb_number, release_date, build, file_version, update_type
        FROM files
        WHERE file_name = ? {ver_clause}
        ORDER BY release_date
    """, [args.file_name] + ver_params)

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
        print(
            f"{row[0]:<12} {row[1]:<15} {row[2]:<15} "
            f"{row[3]:<30} {row[4]}{marker}"
        )
        prev_version = row[3]

    print(f"\nTotal: {len(rows)} entries (* = version changed)")
    conn.close()


def cmd_diff(args):
    """Show files that changed between two builds."""
    conn, db_path, has_version = get_connection()
    cursor = conn.cursor()
    ver_clause, ver_params = _version_filter(has_version, args.version)

    cursor.execute(f"""
        SELECT file_name, file_version FROM files
        WHERE build = ? {ver_clause}
    """, [args.build1] + ver_params)
    build1_files = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute(f"""
        SELECT file_name, file_version FROM files
        WHERE build = ? {ver_clause}
    """, [args.build2] + ver_params)
    build2_files = {row[0]: row[1] for row in cursor.fetchall()}

    if not build1_files:
        print(f"No files found for build {args.build1}")
        return
    if not build2_files:
        print(f"No files found for build {args.build2}")
        return

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

    print(f"Diff: {args.build1} -> {args.build2}\n")

    limit = args.limit

    if changed:
        print(f"CHANGED ({len(changed)}):")
        for name, old_ver, new_ver in sorted(changed)[:limit]:
            print(f"  {name}: {old_ver} -> {new_ver}")
        if len(changed) > limit:
            print(f"  ... and {len(changed) - limit} more")

    if added:
        print(f"\nADDED ({len(added)}):")
        for name, ver in sorted(added)[:limit]:
            print(f"  {name}: {ver}")
        if len(added) > limit:
            print(f"  ... and {len(added) - limit} more")

    if removed:
        print(f"\nREMOVED ({len(removed)}):")
        for name, ver in sorted(removed)[:limit]:
            print(f"  {name}: {ver}")
        if len(removed) > limit:
            print(f"  ... and {len(removed) - limit} more")

    print(
        f"\nSummary: {len(changed)} changed, "
        f"{len(added)} added, {len(removed)} removed"
    )
    conn.close()


def cmd_builds(args):
    """List all available builds/patches."""
    conn, db_path, has_version = get_connection()
    cursor = conn.cursor()
    ver_clause, ver_params = _version_filter(
        has_version, args.version, prefix="WHERE"
    )

    if has_version:
        cursor.execute(f"""
            SELECT version, kb_number, release_date, build, update_type,
                   COUNT(*) as file_count
            FROM files
            {ver_clause}
            GROUP BY version, kb_number, release_date, build, update_type
            ORDER BY version, release_date
        """, ver_params)

        rows = cursor.fetchall()

        print(
            f"{'Ver':<6} {'KB':<12} {'Release Date':<15} "
            f"{'Build':<15} {'Type':<12} {'Files'}"
        )
        print("-" * 80)
        for row in rows:
            print(
                f"{row[0]:<6} {row[1]:<12} {row[2]:<15} "
                f"{row[3]:<15} {row[4]:<12} {row[5]:,}"
            )
    else:
        cursor.execute("""
            SELECT kb_number, release_date, build, update_type,
                   COUNT(*) as file_count
            FROM files
            GROUP BY kb_number, release_date, build, update_type
            ORDER BY release_date
        """)

        rows = cursor.fetchall()

        print(
            f"{'KB':<12} {'Release Date':<15} "
            f"{'Build':<15} {'Type':<12} {'Files'}"
        )
        print("-" * 70)
        for row in rows:
            print(
                f"{row[0]:<12} {row[1]:<15} "
                f"{row[2]:<15} {row[3]:<12} {row[4]:,}"
            )

    print(f"\nTotal: {len(rows)} patches")
    conn.close()


def cmd_sql(args):
    """Run a custom SQL query."""
    conn, db_path, has_version = get_connection()
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
    conn, db_path, has_version = get_connection()
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

    if has_version:
        cursor.execute(
            "SELECT DISTINCT version FROM files ORDER BY version"
        )
        versions = [row[0] for row in cursor.fetchall()]
        version_str = ", ".join(versions)
    else:
        version_str = "24H2 (legacy database)"

    print("Windows 11 Files Database Statistics")
    print("=" * 45)
    print(f"Windows versions:      {version_str}")
    print(f"Total file entries:    {total_rows:,}")
    print(f"Unique file names:     {unique_files:,}")
    print(f"Total patches:         {total_patches}")
    print(f"Build range:           {min_build} -> {max_build}")
    print(f"Date range:            {min_date} -> {max_date}")
    print(f"Database location:     {db_path}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Query Windows 11 update file information"
    )
    parser.add_argument(
        "--version",
        choices=["24H2", "25H2"],
        help="Filter by Windows 11 version (omit for all)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_search = subparsers.add_parser(
        "search", help="Search files by name pattern"
    )
    p_search.add_argument("pattern", help="File name pattern to search")
    p_search.add_argument(
        "--exact", action="store_true",
        help="Exact match instead of contains",
    )
    p_search.add_argument("--limit", type=int, help="Limit results")
    p_search.set_defaults(func=cmd_search)

    p_history = subparsers.add_parser(
        "history", help="Show version history for a file"
    )
    p_history.add_argument("file_name", help="Exact file name")
    p_history.set_defaults(func=cmd_history)

    p_diff = subparsers.add_parser(
        "diff", help="Compare files between two builds"
    )
    p_diff.add_argument("build1", help="First build (e.g., 26100.2894)")
    p_diff.add_argument("build2", help="Second build (e.g., 26100.3037)")
    p_diff.add_argument(
        "--limit", type=int, default=50,
        help="Limit results per category",
    )
    p_diff.set_defaults(func=cmd_diff)

    p_builds = subparsers.add_parser(
        "builds", help="List all available builds"
    )
    p_builds.set_defaults(func=cmd_builds)

    p_sql = subparsers.add_parser("sql", help="Run custom SQL query")
    p_sql.add_argument("query", help="SQL query to execute")
    p_sql.set_defaults(func=cmd_sql)

    p_stats = subparsers.add_parser(
        "stats", help="Show database statistics"
    )
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
