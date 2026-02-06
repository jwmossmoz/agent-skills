# Windows Version Analysis

Queries for analyzing Windows version distribution among Firefox users.

## Table of Contents

- [Quick Queries](#quick-queries)
- [Detailed Analysis](#detailed-analysis)
- [Build Number Reference](#build-number-reference)
- [Aggregate View Details](#aggregate-view-details)

## Quick Queries

### Overall Windows version distribution

```bash
bq query --project_id=mozdata --use_legacy_sql=false --format=pretty "
SELECT
  build_group,
  SUM(count) AS client_days,
  ROUND(SUM(count) * 100.0 / (
    SELECT SUM(count) FROM \`moz-fx-data-shared-prod.telemetry.windows_10_aggregate\`
    WHERE normalized_channel = 'release'
  ), 2) AS percent_of_total
FROM \`moz-fx-data-shared-prod.telemetry.windows_10_aggregate\`
WHERE normalized_channel = 'release'
GROUP BY build_group
ORDER BY client_days DESC
"
```

### Windows 10 vs Windows 11 split

```bash
bq query --project_id=mozdata --use_legacy_sql=false --format=pretty "
SELECT
  CASE
    WHEN build_group LIKE 'Win10%' THEN 'Windows 10'
    WHEN build_group LIKE 'Win11%' THEN 'Windows 11'
  END AS windows_major,
  SUM(count) AS client_days,
  ROUND(SUM(count) * 100.0 / (
    SELECT SUM(count) FROM \`moz-fx-data-shared-prod.telemetry.windows_10_aggregate\`
    WHERE normalized_channel = 'release'
  ), 2) AS percent
FROM \`moz-fx-data-shared-prod.telemetry.windows_10_aggregate\`
WHERE normalized_channel = 'release'
GROUP BY windows_major
ORDER BY client_days DESC
"
```

### Windows 11 versions by channel

```bash
bq query --project_id=mozdata --use_legacy_sql=false --format=pretty "
SELECT
  normalized_channel,
  build_group,
  SUM(count) AS client_days,
  ROUND(SUM(count) * 100.0 / SUM(SUM(count)) OVER (PARTITION BY normalized_channel), 2) AS percent_of_channel
FROM \`moz-fx-data-shared-prod.telemetry.windows_10_aggregate\`
WHERE build_group LIKE 'Win11%'
GROUP BY normalized_channel, build_group
ORDER BY normalized_channel, client_days DESC
"
```

### Check specific Windows version adoption

```bash
bq query --project_id=mozdata --use_legacy_sql=false --format=pretty "
SELECT
  build_group,
  normalized_channel,
  SUM(count) AS client_days
FROM \`moz-fx-data-shared-prod.telemetry.windows_10_aggregate\`
WHERE build_group = 'Win11 25H2'
GROUP BY build_group, normalized_channel
ORDER BY client_days DESC
"
```

## Detailed Analysis

### Windows version with Firefox version cross-reference

```bash
bq query --project_id=mozdata --use_legacy_sql=false --format=pretty "
SELECT
  ff_build_version AS firefox_major_version,
  build_group,
  SUM(count) AS client_days
FROM \`moz-fx-data-shared-prod.telemetry.windows_10_aggregate\`
WHERE build_group IN ('Win11 24H2', 'Win11 25H2')
  AND normalized_channel = 'release'
  AND SAFE_CAST(ff_build_version AS INT64) >= 120
GROUP BY firefox_major_version, build_group
ORDER BY firefox_major_version DESC, client_days DESC
LIMIT 30
"
```

### Detailed OS version from Glean data

Use `baseline_clients_daily` when you need the full `os_version` string (e.g., `10.0.26100`):

```bash
bq query --project_id=mozdata --use_legacy_sql=false --format=pretty "
SELECT
  submission_date,
  client_info.os_version,
  COUNT(DISTINCT client_id) AS dau
FROM \`moz-fx-data-shared-prod.firefox_desktop.baseline_clients_daily\`
WHERE submission_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND normalized_os = 'Windows'
  AND normalized_channel = 'release'
  AND sample_id = 0
GROUP BY submission_date, client_info.os_version
ORDER BY dau DESC
LIMIT 20
"
```

## Build Number Reference

| Build Number | Windows Version | Release |
|-------------|-----------------|---------|
| 17763 | Windows 10 1809 | Nov 2018 |
| 18362 | Windows 10 1903 | May 2019 |
| 18363 | Windows 10 1909 | Nov 2019 |
| 19041 | Windows 10 2004 | May 2020 |
| 19042 | Windows 10 20H2 | Oct 2020 |
| 19043 | Windows 10 21H1 | May 2021 |
| 19044 | Windows 10 21H2 | Nov 2021 |
| 19045 | Windows 10 22H2 | Oct 2022 |
| 22000 | Windows 11 21H2 | Oct 2021 |
| 22621 | Windows 11 22H2 | Sep 2022 |
| 22631 | Windows 11 23H2 | Oct 2023 |
| 26100 | Windows 11 24H2 | Oct 2024 |
| 26200 | Windows 11 25H2 | 2025 |

## Aggregate View Details

The `windows_10_aggregate` view is maintained in the [bigquery-etl repo](https://github.com/mozilla/bigquery-etl/blob/main/sql/moz-fx-data-shared-prod/telemetry/windows_10_aggregate/view.sql).

- **Source table**: `telemetry.clients_daily` (legacy, pre-Glean)
- **Sample**: Fixed 1% (`sample_id = 42`)
- **Time range**: Rolling 28 days from current date
- **Filters**: `os = 'Windows_NT'`, `os_version` starts with `10`, Firefox version ≥ 47

When new Windows versions ship, this view needs updating (e.g., [PR #8432](https://github.com/mozilla/bigquery-etl/pull/8432) added Win11 25H2).

## Related Dashboards

- **Windows Client Distributions**: https://sql.telemetry.mozilla.org/dashboard/windows-10-client-distributions
