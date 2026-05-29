#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "duckdb>=1.3.0",
# ]
# ///
"""
Download Azure Cost Management exports and query local Parquet with DuckDB.

The script intentionally ships without cost data. It reads Azure export blobs
from the user's storage account at runtime and keeps local data under the
configured data root.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path.home() / "moz_artifacts" / "azure-cost"
DEFAULT_DATA_ROOT = DEFAULT_ROOT / "raw"
DEFAULT_DATABASE = DEFAULT_ROOT / "azure_cost.duckdb"
DEFAULT_PATTERNS = ["*.parquet", "*.csv", "*manifest*.json"]
DEFAULT_VIEW = "azure_cost"
DEFAULT_CSV_DATEFORMAT = "%m/%d/%Y"
DEFAULT_CSV_MAX_LINE_SIZE = 8 * 1024 * 1024
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def expand_path(value: str | os.PathLike[str]) -> Path:
    return Path(value).expanduser()


def sql_string(value: str | os.PathLike[str]) -> str:
    return str(value).replace("'", "''")


def sql_ident(value: str) -> str:
    if not IDENT_RE.match(value):
        raise SystemExit(f"Invalid SQL identifier: {value!r}")
    return value


def human_bytes(size: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    amount = float(size)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return f"{size} B"


def load_config(path: str | None) -> dict[str, Any]:
    if not path:
        return {}

    config_path = expand_path(path)
    if not config_path.exists():
        raise SystemExit(f"Config file not found: {config_path}")

    with config_path.open("rb") as fh:
        return tomllib.load(fh)


def config_section(config: dict[str, Any], name: str) -> dict[str, Any]:
    section = config.get(name, {})
    if not isinstance(section, dict):
        raise SystemExit(f"Config section [{name}] must be a table")
    return section


def local_paths(args: argparse.Namespace, config: dict[str, Any]) -> tuple[Path, Path]:
    local = config_section(config, "local")
    data_root = expand_path(
        args.data_root or local.get("data_root") or str(DEFAULT_DATA_ROOT)
    )
    database = expand_path(
        args.database or local.get("database") or str(DEFAULT_DATABASE)
    )
    return data_root, database


def file_format(args: argparse.Namespace, config: dict[str, Any]) -> str:
    local = config_section(config, "local")
    selected = args.file_format or local.get("file_format") or "auto"
    if selected not in {"auto", "parquet", "csv"}:
        raise SystemExit("file_format must be one of: auto, parquet, csv")
    return selected


def csv_options(args: argparse.Namespace, config: dict[str, Any]) -> tuple[int, bool]:
    local = config_section(config, "local")
    max_line_size = args.csv_max_line_size
    if max_line_size is None:
        max_line_size = local.get("csv_max_line_size", DEFAULT_CSV_MAX_LINE_SIZE)
    try:
        max_line_size = int(max_line_size)
    except (TypeError, ValueError) as exc:
        raise SystemExit("csv_max_line_size must be an integer byte count") from exc
    if max_line_size <= 0:
        raise SystemExit("csv_max_line_size must be positive")

    relaxed = bool(args.csv_relaxed or local.get("csv_relaxed", False))
    return max_line_size, relaxed


def list_files(data_root: Path, pattern: str) -> list[Path]:
    if not data_root.exists():
        return []
    return sorted(path for path in data_root.rglob(pattern) if path.is_file())


def csv_files(data_root: Path) -> list[Path]:
    return list_files(data_root, "*.csv") + list_files(data_root, "*.csv.gz")


def get_duckdb_module():
    try:
        import duckdb  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "DuckDB is not available. Run this script with uv, for example:\n"
            "  uv run ~/.claude/skills/azure-cost-duckdb/scripts/azure_cost_duckdb.py --help"
        ) from exc
    return duckdb


def combine_prefix(prefix: str | None, pattern: str) -> str:
    clean_prefix = (prefix or "").strip("/")
    if not clean_prefix:
        return pattern
    return f"{clean_prefix}/{pattern.lstrip('/')}"


def redacted_command(command: list[str]) -> str:
    rendered: list[str] = []
    skip_next = False
    sensitive_flags = {"--sas-token", "--account-key", "--connection-string"}

    for index, part in enumerate(command):
        if skip_next:
            skip_next = False
            continue
        if part in sensitive_flags:
            rendered.extend([part, "REDACTED"])
            skip_next = index + 1 < len(command)
            continue
        if "sig=" in part:
            rendered.append(re.sub(r"([?&]sig=)[^&]+", r"\1REDACTED", part))
            continue
        rendered.append(part)

    return shlex.join(rendered)


def run_checked(command: list[str]) -> None:
    print(redacted_command(command))
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def input_files(data_root: Path, selected_format: str) -> tuple[str, list[Path]]:
    parquet_files = list_files(data_root, "*.parquet")
    csv_export_files = csv_files(data_root)

    if selected_format == "parquet":
        return "parquet", parquet_files
    if selected_format == "csv":
        return "csv", csv_export_files
    if parquet_files:
        return "parquet", parquet_files
    return "csv", csv_export_files


def create_views(
    conn: Any,
    data_root: Path,
    view: str,
    selected_format: str = "auto",
    csv_dateformat: str = DEFAULT_CSV_DATEFORMAT,
    csv_max_line_size: int = DEFAULT_CSV_MAX_LINE_SIZE,
    csv_relaxed: bool = False,
) -> tuple[str, int]:
    view = sql_ident(view)
    files_view = sql_ident(f"{view}_files")
    resolved_format, files = input_files(data_root, selected_format)
    if not files:
        return resolved_format, 0

    if resolved_format == "parquet":
        data_glob = data_root.resolve() / "**" / "*.parquet"
        reader = f"""
            read_parquet(
                '{sql_string(data_glob)}',
                hive_partitioning = true,
                union_by_name = true,
                filename = true
            )
        """
    else:
        data_glob = data_root.resolve() / "**" / "*.csv*"
        relaxed_options = ""
        if csv_relaxed:
            relaxed_options = """
                ,
                strict_mode = false,
                ignore_errors = true
            """
        reader = f"""
            read_csv(
                '{sql_string(data_glob)}',
                union_by_name = true,
                filename = true,
                dateformat = '{sql_string(csv_dateformat)}',
                max_line_size = {csv_max_line_size}
                {relaxed_options}
            )
        """

    conn.execute(f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM {reader}")
    conn.execute(
        f"""
        CREATE OR REPLACE VIEW {files_view} AS
        SELECT filename, count(*) AS row_count
        FROM {view}
        GROUP BY filename
        ORDER BY filename
        """
    )
    return resolved_format, len(files)


def connect_database(database: Path):
    if str(database) != ":memory:":
        database.parent.mkdir(parents=True, exist_ok=True)
    duckdb = get_duckdb_module()
    try:
        return duckdb.connect(str(database))
    except duckdb.IOException as exc:
        if "Conflicting lock" in str(exc):
            raise SystemExit(
                f"DuckDB database is locked: {database}\n"
                "Run helper commands sequentially or use a different --database path."
            ) from exc
        raise


def init_sql_text(
    data_root: Path,
    view: str = DEFAULT_VIEW,
    selected_format: str = "parquet",
    csv_dateformat: str = DEFAULT_CSV_DATEFORMAT,
    csv_max_line_size: int = DEFAULT_CSV_MAX_LINE_SIZE,
    csv_relaxed: bool = False,
) -> str:
    view = sql_ident(view)
    files_view = sql_ident(f"{view}_files")
    if selected_format == "csv":
        data_glob = data_root.expanduser().resolve() / "**" / "*.csv*"
        relaxed_options = ""
        if csv_relaxed:
            relaxed_options = """
    ,
    strict_mode = false,
    ignore_errors = true"""
        reader = f"""read_csv(
    '{sql_string(data_glob)}',
    union_by_name = true,
    filename = true,
    dateformat = '{sql_string(csv_dateformat)}',
    max_line_size = {csv_max_line_size}{relaxed_options}
)"""
    else:
        data_glob = data_root.expanduser().resolve() / "**" / "*.parquet"
        reader = f"""read_parquet(
    '{sql_string(data_glob)}',
    hive_partitioning = true,
    union_by_name = true,
    filename = true
)"""

    return f"""CREATE OR REPLACE VIEW {view} AS
SELECT *
FROM {reader};

CREATE OR REPLACE VIEW {files_view} AS
SELECT filename, count(*) AS row_count
FROM {view}
GROUP BY filename
ORDER BY filename;
"""


def render_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date, Decimal)):
        return str(value)
    return str(value)


def print_table(columns: list[str], rows: list[tuple[Any, ...]]) -> None:
    values = [[render_value(value) for value in row] for row in rows]
    widths = [len(column) for column in columns]
    for row in values:
        for idx, value in enumerate(row):
            widths[idx] = min(max(widths[idx], len(value)), 80)

    def trim(value: str, width: int) -> str:
        if len(value) <= width:
            return value
        return value[: max(width - 1, 0)] + "..."

    header = "  ".join(column.ljust(widths[idx]) for idx, column in enumerate(columns))
    print(header)
    print("  ".join("-" * width for width in widths))
    for row in values:
        print(
            "  ".join(
                trim(value, widths[idx]).ljust(widths[idx])
                for idx, value in enumerate(row)
            )
        )


def output_rows(
    columns: list[str], rows: list[tuple[Any, ...]], output_format: str
) -> None:
    if output_format == "json":
        records = [dict(zip(columns, row, strict=True)) for row in rows]
        print(json.dumps(records, indent=2, default=str))
        return

    if output_format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(columns)
        writer.writerows(rows)
        return

    print_table(columns, rows)


def fetch_and_print(conn: Any, sql: str, output_format: str) -> None:
    cursor = conn.execute(sql)
    if cursor.description is None:
        print("OK")
        return

    rows = cursor.fetchall()
    columns = [column[0] for column in cursor.description]
    output_rows(columns, rows, output_format)


def resolve_latest_run_prefix(
    account_name: str | None,
    source: str,
    auth_mode: str,
    prefix: str,
) -> str:
    if source.startswith("http://") or source.startswith("https://"):
        raise SystemExit("--latest-run requires a container name, not a container URL.")
    if not account_name:
        raise SystemExit("--latest-run requires --account-name or storage.account_name.")

    base_prefix = prefix.strip("/")
    if not base_prefix:
        raise SystemExit("--latest-run requires --prefix or storage.prefix.")
    base = f"{base_prefix}/"

    command = [
        "az",
        "storage",
        "blob",
        "list",
        "--account-name",
        account_name,
        "--container-name",
        source,
        "--auth-mode",
        auth_mode,
        "--prefix",
        base,
        "--query",
        "[].name",
        "--output",
        "json",
    ]
    print(redacted_command(command), file=sys.stderr)
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)

    names = json.loads(result.stdout)
    run_children: dict[str, set[str]] = {}
    for name in names:
        if not isinstance(name, str) or not name.startswith(base):
            continue
        parts = name[len(base):].split("/")
        if len(parts) >= 3:
            run_children.setdefault(parts[0], set()).add(parts[1])

    if not run_children:
        raise SystemExit(f"No export run directories found under {base_prefix}")

    latest_run = sorted(run_children)[-1]
    children = sorted(run_children[latest_run])
    if len(children) == 1:
        latest_prefix = f"{base_prefix}/{latest_run}/{children[0]}"
    else:
        latest_prefix = f"{base_prefix}/{latest_run}"

    print(f"Resolved latest run prefix: {latest_prefix}", file=sys.stderr)
    return latest_prefix


def cmd_sync(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    storage = config_section(config, "storage")
    data_root, _database = local_paths(args, config)
    data_root.mkdir(parents=True, exist_ok=True)

    account_name = (
        args.account_name
        or storage.get("account_name")
        or os.environ.get("AZURE_STORAGE_ACCOUNT")
    )
    source = args.container or storage.get("container") or storage.get("container_url")
    if not source:
        raise SystemExit(
            "Missing container. Pass --container or set storage.container in config."
        )

    auth_mode = args.auth_mode or storage.get("auth_mode") or "login"
    prefix = args.prefix if args.prefix is not None else storage.get("prefix", "")
    if args.latest_run:
        prefix = resolve_latest_run_prefix(account_name, source, auth_mode, prefix)
    configured_patterns = storage.get("patterns", DEFAULT_PATTERNS)
    patterns = args.pattern or configured_patterns
    if isinstance(patterns, str):
        patterns = [patterns]
    if not isinstance(patterns, list) or not all(
        isinstance(pattern, str) for pattern in patterns
    ):
        raise SystemExit("Patterns must be strings")

    if shutil.which("az") is None:
        raise SystemExit("Azure CLI not found. Install it and run `az login` first.")

    for pattern in patterns:
        command = [
            "az",
            "storage",
            "blob",
            "download-batch",
            "--source",
            source,
            "--destination",
            str(data_root),
            "--auth-mode",
            auth_mode,
            "--pattern",
            combine_prefix(prefix, pattern),
            "--max-connections",
            str(args.max_connections),
            "--no-progress",
        ]
        if account_name:
            command.extend(["--account-name", account_name])
        if args.dry_run:
            command.append("--dryrun")
        if not args.no_overwrite:
            command.extend(["--overwrite", "true"])

        run_checked(command)

    parquet_files = list_files(data_root, "*.parquet")
    local_csv_files = csv_files(data_root)
    manifest_files = list_files(data_root, "*manifest*.json")
    total_bytes = sum(path.stat().st_size for path in parquet_files + local_csv_files)
    print(
        f"Local cache: {len(parquet_files)} Parquet files, "
        f"{len(local_csv_files)} CSV files, "
        f"{len(manifest_files)} manifests, {human_bytes(total_bytes)} in {data_root}"
    )


def cmd_query(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    data_root, database = local_paths(args, config)
    selected_format = file_format(args, config)
    csv_max_line_size, csv_relaxed = csv_options(args, config)
    sql = args.sql
    if not sql:
        if sys.stdin.isatty():
            raise SystemExit("Pass --sql or pipe SQL on stdin.")
        sql = sys.stdin.read()

    resolved_format, files = input_files(data_root, selected_format)
    if not files and args.view.lower() in sql.lower():
        raise SystemExit(
            f"No {resolved_format} files found under {data_root}. Run the sync command first."
        )

    conn = connect_database(database)
    try:
        if files:
            create_views(
                conn,
                data_root,
                args.view,
                selected_format,
                args.csv_dateformat,
                csv_max_line_size,
                csv_relaxed,
            )
        fetch_and_print(conn, sql, args.format)
    finally:
        conn.close()


def cmd_schema(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    data_root, database = local_paths(args, config)
    selected_format = file_format(args, config)
    csv_max_line_size, csv_relaxed = csv_options(args, config)
    resolved_format, files = input_files(data_root, selected_format)
    if not files:
        raise SystemExit(
            f"No {resolved_format} files found under {data_root}. Run the sync command first."
        )

    conn = connect_database(database)
    try:
        create_views(
            conn,
            data_root,
            args.view,
            selected_format,
            args.csv_dateformat,
            csv_max_line_size,
            csv_relaxed,
        )
        fetch_and_print(conn, f"DESCRIBE {sql_ident(args.view)}", args.format)
    finally:
        conn.close()


def cmd_stats(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    data_root, database = local_paths(args, config)
    selected_format = file_format(args, config)
    csv_max_line_size, csv_relaxed = csv_options(args, config)
    parquet_files = list_files(data_root, "*.parquet")
    local_csv_files = csv_files(data_root)
    manifest_files = list_files(data_root, "*manifest*.json")
    resolved_format, files = input_files(data_root, selected_format)
    total_bytes = sum(path.stat().st_size for path in parquet_files + local_csv_files)

    print(f"data_root: {data_root}")
    print(f"database: {database}")
    print(f"query_format: {resolved_format}")
    print(f"parquet_files: {len(parquet_files)}")
    print(f"csv_files: {len(local_csv_files)}")
    print(f"manifest_files: {len(manifest_files)}")
    print(f"data_bytes: {total_bytes} ({human_bytes(total_bytes)})")

    if args.count_rows and files:
        conn = connect_database(database)
        try:
            create_views(
                conn,
                data_root,
                args.view,
                selected_format,
                args.csv_dateformat,
                csv_max_line_size,
                csv_relaxed,
            )
            rows = conn.execute(
                f"SELECT count(*) FROM {sql_ident(args.view)}"
            ).fetchone()[0]
            print(f"rows: {rows}")
        finally:
            conn.close()


def cmd_init_sql(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    data_root, _database = local_paths(args, config)
    selected_format = file_format(args, config)
    csv_max_line_size, csv_relaxed = csv_options(args, config)
    if selected_format == "auto":
        selected_format = "parquet"
    print(
        init_sql_text(
            data_root,
            args.view,
            selected_format,
            args.csv_dateformat,
            csv_max_line_size,
            csv_relaxed,
        ),
        end="",
    )


def scan_csv_file(path: Path) -> tuple[int, int, int]:
    line_count = 0
    nul_count = 0
    max_line_size = 0
    current_line_size = 0

    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            nul_count += chunk.count(b"\0")
            parts = chunk.split(b"\n")
            line_count += len(parts) - 1
            if len(parts) == 1:
                current_line_size += len(chunk)
                continue

            max_line_size = max(max_line_size, current_line_size + len(parts[0]))
            if len(parts) > 2:
                max_line_size = max(max_line_size, *(len(part) for part in parts[1:-1]))
            current_line_size = len(parts[-1])

    max_line_size = max(max_line_size, current_line_size)
    return line_count, nul_count, max_line_size


def cmd_validate(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    data_root, _database = local_paths(args, config)
    _selected_format = file_format(args, config)
    csv_max_line_size, _csv_relaxed = csv_options(args, config)
    local_csv_files = csv_files(data_root)
    manifest_files = list_files(data_root, "*manifest*.json")

    print(f"data_root: {data_root}")
    print(f"csv_files: {len(local_csv_files)}")
    print(f"manifest_files: {len(manifest_files)}")
    if not local_csv_files:
        return

    total_lines = 0
    total_nuls = 0
    largest_line = 0
    problem_files: list[tuple[Path, int, int]] = []

    for path in local_csv_files:
        line_count, nul_count, max_line_size = scan_csv_file(path)
        total_lines += line_count
        total_nuls += nul_count
        largest_line = max(largest_line, max_line_size)
        if nul_count or max_line_size > csv_max_line_size:
            problem_files.append((path, nul_count, max_line_size))

    print(f"csv_lines: {total_lines}")
    print(f"csv_data_rows_by_lines: {total_lines - len(local_csv_files)}")
    print(f"csv_nul_bytes: {total_nuls}")
    print(f"csv_max_line_size_config: {csv_max_line_size}")
    print(f"csv_largest_line_bytes: {largest_line}")
    print(f"csv_problem_files: {len(problem_files)}")

    for path, nul_count, max_line_size in problem_files:
        relative = path.relative_to(data_root) if path.is_relative_to(data_root) else path
        print(
            f"{relative}\tnul_bytes={nul_count}\tmax_line_bytes={max_line_size}"
        )


def cmd_doctor(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    data_root, database = local_paths(args, config)
    az = shutil.which("az")
    duckdb = get_duckdb_module()
    parquet_files = list_files(data_root, "*.parquet")
    local_csv_files = csv_files(data_root)

    print(f"az: {az or 'not found'}")
    print(f"duckdb_python: {duckdb.__version__}")
    print(f"data_root: {data_root}")
    print(f"database: {database}")
    print(f"parquet_files: {len(parquet_files)}")
    print(f"csv_files: {len(local_csv_files)}")

    if args.azure_account and az:
        result = subprocess.run(
            ["az", "account", "show", "--output", "json"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("azure_login: unavailable")
            if result.stderr:
                print(result.stderr.strip(), file=sys.stderr)
        else:
            account = json.loads(result.stdout)
            print(f"azure_login: {account.get('user', {}).get('name', 'unknown')}")
            print(f"azure_subscription: {account.get('name', 'unknown')}")


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--config",
        default=os.environ.get("AZURE_COST_DUCKDB_CONFIG"),
        help="TOML config path. Defaults to AZURE_COST_DUCKDB_CONFIG if set.",
    )
    common.add_argument(
        "--data-root",
        help=f"Local export cache root. Default: {DEFAULT_DATA_ROOT}",
    )
    common.add_argument(
        "--database",
        "--db",
        dest="database",
        help=f"DuckDB database path. Default: {DEFAULT_DATABASE}",
    )
    common.add_argument(
        "--view",
        default=DEFAULT_VIEW,
        help=f"DuckDB view name for cost rows. Default: {DEFAULT_VIEW}",
    )
    common.add_argument(
        "--file-format",
        choices=["auto", "parquet", "csv"],
        default=None,
        help="Input format for DuckDB views. Default: auto.",
    )
    common.add_argument(
        "--csv-dateformat",
        default=DEFAULT_CSV_DATEFORMAT,
        help="DuckDB dateformat for CSV exports. Default: %(default)s",
    )
    common.add_argument(
        "--csv-max-line-size",
        type=int,
        default=None,
        help=f"Maximum CSV line size in bytes. Default: {DEFAULT_CSV_MAX_LINE_SIZE}",
    )
    common.add_argument(
        "--csv-relaxed",
        action="store_true",
        help="Use relaxed DuckDB CSV parsing for malformed export rows.",
    )

    parser = argparse.ArgumentParser(
        description="Download Azure Cost Management exports and query them with DuckDB."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync = subparsers.add_parser(
        "sync", parents=[common], help="Download export blobs from Azure Storage."
    )
    sync.add_argument("--account-name", help="Azure Storage account name.")
    sync.add_argument(
        "--container",
        help="Source container name or container URL for az storage blob download-batch.",
    )
    sync.add_argument(
        "--prefix",
        default=None,
        help="Blob prefix for the export directory, such as cost/focus.",
    )
    sync.add_argument(
        "--auth-mode",
        choices=["login", "key"],
        default=None,
        help="Azure Storage auth mode. Default: login.",
    )
    sync.add_argument(
        "--pattern",
        action="append",
        help="Blob pattern to download. Repeatable. Defaults to Parquet, CSV, and manifest files.",
    )
    sync.add_argument(
        "--max-connections",
        type=int,
        default=8,
        help="Parallel download connections per pattern.",
    )
    sync.add_argument(
        "--dry-run",
        action="store_true",
        help="Ask Azure CLI to show planned downloads without transferring data.",
    )
    sync.add_argument(
        "--latest-run",
        action="store_true",
        help="Resolve --prefix to the lexicographically latest export run directory before downloading.",
    )
    sync.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Do not overwrite local files during download.",
    )
    sync.set_defaults(func=cmd_sync)

    query = subparsers.add_parser(
        "query", parents=[common], help="Run SQL against local Azure cost views."
    )
    query.add_argument("--sql", "-q", help="SQL to execute. Reads stdin if omitted.")
    query.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format.",
    )
    query.set_defaults(func=cmd_query)

    schema = subparsers.add_parser(
        "schema", parents=[common], help="Show the inferred azure_cost view schema."
    )
    schema.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format.",
    )
    schema.set_defaults(func=cmd_schema)

    stats = subparsers.add_parser(
        "stats", parents=[common], help="Show local cache statistics."
    )
    stats.add_argument(
        "--count-rows",
        action="store_true",
        help="Scan Parquet files to count rows.",
    )
    stats.set_defaults(func=cmd_stats)

    validate = subparsers.add_parser(
        "validate",
        parents=[common],
        help="Scan local CSV exports for cache/source-data issues.",
    )
    validate.set_defaults(func=cmd_validate)

    init_sql = subparsers.add_parser(
        "init-sql",
        parents=[common],
        help="Print SQL for creating DuckDB views over the local Parquet cache.",
    )
    init_sql.set_defaults(func=cmd_init_sql)

    doctor = subparsers.add_parser(
        "doctor", parents=[common], help="Check local prerequisites and cache state."
    )
    doctor.add_argument(
        "--azure-account",
        action="store_true",
        help="Also call az account show to verify Azure CLI login.",
    )
    doctor.set_defaults(func=cmd_doctor)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
