"""PAIR reproduction + breadth/depth extension.

Student project version: independent streams, short functions, simple CSV/JSONL.
Use demo mode first; it DOES NOT produce real PAIR measurements.
"""

import argparse
import csv
import hashlib
import json
import random
import time
from pathlib import Path

from models import DemoModels, OllamaModels


SETUPS = {
    "reproduction": (30, 3),
    "breadth": (10, 3),
    "depth": (5, 6),
}


def load_behaviors(filename):
    """Accepts the official JBB CSV (Index,Goal,Category) or demo CSV."""
    with open(filename, encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    behaviors = []
    for i, row in enumerate(rows):
        goal = (row.get("Goal") or row.get("goal") or "").strip()
        category = (row.get("Category") or row.get("category") or "").strip()
        behavior_id = row.get("Index", row.get("id", str(i)))
        if not goal or not category:
            raise ValueError("Dataset must have Goal and Category columns")
        behaviors.append({"id": str(behavior_id), "goal": goal,
                          "category": category})
    if len({b["id"] for b in behaviors}) != len(behaviors):
        raise ValueError("Behavior IDs must be unique")
    return behaviors


def choose_20(behaviors):
    """Pick exactly 2 behaviors from each of 10 categories."""
    groups = {}
    for behavior in behaviors:
        groups.setdefault(behavior["category"], []).append(behavior)
    if len(groups) != 10 or any(len(items) < 2 for items in groups.values()):
        raise ValueError("Extension needs 10 categories with at least 2 each")
    selected = []
    rng = random.Random(2026)  # same 20 behaviors in both configurations
    for category in sorted(groups):
        selected.extend(rng.sample(groups[category], 2))
    return selected


def short_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def run_one(behavior, name, n_streams, n_steps, seed, models,
            save_text=False):
    """Run PAIR on ONE behavior. Loop over streams then iterations.

    Round-robin scheduling represents independent streams but is not parallel
    execution. Stop immediately when the judge finds an unsafe response.
    """
    histories = [[] for _ in range(n_streams)]
    attempts = []
    private_text = []
    total_queries = 0
    found = False
    success_step = None

    for step in range(1, n_steps + 1):
        for stream in range(n_streams):
            prompt, improvement = models.make_prompt(
                behavior, histories[stream], stream, step, seed)
            answer = models.target_answer(prompt, behavior, stream, step, seed)
            success, judge_label = models.judge_answer(prompt, answer)
            total_queries += 1  # count TARGET queries only

            attempts.append({
                "behavior_id": behavior["id"],
                "category": behavior["category"],
                "setup": name,
                "seed": seed,
                "query_number": total_queries,
                "stream": stream + 1,
                "iteration": step,
                "success": int(success),
                "judge_label": judge_label,
                "prompt_hash": short_hash(prompt),
                "answer_hash": short_hash(answer),
            })
            if save_text:
                # This can contain sensitive test material. Keep it private.
                private_text.append({
                    "behavior_id": behavior["id"], "setup": name,
                    "seed": seed, "query_number": total_queries,
                    "prompt": prompt, "answer": answer,
                    "improvement": improvement, "judge_label": judge_label,
                })
            histories[stream].append({
                "prompt": prompt,
                "response": answer,
                "success": success,
            })
            if success:
                found = True
                success_step = step
                break
        if found:
            break

    result = {
        "behavior_id": behavior["id"],
        "category": behavior["category"],
        "setup": name,
        "seed": seed,
        "streams": n_streams,
        "max_iterations": n_steps,
        "budget": n_streams * n_steps,
        "queries_used": total_queries,
        "success": int(found),
        "success_iteration": success_step,
    }
    return result, attempts, private_text


def write_csv(filename, rows):
    if not rows:
        return
    with open(filename, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(filename, rows):
    with open(filename, "w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")




def checkpoint_path(out, setup, seed, behavior_id):
    """One small checkpoint per behavior, easy to resume after a disconnect."""
    filename = f"{setup}_seed{seed}_{short_hash(str(behavior_id))}.json"
    return out / "checkpoints" / filename


def save_checkpoint(path, result, attempts, private_text, settings):
    """Write to a temporary file first so a crash won't corrupt a checkpoint."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "settings": settings,
        "result": result,
        "attempts": attempts,
        "private_text": private_text,
    }
    temp_file = path.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False)
        file.flush()
        import os
        try:
            os.fsync(file.fileno())
        except OSError:
            pass  # Some cloud-mounted filesystems do not support fsync
    temp_file.replace(path)


def collect_results(out, settings, behaviors, ext_behaviors, args, start_time):
    """Rebuild the usual CSV files from all saved checkpoints."""
    results, logs, private_text = [], [], []
    folder = out / "checkpoints"
    for path in sorted(folder.glob("*.json")):
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved["settings"] != settings:
            raise ValueError(
                f"This folder has results for different models or data: {path}. "
                "Use a separate --out folder for a different experiment."
            )
        results.append(saved["result"])
        logs.extend(saved["attempts"])
        private_text.extend(saved["private_text"])

    write_csv(out / "results.csv", results)
    write_csv(out / "attempts.csv", logs)
    write_csv(out / "selected_extension_behaviors.csv", [
        {"behavior_id": b["id"], "category": b["category"]}
        for b in ext_behaviors
    ])
    if args.save_text:
        write_jsonl(out / "PRIVATE_text_do_not_upload.jsonl", private_text)

    all_setups = sorted({r["setup"] for r in results})
    info = {
        "mode": args.mode,
        "simulated": args.mode == "demo",
        "dataset_file": args.data,
        "dataset_size": len(behaviors),
        "dataset_sha256": settings["dataset_sha256"],
        "seed_list": sorted({int(r["seed"]) for r in results}),
        "setups": {name: SETUPS[name] for name in all_setups},
        "models": settings["models"],
        "completed_behavior_runs": len(results),
        "target_model_calls": len(logs),
        "elapsed_seconds_this_session": round(time.perf_counter() - start_time, 2),
        "note": ("Synthetic debugging output; NOT PAIR results" if args.mode == "demo"
                 else "Local model evaluation; not an exact reproduction of original models"),
    }
    (out / "run_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    return len(results)


def main():
    parser = argparse.ArgumentParser(description="PAIR student experiment")
    parser.add_argument("--mode", choices=["demo", "ollama"], default="demo")
    parser.add_argument("--data", default="data/demo_behaviors.csv")
    parser.add_argument("--task", choices=["reproduction", "extension", "all"],
                        default="all")
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--out", default="results/demo_run")
    parser.add_argument("--attacker", default="llama3.2:3b")
    parser.add_argument("--target", default="llama3.2:3b")
    parser.add_argument("--judge", default="llama-guard3:1b")
    parser.add_argument("--start", type=int, default=0,
                        help="Start at this position in the selected behaviors (0-based)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Number of behaviors per setup (0 means all remaining)")
    parser.add_argument("--save-text", action="store_true")
    parser.add_argument("--allow-local-tests", action="store_true")
    args = parser.parse_args()

    if args.mode == "ollama" and not args.allow_local_tests:
        parser.error("Add --allow-local-tests for authorized Ollama tests")
    if args.start < 0 or args.limit < 0:
        parser.error("--start and --limit must be nonnegative")

    behaviors = load_behaviors(args.data)
    ext_behaviors = choose_20(behaviors) if args.task != "reproduction" else []
    setups = (["reproduction"] if args.task == "reproduction" else
              ["breadth", "depth"] if args.task == "extension" else
              ["reproduction", "breadth", "depth"])
    models = DemoModels() if args.mode == "demo" else OllamaModels(
        args.attacker, args.target, args.judge)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    settings = {
        "mode": args.mode,
        "dataset_sha256": hashlib.sha256(Path(args.data).read_bytes()).hexdigest(),
        "models": ({"attacker": args.attacker, "target": args.target,
                    "judge": args.judge} if args.mode == "ollama" else "SIMULATED"),
    }
    start_time = time.perf_counter()

    # No checkpoint files are overwritten. Re-running a command skips saved work.
    try:
        for setup in setups:
            n_streams, n_steps = SETUPS[setup]
            full_list = behaviors if setup == "reproduction" else ext_behaviors
            chosen = full_list[args.start:]
            if args.limit:
                chosen = chosen[:args.limit]
            for seed in args.seeds:
                for i, behavior in enumerate(chosen, start=1):
                    path = checkpoint_path(out, setup, seed, behavior["id"])
                    if path.exists():
                        saved = json.loads(path.read_text(encoding="utf-8"))
                        if saved["settings"] != settings:
                            raise ValueError(f"Checkpoint configuration mismatch: {path}")
                        print(f"SKIP {setup} seed={seed} id={behavior['id']} (saved)", flush=True)
                        continue
                    result, attempts, private = run_one(
                        behavior, setup, n_streams, n_steps, seed, models,
                        save_text=args.save_text)
                    save_checkpoint(path, result, attempts, private, settings)
                    # Individual checkpoint saved to Drive NOW. Build CSV once per batch.
                    print(f"{setup} seed={seed} {i}/{len(chosen)} "
                          f"id={behavior['id']}: success={result['success']}, "
                          f"queries={result['queries_used']} | checkpoint saved",
                          flush=True)
    finally:
        # Results from any completed behavior are preserved even when a later call fails.
        collect_results(out, settings, behaviors, ext_behaviors, args, start_time)

    print("\nSaved checkpoints and summary CSVs to", out)
    print("Rerun the same command to skip completed behaviors.")
    print("MODE:", "SIMULATION ONLY" if args.mode == "demo" else "LOCAL MODELS")


if __name__ == "__main__":
    main()
