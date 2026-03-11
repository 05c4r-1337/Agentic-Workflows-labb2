"""
Orchestrator — the central coordinator of the multi-agent documentation workflow.

Flow (full mode):
  1. AnalyzerAgent   → reads file, extracts code elements into memory
  2. PlannerStep     → orchestrator decides what order to document things
  3. DocWriterAgent  → generates documentation for all pending entries
  4. ReviewerAgent   → reviews each entry; rejects go back to DocWriter
  5. FactCheckerAgent→ fact-checks approved entries; failures go back to DocWriter
  6. (loop 3-5 until all approved or max retries hit)
  7. SummaryWriterAgent → generates file summary
  8. OutputAgent     → assembles and writes the final Markdown file

Flow (baseline mode):
  Steps 1-3, then ReviewerAgent in score_only mode (no rejection loop),
  then steps 7-8. Used for performance comparison.
"""

import time
from pathlib import Path
from memory.session_memory import SessionMemory
from agents.analyzer_agent import AnalyzerAgent
from agents.doc_writer_agent import DocWriterAgent
from agents.reviewer_agent import ReviewerAgent
from agents.output_agent import OutputAgent
from agents.summary_agent import SummaryWriterAgent
from agents.fact_checker_agent import FactCheckerAgent
from evaluation import compute_report, save_report, print_report

from config import MAX_RETRIES, MAX_CYCLES

_EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".cs": "csharp",
}


class Orchestrator:
    def __init__(self, target_file: str, output_dir: str = ".", baseline: bool = False):
        self.baseline = baseline
        language = _EXTENSION_TO_LANGUAGE.get(Path(target_file).suffix.lower(), "python")
        stem = Path(target_file).stem
        suffix = "_baseline_docs.md" if baseline else "_docs.md"
        self.memory = SessionMemory(
            target_file=target_file,
            language=language,
            output_path=str(Path(output_dir) / (stem + suffix)),
        )
        self._output_dir = output_dir

    def _plan(self):
        """Orchestrator planning step: log the documentation plan."""
        entries = self.memory.doc_entries
        self.memory.log("Orchestrator", f"Planning documentation for {len(entries)} elements:")
        plan = []
        for entry in entries:
            task = f"Document [{entry.element_type}] {entry.name}"
            plan.append(task)
            self.memory.log("Orchestrator", f"  → {task}")
        self.memory.plan = plan

    def _force_approve_pending(self):
        for e in self.memory.get_pending():
            e.approved = True
            e.force_approved = True

    def run(self):
        mode = "baseline" if self.baseline else "full"
        self.memory.log("Orchestrator", f"=== Documentation Workflow Started (mode: {mode}) ===")
        start_time = time.time()

        # Step 1: Analyze
        analyzer = AnalyzerAgent(self.memory)
        analyzer.run()

        # Step 2: Plan
        self._plan()

        doc_writer = DocWriterAgent(self.memory)
        reviewer = ReviewerAgent(self.memory)
        cycles_used = 0

        if self.baseline:
            # Baseline: single DocWriter pass + score-only review (no rejection loop)
            cycles_used = 1
            self.memory.log("Orchestrator", "--- Baseline: single write pass ---")
            doc_writer.run()
            reviewer.run(score_only=True)
        else:
            # Full: Write → Review → FactCheck loop
            fact_checker = FactCheckerAgent(self.memory)

            iteration = 0
            while iteration < MAX_CYCLES:
                iteration += 1
                cycles_used = iteration
                self.memory.log("Orchestrator", f"--- Write/Review cycle #{iteration}/{MAX_CYCLES} ---")

                doc_writer.run()
                rejected = reviewer.run()
                fact_rejected = fact_checker.run()

                pending = self.memory.get_pending()
                self.memory.log(
                    "Orchestrator",
                    f"Cycle complete. {self.memory.summary()} | {len(rejected)} quality rejections, "
                    f"{len(fact_rejected)} fact-check rejections.",
                )

                if not pending:
                    self.memory.log("Orchestrator", "All elements approved!")
                    break

                if all(e.retry_count >= MAX_RETRIES for e in pending):
                    self.memory.log(
                        "Orchestrator",
                        "Remaining elements hit max retries. Forcing approval.",
                    )
                    for e in pending:
                        e.approved = True
                        e.force_approved = True
                    break
            else:
                self.memory.log(
                    "Orchestrator",
                    f"Reached max cycle limit ({MAX_CYCLES}). Forcing approval of remaining elements.",
                )
                for e in self.memory.get_pending():
                    e.approved = True
                    e.force_approved = True

        # Summary + Output
        summary_writer = SummaryWriterAgent(self.memory)
        summary_writer.run()

        output_agent = OutputAgent(self.memory)
        output_agent.run()

        runtime = time.time() - start_time
        self.memory.log("Orchestrator", "=== Workflow Complete ===")

        # Evaluation report
        report = compute_report(self.memory, mode, cycles_used, runtime)
        stem = Path(self.memory.target_file).stem
        suffix = "_baseline_eval.json" if self.baseline else "_eval.json"
        eval_path = str(Path(self._output_dir) / (stem + suffix))
        save_report(report, eval_path)

        print(f"\nOutput: {self.memory.output_path}")
        print(f"Eval:   {eval_path}")
        print(f"Summary: {self.memory.summary()}")
        print_report(report)
