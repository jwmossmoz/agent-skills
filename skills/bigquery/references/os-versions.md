# OS Version Analysis

Queries for analyzing Windows and macOS version distribution among Firefox users.

## Table of Contents

- [Windows Quick Queries](#windows-quick-queries)
- [Windows Detailed Analysis](#windows-detailed-analysis)
- [Windows Build Number Reference](#windows-build-number-reference)
- [Windows Aggregate View Details](#windows-aggregate-view-details)
- [macOS Quick Queries](#macos-quick-queries)
- [macOS Detailed Analysis](#macos-detailed-analysis)
- [macOS Darwin Version Reference](#macos-darwin-version-reference)
- [Linux Quick Queries](#linux-quick-queries)
- [Linux Kernel-to-Distro Reference](#linux-kernel-to-distro-reference)

## Windows Quick Queries

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

## Windows Detailed Analysis

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

Use `baseline_clients_daily` when you need the full `normalized_os_version` string (Darwin kernel version for macOS, build number for Windows):

```bash
bq query --project_id=mozdata --use_legacy_sql=false --format=pretty "
SELECT
  submission_date,
  normalized_os_version,
  COUNT(DISTINCT client_id) AS dau
FROM \`moz-fx-data-shared-prod.firefox_desktop.baseline_clients_daily\`
WHERE submission_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND normalized_os = 'Windows'
  AND normalized_channel = 'release'
  AND sample_id = 0
GROUP BY submission_date, normalized_os_version
ORDER BY dau DESC
LIMIT 20
"
```

## Windows Build Number Reference

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

## Windows Aggregate View Details

The `windows_10_aggregate` view is maintained in the [bigquery-etl repo](https://github.com/mozilla/bigquery-etl/blob/main/sql/moz-fx-data-shared-prod/telemetry/windows_10_aggregate/view.sql).

- **Source table**: `telemetry.clients_daily` (legacy, pre-Glean)
- **Sample**: Fixed 1% (`sample_id = 42`)
- **Time range**: Rolling 28 days from current date
- **Filters**: `os = 'Windows_NT'`, `os_version` starts with `10`, Firefox version ≥ 47

When new Windows versions ship, this view needs updating (e.g., [PR #8432](https://github.com/mozilla/bigquery-etl/pull/8432) added Win11 25H2).

## macOS Quick Queries

There is no pre-aggregated macOS view like `windows_10_aggregate`. Use `baseline_clients_daily` with `normalized_os = 'Mac'`. The `normalized_os_version` field reports **Darwin kernel versions**, not macOS marketing versions.

### macOS version distribution (by major release)

```bash
bq query --project_id=mozdata --use_legacy_sql=false --format=pretty "
SELECT
  CASE
    WHEN normalized_os_version LIKE '25.%' THEN 'macOS 15 Sequoia'
    WHEN normalized_os_version LIKE '24.%' THEN 'macOS 14 Sonoma'
    WHEN normalized_os_version LIKE '23.%' THEN 'macOS 13 Ventura'
    WHEN normalized_os_version LIKE '22.%' THEN 'macOS 12 Monterey'
    WHEN normalized_os_version LIKE '21.%' OR normalized_os_version LIKE '20.%' THEN 'macOS 11 Big Sur'
    WHEN normalized_os_version LIKE '19.%' THEN 'macOS 10.15 Catalina'
    WHEN normalized_os_version LIKE '18.%' THEN 'macOS 10.14 Mojave'
    ELSE 'Older'
  END AS macos_version,
  COUNT(DISTINCT client_id) AS daily_active_clients,
  ROUND(COUNT(DISTINCT client_id) * 100.0
    / SUM(COUNT(DISTINCT client_id)) OVER (), 2) AS percent_of_macos_dau
FROM \`moz-fx-data-shared-prod.firefox_desktop.baseline_clients_daily\`
WHERE submission_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
  AND normalized_os = 'Mac'
  AND normalized_channel = 'release'
  AND sample_id = 0
GROUP BY macos_version
ORDER BY daily_active_clients DESC
"
```

### Detailed macOS version distribution (by Darwin point release)

```bash
bq query --project_id=mozdata --use_legacy_sql=false --format=pretty "
SELECT
  normalized_os_version AS darwin_version,
  CASE
    WHEN normalized_os_version LIKE '25.%' THEN 'macOS 15 Sequoia'
    WHEN normalized_os_version LIKE '24.%' THEN 'macOS 14 Sonoma'
    WHEN normalized_os_version LIKE '23.%' THEN 'macOS 13 Ventura'
    WHEN normalized_os_version LIKE '22.%' THEN 'macOS 12 Monterey'
    WHEN normalized_os_version LIKE '21.%' OR normalized_os_version LIKE '20.%' THEN 'macOS 11 Big Sur'
    WHEN normalized_os_version LIKE '19.%' THEN 'macOS 10.15 Catalina'
    WHEN normalized_os_version LIKE '18.%' THEN 'macOS 10.14 Mojave'
    ELSE 'Older'
  END AS macos_name,
  COUNT(DISTINCT client_id) AS daily_active_clients,
  ROUND(COUNT(DISTINCT client_id) * 100.0
    / SUM(COUNT(DISTINCT client_id)) OVER (), 2) AS percent_of_macos_dau
FROM \`moz-fx-data-shared-prod.firefox_desktop.baseline_clients_daily\`
WHERE submission_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
  AND normalized_os = 'Mac'
  AND normalized_channel = 'release'
  AND sample_id = 0
GROUP BY darwin_version, macos_name
ORDER BY daily_active_clients DESC
LIMIT 20
"
```

### macOS vs Windows vs Linux split

```bash
bq query --project_id=mozdata --use_legacy_sql=false --format=pretty "
SELECT
  normalized_os,
  COUNT(DISTINCT client_id) AS daily_active_clients,
  ROUND(COUNT(DISTINCT client_id) * 100.0
    / SUM(COUNT(DISTINCT client_id)) OVER (), 2) AS percent_of_dau
FROM \`moz-fx-data-shared-prod.firefox_desktop.baseline_clients_daily\`
WHERE submission_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
  AND normalized_channel = 'release'
  AND sample_id = 0
GROUP BY normalized_os
ORDER BY daily_active_clients DESC
"
```

## macOS Detailed Analysis

### macOS version by channel

```bash
bq query --project_id=mozdata --use_legacy_sql=false --format=pretty "
SELECT
  normalized_channel,
  CASE
    WHEN normalized_os_version LIKE '25.%' THEN 'macOS 15 Sequoia'
    WHEN normalized_os_version LIKE '24.%' THEN 'macOS 14 Sonoma'
    WHEN normalized_os_version LIKE '23.%' THEN 'macOS 13 Ventura'
    WHEN normalized_os_version LIKE '22.%' THEN 'macOS 12 Monterey'
    WHEN normalized_os_version LIKE '21.%' OR normalized_os_version LIKE '20.%' THEN 'macOS 11 Big Sur'
    ELSE 'Older'
  END AS macos_version,
  COUNT(DISTINCT client_id) AS dau,
  ROUND(COUNT(DISTINCT client_id) * 100.0
    / SUM(COUNT(DISTINCT client_id)) OVER (PARTITION BY normalized_channel), 2) AS percent_of_channel
FROM \`moz-fx-data-shared-prod.firefox_desktop.baseline_clients_daily\`
WHERE submission_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
  AND normalized_os = 'Mac'
  AND sample_id = 0
GROUP BY normalized_channel, macos_version
ORDER BY normalized_channel, dau DESC
"
```

### macOS version with Firefox version cross-reference

```bash
bq query --project_id=mozdata --use_legacy_sql=false --format=pretty "
SELECT
  SPLIT(app_display_version, '.')[SAFE_OFFSET(0)] AS firefox_major,
  CASE
    WHEN normalized_os_version LIKE '25.%' THEN 'macOS 15 Sequoia'
    WHEN normalized_os_version LIKE '24.%' THEN 'macOS 14 Sonoma'
    WHEN normalized_os_version LIKE '23.%' THEN 'macOS 13 Ventura'
    ELSE 'macOS 12 or older'
  END AS macos_version,
  COUNT(DISTINCT client_id) AS dau
FROM \`moz-fx-data-shared-prod.firefox_desktop.baseline_clients_daily\`
WHERE submission_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
  AND normalized_os = 'Mac'
  AND normalized_channel = 'release'
  AND sample_id = 0
GROUP BY firefox_major, macos_version
ORDER BY firefox_major DESC, dau DESC
LIMIT 30
"
```

## macOS Darwin Version Reference

The `normalized_os_version` field in `baseline_clients_daily` reports Darwin kernel versions for macOS, not the marketing version numbers.

| Darwin Major | macOS Version | macOS Name | Release |
|-------------|---------------|------------|---------|
| 25.x | 15.x | Sequoia | Sep 2024 |
| 24.x | 14.x | Sonoma | Sep 2023 |
| 23.x | 13.x | Ventura | Oct 2022 |
| 22.x | 12.x | Monterey | Oct 2021 |
| 21.x | 11.x | Big Sur | Nov 2020 |
| 20.x | 11.0 | Big Sur (early) | Nov 2020 |
| 19.x | 10.15 | Catalina | Oct 2019 |
| 18.x | 10.14 | Mojave | Sep 2018 |

**Formula**: macOS major version = Darwin major version - 10 (for Darwin 20+). E.g., Darwin 25 = macOS 15.

## Linux Quick Queries

There is no pre-aggregated Linux view. Use `baseline_clients_daily` with `normalized_os = 'Linux'`. The `normalized_os_version` field reports the **Linux kernel version**, not the distribution name (Ubuntu, Fedora, etc.) — telemetry does not report the distro.

### Linux kernel version distribution

```bash
bq query --project_id=mozdata --use_legacy_sql=false --format=pretty "
SELECT
  normalized_os_version AS kernel_version,
  COUNT(DISTINCT client_id) AS daily_active_clients,
  ROUND(COUNT(DISTINCT client_id) * 100.0
    / SUM(COUNT(DISTINCT client_id)) OVER (), 2) AS percent_of_linux_dau
FROM \`moz-fx-data-shared-prod.firefox_desktop.baseline_clients_daily\`
WHERE submission_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
  AND normalized_os = 'Linux'
  AND normalized_channel = 'release'
  AND sample_id = 0
GROUP BY kernel_version
ORDER BY daily_active_clients DESC
LIMIT 20
"
```

### Linux kernel version by channel

```bash
bq query --project_id=mozdata --use_legacy_sql=false --format=pretty "
SELECT
  normalized_channel,
  normalized_os_version AS kernel_version,
  COUNT(DISTINCT client_id) AS dau,
  ROUND(COUNT(DISTINCT client_id) * 100.0
    / SUM(COUNT(DISTINCT client_id)) OVER (PARTITION BY normalized_channel), 2) AS percent_of_channel
FROM \`moz-fx-data-shared-prod.firefox_desktop.baseline_clients_daily\`
WHERE submission_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
  AND normalized_os = 'Linux'
  AND sample_id = 0
GROUP BY normalized_channel, kernel_version
ORDER BY normalized_channel, dau DESC
LIMIT 30
"
```

### Linux kernel major version rollup

```bash
bq query --project_id=mozdata --use_legacy_sql=false --format=pretty "
SELECT
  CONCAT(SPLIT(normalized_os_version, '.')[SAFE_OFFSET(0)], '.x') AS kernel_major,
  COUNT(DISTINCT client_id) AS daily_active_clients,
  ROUND(COUNT(DISTINCT client_id) * 100.0
    / SUM(COUNT(DISTINCT client_id)) OVER (), 2) AS percent_of_linux_dau
FROM \`moz-fx-data-shared-prod.firefox_desktop.baseline_clients_daily\`
WHERE submission_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
  AND normalized_os = 'Linux'
  AND normalized_channel = 'release'
  AND sample_id = 0
GROUP BY kernel_major
ORDER BY daily_active_clients DESC
"
```

## Linux Kernel-to-Distro Reference

The kernel version can hint at the distribution, but is not definitive. Common mappings:

| Kernel | Likely Distro | Notes |
|--------|--------------|-------|
| 6.8 | Ubuntu 24.04 LTS | Default kernel for Noble Numbat |
| 6.5 | Ubuntu 23.10 | Short-term release |
| 5.15 | Ubuntu 22.04 LTS | Default kernel for Jammy Jellyfish |
| 5.4 | Ubuntu 20.04 LTS | Default kernel for Focal Fossa |
| 4.15 | Ubuntu 18.04 LTS | Default kernel for Bionic Beaver |
| 6.14+ | Fedora 42 / Arch | Rolling release, latest kernels |
| 6.12 | Fedora 41 | Stable Fedora release |
| 6.1 | Debian 12 (Bookworm) | Debian LTS kernel |
| 5.10 | Debian 11 (Bullseye) | Previous Debian LTS |
| 4.19 | Debian 10 (Buster) | Older Debian LTS |
| 3.10 | RHEL/CentOS 7 | Enterprise, EOL Jun 2024 |

**Caveats**: Users can install newer kernels on any distro (e.g., Ubuntu HWE kernels), so these are approximations. Rolling-release distros (Arch, Gentoo, openSUSE Tumbleweed) will always have the latest kernels.

## Related Dashboards

- **Windows Client Distributions**: https://sql.telemetry.mozilla.org/dashboard/windows-10-client-distributions
