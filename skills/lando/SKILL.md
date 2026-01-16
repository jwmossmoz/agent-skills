---
name: lando
description: >
  Check the status of Lando landing jobs using Mozilla's official lando-cli tool.
  Use after submitting try pushes with mach try to verify if your commit has landed.
  Triggers on "lando status", "landing job", "check landing", "commit landed".
---

# Lando

Check the status of Mozilla Lando landing jobs using the official `lando-cli` tool.

## Usage

```bash
# Check landing job status
uvx --from lando-cli lando check-job <JOB_ID>

# Example
uvx --from lando-cli lando check-job 173397
```

## Prerequisites

Requires `~/.mozbuild/lando.toml` with API token:

```toml
[auth]
api_token = "<YOUR_API_TOKEN>"
user_email = "your.email@mozilla.com"
```

Request an API token from the Mozilla Conduit team.

## Documentation

For full documentation on lando-cli and Lando API:

- **lando-cli Package**: https://pypi.org/project/lando-cli/
- **Lando API Documentation**: https://api.lando.services.mozilla.com/
- **Mozilla Conduit Documentation**: https://moz-conduit.readthedocs.io/
- **Source Code**: https://github.com/mozilla-conduit/lando-api
