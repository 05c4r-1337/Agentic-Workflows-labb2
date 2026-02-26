"""
Session memory for the multi-agent documentation workflow.
Shared state that all agents read from and write to.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class DocEntry:
    element_type: str          # 'module', 'class', 'function', 'method'
    name: str
    signature: str
    source_code: str
    documentation: Optional[str] = None
    review_score: Optional[int] = None
    review_feedback: Optional[str] = None
    retry_count: int = 0
    approved: bool = False


@dataclass
class SessionMemory:
    target_file: str = ""
    source_code: str = ""
    doc_entries: list[DocEntry] = field(default_factory=list)
    plan: list[str] = field(default_factory=list)
    agent_log: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    output_path: str = ""

    def log(self, agent: str, message: str):
        entry = f"[{agent}] {message}"
        self.agent_log.append(entry)
        print(entry)

    def get_pending(self) -> list[DocEntry]:
        return [e for e in self.doc_entries if not e.approved]

    def get_approved(self) -> list[DocEntry]:
        return [e for e in self.doc_entries if e.approved]

    def summary(self) -> str:
        total = len(self.doc_entries)
        approved = len(self.get_approved())
        return f"{approved}/{total} elements documented and approved"
