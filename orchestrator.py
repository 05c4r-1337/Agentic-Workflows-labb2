"""
Orchestrator — the central coordinator of the multi-agent documentation workflow.

Flow:
  1. AnalyzerAgent   → reads file, extracts code elements into memory
  2. PlannerStep     → orchestrator decides what order to document things
  3. DocWriterAgent  → generates documentation for all pending entries
  4. ReviewerAgent   → reviews each entry; rejects go back to DocWriter
  5. (loop 3-4 until all approved or max retries hit)
  6. OutputAgent     → assembles and writes the final Markdown file
"""

from pathlib import Path
from memory.session_memory import SessionMemory
from agents.analyzer_agent import AnalyzerAgent
from agents.doc_writer_agent import DocWriterAgent
from agents.reviewer_agent import ReviewerAgent
from agents.output_agent import OutputAgent

MAX_CYCLES = 10


class Orchestrator:
    def __init__(self, target_file: str, output_dir: str = "."):
        self.memory = SessionMemory(
            target_file=target_file,
            output_path=str(
                Path(output_dir) / (Path(target_file).stem + "_docs.md")
            ),
        )

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

    def run(self):
        self.memory.log("Orchestrator", "=== Documentation Workflow Started ===")

        # Step 1: Analyze
        analyzer = AnalyzerAgent(self.memory)
        analyzer.run()

        # Step 2: Plan
        self._plan()

        # Steps 3-4: Write → Review loop
        doc_writer = DocWriterAgent(self.memory)
        reviewer = ReviewerAgent(self.memory)

        iteration = 0
        while iteration < MAX_CYCLES:
            iteration += 1
            self.memory.log("Orchestrator", f"--- Write/Review cycle #{iteration}/{MAX_CYCLES} ---")

            doc_writer.run()
            rejected = reviewer.run()

            pending = self.memory.get_pending()
            self.memory.log(
                "Orchestrator",
                f"Cycle complete. {self.memory.summary()} | {len(rejected)} sent for revision.",
            )

            if not pending:
                self.memory.log("Orchestrator", "All elements approved!")
                break

            if all(e.retry_count >= 3 for e in pending):
                self.memory.log(
                    "Orchestrator",
                    "Remaining elements hit max retries. Forcing approval.",
                )
                for e in pending:
                    e.approved = True
                break
        else:
            self.memory.log(
                "Orchestrator",
                f"Reached max cycle limit ({MAX_CYCLES}). Forcing approval of remaining elements.",
            )
            for e in self.memory.get_pending():
                e.approved = True

        # Step 5: Output
        output_agent = OutputAgent(self.memory)
        output_agent.run()

        self.memory.log("Orchestrator", "=== Workflow Complete ===")
        print(f"\nOutput: {self.memory.output_path}")
        print(f"Summary: {self.memory.summary()}")
