"""
Evaluation — computes and saves performance metrics for a documentation run.
"""

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from memory.session_memory import SessionMemory


@dataclass
class EvalReport:
    file: str
    mode: str                   # "full" or "baseline"
    total_elements: int
    approved_normally: int
    force_approved: int
    approval_rate: float        # 0.0 – 1.0
    avg_score: float
    min_score: int
    max_score: int
    quality_rejections: int
    fact_check_rejections: int
    cycles_used: int
    runtime_seconds: float


def compute_report(
    memory: SessionMemory,
    mode: str,
    cycles_used: int,
    runtime_seconds: float,
) -> EvalReport:
    entries = memory.doc_entries
    scores = [e.review_score for e in entries if e.review_score is not None]
    total = len(entries)

    quality_rejections = sum(
        e.retry_count - e.fact_check_retries for e in entries
    )

    return EvalReport(
        file=memory.target_file,
        mode=mode,
        total_elements=total,
        approved_normally=sum(1 for e in entries if e.approved and not e.force_approved),
        force_approved=sum(1 for e in entries if e.force_approved),
        approval_rate=round(sum(1 for e in entries if e.approved) / total, 2) if total else 0.0,
        avg_score=round(sum(scores) / len(scores), 1) if scores else 0.0,
        min_score=min(scores) if scores else 0,
        max_score=max(scores) if scores else 0,
        quality_rejections=max(quality_rejections, 0),
        fact_check_rejections=sum(e.fact_check_retries for e in entries),
        cycles_used=cycles_used,
        runtime_seconds=round(runtime_seconds, 1),
    )


def save_report(report: EvalReport, output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(asdict(report), f, indent=2)


def print_report(report: EvalReport) -> None:
    w = 50
    print(f"\n{'=' * w}")
    print(f"  Evaluation Report — {report.mode.upper()} mode")
    print(f"{'=' * w}")
    print(f"  File:                  {report.file}")
    print(f"  Total elements:        {report.total_elements}")
    print(f"  Approved normally:     {report.approved_normally}/{report.total_elements} ({report.approval_rate:.0%})")
    print(f"  Force-approved:        {report.force_approved}")
    print(f"  Avg review score:      {report.avg_score}/10")
    print(f"  Min / Max score:       {report.min_score} / {report.max_score}")
    print(f"  Quality rejections:    {report.quality_rejections}")
    print(f"  Fact-check rejections: {report.fact_check_rejections}")
    print(f"  Cycles used:           {report.cycles_used}")
    print(f"  Runtime:               {report.runtime_seconds}s")
    print(f"{'=' * w}\n")
