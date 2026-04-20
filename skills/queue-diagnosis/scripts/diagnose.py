#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""
Diagnose why a Taskcluster worker pool queue is backed up.

Gathers pool status from Taskcluster CLI and demand analysis from BigQuery
(via Redash) in parallel, then outputs a structured JSON diagnostic report.

Usage:
    uv run diagnose.py gecko-t/win11-64-25h2
    uv run diagnose.py gecko-t/win11-64-25h2 --days 5
    uv run diagnose.py gecko-t/win11-64-25h2 --output ~/moz_artifacts/diag.json
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

REDASH_SCRIPT = Path.home() / ".claude" / "skills" / "redash" / "scripts" / "query_redash.py"

TC_ROOT = "https://firefox-ci-tc.services.mozilla.com"
TREEHERDER_ROOT = "https://treeherder.mozilla.org"


def tc_task_group_url(task_group_id: str) -> str:
    return f"{TC_ROOT}/tasks/groups/{task_group_id}"


def tc_pool_url(pool_id: str) -> str:
    return f"{TC_ROOT}/worker-manager/{pool_id}"


def tc_provisioner_url(pool_id: str) -> str:
    provisioner, worker_type = pool_id.split("/", 1)
    return (
        f"{TC_ROOT}/provisioners/{provisioner}"
        f"/worker-types/{worker_type}"
    )


def treeherder_task_group_url(
    project: str, task_group_id: str,
) -> str:
    return (
        f"{TREEHERDER_ROOT}/jobs?repo={project}"
        f"&taskGroupId={task_group_id}"
    )


AUTH_ERROR_MARKERS = ("401", "AuthenticationFailed", "InsufficientScopes")


def run_tc_command(args: list[str]) -> dict:
    """Run a taskcluster CLI command and return parsed JSON.

    Returns {"error": ..., "auth_error": True} on 401/auth failures so
    callers can surface that distinctly from "pool not managed" (which is
    a legitimate 404 for hardware pools).
    """
    result = subprocess.run(
        ["taskcluster", *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        out = {"error": stderr}
        if any(m in stderr for m in AUTH_ERROR_MARKERS):
            out["auth_error"] = True
        return out
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw": result.stdout.strip()}


def list_all_workers(pool_id: str) -> dict:
    """Fetch every worker in a pool, following continuationToken pagination.

    The default page size masks the full stopping-worker cohort on busy
    pools (e.g. a 2000-cap pool returns 1000 per page). The ghost check
    below needs the complete set, and oldest_stopping_age should also be
    computed against the whole list.
    """
    all_workers: list[dict] = []
    token: str | None = None
    for _ in range(20):  # safety cap: 20 pages * 500 = 10k workers
        args = [
            "api", "workerManager", "listWorkersForWorkerPool",
            pool_id, "--limit=500",
        ]
        if token:
            args += ["--continuationToken", token]
        resp = run_tc_command(args)
        if "error" in resp:
            return {"error": resp["error"], "workers": all_workers}
        all_workers.extend(resp.get("workers", []))
        token = resp.get("continuationToken")
        if not token:
            break
    return {"workers": all_workers}


def check_azure_ghosts(
    pool_id: str, provider_id: str, workers: list[dict],
) -> dict | None:
    """Cross-check TC 'stopping' workers against actual Azure VMs.

    Returns None if the pool is not on Azure or az CLI is unavailable so
    callers can skip the section silently. For supported pools, returns a
    dict with ghost_count (TC-tracked workers with no matching Azure VM),
    which is the strongest signal we have that worker-manager has lost
    track of reaped VMs and the inflated current_capacity is not real.
    """
    if not provider_id or not provider_id.startswith("azure"):
        return None
    if not shutil.which("az"):
        return {
            "skipped": "az CLI not found on PATH",
        }
    rg = f"rg-tc-{pool_id.replace('/', '-')}"
    try:
        result = subprocess.run(
            [
                "az", "vm", "list",
                "--resource-group", rg,
                "--query", "[].name",
                "-o", "tsv",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return {"skipped": "az vm list timed out after 60s"}
    if result.returncode != 0:
        return {
            "skipped": (
                f"az vm list failed: {result.stderr.strip()[:200]}"
            ),
            "resource_group": rg,
        }

    az_vms = {
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    }
    tc_stopping = {
        w.get("workerId") for w in workers
        if w.get("state") == "stopping" and w.get("workerId")
    }
    ghosts = tc_stopping - az_vms
    real = tc_stopping & az_vms
    return {
        "resource_group": rg,
        "azure_vms_in_rg": len(az_vms),
        "tc_stopping_count": len(tc_stopping),
        "ghost_count": len(ghosts),
        "real_stopping_count": len(real),
        "ghost_pct": (
            round(len(ghosts) / len(tc_stopping) * 100, 1)
            if tc_stopping else 0
        ),
    }


def run_redash_query(sql: str) -> list[dict]:
    """Run a SQL query via the Redash skill script and return rows."""
    if not REDASH_SCRIPT.exists():
        return [{"error": f"Redash script not found at {REDASH_SCRIPT}"}]

    result = subprocess.run(
        ["uv", "run", str(REDASH_SCRIPT), "--sql", sql, "--format", "json"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        return [{"error": result.stderr.strip()}]
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return [{"error": f"Could not parse output: {result.stdout[:500]}"}]


STOPPING_PCT_NOTEWORTHY_THRESHOLD = 30
OLDEST_STOPPING_AGE_NOTEWORTHY_MINUTES = 60
HEADROOM_PCT_WARN_THRESHOLD = 10

# Per-error-instance identifiers that vary across otherwise-identical
# Azure errors. Stripping these lets similar errors share one bucket
# instead of exploding into N single-count entries.
_NORMALIZE_PATTERNS = [
    (re.compile(r"vm-[a-z0-9]+"), "vm-<ID>"),
    (re.compile(r"deploy-[a-z0-9]+"), "deploy-<ID>"),
    (re.compile(r"rg-[a-z0-9-]+"), "rg-<ID>"),
    (re.compile(r"\d{8}T\d{6}Z"), "<TS>"),
    (
        re.compile(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
            r"[0-9a-f]{4}-[0-9a-f]{12}"
        ),
        "<UUID>",
    ),
]


def _normalize_error(desc: str) -> str:
    """Strip per-instance identifiers so similar errors share one bucket."""
    first_line = desc.split("\n")[0]
    for pattern, replacement in _NORMALIZE_PATTERNS:
        first_line = pattern.sub(replacement, first_line)
    return first_line[:200]


def _format_ghost_fragment(ghost_info: dict | None) -> str:
    """Render the ghost cross-check result as an inline sentence.

    Returns an empty string when the check was skipped (non-Azure pool,
    missing az CLI, or auth failure) so the caller can concat safely.
    """
    if not ghost_info or ghost_info.get("skipped"):
        return ""
    gc = ghost_info.get("ghost_count")
    if gc is None:
        return ""
    return (
        f" Azure cross-check: {gc} of "
        f"{ghost_info.get('tc_stopping_count', 0)} stopping workers "
        f"({ghost_info.get('ghost_pct', 0)}%) have no matching VM in "
        f"{ghost_info.get('resource_group')} — those are confirmed "
        f"worker-manager ghosts."
    )


def _add_supply_health_signals(
    status: dict,
    workers_info: dict,
    ghost_info: dict | None = None,
) -> None:
    """Compute supply-side health signals from pool counts and worker list.

    Emits two classes of findings:
    - 'warnings': high-severity issues blocking active demand. Fire only
      when the pool has pending tasks AND capacity is near-max AND a large
      share of capacity is stopping. This is the "ghosts are blocking new
      provisioning" case.
    - 'notes': informational signals that describe unusual state but are
      not necessarily urgent. A pool with 0 pending tasks and 100%
      stopping is likely just draining between shifts, not blocked.

    Also populates the raw diagnostic fields so Claude can reason about
    them directly:
    - stopping_pct: fraction of currentCapacity in 'stopping' state
    - oldest_stopping_age_minutes: age of the oldest stopping worker
    - capacity_headroom: max_capacity - current_capacity (how many more
      workers worker-manager could request right now)
    """
    warnings = []
    notes = []

    current = status.get("current_capacity") or 0
    stopping = status.get("stopping") or 0
    running = status.get("running") or 0
    pending = status.get("pending_tasks")
    pending_num = pending if isinstance(pending, int) else 0
    max_cap = status.get("max_capacity")
    max_cap_num = max_cap if isinstance(max_cap, int) else None

    stopping_pct = None
    if current > 0:
        stopping_pct = round(stopping / current * 100, 1)
        status["stopping_pct"] = stopping_pct

    headroom = None
    effective_ceiling = None
    if max_cap_num is not None:
        headroom = max_cap_num - current
        status["capacity_headroom"] = headroom
        if max_cap_num > 0:
            headroom_pct = round(headroom / max_cap_num * 100, 1)
            status["capacity_headroom_pct"] = headroom_pct
        # Effective capacity ceiling: what the pool could actually sustain
        # if every 'stopping' worker is a zombie worker-manager cannot
        # reap. When this is far below max_capacity, the reported
        # 'current_capacity' is inflated by ghosts and scale-up looks
        # throttled even when demand could theoretically be served.
        effective_ceiling = max_cap_num - stopping
        status["effective_capacity_ceiling"] = effective_ceiling
        if max_cap_num > 0:
            status["effective_capacity_pct"] = round(
                effective_ceiling / max_cap_num * 100, 1
            )

    # Only compute oldest_stopping_age if the paginated worker list is
    # actually complete. If listWorkersForWorkerPool errored mid-pagination
    # or returned fewer stopping workers than the pool's stoppingCount,
    # any "oldest" we report is computed from a subset and is meaningless —
    # the real oldest could be among the workers we missed. Flag the gap
    # instead of silently reporting a wrong number.
    oldest_age = None
    stopping_seen = None
    if "error" in workers_info:
        notes.append(
            "worker list fetch errored mid-pagination; "
            f"oldest_stopping_age skipped ({workers_info.get('error', '')[:160]})."
        )
    else:
        stopping_workers = [
            w for w in workers_info.get("workers", [])
            if w.get("state") == "stopping"
        ]
        stopping_seen = len(stopping_workers)
        status["stopping_workers_seen"] = stopping_seen

        if stopping is not None and stopping_seen < stopping * 0.95:
            # Allow some slack for in-flight state transitions between the
            # pool_info call and the worker list call, but a real gap means
            # pagination is incomplete — refuse to report a misleading age.
            notes.append(
                f"paginated worker list only returned {stopping_seen} "
                f"stopping workers but pool reports {stopping}; "
                f"oldest_stopping_age skipped because it would be computed "
                f"from an incomplete sample. Raise the pagination page cap "
                f"in list_all_workers if this keeps happening."
            )
        else:
            timestamps = sorted(
                w.get("lastModified", "") for w in stopping_workers
                if w.get("lastModified")
            )
            if timestamps:
                status["oldest_stopping_lastModified"] = timestamps[0]
                try:
                    oldest_dt = datetime.fromisoformat(
                        timestamps[0].replace("Z", "+00:00"),
                    )
                    oldest_age = round(
                        (datetime.now(timezone.utc) - oldest_dt)
                        .total_seconds() / 60,
                        1,
                    )
                    status["oldest_stopping_age_minutes"] = oldest_age
                except (ValueError, AttributeError):
                    pass

    # High-severity: ghosts blocking active demand
    blocking = (
        stopping_pct is not None
        and stopping_pct >= STOPPING_PCT_NOTEWORTHY_THRESHOLD
        and pending_num > 0
        and headroom is not None
        and max_cap_num
        and (headroom / max_cap_num * 100) < HEADROOM_PCT_WARN_THRESHOLD
    )
    if blocking:
        eff_pct = (
            round(effective_ceiling / max_cap_num * 100, 1)
            if effective_ceiling is not None and max_cap_num
            else None
        )
        ghost_frag = _format_ghost_fragment(ghost_info)
        tail = ghost_frag or (
            " If those stopping workers are ghosts (VMs gone from cloud), "
            "they are blocking new provisioning. Cross-reference TC "
            "worker IDs against cloud VMs to confirm."
        )
        warnings.append(
            f"pool has {pending_num} pending tasks but reported capacity "
            f"is {current}/{max_cap_num} "
            f"({round(headroom / max_cap_num * 100, 1)}% headroom). "
            f"{stopping_pct}% of that ({stopping}) is in 'stopping', so "
            f"the effective scale-up ceiling is only "
            f"{effective_ceiling}/{max_cap_num}"
            f"{f' ({eff_pct}%)' if eff_pct is not None else ''}."
            f"{tail}"
        )

    # Informational: unusual state but not urgent
    if stopping_pct is not None and stopping_pct >= STOPPING_PCT_NOTEWORTHY_THRESHOLD and not blocking:
        if pending_num == 0 and running == 0:
            notes.append(
                f"stopping workers are {stopping_pct}% of capacity "
                f"({stopping}/{current}) but pool has 0 pending and 0 "
                f"running. Likely just draining between shifts — not "
                f"urgent unless demand returns before cleanup completes."
            )
        else:
            eff = (
                f", effective ceiling {effective_ceiling}/{max_cap_num}"
                if effective_ceiling is not None and max_cap_num
                else ""
            )
            ghost_frag = _format_ghost_fragment(ghost_info)
            notes.append(
                f"stopping workers are {stopping_pct}% of capacity "
                f"({stopping}/{current}). High but not currently blocking "
                f"demand (pending={pending_num}, headroom={headroom}"
                f"{eff}). Real scale-up ceiling is lower than "
                f"current_capacity suggests — stopping workers inflate the "
                f"reported count without providing usable capacity."
                f"{ghost_frag}"
            )

    if oldest_age is not None and oldest_age >= OLDEST_STOPPING_AGE_NOTEWORTHY_MINUTES:
        msg = (
            f"oldest stopping worker is {oldest_age} min old (threshold "
            f"{OLDEST_STOPPING_AGE_NOTEWORTHY_MINUTES} min). Stuck "
            f"stopping workers usually mean worker-manager cannot reap "
            f"them — check for VMs gone from the cloud provider while TC "
            f"still tracks them."
        )
        if blocking:
            warnings.append(msg)
        else:
            notes.append(msg)

    if warnings:
        status["warnings"] = warnings
    if notes:
        status["notes"] = notes


def get_pool_status(pool_id: str) -> dict:
    """Fetch worker pool config, pending tasks, and provisioning errors.

    The queue pendingTasks API works for all pools. The worker-manager
    APIs only work for pools managed by Taskcluster worker-manager
    (cloud pools). Hardware pools (e.g., releng-hardware/*) return 404
    from worker-manager, so those calls are non-fatal.
    """
    provisioner, worker_type = pool_id.split("/", 1)

    pending_info = run_tc_command([
        "api", "queue", "pendingTasks", pool_id,
    ])
    pool_info = run_tc_command([
        "api", "workerManager", "workerPool", pool_id,
    ])
    errors = run_tc_command([
        "api", "workerManager", "listWorkerPoolErrors", pool_id,
    ])
    workers_info = list_all_workers(pool_id)

    status = {
        "pool_id": pool_id,
        "pending_tasks": pending_info.get("pendingTasks", "unknown"),
    }

    # Fail loud on auth errors rather than silently treating the pool as
    # unmanaged (a hardware pool returns 404, an expired client returns
    # 401 — both used to land in the same branch).
    if any(
        call.get("auth_error")
        for call in (pool_info, errors, workers_info)
    ):
        status["auth_failure"] = True
        status["managed"] = None
        status["error_count"] = "unavailable"
        status["warnings"] = [
            "Taskcluster CLI authentication failed (401). Run "
            "`taskcluster signin` and retry. Supply-side data is "
            "unavailable until credentials are refreshed."
        ]
        return status

    if "error" not in pool_info:
        status["managed"] = True
        status["provider_id"] = pool_info.get("providerId", "unknown")
        status["current_capacity"] = pool_info.get("currentCapacity", 0)
        status["requested"] = pool_info.get("requestedCount", 0)
        status["running"] = pool_info.get("runningCount", 0)
        status["stopping"] = pool_info.get("stoppingCount", 0)
        status["stopped"] = pool_info.get("stoppedCount", 0)

        config = pool_info.get("config", {})
        launch_configs = config.get("launchConfigs", [{}])
        status["max_capacity"] = config.get("maxCapacity", "unknown")
        status["min_capacity"] = config.get("minCapacity", 0)

        if launch_configs:
            lc = launch_configs[0]
            # Azure ARM template pools store VM details in
            # armDeployment.parameters; non-ARM pools use top-level
            # hardwareProfile/priority fields.
            arm_params = (
                lc.get("armDeployment", {}).get("parameters", {})
            )
            status["vm_size"] = (
                arm_params.get("vmSize", {}).get("value")
                or lc.get("hardwareProfile", {}).get("vmSize", "unknown")
            )
            priority = (
                arm_params.get("priority", {}).get("value")
                or lc.get("priority", "unknown")
            )
            eviction = lc.get("evictionPolicy", "unknown")
            if priority == "Spot" or eviction == "Delete":
                status["vm_type"] = "Spot"
            else:
                status["vm_type"] = priority

        # Cross-check stopping workers against Azure VMs. This is the
        # authoritative signal for the "inflated capacity" story — if
        # TC-tracked stopping workers don't exist in Azure, they are
        # phantom records worker-manager failed to reap.
        ghost_info = check_azure_ghosts(
            pool_id,
            status["provider_id"],
            workers_info.get("workers", []),
        )
        if ghost_info:
            status["azure_ghost_check"] = ghost_info

        # Must run after max_capacity is populated so headroom can be
        # computed, and after ghost_info so warnings can cite it.
        _add_supply_health_signals(status, workers_info, ghost_info)
    else:
        # Hardware pools are not managed by worker-manager
        status["managed"] = False

    if "error" not in errors:
        error_list = errors.get("workerPoolErrors", [])
        status["error_count"] = len(error_list)

        timestamps = [
            err.get("reported") for err in error_list
            if err.get("reported")
        ]
        if timestamps:
            status["oldest_error"] = min(timestamps)
            status["newest_error"] = max(timestamps)

        # Bucket by normalized description so per-VM errors collapse into
        # one row. Keep a full-line sample per bucket — the first 120 chars
        # used to truncate away the actionable part (e.g. "...is unlicensed").
        # Also count per region so a single-region quota event isn't
        # mistaken for a pool-wide issue.
        error_summary = {}
        errors_by_region = {}
        for err in error_list:
            desc = err.get("description", "unknown")
            key = _normalize_error(desc)
            bucket = error_summary.setdefault(
                key,
                {"count": 0, "sample": desc.split("\n")[0][:500]},
            )
            bucket["count"] += 1
            region = err.get("extra", {}).get("workerGroup") or "unknown"
            errors_by_region[region] = (
                errors_by_region.get(region, 0) + 1
            )
        # Sort by count desc so the recurring patterns lead; isolated
        # single-event errors fall to the tail where they belong.
        status["errors"] = dict(
            sorted(
                error_summary.items(),
                key=lambda kv: -kv[1]["count"],
            )
        )
        if errors_by_region:
            status["errors_by_region"] = dict(
                sorted(
                    errors_by_region.items(),
                    key=lambda kv: -kv[1],
                )
            )
    else:
        # Hardware pools have no worker-manager error tracking
        status["error_count"] = "n/a"
        if status.get("managed") is not False:
            status["errors"] = errors

    return status


def get_queue_times(pool_id: str, start_date: str, end_date: str) -> dict:
    """Get queue time percentiles for the date range."""
    sql = f"""
WITH base AS (
  SELECT
    tr.task_id,
    tr.run_id,
    tr.state,
    tr.reason_resolved,
    tr.scheduled,
    tr.started
  FROM `moz-fx-data-shared-prod.fxci.task_runs` tr
  JOIN `moz-fx-data-shared-prod.fxci.tasks` t USING (task_id)
  WHERE tr.submission_date BETWEEN DATE '{start_date}' - 1
    AND DATE '{end_date}' + 1
    AND t.submission_date BETWEEN DATE '{start_date}' - 1
    AND DATE '{end_date}' + 1
    AND tr.scheduled >= TIMESTAMP('{start_date} 00:00:00+00')
    AND tr.scheduled < TIMESTAMP('{end_date} 00:00:00+00')
    AND t.task_queue_id = '{pool_id}'
)
SELECT
  COUNT(*) AS total_runs,
  COUNTIF(started IS NOT NULL) AS started_runs,
  APPROX_QUANTILES(
    IF(started IS NOT NULL,
       TIMESTAMP_DIFF(started, scheduled, MILLISECOND), NULL),
    100
  )[OFFSET(50)] AS median_queue_ms,
  APPROX_QUANTILES(
    IF(started IS NOT NULL,
       TIMESTAMP_DIFF(started, scheduled, MILLISECOND), NULL),
    100
  )[OFFSET(90)] AS p90_queue_ms,
  APPROX_QUANTILES(
    IF(started IS NOT NULL,
       TIMESTAMP_DIFF(started, scheduled, MILLISECOND), NULL),
    100
  )[OFFSET(95)] AS p95_queue_ms,
  MAX(
    IF(started IS NOT NULL,
       TIMESTAMP_DIFF(started, scheduled, MILLISECOND), NULL)
  ) AS max_queue_ms,
  COUNTIF(
    state = 'exception' AND reason_resolved = 'deadline-exceeded'
  ) AS expired_count
FROM base
"""
    rows = run_redash_query(sql)
    if rows and "error" not in rows[0]:
        return rows[0]
    return {"error": rows}


def get_daily_volume(
    pool_id: str, start_date: str, end_date: str,
) -> list[dict]:
    """Get daily task counts broken down by project."""
    sql = f"""
SELECT
  DATE(tr.scheduled) AS day,
  t.tags.project AS project,
  COUNT(*) AS task_count,
  COUNTIF(tr.started IS NOT NULL) AS started_count,
  COUNTIF(
    tr.state = 'exception'
    AND tr.reason_resolved = 'deadline-exceeded'
  ) AS expired_count,
  APPROX_QUANTILES(
    IF(tr.started IS NOT NULL,
       TIMESTAMP_DIFF(tr.started, tr.scheduled, MILLISECOND), NULL),
    100
  )[OFFSET(50)] AS median_queue_ms
FROM `moz-fx-data-shared-prod.fxci.task_runs` tr
JOIN `moz-fx-data-shared-prod.fxci.tasks` t USING (task_id)
WHERE tr.submission_date BETWEEN '{start_date}' AND '{end_date}'
  AND t.submission_date BETWEEN '{start_date}' AND '{end_date}'
  AND tr.scheduled >= TIMESTAMP('{start_date} 00:00:00+00')
  AND tr.scheduled < TIMESTAMP('{end_date} 00:00:00+00')
  AND t.task_queue_id = '{pool_id}'
GROUP BY 1, 2
ORDER BY 1, 2
"""
    rows = run_redash_query(sql)
    if rows and "error" in rows[0]:
        return rows
    # Drop telemetry rows with no project tag — usually a single edge-case
    # task per day that pollutes the summary without adding signal.
    return [r for r in rows if r.get("project")]


def get_top_pushers(
    pool_id: str, start_date: str, end_date: str,
) -> list[dict]:
    """Get top task submitters in the date range."""
    sql = f"""
SELECT
  t.tags.project AS project,
  t.tags.created_for_user AS pusher,
  COUNT(DISTINCT t.task_group_id) AS task_groups,
  COUNT(*) AS total_tasks
FROM `moz-fx-data-shared-prod.fxci.task_runs` tr
JOIN `moz-fx-data-shared-prod.fxci.tasks` t USING (task_id)
WHERE tr.submission_date BETWEEN '{start_date}' AND '{end_date}'
  AND t.submission_date BETWEEN '{start_date}' AND '{end_date}'
  AND tr.scheduled >= TIMESTAMP('{start_date} 00:00:00+00')
  AND tr.scheduled < TIMESTAMP('{end_date} 00:00:00+00')
  AND t.task_queue_id = '{pool_id}'
GROUP BY 1, 2
ORDER BY total_tasks DESC
LIMIT 25
"""
    return run_redash_query(sql)


def get_top_task_groups(
    pool_id: str, start_date: str, end_date: str,
) -> list[dict]:
    """Get the largest individual task groups with links."""
    sql = f"""
SELECT
  t.tags.project AS project,
  t.task_group_id,
  t.tags.created_for_user AS pusher,
  COUNT(*) AS total_tasks,
  COUNTIF(tr.started IS NOT NULL) AS started_tasks,
  COUNTIF(
    tr.state = 'exception'
    AND tr.reason_resolved = 'deadline-exceeded'
  ) AS expired_tasks,
  APPROX_QUANTILES(
    IF(tr.started IS NOT NULL,
       TIMESTAMP_DIFF(tr.started, tr.scheduled, MILLISECOND), NULL),
    100
  )[OFFSET(50)] AS median_queue_ms,
  MAX(
    IF(tr.started IS NOT NULL,
       TIMESTAMP_DIFF(tr.started, tr.scheduled, MILLISECOND), NULL)
  ) AS max_queue_ms
FROM `moz-fx-data-shared-prod.fxci.task_runs` tr
JOIN `moz-fx-data-shared-prod.fxci.tasks` t USING (task_id)
WHERE tr.submission_date BETWEEN '{start_date}' AND '{end_date}'
  AND t.submission_date BETWEEN '{start_date}' AND '{end_date}'
  AND tr.scheduled >= TIMESTAMP('{start_date} 00:00:00+00')
  AND tr.scheduled < TIMESTAMP('{end_date} 00:00:00+00')
  AND t.task_queue_id = '{pool_id}'
GROUP BY 1, 2, 3
ORDER BY total_tasks DESC
LIMIT 30
"""
    rows = run_redash_query(sql)
    for row in rows:
        if "error" in row:
            break
        tg = row.get("task_group_id", "")
        project = row.get("project", "")
        row["tc_url"] = tc_task_group_url(tg)
        if project:
            row["treeherder_url"] = treeherder_task_group_url(
                project, tg,
            )
    return rows


def add_pool_links(report: dict, pool_id: str) -> None:
    """Add a links section with clickable URLs for the pool."""
    pool_status = report.get("pool_status", {})
    managed = pool_status.get("managed", True)

    links = {"pending_tasks": tc_provisioner_url(pool_id)}
    if managed:
        links["worker_pool"] = tc_pool_url(pool_id)
    else:
        links["note"] = (
            "This pool is not managed by worker-manager "
            "(hardware pool). No worker-manager dashboard available."
        )
    report["links"] = links


def main():
    parser = argparse.ArgumentParser(
        description="Diagnose worker pool queue backlog",
    )
    parser.add_argument(
        "pool_id",
        help="Worker pool ID (e.g., gecko-t/win11-64-25h2)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Days of history for daily volume (default: 7)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Save report to JSON file",
    )
    args = parser.parse_args()

    if "/" not in args.pool_id:
        print(
            "Error: pool_id must be provisioner/worker-type "
            f"(e.g., gecko-t/win11-64-25h2), got: {args.pool_id}",
            file=sys.stderr,
        )
        sys.exit(1)

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    end_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    qt_start = (now - timedelta(days=3)).strftime("%Y-%m-%d")
    vol_start = (now - timedelta(days=args.days)).strftime("%Y-%m-%d")
    pusher_start = (now - timedelta(days=2)).strftime("%Y-%m-%d")

    print(f"Diagnosing {args.pool_id}...", file=sys.stderr)
    print(
        f"  Queue times: {qt_start} to {today}",
        file=sys.stderr,
    )
    print(
        f"  Daily volume: {vol_start} to {today} ({args.days} days)",
        file=sys.stderr,
    )
    print(
        f"  Top pushers: {pusher_start} to {today} (48h)",
        file=sys.stderr,
    )

    report = {}

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(get_pool_status, args.pool_id): "pool_status",
            pool.submit(
                get_queue_times, args.pool_id, qt_start, today,
            ): "queue_times",
            pool.submit(
                get_daily_volume, args.pool_id, vol_start, end_date,
            ): "daily_volume",
            pool.submit(
                get_top_pushers, args.pool_id, pusher_start, end_date,
            ): "top_pushers",
            pool.submit(
                get_top_task_groups, args.pool_id, pusher_start, end_date,
            ): "top_task_groups",
        }

        for future in as_completed(futures):
            key = futures[future]
            try:
                report[key] = future.result()
                print(f"  {key}: done", file=sys.stderr)
            except Exception as exc:
                report[key] = {"error": str(exc)}
                print(f"  {key}: FAILED ({exc})", file=sys.stderr)

    # Separate unstarted task groups so they don't get buried under the
    # actively-running ones. Unstarted (started=0) groups are typically
    # pending-or-scheduled, worth a distinct look.
    groups = report.get("top_task_groups")
    if isinstance(groups, list):
        started = [
            g for g in groups if (g.get("started_tasks") or 0) > 0
        ]
        unstarted = [
            g for g in groups if g.get("started_tasks") == 0
        ]
        report["top_task_groups"] = started
        if unstarted:
            report["unstarted_task_groups"] = unstarted

    report["generated_at"] = now.isoformat()
    report["pool_id"] = args.pool_id
    add_pool_links(report, args.pool_id)

    output = json.dumps(report, indent=2, default=str)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output)
        print(f"\nReport saved to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
