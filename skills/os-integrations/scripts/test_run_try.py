#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "taskcluster", "requests", "httpx"]
# ///
"""Test builder discovery and try command generation without submissions."""

import contextlib
import io
import shlex
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import discover_tasks
import run_try

DECISION = "frozen-autoland-decision"
LABELS = [
    "build-win64-plain/debug",
    "generate-profile-win64-shippable/opt",
    "toolchain-win64-clang",
]
GRAPH = {
    label: {"label": label, "task": {"workerType": "b-win2022"}}
    for label in LABELS
}
GRAPH["other"] = {"label": "build-linux64/debug", "task": {"workerType": "b-linux"}}
POOLS = {
    "b-win2025": "gecko-1/b-win2025-alpha",
    "b-win2025-core": "gecko-1/b-win2025-core-alpha",
    "b-win2025-gpu": "gecko-1/b-win2025-gpu-alpha",
}


class BuilderTests(unittest.TestCase):
    def preview(self, *args, graph=GRAPH):
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            patch.object(sys, "argv", ["run_try.py", *args, "--dry-run"]),
            patch.object(run_try, "FIREFOX_DIR", Path("/tmp/firefox-test")),
            patch.object(run_try, "fetch_task_graph", return_value=graph) as fetch,
            patch.object(run_try, "get_latest_autoland_decision_task", return_value=DECISION) as latest,
            patch.object(run_try, "preflight_check") as preflight,
            patch.object(run_try.subprocess, "Popen") as execute,
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            status = run_try.main()
        preflight.assert_not_called()
        execute.assert_not_called()
        command = next(
            (shlex.split(line.removeprefix("Command: ")) for line in stdout.getvalue().splitlines()
             if line.startswith("Command: ")),
            [],
        )
        return status, command, stdout.getvalue(), stderr.getvalue(), fetch, latest

    def test_full_graph_artifact(self):
        url = discover_tasks.get_task_graph_url("autoland", full=True)
        self.assertIn("gecko.v2.autoland.latest.taskgraph.decision", url)
        self.assertTrue(url.endswith("public%2Ffull-task-graph.json"))

    def test_scheduled_graph_default(self):
        url = discover_tasks.get_task_graph_url("autoland")
        self.assertTrue(url.endswith("public%2Ftask-graph.json"))

    def test_frozen_decision_artifact(self):
        url = discover_tasks.get_task_graph_url("autoland", full=True, task_id=DECISION)
        self.assertIn(f"/api/queue/v1/task/{DECISION}/artifacts/", url)
        self.assertNotIn("latest", url)
        self.assertTrue(url.endswith("public%2Ffull-task-graph.json"))

    def test_fetch_uses_full_graph_and_decision(self):
        with patch.object(discover_tasks.httpx, "Client") as client:
            client.return_value.__enter__.return_value.get.return_value.json.return_value = GRAPH
            graph = discover_tasks.fetch_task_graph(full=True, task_id=DECISION)
        self.assertEqual(graph, GRAPH)
        client.assert_called_once_with(timeout=60.0, follow_redirects=True)
        client.return_value.__enter__.return_value.get.assert_called_once_with(
            discover_tasks.get_task_graph_url("mozilla-central", full=True, task_id=DECISION)
        )

    def test_filter_excludes_other_workers(self):
        self.assertEqual(discover_tasks.filter_by_worker_type(GRAPH, "b-win2022"), LABELS)

    def test_three_builder_presets(self):
        for preset, pool in POOLS.items():
            with self.subTest(preset=preset):
                status, command, stdout, _, fetch, latest = self.preview(
                    preset, "--task-id", DECISION, "--checkout", "/tmp/isolated-firefox"
                )
                self.assertEqual(status, 0)
                fetch.assert_called_once_with(branch="autoland", full=True, task_id=DECISION)
                latest.assert_not_called()
                self.assertIn("--full", command)
                self.assertIn("--all-tasks", command)
                self.assertIn("--no-artifact", command)
                self.assertNotIn("--use-existing-tasks", command)
                self.assertNotIn("--task-id", command)
                self.assertNotIn("--worker-suffix", command)
                self.assertEqual(command[command.index("--worker-override") + 1], f"b-win2022={pool}")
                queries = [command[i + 1] for i, arg in enumerate(command) if arg == "-q"]
                self.assertEqual(queries, [f"^{label}$" for label in LABELS])
                self.assertIn(f"Directory: {Path('/tmp/isolated-firefox').resolve()}", stdout)

    def test_builder_defaults_to_autoland_and_fresh_tasks(self):
        status, command, _, _, fetch, latest = self.preview("b-win2025")
        self.assertEqual(status, 0)
        fetch.assert_called_once_with(branch="autoland", full=True, task_id=None)
        latest.assert_not_called()
        self.assertNotIn("--use-existing-tasks", command)

    def test_empty_builder_graph_stops(self):
        status, command, _, stderr, _, _ = self.preview("b-win2025-core", graph={})
        self.assertEqual(status, 1)
        self.assertEqual(command, [])
        self.assertIn("Error: No tasks found", stderr)

    def test_failed_builder_discovery_stops(self):
        status, command, _, stderr, _, _ = self.preview("b-win2025-gpu", graph=None)
        self.assertEqual(status, 1)
        self.assertEqual(command, [])
        self.assertIn("Error: Failed to fetch task graph", stderr)

    def test_existing_test_preset_reuses_builds(self):
        status, command, _, _, fetch, latest = self.preview("win11-24h2")
        self.assertEqual(status, 0)
        fetch.assert_not_called()
        latest.assert_called_once()
        self.assertIn("--use-existing-tasks", command)
        self.assertEqual(command[command.index("--use-existing-tasks") + 1], f"task-id={DECISION}")

    def test_existing_preset_fresh_build_opt_out(self):
        status, command, _, _, _, latest = self.preview("win11-24h2", "--fresh-build")
        self.assertEqual(status, 0)
        latest.assert_not_called()
        self.assertNotIn("--use-existing-tasks", command)

    def test_existing_worker_discovery_preserves_defaults(self):
        status, command, _, _, fetch, _ = self.preview("b-win2022", "--discover")
        self.assertEqual(status, 0)
        fetch.assert_called_once_with(branch="mozilla-central", full=False, task_id=None)
        queries = [command[i + 1] for i, arg in enumerate(command) if arg == "-q"]
        self.assertEqual(queries, LABELS)


if __name__ == "__main__":
    unittest.main()
