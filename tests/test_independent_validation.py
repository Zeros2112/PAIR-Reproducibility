from pathlib import Path
import unittest
import json
import subprocess
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

OUTPUT = ROOT / "results" / "independent_validation"

from validation.statistical_analysis import (
    calculate_descriptive_statistics,
)


class TestDescriptiveStatistics(unittest.TestCase):

    def setUp(self):

        self.data = pd.DataFrame({
            "setup": ["test"] * 4,
            "seed": [0, 0, 0, 0],
            "success": [1, 0, 1, 0],
            "queries_used": [2, 8, 4, 10],
        })

        self.summary = (
            calculate_descriptive_statistics(self.data)
            .iloc[0]
        )

    def test_total_runs(self):

        self.assertEqual(
            self.summary["total_runs"], 4
        )

    def test_flagged_runs(self):

        self.assertEqual(
            self.summary["flagged_runs"], 2
        )

    def test_unflagged_runs(self):

        self.assertEqual(
            self.summary["unflagged_runs"], 2
        )

    def test_judge_assessed_rate(self):

        self.assertAlmostEqual(
            self.summary["judge_assessed_rate_pct"],
            50.0,
        )

    def test_total_recorded_queries(self):

        self.assertEqual(
            self.summary["total_recorded_queries"],
            24,
        )

    def test_mean_queries_all(self):

        self.assertAlmostEqual(
            self.summary["mean_queries_all"],
            6.0,
        )

    def test_mean_queries_flagged(self):

        self.assertAlmostEqual(
            self.summary["mean_queries_flagged"],
            3.0,
        )

    def test_standard_deviation(self):

        self.assertAlmostEqual(
            self.summary["sd_queries_all"],
            (40 / 3) ** 0.5,
        )


class TestStatisticalReports(unittest.TestCase):

    def test_paired_outcome_totals(self):

        data = pd.read_csv(
            OUTPUT / "paired_outcomes.csv"
        )

        self.assertEqual(data["count"].sum(), 60)

        self.assertAlmostEqual(
            data["percentage"].sum(), 100.0
        )

    def test_paired_outcome_agreement(self):

        data = pd.read_csv(
            OUTPUT / "paired_outcomes.csv"
        )

        counts = data.set_index("outcome")["count"]

        agreement = (
            counts["Both flagged"]
            + counts["Neither flagged"]
        ) / counts.sum()

        self.assertAlmostEqual(
            agreement, 52 / 60
        )

    def test_repeatability_totals(self):

        data = pd.read_csv(
            OUTPUT / "repeatability_summary.csv"
        )

        totals = data.groupby(
            "setup"
        )["number_of_behaviors"].sum()

        self.assertEqual(totals["breadth"], 20)
        self.assertEqual(totals["depth"], 20)

    def test_repeatability_consistency(self):

        data = pd.read_csv(
            OUTPUT / "repeatability_summary.csv"
        )

        consistent = data[
            data["flagged_seeds"].isin([0, 3])
        ]

        totals = consistent.groupby(
            "setup"
        )["number_of_behaviors"].sum()

        self.assertEqual(totals["breadth"], 16)
        self.assertEqual(totals["depth"], 17)

    def test_bootstrap_point_estimates(self):

        filenames = [
            "bootstrap_confidence_interval.csv",
            "stratified_bootstrap_interval.csv",
        ]

        for filename in filenames:

            with self.subTest(filename=filename):

                result = pd.read_csv(
                    OUTPUT / filename
                ).iloc[0]

                self.assertAlmostEqual(
                    result["observed_difference_pp"],
                    100 * 2 / 60,
                )

    def test_bootstrap_interval_ordering(self):

        filenames = [
            "bootstrap_confidence_interval.csv",
            "stratified_bootstrap_interval.csv",
        ]

        for filename in filenames:

            with self.subTest(filename=filename):

                result = pd.read_csv(
                    OUTPUT / filename
                ).iloc[0]

                self.assertLessEqual(
                    result["ci_lower_pp"],
                    result["observed_difference_pp"],
                )

                self.assertGreaterEqual(
                    result["ci_upper_pp"],
                    result["observed_difference_pp"],
                )

    def test_bootstrap_report_consistency(self):

        filenames = [
            "bootstrap_confidence_interval.csv",
            "stratified_bootstrap_interval.csv",
        ]

        for filename in filenames:

            with self.subTest(filename=filename):

                result = pd.read_csv(
                    OUTPUT / filename
                ).iloc[0]

                includes_zero = (
                    result["ci_lower_pp"]
                    <= 0
                    <= result["ci_upper_pp"]
                )

                self.assertEqual(
                    bool(result["interval_includes_zero"]),
                    includes_zero,
                )


class TestIntegrityAudit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.execution = subprocess.run(
            [
                sys.executable,
                str(ROOT / "validation" / "audit_results.py"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

        if cls.execution.returncode != 0:

            raise RuntimeError(
                cls.execution.stdout
                + "\n"
                + cls.execution.stderr
            )

        with open(
            OUTPUT / "integrity_audit.json",
            encoding="utf-8",
        ) as file:

            cls.report = json.load(file)

    def test_audit_execution(self):

        self.assertEqual(
            self.execution.returncode, 0
        )

    def test_expected_total_runs(self):

        self.assertEqual(
            self.report["total_runs"], 220
        )

    def test_expected_total_attempts(self):

        self.assertEqual(
            self.report["total_attempts"], 5996
        )

    def test_all_integrity_checks_executed(self):

        self.assertEqual(
            self.execution.stdout.count("[PASS]"),
            42,
        )

        self.assertNotIn(
            "[FAIL]",
            self.execution.stdout,
        )

    def test_overall_audit_result(self):

        self.assertIn(
            "Checks passed: 42/42",
            self.execution.stdout,
        )


if __name__ == "__main__":
    unittest.main()
