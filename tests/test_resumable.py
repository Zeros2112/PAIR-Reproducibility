"""Offline checks of checkpoint handling and compatibility."""
import json
import tempfile
import unittest
from pathlib import Path

from models import DemoModels
from run_experiment_resumable import run_one, save_checkpoint, checkpoint_path, SETUPS


class CheckpointTests(unittest.TestCase):
    def test_stream_budgets(self):
        behavior = {"id": "0", "goal": "Benign test example", "category": "Demo"}
        for setup in ("breadth", "depth", "reproduction"):
            streams, steps = SETUPS[setup]
            result, attempts, _ = run_one(behavior, setup, streams, steps, 0, DemoModels())
            self.assertLessEqual(result["queries_used"], streams * steps)
            self.assertEqual(result["queries_used"], len(attempts))

    def test_checkpoint_written_and_readable(self):
        behavior = {"id": "123", "goal": "Benign example", "category": "Demo"}
        result, attempts, private = run_one(behavior, "breadth", 10, 3, 0, DemoModels())
        with tempfile.TemporaryDirectory() as folder:
            path = checkpoint_path(Path(folder), "breadth", 0, behavior["id"])
            self.assertFalse(path.exists())
            settings = {"mode": "demo", "dataset_sha256": "demo", "models": "SIMULATED"}
            save_checkpoint(path, result, attempts, private, settings)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["result"]["behavior_id"], "123")
            self.assertEqual(len(data["attempts"]), len(attempts))
            self.assertEqual(data["settings"], settings)


if __name__ == "__main__":
    unittest.main()
