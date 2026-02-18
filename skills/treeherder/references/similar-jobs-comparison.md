# Comparing Jobs with Treeherder `similar_jobs` API

Use this workflow when a try job fails and you need to know whether equivalent jobs passed on other branches.

## API summary

- Similar jobs endpoint (repo-local history by job ID):
  - `GET /api/project/{repo}/jobs/{job_id}/similar_jobs/?count={N}`
- Cross-branch comparison endpoint (exact job type matches):
  - `GET /api/project/{repo}/jobs/?job_type_name={name}&result=success&count={N}`

Base URL:

```text
https://treeherder.mozilla.org/api/
```

## Step 1: Resolve job ID from Treeherder UI task run

If you have a selected task run from the UI (`selectedTaskRun=<task_id>.0`), resolve it to a job ID:

```bash
curl -s "https://treeherder.mozilla.org/api/project/try/jobs/?task_id=BM40CReDQzaANmxbrbkJHA&count=5" \
  | jq '.results[0] | {id, task_id, job_type_name, result, platform}'
```

## Step 2: Get similar jobs history in the same repo

```bash
curl -s "https://treeherder.mozilla.org/api/project/try/jobs/549239688/similar_jobs/?count=100" \
  | jq '{meta, total: (.results | length), pass_count: ([.results[] | select(.result==\"success\")] | length), fail_count: ([.results[] | select(.result==\"testfailed\" or .result==\"busted\")] | length)}'
```

This shows whether the failure is likely intermittent on that repo.

## Step 3: Compare equivalent jobs across branches

Extract the `job_type_name`, then query other repos for successful runs:

```bash
job_type="test-windows11-64-24h2/debug-mochitest-browser-chrome-msix-13"
enc=$(jq -nr --arg v "$job_type" '$v|@uri')

for repo in autoland mozilla-central mozilla-beta; do
  curl -s "https://treeherder.mozilla.org/api/project/${repo}/jobs/?job_type_name=${enc}&result=success&count=2000" \
    | jq -r --arg repo "$repo" '
        if (.results|length)==0 then
          "\($repo)\tNO_MATCH"
        else
          (.results|last) as $last
          | "\($repo)\t\($last.last_modified)\t\($last.ref_data_name)\t\($last.id)"
        end'
done
```

Notes:
- `similar_jobs` is tied to one repo and one job ID.
- Cross-branch comparisons are done by matching `job_type_name` on each target repo.
- Use a larger `count` when branch history is sparse.

## Equivalent `treeherder-cli` command

`treeherder-cli` has a direct wrapper for `similar_jobs`:

```bash
treeherder-cli --similar-history 549239688 --repo try --similar-count 100 --json
```

Use this for fast per-job history, then use the `/jobs/` API queries above when you need cross-branch pass evidence.
