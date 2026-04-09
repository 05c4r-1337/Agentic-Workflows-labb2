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

    # Documentation state
    file_documentation: Optional[str] = None
    file_approved: bool = False
    file_feedback: Optional[str] = None
    file_review_score: Optional[int] = None
    file_fact_check_issues: Optional[str] = None
    fact_check_retries: int = 0

    # Summary
    file_summary: Optional[str] = None

    # Internal
    agent_log: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def log(self, agent: str, message: str):
        entry = f"[{agent}] {message}"
        self.agent_log.append(entry)
        print(entry)

    def summary(self) -> str:
        status = "approved" if self.file_approved else "pending"
        score = f", score: {self.file_review_score}/10" if self.file_review_score else ""
        retries = f", retries: {self.fact_check_retries}" if self.fact_check_retries else ""
        return f"Documentation {status}{score}{retries}"

    def reset_for_retry(self):
        """Clear documentation state before a rewrite cycle."""
        self.file_documentation = None
        self.file_approved = False
        self.file_review_score = None