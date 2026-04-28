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
from datetime import datetime
from pathlib import Path
from memory.session_memory import SessionMemory
from agents.doc_writer_agent import DocWriterAgent
from agents.reviewer_agent import ReviewerAgent
from agents.output_agent import OutputAgent
from agents.fact_checker_agent import FactCheckerAgent
from evaluation import compute_report, save_report, print_report
from tools.code_tools import read_file
from config import MAX_RETRIES, MAX_CYCLES

_EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".cs": "csharp",
}


class Orchestrator:
    def __init__(self, target_file: str, output_dir: str = ".", baseline: bool = False, verbose: bool = False):
        self.baseline = baseline
        language = _EXTENSION_TO_LANGUAGE.get(Path(target_file).suffix.lower(), "python")
        stem = Path(target_file).stem
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_baseline_docs_{ts}.md" if baseline else f"_docs_{ts}.md"
        verbose_log_path = None
        if verbose:
            logs_dir = Path("logs")
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_suffix = f"_baseline_verbose_{ts}.txt" if baseline else f"_verbose_{ts}.txt"
            verbose_log_path = str(logs_dir / (stem + log_suffix))
        self.memory = SessionMemory(
            target_file=target_file,
            language=language,
            output_path=str(Path(output_dir) / (stem + suffix)),
            verbose_log_path=verbose_log_path,
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

    # Step 1: just read the file
        self.memory.source_code = read_file(self.memory.target_file)
        self.memory.log("Orchestrator", f"Read file: {self.memory.target_file}")

        doc_writer = DocWriterAgent(self.memory)
        reviewer = ReviewerAgent(self.memory)
        cycles_used = 0

        if self.baseline:
            cycles_used = 1
            doc_writer.run()
            reviewer.run(score_only=True)
        else:
            fact_checker = FactCheckerAgent(self.memory)
            for iteration in range(1, MAX_CYCLES + 1):
                cycles_used = iteration
                self.memory.log("Orchestrator", f"--- Cycle #{iteration}/{MAX_CYCLES} ---")

                doc_writer.run()
                approved = reviewer.run()
                fact_rejected = fact_checker.run()
                self.memory.record_candidate(fact_check_clean=not fact_rejected)

                if approved and not fact_rejected:
                    self.memory.log("Orchestrator", "Documentation approved!")
                    break

                retries = getattr(self.memory, 'fact_check_retries', 0)
                if retries >= MAX_RETRIES:
                    self.memory.log("Orchestrator", "Max retries hit, keeping current documentation.")
                    self.memory.file_approved = True
                    break
            else:
                self.memory.log("Orchestrator", "Max cycles reached, forcing approval.")
                self.memory.file_approved = True

        #  Output

        output_agent = OutputAgent(self.memory)
        output_agent.run()

        runtime = time.time() - start_time
        self.memory.log("Orchestrator", "=== Workflow Complete ===")

        # Evaluation report
        report = compute_report(self.memory, mode, cycles_used, runtime)
        stem = Path(self.memory.target_file).stem
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_baseline_eval_{ts}.json" if self.baseline else f"_eval_{ts}.json"
        eval_path = str(Path(self._output_dir) / (stem + suffix))
        save_report(report, eval_path)

        print(f"\nOutput: {self.memory.output_path}")
        print(f"Eval:   {eval_path}")
        if self.memory.verbose_log_path:
            print(f"Log:    {self.memory.verbose_log_path}")
        print(f"Summary: {self.memory.summary()}")
        print_report(report)
        return report
