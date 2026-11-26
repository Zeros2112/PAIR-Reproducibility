"""Make the result tables and 3 plots for our report.

All percentages here come from results.csv; the script never makes up results.
"""

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


def load_csv(path):
    with open(path, encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def save_csv(path, rows):
    if not rows:
        return
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def calculate_summary(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["setup"], int(row["seed"]))].append(row)

    summaries = []
    for (setup, seed), group in sorted(groups.items()):
        passed = [r for r in group if int(r["success"]) == 1]
        queries = [int(r["queries_used"]) for r in group]
        summaries.append({
            "setup": setup,
            "seed": seed,
            "behaviors": len(group),
            "successes": len(passed),
            "success_rate_pct": round(100 * len(passed) / len(group), 2),
            "queries_per_success": round(statistics.mean(
                int(r["queries_used"]) for r in passed), 2) if passed else "NA",
            "mean_queries_all": round(statistics.mean(queries), 2),
            "total_target_queries": sum(queries),
        })
    return summaries


def seed_summary(summary):
    groups = defaultdict(list)
    for row in summary:
        groups[row["setup"]].append(row)
    output = []
    for setup, group in sorted(groups.items()):
        success = [r["success_rate_pct"] for r in group]
        output.append({
            "setup": setup,
            "seeds": len(group),
            "mean_success_pct": round(statistics.mean(success), 2),
            "sd_success_pct": round(statistics.stdev(success), 2)
            if len(success) > 1 else 0,
            "mean_queries_per_success": round(statistics.mean([
                float(r["queries_per_success"]) for r in group
                if r["queries_per_success"] != "NA"
            ]), 2) if any(r["queries_per_success"] != "NA" for r in group) else "NA",
        })
    return output


def make_curve(rows):
    # Each behavior counts as a success after its first successful query.
    groups = defaultdict(list)
    for row in rows:
        if row["setup"] in ("breadth", "depth"):
            groups[row["setup"]].append(row)
    output = []
    for setup, group in sorted(groups.items()):
        for budget in range(1, 31):
            successful = sum(
                int(r["success"]) and int(r["queries_used"]) <= budget
                for r in group
            )
            output.append({
                "setup": setup, "queries": budget,
                "success_rate_pct": round(100 * successful / len(group), 2),
            })
    return output


def category_summary(rows):
    groups = defaultdict(list)
    for row in rows:
        if row["setup"] == "reproduction":
            groups[row["category"]].append(row)
    output = []
    for category, group in sorted(groups.items()):
        output.append({
            "category": category,
            "trials": len(group),
            "successes": sum(int(r["success"]) for r in group),
            "success_rate_pct": round(100 * sum(int(r["success"])
                                          for r in group) / len(group), 2),
        })
    return output


def make_plots(output, summary, curve, categories, simulated):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Matplotlib missing: CSV tables created, but no PNG figures.")
        return

    label = "SIMULATED DATA - NOT ACTUAL PAIR RESULTS" if simulated else "Local model evaluation"
    figures = output / "figures"
    figures.mkdir(exist_ok=True)

    if curve:
        fig, ax = plt.subplots(figsize=(7.4, 4.3))
        for setup in ("breadth", "depth"):
            points = [r for r in curve if r["setup"] == setup]
            ax.plot([r["queries"] for r in points],
                    [r["success_rate_pct"] for r in points],
                    linewidth=2, label="10 streams x 3 steps" if setup == "breadth"
                    else "5 streams x 6 steps")
        ax.set(xlabel="Target queries allowed per behavior", ylabel="Success rate (%)",
               xlim=(1, 30), ylim=(0, 100), title="Breadth vs. depth (30-query budget)")
        ax.grid(alpha=0.25)
        ax.legend()
        fig.text(0.5, 0.01, label, ha="center", fontsize=8)
        fig.tight_layout(rect=(0, 0.05, 1, 1))
        fig.savefig(figures / "extension_curve.png", dpi=180)
        plt.close(fig)

    ext = [r for r in summary if r["setup"] in ("breadth", "depth")]
    if ext:
        names = ["Breadth (10x3)", "Depth (5x6)"]
        vals = [next((r["mean_success_pct"] for r in ext
                      if r["setup"] == key), 0) for key in ("breadth", "depth")]
        errs = [next((r["sd_success_pct"] for r in ext
                      if r["setup"] == key), 0) for key in ("breadth", "depth")]
        fig, ax = plt.subplots(figsize=(6.3, 4))
        ax.bar(names, vals, yerr=errs, capsize=5)
        ax.set(ylabel="Success rate (%)", ylim=(0, 100),
               title="Extension: mean success across seeds")
        fig.text(0.5, 0.01, label, ha="center", fontsize=8)
        fig.tight_layout(rect=(0, 0.05, 1, 1))
        fig.savefig(figures / "extension_comparison.png", dpi=180)
        plt.close(fig)

    if categories:
        fig, ax = plt.subplots(figsize=(7.8, 4.6))
        ax.barh([r["category"] for r in categories],
                [r["success_rate_pct"] for r in categories])
        ax.set(xlabel="Success rate (%)", xlim=(0, 100),
               title="Reproduction setup: results by category")
        ax.invert_yaxis()
        fig.text(0.5, 0.01, label, ha="center", fontsize=8)
        fig.tight_layout(rect=(0, 0.05, 1, 1))
        fig.savefig(figures / "reproduction_categories.png", dpi=180)
        plt.close(fig)


def make_review_sample(output, attempts, count=10):
    # We do not publish full prompts/responses. Reviewers can locate originals
    # in PRIVATE_text_do_not_upload.jsonl if --save-text was used.
    # Pick spread-out attempts, not just the first 10 records.
    if not attempts:
        return
    step = max(1, len(attempts) // count)
    selected = attempts[::step][:count]
    rows = []
    for r in selected:
        rows.append({
            "behavior_id": r["behavior_id"], "setup": r["setup"],
            "seed": r["seed"], "query_number": r["query_number"],
            "judge_label": r["judge_label"],
            "human_unsafe_0_or_1": "", "notes": "",
        })
    save_csv(output / "manual_review_template.csv", rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="results/demo_run")
    args = parser.parse_args()
    output = Path(args.input)
    results = load_csv(output / "results.csv")
    attempts = load_csv(output / "attempts.csv")
    info = json.loads((output / "run_info.json").read_text(encoding="utf-8"))

    summary = calculate_summary(results)
    seed_stats = seed_summary(summary)
    curve = make_curve(results)
    categories = category_summary(results)
    save_csv(output / "summary_by_seed.csv", summary)
    save_csv(output / "summary_across_seeds.csv", seed_stats)
    save_csv(output / "success_curve.csv", curve)
    save_csv(output / "reproduction_categories.csv", categories)
    make_review_sample(output, attempts)
    make_plots(output, seed_stats, curve, categories, info["simulated"])

    print("\n" + ("SIMULATED RESULTS - DO NOT REPORT AS EMPIRICAL RESULTS"
                   if info["simulated"] else "LOCAL MODEL RESULTS"))
    for r in seed_stats:
        print(f"{r['setup']}: {r['mean_success_pct']}% "
              f"+/- {r['sd_success_pct']}% (over {r['seeds']} seeds)")
    print("Wrote tables and figures to", output)


if __name__ == "__main__":
    main()
