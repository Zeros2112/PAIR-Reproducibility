
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "results" / "independent_validation"

OUTPUT = INPUT / "figures"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.labelsize": 10,
    "axes.titlesize": 12,
    "legend.fontsize": 9,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

BREADTH_COLOR = "#4477AA"
DEPTH_COLOR = "#228833"


def save_figure(fig, filename):

    OUTPUT.mkdir(parents=True, exist_ok=True)

    fig.savefig(
        OUTPUT / f"{filename}.pdf",
        bbox_inches="tight",
    )

    fig.savefig(
        OUTPUT / f"{filename}.png",
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(f"Saved: {filename}.pdf and {filename}.png")


def plot_bootstrap_intervals():

    unstratified = pd.read_csv(
        INPUT / "bootstrap_confidence_interval.csv"
    )

    stratified = pd.read_csv(
        INPUT / "stratified_bootstrap_interval.csv"
    )

    data = pd.concat(
        [unstratified, stratified],
        ignore_index=True,
    )

    observed = data["observed_difference_pp"].to_numpy()
    lower = data["ci_lower_pp"].to_numpy()
    upper = data["ci_upper_pp"].to_numpy()

    errors = np.array([
        observed - lower,
        upper - observed,
    ])

    fig, ax = plt.subplots(figsize=(6.5, 3.0))

    positions = [1, 0]

    ax.errorbar(
        observed,
        positions,
        xerr=errors,
        fmt="o",
        color="#333333",
        capsize=5,
        markersize=6,
        linewidth=1.8,
    )

    ax.axvline(
        0,
        color="gray",
        linestyle="--",
        linewidth=1,
    )

    ax.set_yticks(positions)

    ax.set_yticklabels([
        "Unstratified",
        "Category-stratified",
    ])

    ax.set_xlabel(
        "Difference in judge-assessed rates (Depth - Breadth, pp)"
    )

    ax.set_title("95% Bootstrap Confidence Intervals")

    ax.set_ylim(-0.6, 1.6)

    ax.grid(axis="x", alpha=0.2)

    for i, position in enumerate(positions):

        ax.text(
            observed[i],
            position + 0.22,
            f"{observed[i]:+.2f} "
            f"[{lower[i]:+.2f}, {upper[i]:+.2f}]",
            ha="center",
            fontsize=9,
        )

    fig.tight_layout()

    save_figure(fig, "bootstrap_intervals")


def plot_repeatability():

    data = pd.read_csv(
        INPUT / "repeatability_summary.csv"
    )

    counts = data.pivot(
        index="flagged_seeds",
        columns="setup",
        values="number_of_behaviors",
    ).sort_index()

    positions = np.arange(len(counts))
    width = 0.35

    fig, ax = plt.subplots(figsize=(6.5, 3.8))

    breadth_bars = ax.bar(
        positions - width / 2,
        counts["breadth"],
        width,
        label="Breadth",
        color=BREADTH_COLOR,
    )

    depth_bars = ax.bar(
        positions + width / 2,
        counts["depth"],
        width,
        label="Depth",
        color=DEPTH_COLOR,
        hatch="//",
    )

    ax.bar_label(breadth_bars, padding=3)
    ax.bar_label(depth_bars, padding=3)

    ax.set_xticks(positions)

    ax.set_xticklabels([
        f"{seed} of 3"
        for seed in counts.index
    ])

    ax.set_xlabel("Number of seeds with flagged outcomes")
    ax.set_ylabel("Number of behaviors")

    ax.set_title("Behavior-Level Repeatability")

    ax.set_ylim(0, counts.max().max() + 4)

    ax.legend()

    ax.grid(axis="y", alpha=0.2)
    ax.set_axisbelow(True)

    fig.tight_layout()

    save_figure(fig, "behavior_repeatability")


def plot_paired_outcomes():

    data = pd.read_csv(
        INPUT / "paired_outcomes.csv"
    )

    counts = data.set_index("outcome")["count"]

    matrix = np.array([
        [
            counts["Both flagged"],
            counts["Breadth only"],
        ],
        [
            counts["Depth only"],
            counts["Neither flagged"],
        ],
    ])

    total = matrix.sum()

    agreement = 100 * np.trace(matrix) / total

    fig, ax = plt.subplots(figsize=(5, 4))

    ax.imshow(
        matrix,
        cmap="Blues",
        vmin=0,
        vmax=matrix.max(),
    )

    for row in range(2):

        for col in range(2):

            count = matrix[row, col]
            percentage = 100 * count / total

            text_color = (
                "white"
                if count > matrix.max() / 2
                else "black"
            )

            ax.text(
                col,
                row,
                f"{count}\n({percentage:.1f}%)",
                ha="center",
                va="center",
                fontsize=12,
                color=text_color,
            )

    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])

    ax.set_xticklabels(["Flagged", "Unflagged"])
    ax.set_yticklabels(["Flagged", "Unflagged"])

    ax.set_xlabel("Depth")
    ax.set_ylabel("Breadth")

    ax.set_title(
        f"Paired Outcome Agreement: {agreement:.2f}%"
    )

    fig.tight_layout()

    save_figure(fig, "paired_outcome_agreement")


def main():

    print("\nGENERATING INDEPENDENT ANALYSIS FIGURES\n")

    OUTPUT.mkdir(parents=True, exist_ok=True)

    plot_bootstrap_intervals()

    plot_repeatability()

    plot_paired_outcomes()

    print(f"\nAll figures saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
