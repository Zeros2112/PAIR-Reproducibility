"""Basic tests for our own code. Run: python -m unittest discover -s tests"""

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models import DemoModels
from run_experiment import choose_20, load_behaviors, run_one


class TestPair(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "data" / "demo_behaviors.csv"
        cls.behaviors = load_behaviors(path)

    def test_pick_two_per_category(self):
        selected = choose_20(self.behaviors)
        self.assertEqual(len(selected), 20)
        self.assertEqual(len(set(b["category"] for b in selected)), 10)

    def test_budgets_and_query_numbers(self):
        models = DemoModels()
        for name, streams, steps in (("breadth", 10, 3), ("depth", 5, 6),
                                     ("reproduction", 30, 3)):
            result, logs, _ = run_one(self.behaviors[0], name,
                                      streams, steps, 0, models)
            self.assertLessEqual(result["queries_used"], streams * steps)
            self.assertEqual(result["queries_used"], len(logs))
            self.assertEqual([x["query_number"] for x in logs],
                             list(range(1, len(logs) + 1)))

    def test_repeatable_demo(self):
        models = DemoModels()
        a = run_one(self.behaviors[0], "breadth", 10, 3, 4, models)
        b = run_one(self.behaviors[0], "breadth", 10, 3, 4, models)
        self.assertEqual(a, b)

    def test_streams_have_separate_histories(self):
        class HistoryCheck(DemoModels):
            def make_prompt(self, goal, history, stream, step, seed):
                self_test.assertEqual(len(history), step - 1)
                return super().make_prompt(goal, history, stream, step, seed)
            def target_answer(self, prompt, goal, stream, step, seed):
                return "DEMO_REFUSAL"  # forces all streams to finish
        self_test = self
        result, logs, _ = run_one(self.behaviors[0], "depth", 5, 6, 2,
                                  HistoryCheck())
        self.assertEqual(result["queries_used"], 30)
        self.assertEqual(result["success"], 0)


if __name__ == "__main__":
    unittest.main()
