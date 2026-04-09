"""
Evaluation — computes and saves performance metrics for a documentation run.
"""

import json
from dataclasses import dataclass, asdict
from memory.session_memory import SessionMemory


@dataclass
class EvalReport:
    file: str
    mode: str
    approved: bool
    force_approved: bool
    review_score: int
    fact_check_retries: int
    cycles_used: int
    runtime_seconds: float


def compute_report(
    memory: SessionMemory,
    mode: str,
    cycles_used: int,
    runtime_seconds: float,
) -> EvalReport:
    return EvalReport(
        file=memory.target_file,
        mode=mode,
        approved=memory.file_approved,
        force_approved=memory.file_approved and memory.file_review_score is not None and memory.file_review_score < 7,
        review_score=memory.file_review_score or 0,
        fact_check_retries=memory.fact_check_retries,
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
    print(f"  Approved:              {report.approved}")
    print(f"  Force-approved:        {report.force_approved}")
    print(f"  Review score:          {report.review_score}/10")
    print(f"  Fact-check retries:    {report.fact_check_retries}")
    print(f"  Cycles used:           {report.cycles_used}")
    print(f"  Runtime:               {report.runtime_seconds}s")
    print(f"{'=' * w}\n")