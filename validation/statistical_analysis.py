
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

OUTPUT = ROOT / "results" / "independent_validation"

REPRODUCTION = ROOT / "results" / "local_reproduction"
EXTENSION = ROOT / "results" / "local_extension"


def load_results(folder):

    return pd.read_csv(
        folder / "results.csv",
        dtype={"behavior_id": str},
    )



def calculate_descriptive_statistics(results):

    summaries = []

    for (setup, seed), group in results.groupby(
        ["setup", "seed"]
    ):

        flagged = group[group["success"] == 1]

        total_runs = len(group)
        flagged_runs = len(flagged)

        summaries.append({
            "setup": setup,
            "seed": seed,
            "total_runs": total_runs,
            "flagged_runs": flagged_runs,
            "unflagged_runs": total_runs - flagged_runs,

            "judge_assessed_rate_pct":
                100 * flagged_runs / total_runs,

            "total_recorded_queries":
                int(group["queries_used"].sum()),

            "mean_queries_all":
                group["queries_used"].mean(),

            "mean_queries_flagged":
                flagged["queries_used"].mean(),

            "sd_queries_all":
                group["queries_used"].std(ddof=1),
        })

    return pd.DataFrame(summaries)

def calculate_paired_outcomes(extension):

    paired = extension.pivot(
        index=["behavior_id", "seed"],
        columns="setup",
        values="success",
    )

    # Validate that every observation has both conditions.
    if len(paired) != 60:
        raise ValueError("Expected 60 matched observations.")

    if paired[["breadth", "depth"]].isna().any().any():
        raise ValueError("Incomplete matched observations.")

    breadth = paired["breadth"]
    depth = paired["depth"]

    both = ((breadth == 1) & (depth == 1)).sum()

    breadth_only = ((breadth == 1) & (depth == 0)).sum()

    depth_only = ((breadth == 0) & (depth == 1)).sum()

    neither = ((breadth == 0) & (depth == 0)).sum()

    total = len(paired)

    summary = pd.DataFrame([
        {
            "outcome": "Both flagged",
            "count": both,
            "percentage": 100 * both / total,
        },
        {
            "outcome": "Breadth only",
            "count": breadth_only,
            "percentage": 100 * breadth_only / total,
        },
        {
            "outcome": "Depth only",
            "count": depth_only,
            "percentage": 100 * depth_only / total,
        },
        {
            "outcome": "Neither flagged",
            "count": neither,
            "percentage": 100 * neither / total,
        },
    ])

    agreement = 100 * (both + neither) / total

    print("\nPAIRED OUTCOME ANALYSIS\n")

    print(summary.round(2).to_string(index=False))

    print(f"\nMatched observations: {total}")
    print(f"Outcome agreement: {agreement:.2f}%")

    summary.to_csv(
        OUTPUT / "paired_outcomes.csv",
        index=False,
    )

    return paired



def calculate_bootstrap_interval(paired):

    # Verify the repeated-measures structure.
    observations_per_behavior = (
        paired.groupby(level="behavior_id").size()
    )

    if len(observations_per_behavior) != 20:
        raise ValueError("Expected 20 unique behaviors.")

    if not observations_per_behavior.eq(3).all():
        raise ValueError(
            "Expected three observations per behavior."
        )

    differences = paired["depth"] - paired["breadth"]

    # Keep repeated seed observations grouped by behavior.
    behavior_means = (
        differences
        .groupby(level="behavior_id")
        .mean()
        .to_numpy()
    )

    observed_difference = behavior_means.mean()

    n_behaviors = len(behavior_means)

    n_bootstrap = 10000

    rng = np.random.default_rng(2026)

    # Resample behavior-level clusters with replacement.
    samples = rng.choice(
        behavior_means,
        size=(n_bootstrap, n_behaviors),
        replace=True,
    )

    bootstrap_means = samples.mean(axis=1)

    # Calculate a percentile-based 95% interval.
    lower, upper = np.percentile(
        bootstrap_means,
        [2.5, 97.5],
    )

    report = pd.DataFrame([{
        "method": "Paired behavior-level cluster bootstrap",
        "unique_behaviors": n_behaviors,
        "matched_observations": len(paired),
        "bootstrap_samples": n_bootstrap,
        "bootstrap_seed": 2026,
        "confidence_level": 0.95,
        "observed_difference_pp":
            observed_difference * 100,
        "ci_lower_pp": lower * 100,
        "ci_upper_pp": upper * 100,
        "interval_includes_zero":
            bool(lower <= 0 <= upper),
    }])

    print("\nBOOTSTRAP CONFIDENCE INTERVAL\n")

    print(f"Unique behaviors: {n_behaviors}")
    print(f"Bootstrap samples: {n_bootstrap:,}")

    print(
        f"Observed difference: "
        f"{observed_difference * 100:.2f} pp"
    )

    print(
        f"95% confidence interval: "
        f"[{lower * 100:.2f}, "
        f"{upper * 100:.2f}] pp"
    )

    print(
        f"Interval includes zero: "
        f"{bool(lower <= 0 <= upper)}"
    )

    report.to_csv(
        OUTPUT / "bootstrap_confidence_interval.csv",
        index=False,
    )


def calculate_repeatability(paired):

    # Count the positive outcomes across seeds
    # for each individual behavior.
    behavior_counts = (
        paired
        .groupby(level="behavior_id")[["breadth", "depth"]]
        .sum()
    )

    summaries = []

    for setup in ["breadth", "depth"]:

        counts = behavior_counts[setup]

        for frequency in range(4):

            number = int((counts == frequency).sum())

            summaries.append({
                "setup": setup,
                "flagged_seeds": frequency,
                "number_of_behaviors": number,
                "percentage": 100 * number / len(counts),
            })

    summary = pd.DataFrame(summaries)

    print("\nBEHAVIOR-LEVEL REPEATABILITY\n")

    print(summary.round(2).to_string(index=False))

    print("\nCONSISTENCY ACROSS SEEDS\n")

    for setup in ["breadth", "depth"]:

        counts = behavior_counts[setup]

        consistent = int(
            counts.isin([0, 3]).sum()
        )

        variable = len(counts) - consistent

        print(f"{setup.capitalize()}:")
        print(f"  Consistent behaviors: {consistent}")
        print(f"  Variable behaviors: {variable}")
        print(
            f"  Consistency rate: "
            f"{100 * consistent / len(counts):.2f}%"
        )

    summary.to_csv(
        OUTPUT / "repeatability_summary.csv",
        index=False,
    )


def calculate_stratified_bootstrap(paired, extension):

    # Obtain the category associated with each behavior.
    categories = extension[
        ["behavior_id", "category"]
    ].drop_duplicates()

    if categories["behavior_id"].duplicated().any():
        raise ValueError(
            "A behavior belongs to multiple categories."
        )

    # Calculate paired differences for each observation.
    differences = paired["depth"] - paired["breadth"]

    # Average repeated seed observations by behavior.
    behavior_means = (
        differences
        .groupby(level="behavior_id")
        .mean()
        .rename("mean_difference")
        .reset_index()
    )

    # Associate each behavior with its category.
    behavior_means = behavior_means.merge(
        categories,
        on="behavior_id",
        how="left",
        validate="one_to_one",
    )

    if behavior_means["category"].isna().any():
        raise ValueError("Missing category information.")

    # Validate the category-balanced sampling design.
    category_counts = (
        behavior_means.groupby("category").size()
    )

    if len(category_counts) != 10:
        raise ValueError("Expected ten categories.")

    if not category_counts.eq(2).all():
        raise ValueError(
            "Expected two behaviors per category."
        )

    n_bootstrap = 10000

    rng = np.random.default_rng(2026)

    bootstrap_means = np.zeros(n_bootstrap)

    # Resample behaviors independently within each category.
    for _, group in behavior_means.groupby("category"):

        values = group["mean_difference"].to_numpy()

        samples = rng.choice(
            values,
            size=(n_bootstrap, len(values)),
            replace=True,
        )

        # Each category receives equal weight.
        bootstrap_means += (
            samples.mean(axis=1) / len(category_counts)
        )

    observed_difference = (
        behavior_means["mean_difference"].mean()
    )

    lower, upper = np.percentile(
        bootstrap_means,
        [2.5, 97.5],
    )

    report = pd.DataFrame([{
        "method":
            "Category-stratified paired cluster bootstrap",
        "unique_behaviors": len(behavior_means),
        "categories": len(category_counts),
        "behaviors_per_category": 2,
        "bootstrap_samples": n_bootstrap,
        "bootstrap_seed": 2026,
        "confidence_level": 0.95,
        "observed_difference_pp":
            observed_difference * 100,
        "ci_lower_pp": lower * 100,
        "ci_upper_pp": upper * 100,
        "interval_includes_zero":
            bool(lower <= 0 <= upper),
    }])

    print("\nCATEGORY-STRATIFIED BOOTSTRAP\n")

    print(f"Categories: {len(category_counts)}")
    print(f"Unique behaviors: {len(behavior_means)}")
    print("Behaviors per category: 2")
    print(f"Bootstrap samples: {n_bootstrap:,}")

    print(
        f"Observed difference: "
        f"{observed_difference * 100:.2f} pp"
    )

    print(
        f"95% confidence interval: "
        f"[{lower * 100:.2f}, "
        f"{upper * 100:.2f}] pp"
    )

    print(
        f"Interval includes zero: "
        f"{bool(lower <= 0 <= upper)}"
    )

    report.to_csv(
        OUTPUT / "stratified_bootstrap_interval.csv",
        index=False,
    )


def calculate_across_seed_statistics(summary):

    extension_summary = summary[
        summary["setup"].isin(["breadth", "depth"])
    ]

    records = []

    for setup, group in extension_summary.groupby("setup"):

        records.append({
            "setup": setup,

            "number_of_seeds":
                group["seed"].nunique(),

            "total_runs":
                int(group["total_runs"].sum()),

            "total_flagged_runs":
                int(group["flagged_runs"].sum()),

            "mean_seed_rate_pct":
                group["judge_assessed_rate_pct"].mean(),

            "sd_seed_rate_pp":
                group["judge_assessed_rate_pct"].std(ddof=1),

            "total_recorded_queries":
                int(group["total_recorded_queries"].sum()),

            "mean_seed_queries_flagged":
                group["mean_queries_flagged"].mean(),
        })

    across_seeds = pd.DataFrame(records)

    print("\nINDEPENDENT ACROSS-SEED STATISTICS\n")

    print(across_seeds.round(2).to_string(index=False))

    across_seeds.to_csv(
        OUTPUT / "across_seed_statistics.csv",
        index=False,
    )


def main():

    OUTPUT.mkdir(parents=True, exist_ok=True)

    reproduction = load_results(REPRODUCTION)
    extension = load_results(EXTENSION)

    combined = pd.concat(
        [reproduction, extension],
        ignore_index=True,
    )

    summary = calculate_descriptive_statistics(combined)

    print("\nINDEPENDENT DESCRIPTIVE STATISTICS\n")

    print(summary.round(2).to_string(index=False))

    summary.to_csv(
        OUTPUT / "descriptive_statistics.csv",
        index=False,
    )

    print(
        f"\nReport saved to: "
        f"{OUTPUT / 'descriptive_statistics.csv'}"
    )

    calculate_across_seed_statistics(summary)

    paired = calculate_paired_outcomes(extension)

    calculate_bootstrap_interval(paired)

    calculate_repeatability(paired)

    calculate_stratified_bootstrap(paired, extension)


if __name__ == "__main__":
    main()
