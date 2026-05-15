#!/usr/bin/env python3
"""Trace Taskcluster VM request-to-generic-worker-ready timing."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


WORKER_METRICS_RE = re.compile(r"WORKER_METRICS\s+({.*})")
MAINTAIN_EVENT_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9_-]+) :: (?P<action>begin|end) - (?P<timestamp>\S+)$"
)
WORKER_METRIC_TYPES = {
    "instanceBoot",
    "instanceReboot",
    "instanceShutdown",
    "workerReady",
    "taskStart",
    "taskFinish",
}
PROMETHEUS_DATASOURCE_UID = "adpvtjmrxoc1sb"


@dataclass(frozen=True)
class Event:
    source: str
    kind: str
    time: datetime
    fields: dict[str, Any]


def parse_time(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    value = re.sub(r"(\.\d{6})\d+([+-]\d\d:\d\d)$", r"\1\2", value)
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def format_time(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def format_delta(start: datetime | None, end: datetime | None) -> str:
    if start is None or end is None:
        return "-"
    seconds = int((end - start).total_seconds())
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{sign}{hours}h{minutes:02d}m{seconds:02d}s"
    return f"{sign}{minutes}m{seconds:02d}s"


def splunk_search_time(value: str | None, default: str, pad_seconds: int) -> str:
    if not value:
        return default
    if re.fullmatch(r"\d+[smhdw]", value):
        return f"-{value}"
    return str(int(parse_time(value).timestamp()) + pad_seconds)


def run_command(args: list[str], input_text: str | None = None) -> str:
    try:
        completed = subprocess.run(
            args,
            check=True,
            input=input_text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        raise SystemExit(f"required command not found: {args[0]}") from None
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        stdout = exc.stdout.strip()
        details = stderr or stdout or f"exit {exc.returncode}"
        raise SystemExit(f"{args[0]} failed: {details}") from None
    return completed.stdout


def tc_events(env: str, worker_id: str, since: str, until: str | None, event_type: str) -> list[Event]:
    args = [
        "tc-logview",
        "query",
        "-e",
        env,
        "--type",
        event_type,
        "--where",
        f"workerId={worker_id}",
        "--json",
    ]
    if re.fullmatch(r"\d+[smhdw]", since):
        args.extend(["--since", since])
    else:
        args.extend(["--from", since])
    if until:
        args.extend(["--to", until])

    events: list[Event] = []
    for line in run_command(args).splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        ts = data.get("ts")
        if ts:
            events.append(Event("tc-logview", event_type, parse_time(ts), data))
    return events


def parse_paperctl_json(output: str) -> list[dict[str, Any]]:
    start = output.find("[")
    if start == -1:
        return []
    return json.loads(output[start:])


def papertrail_worker_metrics(worker_id: str, since: str, until: str | None, limit: int) -> list[Event]:
    paper_since = f"-{since}" if re.fullmatch(r"\d+[smhdw]", since) else since
    args = [
        "paperctl",
        "search",
        f"{worker_id} AND WORKER_METRICS",
        "--since",
        paper_since,
        "--limit",
        str(limit),
        "--output",
        "json",
    ]
    if until:
        args.extend(["--until", until])

    events: list[Event] = []
    for row in parse_paperctl_json(run_command(args)):
        message = row.get("message", "")
        match = WORKER_METRICS_RE.search(message)
        if not match:
            continue
        fields = json.loads(match.group(1))
        if fields.get("workerId") != worker_id:
            continue
        if fields.get("eventType") not in WORKER_METRIC_TYPES:
            continue
        timestamp = fields.get("timestamp")
        if isinstance(timestamp, (int, float)):
            event_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        else:
            event_time = parse_time(row["time"])
        events.append(Event("papertrail", fields.get("eventType", "WORKER_METRICS"), event_time, fields))
    return events


def papertrail_maintain_events(worker_id: str, since: str, until: str | None, limit: int) -> list[Event]:
    paper_since = f"-{since}" if re.fullmatch(r"\d+[smhdw]", since) else since
    args = [
        "paperctl",
        "search",
        f"{worker_id} AND MaintainSystem",
        "--since",
        paper_since,
        "--limit",
        str(limit),
        "--output",
        "json",
    ]
    if until:
        args.extend(["--until", until])

    events: list[Event] = []
    for row in parse_paperctl_json(run_command(args)):
        if row.get("program") != "MaintainSystem":
            continue
        message = row.get("message", "")
        match = MAINTAIN_EVENT_RE.search(message)
        if not match:
            continue
        name = match.group("name")
        action = match.group("action")
        event_time = parse_time(match.group("timestamp"))
        events.append(
            Event(
                "papertrail",
                f"maintain:{name}:{action}",
                event_time,
                {"function": name, "action": action, "severity": row.get("severity")},
            )
        )
    return events


def splunk_events(worker_id: str, since: str, until: str | None) -> list[Event]:
    # Splunk's _time for azure_audit can lag the raw Azure Activity Log `time`
    # field by several minutes. Pad absolute windows and filter on raw time.
    earliest = splunk_search_time(since, "-6h", -3600)
    latest = splunk_search_time(until, "now", 3600)
    spl = f'''search index=azure_audit "{worker_id}" earliest={earliest} latest={latest}
| search operationName="MICROSOFT.COMPUTE/VIRTUALMACHINES/WRITE" OR operationName="MICROSOFT.NETWORK/NETWORKINTERFACES/WRITE"
| rex field=resourceId "(?i)resourcegroups/(?<rg>[^/]+)"
| sort 0 time
| table time operationName resultType resultSignature resourceId rg'''
    harness = f'''
import json
SPL = {json.dumps(spl)}
tabs = list_tabs()
st = next((t for t in tabs if "splunkcloud" in t.get("url", "")), None)
if not st:
    print(json.dumps({{"error": "no Splunk tab open"}}))
else:
    switch_tab(st["targetId"])
    JS = """
(async () => {{
  const csrf = document.cookie.split(";").map(c=>c.trim())
    .find(c=>c.startsWith("splunkweb_csrf_token_"));
  if (!csrf) return JSON.stringify({{error: "missing csrf"}});
  const body = new URLSearchParams({{search: %s, output_mode: "json", max_count: "0"}});
  const r = await fetch("/en-US/splunkd/__raw/services/search/jobs", {{
    method: "POST", credentials: "include",
    headers: {{
      "Content-Type": "application/x-www-form-urlencoded",
      "X-Splunk-Form-Key": csrf.split("=")[1],
      "X-Requested-With": "XMLHttpRequest",
    }},
    body: body.toString(),
  }});
  if (r.status !== 201) return JSON.stringify({{error: "submit", status: r.status, text: await r.text()}});
  const {{sid}} = await r.json();
  for (let i = 0; i < 180; i++) {{
    const sj = await (await fetch(
      "/en-US/splunkd/__raw/services/search/jobs/" + sid + "?output_mode=json",
      {{credentials: "include"}})).json();
    const c = (sj.entry?.[0]?.content) || {{}};
    if (c.dispatchState === "DONE") break;
    if (c.dispatchState === "FAILED") return JSON.stringify({{error: "failed", sid}});
    await new Promise(rs => setTimeout(rs, 1000));
  }}
  const j = await (await fetch(
    "/en-US/splunkd/__raw/services/search/jobs/" + sid + "/results?output_mode=json&count=500",
    {{credentials: "include"}})).json();
  return JSON.stringify({{sid, results: j.results || []}});
}})()
""" % json.dumps(SPL)
    print(js(JS))
'''
    output = run_command(["browser-harness"], input_text=harness)
    data = json.loads(output.strip().splitlines()[-1])
    if data.get("error"):
        raise SystemExit(f"Splunk query failed: {data}")

    events: list[Event] = []
    since_time = None if re.fullmatch(r"\d+[smhdw]", since) else parse_time(since)
    until_time = parse_time(until) if until else None
    for row in data.get("results", []):
        if not row.get("time"):
            continue
        event_time = parse_time(row["time"])
        if since_time and event_time < since_time:
            continue
        if until_time and event_time > until_time:
            continue
        result_type = str(row.get("resultType", "")).lower()
        operation_name = str(row.get("operationName", "")).upper()
        if operation_name.endswith("/VIRTUALMACHINES/WRITE"):
            kind = f"azure-vm-write-{result_type}"
        elif operation_name.endswith("/NETWORKINTERFACES/WRITE"):
            kind = f"azure-nic-write-{result_type}"
        else:
            kind = f"azure-{result_type}"
        events.append(Event("splunk", kind, event_time, row))
    return events


def yardstick_metrics(
    worker_pool_id: str,
    query_time: datetime,
    window: str,
    percentiles: list[float],
) -> dict[str, dict[str, str | None]]:
    queries: dict[str, str] = {}
    for metric in ("registration", "provision", "startup"):
        for percentile in percentiles:
            key = f"{metric}_p{int(percentile * 100):02d}"
            queries[key] = (
                f'histogram_quantile({percentile}, '
                f'sum(increase(fxci_worker_manager_worker_{metric}_seconds_bucket'
                f'{{workerPoolId="{worker_pool_id}"}}[{window}])) by (le))'
            )

    harness = f'''
import json
tabs = list_tabs(include_chrome=False)
st = next((t for t in tabs if "yardstick.mozilla.org" in t.get("url", "")), None)
if not st:
    print(json.dumps({{"error": "no Yardstick tab open"}}))
else:
    switch_tab(st)
    QUERIES = {json.dumps(queries)}
    QUERY_TIME = {int(query_time.timestamp())}
    DATASOURCE = {json.dumps(PROMETHEUS_DATASOURCE_UID)}
    JS = """
(async () => {{
  const out = {{}};
  for (const [name, q] of Object.entries(%s)) {{
    const params = new URLSearchParams({{query: q, time: String(%s)}});
    const url = "/api/datasources/proxy/uid/%s/api/v1/query?" + params.toString();
    const r = await fetch(url, {{credentials: "include"}});
    const j = await r.json();
    out[name] = j.data?.result?.[0]?.value?.[1] ?? null;
  }}
  return JSON.stringify({{results: out}});
}})()
""" % (json.dumps(QUERIES), QUERY_TIME, DATASOURCE)
    print(js(JS))
'''
    output = run_command(["browser-harness"], input_text=harness)
    data = json.loads(output.strip().splitlines()[-1])
    if data.get("error"):
        raise SystemExit(f"Yardstick query failed: {data}")

    out: dict[str, dict[str, str | None]] = {}
    for key, value in data.get("results", {}).items():
        metric, percentile = key.rsplit("_", 1)
        out.setdefault(metric, {})[percentile] = value
    return out


def first_event(events: list[Event], kind: str, after: datetime | None = None) -> Event | None:
    candidates = [event for event in events if event.kind == kind]
    if after is not None:
        candidates = [event for event in candidates if event.time >= after]
    if not candidates:
        return None
    return min(candidates, key=lambda event: event.time)


def next_event(events: list[Event], kind: str, after: datetime) -> Event | None:
    candidates = [event for event in events if event.kind == kind and event.time >= after]
    if not candidates:
        return None
    return min(candidates, key=lambda event: event.time)


def latest_event(events: list[Event], kind: str, before: datetime | None = None) -> Event | None:
    candidates = [event for event in events if event.kind == kind]
    if before is not None:
        candidates = [event for event in candidates if event.time <= before]
    if not candidates:
        return None
    return max(candidates, key=lambda event: event.time)


def worker_pool_from_events(events: list[Event]) -> str | None:
    for event in events:
        value = event.fields.get("workerPoolId")
        if value:
            return str(value)
    return None


def print_event_table(events: list[Event]) -> None:
    print("Events")
    print("time                       source       type                             details")
    print("-------------------------- ------------ -------------------------------- --------------------------------")
    for event in sorted(events, key=lambda item: item.time):
        detail_bits = []
        for key in (
            "function",
            "action",
            "workerPoolId",
            "workerGroup",
            "region",
            "instanceType",
            "registrationDuration",
            "taskId",
            "operationName",
            "resultType",
            "resultSignature",
            "rg",
        ):
            value = event.fields.get(key)
            if value not in (None, ""):
                detail_bits.append(f"{key}={value}")
        print(
            f"{format_time(event.time):26} "
            f"{event.source:12} "
            f"{event.kind:32} "
            f"{', '.join(detail_bits)}"
        )


def print_in_vm_durations(events: list[Event], ready: Event | None) -> None:
    if ready is None:
        return

    set_name_begin = latest_event(events, "maintain:Set-AzVMName:begin", ready.time)
    puppet_begin = latest_event(events, "maintain:Puppet-Run:begin", ready.time)
    puppet_end = latest_event(events, "maintain:Puppet-Run:end", ready.time)
    link_begin = latest_event(events, "maintain:LinkZY2D:begin", ready.time)
    link_end = latest_event(events, "maintain:LinkZY2D:end", ready.time)
    start_runner_begin = latest_event(events, "maintain:Start-WorkerRunner:begin", ready.time)
    start_runner_end = latest_event(events, "maintain:Start-WorkerRunner:end", ready.time)

    if not any((set_name_begin, puppet_begin, puppet_end, link_begin, link_end, start_runner_begin, start_runner_end)):
        return

    print()
    print("In-VM startup durations")
    print(f"latest Set-AzVMName begin -> workerReady:    {format_delta(set_name_begin.time if set_name_begin else None, ready.time)}")
    print(f"latest Puppet-Run begin -> Puppet-Run end:   {format_delta(puppet_begin.time if puppet_begin else None, puppet_end.time if puppet_end else None)}")
    print(f"latest Puppet-Run end -> LinkZY2D end:       {format_delta(puppet_end.time if puppet_end else None, link_end.time if link_end else None)}")
    print(f"latest LinkZY2D begin -> LinkZY2D end:       {format_delta(link_begin.time if link_begin else None, link_end.time if link_end else None)}")
    print(f"latest Start-WorkerRunner begin -> end:      {format_delta(start_runner_begin.time if start_runner_begin else None, start_runner_end.time if start_runner_end else None)}")
    print(f"latest Start-WorkerRunner end -> workerReady:{format_delta(start_runner_end.time if start_runner_end else None, ready.time)}")


def print_boot_cycles(events: list[Event]) -> None:
    boots = sorted([event for event in events if event.kind == "instanceBoot"], key=lambda event: event.time)
    reboots = sorted([event for event in events if event.kind == "instanceReboot"], key=lambda event: event.time)
    if not boots and not reboots:
        return

    print()
    print("Boot/reboot ready cycles")
    if boots:
        print("instanceBoot -> next workerReady")
        for boot in boots[:10]:
            ready = next_event(events, "workerReady", boot.time)
            if ready:
                print(f"  {format_time(boot.time)} -> {format_time(ready.time)}  {format_delta(boot.time, ready.time)}")
    if reboots:
        print("instanceReboot -> next instanceBoot -> next workerReady")
        for reboot in reboots[:10]:
            boot = next_event(events, "instanceBoot", reboot.time)
            ready = next_event(events, "workerReady", boot.time if boot else reboot.time)
            if ready:
                print(
                    f"  {format_time(reboot.time)} -> {format_time(boot.time if boot else None)} -> "
                    f"{format_time(ready.time)}  "
                    f"reboot-to-boot={format_delta(reboot.time, boot.time if boot else None)}, "
                    f"boot-to-ready={format_delta(boot.time if boot else None, ready.time)}, "
                    f"reboot-to-ready={format_delta(reboot.time, ready.time)}"
                )


def print_yardstick_section(worker_pool_id: str, query_time: datetime, window: str, percentiles: list[float]) -> None:
    metrics = yardstick_metrics(worker_pool_id, query_time, window, percentiles)
    print()
    print(f"Yardstick worker-manager histograms ({worker_pool_id}, window={window}, time={format_time(query_time)})")
    print("metric        " + " ".join(f"p{int(p * 100):02d}".rjust(10) for p in percentiles))
    print("------------- " + " ".join("-" * 10 for _ in percentiles))
    for metric in ("registration", "provision", "startup"):
        values = []
        for percentile in percentiles:
            raw = metrics.get(metric, {}).get(f"p{int(percentile * 100):02d}")
            values.append(f"{float(raw):.0f}s".rjust(10) if raw is not None else "-".rjust(10))
        print(f"{metric:13} {' '.join(values)}")
    print()
    print("Note: Yardstick values end at worker-manager registration; they do not include worker-running -> workerReady.")


def parse_percentiles(value: str) -> list[float]:
    percentiles = []
    for item in value.split(","):
        percentile = float(item.strip())
        if percentile > 1:
            percentile = percentile / 100
        if percentile <= 0 or percentile >= 1:
            raise argparse.ArgumentTypeError("percentiles must be between 0 and 1, or 1 and 100")
        percentiles.append(percentile)
    return percentiles


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worker_id", help="Taskcluster workerId / Azure VM name")
    parser.add_argument("--env", default="fx-ci", help="tc-logview environment")
    parser.add_argument("--since", default="6h", help="relative or absolute start time")
    parser.add_argument("--until", help="absolute end time")
    parser.add_argument("--papertrail-limit", type=int, default=200)
    parser.add_argument("--splunk", action="store_true", help="include Azure Activity Log VM/NIC events via Splunk Web")
    parser.add_argument("--yardstick", action="store_true", help="include pool-level Yardstick Prometheus histogram quantiles")
    parser.add_argument("--worker-pool-id", help="workerPoolId for Yardstick, e.g. gecko-t/win11-64-25h2")
    parser.add_argument("--yardstick-time", help="absolute query time; defaults to workerReady time, then now")
    parser.add_argument("--yardstick-window", default="1h", help="Prometheus increase window for Yardstick metrics")
    parser.add_argument("--yardstick-percentiles", type=parse_percentiles, default=parse_percentiles("0.50,0.95"))
    args = parser.parse_args()

    events: list[Event] = []
    for event_type in ("worker-requested", "worker-running", "task-claimed"):
        events.extend(tc_events(args.env, args.worker_id, args.since, args.until, event_type))
    events.extend(papertrail_worker_metrics(args.worker_id, args.since, args.until, args.papertrail_limit))
    events.extend(papertrail_maintain_events(args.worker_id, args.since, args.until, args.papertrail_limit))
    if args.splunk:
        events.extend(splunk_events(args.worker_id, args.since, args.until))

    if not events:
        print(f"No events found for {args.worker_id}", file=sys.stderr)
        return 1

    requested = first_event(events, "worker-requested")
    running = first_event(events, "worker-running", requested.time if requested else None)
    boot = first_event(events, "instanceBoot", requested.time if requested else None)
    ready = first_event(events, "workerReady", requested.time if requested else None)
    first_claim = first_event(events, "task-claimed", requested.time if requested else None)
    first_task_start = first_event(events, "taskStart", requested.time if requested else None)
    azure_vm_start = first_event(events, "azure-vm-write-start")
    azure_vm_accept = first_event(events, "azure-vm-write-accept")
    azure_vm_success = first_event(events, "azure-vm-write-success")

    print(f"Worker: {args.worker_id}")
    print_event_table(events)
    print()
    print("Durations")
    print(f"azure VM write start -> workerReady:  {format_delta(azure_vm_start.time if azure_vm_start else None, ready.time if ready else None)}")
    print(f"azure VM write accept -> workerReady: {format_delta(azure_vm_accept.time if azure_vm_accept else None, ready.time if ready else None)}")
    print(f"azure VM write success -> workerReady:{format_delta(azure_vm_success.time if azure_vm_success else None, ready.time if ready else None)}")
    print(f"worker-requested -> worker-running: {format_delta(requested.time if requested else None, running.time if running else None)}")
    print(f"worker-requested -> instanceBoot:    {format_delta(requested.time if requested else None, boot.time if boot else None)}")
    print(f"instanceBoot     -> workerReady:     {format_delta(boot.time if boot else None, ready.time if ready else None)}")
    print(f"worker-running   -> workerReady:     {format_delta(running.time if running else None, ready.time if ready else None)}")
    print(f"worker-requested -> workerReady:     {format_delta(requested.time if requested else None, ready.time if ready else None)}")
    print(f"workerReady      -> first taskStart: {format_delta(ready.time if ready else None, first_task_start.time if first_task_start else None)}")
    print(f"workerReady      -> first task-claim:{format_delta(ready.time if ready else None, first_claim.time if first_claim else None)}")
    print_in_vm_durations(events, ready)
    print_boot_cycles(events)

    if args.yardstick:
        worker_pool_id = args.worker_pool_id or worker_pool_from_events(events)
        if not worker_pool_id:
            raise SystemExit("Yardstick query needs --worker-pool-id; no workerPoolId found in events")
        if args.yardstick_time:
            query_time = parse_time(args.yardstick_time)
        elif ready:
            query_time = ready.time
        else:
            query_time = datetime.now(timezone.utc)
        print_yardstick_section(worker_pool_id, query_time, args.yardstick_window, args.yardstick_percentiles)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
