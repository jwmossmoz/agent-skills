# BigQuery Table Reference

## Table of Contents

- [Pre-Aggregated Tables (Use First)](#pre-aggregated-tables)
- [Baseline Tables](#baseline-tables)
- [Events Tables](#events-tables)
- [Search Tables](#search-tables)
- [Common Patterns](#common-patterns)
- [Other Products](#other-products)

## Pre-Aggregated Tables

### active_users_aggregates_v3

**Path**: `moz-fx-data-shared-prod.firefox_desktop_derived.active_users_aggregates_v3`

Pre-computed DAU/MAU/WAU by standard dimensions. Always check this first.

**Dimensions**: `submission_date`, `app_version`, `os`, `channel`, `country`, `locale`

```sql
-- DAU by country (last 7 days)
SELECT
  submission_date,
  country,
  SUM(dau) AS daily_active_clients
FROM `moz-fx-data-shared-prod.firefox_desktop_derived.active_users_aggregates_v3`
WHERE submission_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND channel = 'release'
GROUP BY submission_date, country
ORDER BY submission_date DESC, daily_active_clients DESC
```

**Limitation**: Has `os` (e.g., "Windows") but NOT `os_version`. For OS version breakdowns, use `baseline_clients_daily`.

### windows_10_aggregate

**Path**: `moz-fx-data-shared-prod.telemetry.windows_10_aggregate`

Pre-aggregated Windows version distribution with human-readable build groups.

**Columns**: `name`, `version`, `build_number`, `ubr`, `build_group`, `ff_build_version`, `normalized_channel`, `count`, `total_obs`

**Build Group Mappings**:

| build_group | Build Number | Windows Version |
|-------------|-------------|-----------------|
| Win10 <1809 | ≤17134 | Windows 10 pre-1809 |
| Win10 1809 | ≤17763 | Windows 10 1809 |
| Win10 1903 | ≤18362 | Windows 10 1903 |
| Win10 1909 | ≤18363 | Windows 10 1909 |
| Win10 2004 | ≤19041 | Windows 10 2004 |
| Win10 20H2 | ≤19042 | Windows 10 20H2 |
| Win10 21H1 | ≤19043 | Windows 10 21H1 |
| Win10 21H2 | ≤19044 | Windows 10 21H2 |
| Win10 22H2 | ≤19045 | Windows 10 22H2 |
| Win10 Insider | <22000 | Windows 10 Insider |
| Win11 21H2 | =22000 | Windows 11 21H2 |
| Win11 22H2 | ≤22621 | Windows 11 22H2 |
| Win11 23H2 | ≤22631 | Windows 11 23H2 |
| Win11 24H2 | ≤26100 | Windows 11 24H2 |
| Win11 25H2 | ≤26200 | Windows 11 25H2 |
| Win11 Insider | >26200 | Windows 11 Insider |

**Notes**: Uses `telemetry.clients_daily` (legacy, pre-Glean). Fixed 1% sample (`sample_id = 42`). Rolling 28-day window. View definition maintained at [bigquery-etl](https://github.com/mozilla/bigquery-etl/blob/main/sql/moz-fx-data-shared-prod/telemetry/windows_10_aggregate/view.sql).

## Baseline Tables

### baseline_clients_daily

**Path**: `moz-fx-data-shared-prod.firefox_desktop.baseline_clients_daily`

One row per client per day. Best for DAU with custom dimensions not in aggregates.

**Key columns**: `submission_date`, `client_id`, `sample_id`, `normalized_channel`, `normalized_os`, `normalized_country_code`, `client_info.os_version`, `client_info.architecture`, `client_info.app_display_version`

```sql
-- DAU by OS version
SELECT
  submission_date,
  client_info.os_version,
  COUNT(DISTINCT client_id) AS dau
FROM `moz-fx-data-shared-prod.firefox_desktop.baseline_clients_daily`
WHERE submission_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND normalized_os = 'Windows'
  AND normalized_channel = 'release'
  AND sample_id = 0  -- 1% sample for dev
GROUP BY submission_date, client_info.os_version
ORDER BY dau DESC
```

### baseline_clients_last_seen

**Path**: `moz-fx-data-shared-prod.firefox_desktop.baseline_clients_last_seen`

Bit patterns encoding 28-day activity history. Scan 1 day instead of 28 for MAU.

```sql
-- DAU/WAU/MAU in one query (scan single day)
SELECT
  submission_date,
  COUNT(DISTINCT CASE WHEN days_seen_bits & 1 > 0 THEN client_id END) AS dau,
  COUNT(DISTINCT CASE WHEN days_seen_bits & 127 > 0 THEN client_id END) AS wau,
  COUNT(DISTINCT CASE WHEN days_seen_bits > 0 THEN client_id END) AS mau
FROM `moz-fx-data-shared-prod.firefox_desktop.baseline_clients_last_seen`
WHERE submission_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
  AND normalized_channel = 'release'
GROUP BY submission_date
```

**Bit pattern reference**: Bit 0 = today, bit 1 = yesterday, ..., bit 27 = 27 days ago.
- DAU: `days_seen_bits & 1 > 0`
- WAU: `days_seen_bits & 127 > 0` (7-bit mask)
- MAU: `days_seen_bits > 0` (any bit set in 28 days)

## Events Tables

### events_stream

**Path**: `moz-fx-data-shared-prod.firefox_desktop.events_stream`

Pre-unnested events, one row per event. Clustered by `event_category`.

```sql
-- Event counts by category
SELECT
  DATE(submission_timestamp) AS date,
  event_category,
  event_name,
  COUNT(*) AS total_events,
  COUNT(DISTINCT client_id) AS unique_clients
FROM `moz-fx-data-shared-prod.firefox_desktop.events_stream`
WHERE DATE(submission_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND event_category = 'shopping'  -- clustered column, fast!
  AND sample_id = 0
GROUP BY date, event_category, event_name
ORDER BY total_events DESC
```

**Never use** `events_v1` — it requires UNNEST and is not clustered.

## Search Tables

### mobile_search_clients_daily_v2

**Path**: `moz-fx-data-shared-prod.search.mobile_search_clients_daily_v2`

Pre-aggregated mobile search metrics per client per day.

```sql
SELECT
  submission_date,
  search_engine,
  SUM(sap_searches) AS sap_count,
  COUNT(DISTINCT client_id) AS searching_clients
FROM `moz-fx-data-shared-prod.search.mobile_search_clients_daily_v2`
WHERE submission_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND normalized_app_id = 'org.mozilla.firefox'
GROUP BY submission_date, search_engine
ORDER BY sap_count DESC
```

## Common Patterns

### Cost-checking before running

```bash
bq query --project_id=mozdata --use_legacy_sql=false --dry_run \
  "SELECT COUNT(*) FROM \`moz-fx-data-shared-prod.firefox_desktop.baseline_clients_daily\` WHERE submission_date = CURRENT_DATE()"
```

### Sampling for development

Always use `sample_id = 0` during development (1% of data). Remove for production.

### Partitioning

All tables are partitioned by date. Queries **must** filter on the partition column:
- `submission_date` for derived/aggregated tables
- `DATE(submission_timestamp)` for raw ping tables

Queries without partition filters will scan the entire table (expensive!).

## Other Products

Replace `firefox_desktop` with the product name for other Mozilla products:

| Product | Dataset |
|---------|---------|
| Firefox Desktop | `firefox_desktop` |
| Firefox Android (Fenix) | `fenix` |
| Firefox iOS | `firefox_ios` |
| Focus Android | `focus_android` |
| Focus iOS | `focus_ios` |
