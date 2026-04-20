"""
Session memory for the multi-agent documentation workflow.
Shared state that all agents read from and write to.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class SessionMemory:
    # Input
    target_file: str = ""
    source_code: str = ""
    language: str = "python"
    output_path: str = ""
    verbose_log_path: Optional[str] = None

    # Documentation state
    file_documentation: Optional[str] = None
    file_approved: bool = False
    file_feedback: Optional[str] = None
    file_review_score: Optional[int] = None
    file_fact_check_issues: Optional[str] = None
    fact_check_retries: int = 0
    file_review_formatted: Optional[str] = None
    # Best-so-far tracking. Fact-clean beats not-clean; within a tier, highest score wins.
    best_documentation: Optional[str] = None
    best_score: int = 0
    best_fact_clean: bool = False
    # Summary
    file_summary: Optional[str] = None

    # Internal
    agent_log: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def log(self, agent: str, message: str):
        entry = f"[{agent}] {message}"
        self.agent_log.append(entry)
        print(entry)
        if self.verbose_log_path:
            with open(self.verbose_log_path, "a", encoding="utf-8") as f:
                f.write(entry + "\n")

    def log_output(self, agent: str, label: str, content: str):
        """Write full agent output content to the verbose log file only (not terminal)."""
        if not self.verbose_log_path:
            return
        separator = "=" * 60
        header = f"{separator}\n[{agent}] {label}\n{separator}\n"
        with open(self.verbose_log_path, "a", encoding="utf-8") as f:
            f.write(header + content + "\n\n")

    def summary(self) -> str:
        status = "approved" if self.file_approved else "pending"
        score = f", score: {self.file_review_score}/10" if self.file_review_score else ""
        retries = f", retries: {self.fact_check_retries}" if self.fact_check_retries else ""
        return f"Documentation {status}{score}{retries}"

    def record_candidate(self, fact_check_clean: bool):
        """Keep the best doc seen so far. Prefer fact-clean; fall back to best by score."""
        if not self.file_documentation:
            return
        score = self.file_review_score or 0
        # Fact-clean always beats not-clean, regardless of score.
        if fact_check_clean and not self.best_fact_clean:
            self.best_documentation = self.file_documentation
            self.best_score = score
            self.best_fact_clean = True
            return
        # Within the same tier, prefer higher score.
        if fact_check_clean == self.best_fact_clean and score > self.best_score:
            self.best_documentation = self.file_documentation
            self.best_score = score