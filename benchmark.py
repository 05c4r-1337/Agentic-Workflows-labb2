"""
Benchmark — runs the baseline and full workflows N times each on the same file
and prints a side-by-side comparison. Used to answer: does the agentic loop
actually improve on a single DocWriter pass?

Usage:
    python benchmark.py sample_code/RagQueryService.cs --runs 3
"""

import argparse
import contextlib
import csv
import io
import json
import statistics
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from orchestrator import Orchestrator

# Windows consoles default to cp1252 and crash on the arrow glyphs below.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def run_once(target: str, output_dir: Path, baseline: bool):
    orch = Orchestrator(
        target_file=target,
        output_dir=str(output_dir),
        baseline=baseline,
        verbose=False,
    )
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return orch.run()


def summarize(reports):
    scores = [r.review_score for r in reports]
    cycles = [r.cycles_used for r in reports]
    retries = [r.fact_check_retries for r in reports]
    runtimes = [r.runtime_seconds for r in reports]
    approved = sum(1 for r in reports if r.approved and not r.force_approved)
    force = sum(1 for r in reports if r.force_approved)
    n = len(reports)
    return {
        "n": n,
        "avg_score": statistics.mean(scores),
        "std_score": statistics.stdev(scores) if n > 1 else 0.0,
        "min_score": min(scores),
        "max_score": max(scores),
        "approval_rate": approved / n,
        "force_rate": force / n,
        "avg_cycles": statistics.mean(cycles),
        "avg_retries": statistics.mean(retries),
        "avg_runtime": statistics.mean(runtimes),
        "total_runtime": sum(runtimes),
    }


def _fmt_score(v: float, std: float | None = None) -> str:
    if std is None or std == 0:
        return f"{v:.1f}/10"
    return f"{v:.1f} ± {std:.1f}"


def _fmt_pct(v: float) -> str:
    return f"{v * 100:.0f}%"


def _delta(base: float, full: float, unit: str = "", fmt=lambda v: f"{v:+.1f}") -> str:
    d = full - base
    if abs(d) < 1e-9:
        return ""
    arrow = "▲" if d > 0 else "▼"
    return f"  {arrow} {fmt(d)}{unit}"


def print_table(target: str, base: dict, full: dict):
    w = 74
    print(f"\n{'=' * w}")
    print(f"  Benchmark: {target}   ({base['n']} runs per mode)")
    print(f"{'=' * w}")
    print(f"  {'Metric':<28} {'Baseline':>15} {'Full':>15}   Delta")
    print(f"  {'-' * (w - 4)}")

    def row(label, b_str, f_str, delta=""):
        print(f"  {label:<28} {b_str:>15} {f_str:>15}{delta}")

    row(
        "Avg review score",
        _fmt_score(base["avg_score"], base["std_score"]),
        _fmt_score(full["avg_score"], full["std_score"]),
        _delta(base["avg_score"], full["avg_score"]),
    )
    row(
        "Min / Max score",
        f"{base['min_score']} / {base['max_score']}",
        f"{full['min_score']} / {full['max_score']}",
    )
    row(
        "Approval rate",
        _fmt_pct(base["approval_rate"]),
        _fmt_pct(full["approval_rate"]),
        _delta(base["approval_rate"] * 100, full["approval_rate"] * 100, "%", lambda v: f"{v:+.0f}"),
    )
    row(
        "Force-approved rate",
        _fmt_pct(base["force_rate"]),
        _fmt_pct(full["force_rate"]),
    )
    row(
        "Avg cycles",
        f"{base['avg_cycles']:.1f}",
        f"{full['avg_cycles']:.1f}",
        _delta(base["avg_cycles"], full["avg_cycles"]),
    )
    row(
        "Avg fact-check retries",
        f"{base['avg_retries']:.1f}",
        f"{full['avg_retries']:.1f}",
        _delta(base["avg_retries"], full["avg_retries"]),
    )
    row(
        "Avg runtime",
        f"{base['avg_runtime']:.1f}s",
        f"{full['avg_runtime']:.1f}s",
        _delta(base["avg_runtime"], full["avg_runtime"], "s"),
    )
    row(
        "Total runtime",
        f"{base['total_runtime']:.1f}s",
        f"{full['total_runtime']:.1f}s",
    )
    print(f"{'=' * w}")

    verdict = full["avg_score"] - base["avg_score"]
    if verdict >= 1.0:
        print(f"  Full workflow scores {verdict:+.1f} higher on average.")
    elif verdict <= -1.0:
        print(f"  Baseline scores {-verdict:+.1f} higher on average — agentic loop not helping.")
    else:
        print(f"  No meaningful score difference ({verdict:+.1f}).")
    print(f"{'=' * w}\n")


def main():
    parser = argparse.ArgumentParser(description="Run baseline vs full workflow and compare.")
    parser.add_argument("target", help="Path to source file (.py or .cs)")
    parser.add_argument("--runs", type=int, default=3, help="Runs per mode (default: 3)")
    parser.add_argument("--output-dir", default="benchmarks", help="Where to store per-run artefacts")
    args = parser.parse_args()

    if not Path(args.target).exists():
        print(f"Error: file not found: {args.target}")
        return 1

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    total_start = time.time()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = Path(args.target).stem
    csv_path = out / f"benchmark_{stem}_{ts}.csv"
    summary_path = out / f"benchmark_{stem}_{ts}.json"

    # Open CSV up front and flush after each row so a crash leaves us partial data.
    csv_file = open(csv_path, "w", newline="", encoding="utf-8")
    writer = csv.writer(csv_file)
    writer.writerow(["mode", "run", "review_score", "approved", "force_approved",
                     "cycles_used", "fact_check_retries", "runtime_seconds", "error"])

    def collect(mode_label: str, baseline: bool):
        reports, failures = [], []
        print(f"\n{mode_label} — {args.runs} run(s)")
        for i in range(args.runs):
            t0 = time.time()
            try:
                r = run_once(args.target, out, baseline=baseline)
            except Exception as e:
                elapsed = time.time() - t0
                err = f"{type(e).__name__}: {e}"
                print(f"  [{i + 1}/{args.runs}] FAILED ({elapsed:.1f}s) — {err}")
                failures.append((i + 1, err))
                writer.writerow(["baseline" if baseline else "full", i + 1,
                                 "", "", "", "", "", round(elapsed, 1), err])
                csv_file.flush()
                continue
            reports.append(r)
            elapsed = time.time() - t0
            if baseline:
                print(f"  [{i + 1}/{args.runs}] score={r.review_score}/10  "
                      f"cycles={r.cycles_used}  {elapsed:.1f}s")
            else:
                status = "approved" if r.approved and not r.force_approved else "forced"
                print(f"  [{i + 1}/{args.runs}] score={r.review_score}/10  "
                      f"cycles={r.cycles_used}  retries={r.fact_check_retries}  "
                      f"{status}  {elapsed:.1f}s")
            writer.writerow(["baseline" if baseline else "full", i + 1,
                             r.review_score, r.approved, r.force_approved,
                             r.cycles_used, r.fact_check_retries, r.runtime_seconds, ""])
            csv_file.flush()
        return reports, failures

    try:
        base_reports, base_failures = collect("Baseline", baseline=True)
        full_reports, full_failures = collect("Full workflow", baseline=False)
    finally:
        csv_file.close()

    if not base_reports or not full_reports:
        print("\nNot enough successful runs in one of the modes to produce a comparison.")
        print(f"CSV (partial): {csv_path}")
        return 1

    base_stats = summarize(base_reports)
    full_stats = summarize(full_reports)
    if base_failures or full_failures:
        print(f"\nFailures: baseline={len(base_failures)}  full={len(full_failures)}")
    print_table(args.target, base_stats, full_stats)

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "target": args.target,
                "runs_per_mode": args.runs,
                "total_elapsed_seconds": round(time.time() - total_start, 1),
                "baseline": {
                    "summary": base_stats,
                    "runs": [asdict(r) for r in base_reports],
                    "failures": [{"run": n, "error": e} for n, e in base_failures],
                },
                "full": {
                    "summary": full_stats,
                    "runs": [asdict(r) for r in full_reports],
                    "failures": [{"run": n, "error": e} for n, e in full_failures],
                },
            },
            f,
            indent=2,
        )

    print(f"Summary: {summary_path}")
    print(f"CSV:     {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
