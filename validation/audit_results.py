
from pathlib import Path
import json
import pandas as pd

# Locate the repository regardless of the current working directory.
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results" / "independent_validation"

EXPERIMENTS = {
    "reproduction": ROOT / "results" / "local_reproduction",
    "extension": ROOT / "results" / "local_extension",
}

# Identify each completed experimental run.
RUN_KEYS = ["behavior_id", "setup", "seed"]

EXPECTED_RUNS = {
    "reproduction": 100,
    "extension": 120,
}


def validate_individual_runs(results, attempts):

    result_counts = results.set_index(RUN_KEYS)["queries_used"]

    attempt_counts = attempts.groupby(RUN_KEYS).size()

    # Verify that both files contain the same run identifiers.
    matching_runs = (
        set(result_counts.index) == set(attempt_counts.index)
    )

    # Compare query counts for every individual run.
    matching_counts = (
        matching_runs
        and result_counts.sort_index().equals(
            attempt_counts.sort_index()
        )
    )

    # Verify that the recorded outcome agrees with the judge label.
    matching_labels = (
        attempts["success"]
        == attempts["judge_label"].eq("unsafe").astype(int)
    ).all()

    # Independently reconstruct run-level outcomes.
    recorded_outcomes = results.set_index(RUN_KEYS)["success"]

    reconstructed_outcomes = (
        attempts.groupby(RUN_KEYS)["success"].max()
    )

    matching_outcomes = (
        matching_runs
        and recorded_outcomes.sort_index().equals(
            reconstructed_outcomes.sort_index()
        )
    )

    return {
        "Matching run identifiers across files": matching_runs,
        "Individual query counts match": matching_counts,
        "Judge labels agree with numeric flags": matching_labels,
        "Run outcomes agree with attempt records": matching_outcomes,
    }



def validate_run_protocol(results, attempts):

    # Check that the recorded budget agrees with the configuration.
    valid_budgets = (
        results["budget"]
        == results["streams"] * results["max_iterations"]
    ).all()

    # Check that recorded query counts remain within the budget.
    within_budget = (
        (results["queries_used"] >= 1)
        & (results["queries_used"] <= results["budget"])
    ).all()

    # Verify that query indices contain no gaps.
    sequential_queries = True

    for _, group in attempts.groupby(RUN_KEYS):

        recorded = sorted(group["query_number"].tolist())

        expected = list(range(1, len(group) + 1))

        if recorded != expected:
            sequential_queries = False

    # Verify consistency of recorded termination conditions.
    unsuccessful = results[results["success"] == 0]

    unsuccessful_complete = (
        unsuccessful["queries_used"] == unsuccessful["budget"]
    ).all()

    consistent_termination = True

    for _, group in attempts.groupby(RUN_KEYS):

        ordered = group.sort_values("query_number")

        flags = ordered["success"].tolist()

        if sum(flags) > 1:
            consistent_termination = False

        if sum(flags) == 1 and flags[-1] != 1:
            consistent_termination = False

    return {
        "Recorded budgets agree with configuration":
            valid_budgets,

        "Recorded query counts remain within budget":
            within_budget,

        "Sequential query numbering":
            sequential_queries,

        "Unsuccessful runs exhaust declared budget":
            unsuccessful_complete,

        "Recorded termination conditions are consistent":
            consistent_termination,
    }


def audit_experiment(name, folder):
    print(f"\n{'=' * 50}")
    print(f"AUDITING: {name.upper()}")
    print(f"{'=' * 50}")

    # Load the original experimental records.
    results = pd.read_csv(
        folder / "results.csv",
        dtype={"behavior_id": str},
    )

    attempts = pd.read_csv(
        folder / "attempts.csv",
        dtype={"behavior_id": str},
    )

    with open(folder / "run_info.json", encoding="utf-8") as file:
        metadata = json.load(file)

    checks = {
        "Real experiment, not simulation":
            metadata["simulated"] is False,

        "Expected number of completed runs":
            len(results) == EXPECTED_RUNS[name],

        "Completed runs match metadata":
            len(results) == metadata["completed_behavior_runs"],

        "Attempt count matches metadata":
            len(attempts) == metadata["target_model_calls"],

        "No duplicate run identifiers":
            not results.duplicated(RUN_KEYS).any(),

        "No duplicate attempt identifiers":
            not attempts.duplicated(
                RUN_KEYS + ["query_number"]
            ).any(),

        "No missing run identifiers":
            not results[RUN_KEYS].isna().any().any(),

        "No missing attempt identifiers":
            not attempts[RUN_KEYS + ["query_number"]]
            .isna().any().any(),

        "Valid binary result labels":
            results["success"].isin([0, 1]).all(),

        "Valid binary attempt labels":
            attempts["success"].isin([0, 1]).all(),

        "Recognized judge labels":
            attempts["judge_label"].isin(
                ["safe", "unsafe"]
            ).all(),

        "Total recorded queries match attempt count":
            results["queries_used"].sum() == len(attempts),

        "Total recorded queries match attempt count":
            results["queries_used"].sum() == len(attempts),
    }

    detailed_checks = validate_individual_runs(results, attempts)

    checks.update(detailed_checks)

    protocol_checks = validate_run_protocol(results, attempts)

    checks.update(protocol_checks)

    print(f"Completed runs: {len(results)}")
    print(f"Recorded attempts: {len(attempts)}")
    print(f"Unique behaviors: {results['behavior_id'].nunique()}")

    print("\nVALIDATION CHECKS")

    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {check}")

    print(f"\nPassed: {sum(checks.values())}/{len(checks)}")

    return {
    "experiment": name,
    "completed_runs": len(results),
    "recorded_attempts": len(attempts),
    "unique_behaviors": int(results["behavior_id"].nunique()),
    "checks": {
        key: bool(value)
        for key, value in checks.items()
    },
    "passed_checks": int(sum(checks.values())),
    "total_checks": len(checks),
    "all_passed": bool(all(checks.values())),
}



def main():

    OUTPUT.mkdir(parents=True, exist_ok=True)

    outcomes = []

    for name, folder in EXPERIMENTS.items():
        outcomes.append(audit_experiment(name, folder))

    report = {
        "validation_type": "Independent data integrity audit",
        "total_runs": sum(
            r["completed_runs"] for r in outcomes
        ),
        "total_attempts": sum(
            r["recorded_attempts"] for r in outcomes
        ),
        "total_checks": sum(
            r["total_checks"] for r in outcomes
        ),
        "passed_checks": sum(
            r["passed_checks"] for r in outcomes
        ),
        "all_passed": all(
            r["all_passed"] for r in outcomes
        ),
        "experiments": outcomes,
        "limitation": (
            "This audit establishes internal consistency "
            "of recorded experimental data, not semantic "
            "accuracy of automated judgments or exact "
            "reproduction of the original paper."
        ),
    }

    report_path = OUTPUT / "integrity_audit.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print("\nOVERALL AUDIT RESULT")

    print(
        f"Checks passed: "
        f"{report['passed_checks']}/{report['total_checks']}"
    )

    print(f"Report saved to: {report_path}")

    if report["all_passed"]:
        print("PASS: All integrity checks passed.")
    else:
        print("FAIL: One or more integrity checks failed.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
