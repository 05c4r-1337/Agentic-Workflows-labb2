"""
Compare two evaluation JSON reports side by side.

Usage:
    python compare.py <baseline_eval.json> <full_eval.json>

Example:
    python compare.py docs/example_baseline_eval.json docs/example_eval.json
"""

import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fmt_pct(v: float) -> str:
    return f"{v * 100:.0f}%"


def main():
    if len(sys.argv) != 3:
        print("Usage: python compare.py <baseline_eval.json> <full_eval.json>")
        sys.exit(1)

    base = load(sys.argv[1])
    full = load(sys.argv[2])

    w_label, w_val = 30, 14

    def row(label, b, f, fmt=str):
        bv = fmt(b) if callable(fmt) else fmt
        fv = fmt(f) if callable(fmt) else fmt
        diff = ""
        if isinstance(b, (int, float)) and isinstance(f, (int, float)):
            delta = f - b
            if delta > 0:
                diff = f"  ▲ +{delta:.1f}".rstrip("0").rstrip(".")
            elif delta < 0:
                diff = f"  ▼ {delta:.1f}".rstrip("0").rstrip(".")
        print(f"  {label:<{w_label}} {str(fmt(b)):>{w_val}} {str(fmt(f)):>{w_val}}{diff}")

    print(f"\n{'=' * 65}")
    print(f"  Baseline vs Full Workflow — {Path(base['file']).name}")
    print(f"{'=' * 65}")
    print(f"  {'Metric':<{w_label}} {'Baseline':>{w_val}} {'Full':>{w_val}}")
    print(f"  {'-' * (w_label + w_val * 2 + 2)}")

    row("Avg review score",        base["avg_score"],             full["avg_score"],             lambda v: f"{v}/10")
    row("Min score",                base["min_score"],             full["min_score"],             lambda v: f"{v}/10")
    row("Max score",                base["max_score"],             full["max_score"],             lambda v: f"{v}/10")
    row("Approval rate",            base["approval_rate"],         full["approval_rate"],         fmt_pct)
    row("Approved normally",        base["approved_normally"],     full["approved_normally"])
    row("Force-approved",           base["force_approved"],        full["force_approved"])
    row("Quality rejections",       base["quality_rejections"],    full["quality_rejections"])
    row("Fact-check rejections",    base["fact_check_rejections"], full["fact_check_rejections"])
    row("Cycles used",              base["cycles_used"],           full["cycles_used"])
    row("Runtime (s)",              base["runtime_seconds"],       full["runtime_seconds"],       lambda v: f"{v}s")

    print(f"{'=' * 65}\n")


if __name__ == "__main__":
    main()
