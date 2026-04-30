#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "beautifulsoup4>=4.12.0",
#   "requests>=2.32.0",
# ]
# ///
"""
Build and refresh the combined Windows 11 files database (24H2 + 25H2).

The script seeds from the legacy 24H2 database and then:
1) Pulls latest 24H2/25H2 KB + build metadata from Microsoft release history.
2) Downloads missing KB file-info CSVs from support.microsoft.com.
3) Inserts per-version rows by selecting the matching CSV section, falling
   back to the 24H2 section when MS only publishes one (the typical case
   today, since 24H2 and 25H2 share servicing binaries).
4) Creates a combined database with a `version` column.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import requests
from bs4 import BeautifulSoup


RELEASE_HISTORY_URL = (
    "https://learn.microsoft.com/en-us/windows/release-health/"
    "windows11-release-information"
)

TABLE_IDS_BY_VERSION = {
    "25H2": "historyTable_1",
    "24H2": "historyTable_2",
}

SECTION_HEADER_RE = re.compile(
    r"^Windows 11,\s*version\s*(\d{2}H\d)\s+.*$",
    re.IGNORECASE,
)

HELP_URL_TEMPLATE = "https://support.microsoft.com/help/{kb}"
DEFAULT_TIMEOUT = 60
MAX_RETRIES = 3


@dataclass(frozen=True)
class ReleaseEntry:
    version: str
    kb_number: str
    release_date: str
    build: str
    update_type: str


def log(message: str, verbose: bool = True) -> None:
    if verbose:
        print(message)


def classify_update_type(update_code: str) -> str:
    code = update_code.strip().upper()
    if "OOB" in code:
        return "oob"
    if code.endswith("D") or code.endswith("C"):
        return "preview"
    if code.endswith("B"):
        return "standard"
    return "standard"


def fetch_text(session: requests.Session, url: str) -> str:
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            if not response.encoding:
                response.encoding = "utf-8"
            return response.text
        except requests.RequestException as exc:
            last_error = exc
            if attempt == MAX_RETRIES:
                break
            time.sleep(attempt)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def parse_release_entries(html: str) -> List[ReleaseEntry]:
    soup = BeautifulSoup(html, "html.parser")
    entries: List[ReleaseEntry] = []

    for version, table_id in TABLE_IDS_BY_VERSION.items():
        table = soup.select_one(f"table#{table_id}")
        if table is None:
            raise RuntimeError(
                f"Could not find release history table '{table_id}' "
                f"for version {version}"
            )

        for tr in table.select("tr")[1:]:
            tds = [td.get_text(" ", strip=True) for td in tr.select("td")]
            if len(tds) < 5:
                continue

            update_code = tds[1]
            release_date = tds[2]
            build = tds[3]
            kb_text = tds[4]
            kb_match = re.search(r"KB(\d+)", kb_text, re.IGNORECASE)
            if kb_match is None:
                continue

            entries.append(
                ReleaseEntry(
                    version=version,
                    kb_number=f"KB{kb_match.group(1)}",
                    release_date=release_date,
                    build=build,
                    update_type=classify_update_type(update_code),
                )
            )

    deduped = {
        (e.version, e.kb_number, e.build): e
        for e in entries
    }
    return sorted(
        deduped.values(),
        key=lambda e: (e.version, e.release_date, e.build),
    )


def extract_file_info_links(article_html: str) -> Tuple[str, str | None]:
    soup = BeautifulSoup(article_html, "html.parser")
    cu_link = None
    ssu_link = None

    for p in soup.find_all("p"):
        text = " ".join(p.get_text(" ", strip=True).split()).lower()
        links = [
            a["href"]
            for a in p.find_all("a", href=True)
            if "go.microsoft.com/fwlink/" in a["href"]
        ]
        if not links:
            continue

        if (
            "download the file information for cumulative update" in text
            and cu_link is None
        ):
            cu_link = links[0]
        if (
            "download the file information for the ssu" in text
            and ssu_link is None
        ):
            ssu_link = links[0]

    if cu_link is None:
        raise RuntimeError("Could not locate cumulative update file info link")

    return cu_link, ssu_link


def parse_file_info_csv(csv_text: str) -> Dict[str, List[Tuple[str, str, str, str, str]]]:
    sections: Dict[str, List[Tuple[str, str, str, str, str]]] = {}
    current_version: str | None = None

    for raw_line in csv_text.splitlines():
        line = raw_line.lstrip("\ufeff").strip()
        if not line:
            continue

        section_match = SECTION_HEADER_RE.match(line)
        if section_match:
            current_version = section_match.group(1).upper()
            sections.setdefault(current_version, [])
            continue

        if line.startswith('"File name","File version","Date","Time","File size"'):
            continue

        if current_version is None or not line.startswith('"'):
            continue

        try:
            row = next(csv.reader(io.StringIO(line)))
        except csv.Error:
            continue

        if len(row) < 5:
            continue

        sections[current_version].append(
            (row[0], row[1], row[2], row[3], row[4])
        )

    return sections


def select_rows_for_version(
    sections: Dict[str, List[Tuple[str, str, str, str, str]]],
    target_version: str,
) -> Tuple[List[Tuple[str, str, str, str, str]], str]:
    if target_version in sections and sections[target_version]:
        return sections[target_version], target_version

    non_empty_versions = [v for v, rows in sections.items() if rows]
    if len(non_empty_versions) == 1:
        only_version = non_empty_versions[0]
        return sections[only_version], only_version

    if target_version == "25H2" and sections.get("24H2"):
        return sections["24H2"], "24H2"

    raise RuntimeError(
        f"No usable rows for {target_version}. Available sections: "
        f"{', '.join(sorted(non_empty_versions)) or 'none'}"
    )


def create_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE files(
            version TEXT NOT NULL,
            kb_number TEXT NOT NULL,
            release_date TEXT NOT NULL,
            build TEXT NOT NULL,
            update_type TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_version TEXT,
            date TEXT,
            time TEXT,
            file_size TEXT
        )
        """
    )


def create_indexes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX idx_files_version ON files(version);
        CREATE INDEX idx_files_file_name ON files(file_name);
        CREATE INDEX idx_files_kb_number ON files(kb_number);
        CREATE INDEX idx_files_build ON files(build);
        CREATE INDEX idx_files_file_version ON files(file_version);
        """
    )


def copy_legacy_24h2_rows(
    conn: sqlite3.Connection,
    legacy_db_path: Path,
) -> int:
    escaped = str(legacy_db_path).replace("'", "''")
    conn.execute(f"ATTACH DATABASE '{escaped}' AS legacy")
    conn.execute(
        """
        INSERT INTO files(
            version, kb_number, release_date, build, update_type,
            file_name, file_version, date, time, file_size
        )
        SELECT
            '24H2', kb_number, release_date, build, update_type,
            file_name, file_version, date, time, file_size
        FROM legacy.files
        """
    )
    copied = conn.execute("SELECT changes()").fetchone()[0]
    conn.commit()
    conn.execute("DETACH DATABASE legacy")
    return copied


def get_existing_builds(
    conn: sqlite3.Connection,
) -> set[Tuple[str, str, str]]:
    rows = conn.execute(
        """
        SELECT version, kb_number, build
        FROM files
        GROUP BY version, kb_number, build
        """
    ).fetchall()
    return {(row[0], row[1], row[2]) for row in rows}


def get_kb_payloads(
    session: requests.Session,
    kb_number: str,
    cache: Dict[str, Tuple[Dict[str, List[Tuple[str, str, str, str, str]]], Dict[str, List[Tuple[str, str, str, str, str]]]]],
    verbose: bool,
) -> Tuple[Dict[str, List[Tuple[str, str, str, str, str]]], Dict[str, List[Tuple[str, str, str, str, str]]]]:
    if kb_number in cache:
        return cache[kb_number]

    kb_digits = re.sub(r"^KB", "", kb_number, flags=re.IGNORECASE)
    article_url = HELP_URL_TEMPLATE.format(kb=kb_digits)
    log(f"  Fetching {kb_number} metadata", verbose)
    article_html = fetch_text(session, article_url)
    cu_link, ssu_link = extract_file_info_links(article_html)

    cu_sections = parse_file_info_csv(fetch_text(session, cu_link))
    ssu_sections: Dict[str, List[Tuple[str, str, str, str, str]]] = {}
    if ssu_link:
        ssu_sections = parse_file_info_csv(fetch_text(session, ssu_link))

    cache[kb_number] = (cu_sections, ssu_sections)
    return cache[kb_number]


def insert_payload_rows(
    conn: sqlite3.Connection,
    version: str,
    entry: ReleaseEntry,
    update_type: str,
    rows: Iterable[Tuple[str, str, str, str, str]],
) -> int:
    payload = [
        (
            version,
            entry.kb_number,
            entry.release_date,
            entry.build,
            update_type,
            file_name,
            file_version,
            row_date,
            row_time,
            file_size,
        )
        for (file_name, file_version, row_date, row_time, file_size) in rows
    ]

    if not payload:
        return 0

    conn.executemany(
        """
        INSERT INTO files(
            version, kb_number, release_date, build, update_type,
            file_name, file_version, date, time, file_size
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        payload,
    )
    return len(payload)


def ensure_entry(
    conn: sqlite3.Connection,
    session: requests.Session,
    entry: ReleaseEntry,
    payload_cache: Dict[str, Tuple[Dict[str, List[Tuple[str, str, str, str, str]]], Dict[str, List[Tuple[str, str, str, str, str]]]]],
    verbose: bool,
) -> int:
    cu_sections, ssu_sections = get_kb_payloads(
        session=session,
        kb_number=entry.kb_number,
        cache=payload_cache,
        verbose=verbose,
    )

    cu_rows, cu_source = select_rows_for_version(cu_sections, entry.version)
    log(
        f"  Inserting {entry.version} {entry.kb_number} {entry.build} "
        f"(CU source={cu_source}, rows={len(cu_rows)})",
        verbose,
    )
    inserted = insert_payload_rows(
        conn=conn,
        version=entry.version,
        entry=entry,
        update_type=entry.update_type,
        rows=cu_rows,
    )

    if ssu_sections:
        ssu_rows, ssu_source = select_rows_for_version(
            ssu_sections, entry.version
        )
        log(
            f"  Inserting {entry.version} {entry.kb_number} {entry.build} "
            f"(SSU source={ssu_source}, rows={len(ssu_rows)})",
            verbose,
        )
        inserted += insert_payload_rows(
            conn=conn,
            version=entry.version,
            entry=entry,
            update_type="ssu",
            rows=ssu_rows,
        )

    return inserted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh Windows 11 files DB with 24H2 + 25H2 data"
    )
    parser.add_argument(
        "--legacy-db",
        default=str(Path.home() / "moz_artifacts" / "win11_24h2_files.db"),
        help="Path to legacy 24H2-only database",
    )
    parser.add_argument(
        "--output-db",
        default=str(Path.home() / "moz_artifacts" / "win11_files.db"),
        help="Path to output combined database",
    )
    parser.add_argument(
        "--release-url",
        default=RELEASE_HISTORY_URL,
        help="Windows 11 release history URL",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce logging",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    verbose = not args.quiet

    legacy_db = Path(args.legacy_db).expanduser()
    output_db = Path(args.output_db).expanduser()
    tmp_db = output_db.with_suffix(output_db.suffix + ".tmp")

    if not legacy_db.exists():
        print(f"Error: legacy DB not found: {legacy_db}", file=sys.stderr)
        return 1

    output_db.parent.mkdir(parents=True, exist_ok=True)
    if tmp_db.exists():
        tmp_db.unlink()

    session = requests.Session()
    session.headers.update(
        {"User-Agent": "win11-files-db-updater/1.0"}
    )

    log("Fetching release history metadata...", verbose)
    release_html = fetch_text(session, args.release_url)
    release_entries = parse_release_entries(release_html)
    entries_24h2 = [e for e in release_entries if e.version == "24H2"]
    entries_25h2 = [e for e in release_entries if e.version == "25H2"]

    if not entries_24h2 or not entries_25h2:
        print(
            "Error: failed to parse 24H2/25H2 release entries.",
            file=sys.stderr,
        )
        return 1

    log(
        f"Parsed release entries: 24H2={len(entries_24h2)}, "
        f"25H2={len(entries_25h2)}",
        verbose,
    )

    conn = sqlite3.connect(tmp_db)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA cache_size=-200000")

        create_schema(conn)
        copied_rows = copy_legacy_24h2_rows(conn, legacy_db)
        log(f"Seeded {copied_rows:,} legacy 24H2 rows", verbose)

        existing_builds = get_existing_builds(conn)
        payload_cache: Dict[
            str,
            Tuple[
                Dict[str, List[Tuple[str, str, str, str, str]]],
                Dict[str, List[Tuple[str, str, str, str, str]]],
            ],
        ] = {}

        # Group entries by KB so each KB's CSV is fetched once and
        # both versions (24H2 + 25H2) share the cached payload.
        entries_by_kb: Dict[str, List[ReleaseEntry]] = {}
        for entry in release_entries:
            entries_by_kb.setdefault(entry.kb_number, []).append(entry)

        inserted_by_version: Dict[str, int] = {"24H2": 0, "25H2": 0}
        for kb_number in sorted(
            entries_by_kb,
            key=lambda kb: min(e.release_date for e in entries_by_kb[kb]),
        ):
            for entry in entries_by_kb[kb_number]:
                key = (entry.version, entry.kb_number, entry.build)
                if key in existing_builds:
                    continue

                try:
                    inserted = ensure_entry(
                        conn=conn,
                        session=session,
                        entry=entry,
                        payload_cache=payload_cache,
                        verbose=verbose,
                    )
                except Exception as exc:  # noqa: BLE001
                    print(
                        f"Warning: skipped {entry.version} "
                        f"{entry.kb_number} {entry.build}: {exc}",
                        file=sys.stderr,
                    )
                    continue
                inserted_by_version[entry.version] = (
                    inserted_by_version.get(entry.version, 0) + inserted
                )
                existing_builds.add(key)
                conn.commit()

        log(
            f"Inserted new rows: 24H2={inserted_by_version['24H2']:,}, "
            f"25H2={inserted_by_version['25H2']:,}",
            verbose,
        )

        create_indexes(conn)
        conn.commit()

        versions = [
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT version FROM files ORDER BY version"
            )
        ]
        total_rows = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        log(
            f"Final DB rows: {total_rows:,} "
            f"(versions: {', '.join(versions)})",
            verbose,
        )
    finally:
        conn.close()

    if output_db.exists():
        output_db.unlink()
    tmp_db.replace(output_db)

    print(f"Updated database: {output_db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
