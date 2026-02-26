# Session JSONL Formats

## Claude Code

Path: `~/.claude/projects/<project-dir>/<session-uuid>.jsonl`

Each line is a JSON object. Key fields:

- `type`: `"user"` | `"assistant"` | `"file-history-snapshot"`
- `message.role`: `"user"` | `"assistant"`
- `message.content`: string or array of content blocks
- `timestamp`: ISO 8601
- `cwd`: working directory
- `gitBranch`: current git branch
- `sessionId`: session UUID

**User messages** have `type: "user"` and `message.content` as a plain string.

**Assistant messages** have `type: "assistant"` and `message.content` as an array of blocks:
- `{"type": "text", "text": "..."}` - text output
- `{"type": "tool_use", "name": "...", "input": {...}}` - tool calls
- `{"type": "thinking", "thinking": "..."}` - internal reasoning (skip)

To extract the initial prompt, find the first object with `type: "user"`.

To identify key actions, scan for `tool_use` blocks with names like `Bash`, `Edit`, `Write`, `Skill`.

## Codex

Path: `~/.codex/sessions/YYYY/MM/DD/<name>-<uuid>.jsonl`

Each line is a JSON object. Key fields:

- `type`: `"session_meta"` | `"response_item"` | `"event_msg"`
- `payload.role`: `"user"` | `"assistant"` | `"developer"`
- `payload.content`: array of content blocks
- `timestamp`: ISO 8601

**Session metadata** has `type: "session_meta"` with `payload.cwd` and `payload.id`.

**User messages** have `type: "response_item"` and `payload.role: "user"`. The initial user prompt is typically the last `"user"` role message before the first `"event_msg"` with `type: "task_started"`.

**Tool calls** appear as `type: "response_item"` with `payload.type: "function_call"`.

**Tool results** appear as `type: "response_item"` with `payload.type: "function_call_output"`.

To identify key actions, look for `function_call` items and assistant text responses.
