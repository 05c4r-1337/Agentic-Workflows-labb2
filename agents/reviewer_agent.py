"""
Reviewer Agent — evaluates the quality of generated documentation.
Scores each DocEntry 1-10 and provides feedback. If score < 7,
the entry is sent back for revision by the DocWriter.
"""

import re
from agents.base_agent import BaseAgent
from memory.session_memory import DocEntry
from tools.ollama_tools import call_ollama
from config import APPROVAL_THRESHOLD, MAX_RETRIES

_LANGUAGE_LABELS = {
    "python": "Python",
    "csharp": "C#",
}

_CODE_FENCES = {
    "python": "python",
    "csharp": "csharp",
}


def _build_system_prompt(language: str) -> str:
    label = _LANGUAGE_LABELS.get(language, language)
    return (
        f"You are a strict technical documentation reviewer.\n"
        f"Evaluate {label} documentation on a scale from 1 to 10.\n"
        "Criteria: clarity, completeness, correct parameter descriptions, return values, example quality.\n"
        "Always respond in this exact format:\n"
        "SCORE: <number>\n"
        "FEEDBACK: <one or two sentences of specific feedback>"
    )


def build_review_prompt(entry: DocEntry, language: str = "python") -> str:
    label = _LANGUAGE_LABELS.get(language, language)
    fence = _CODE_FENCES.get(language, "")
    return f"""Review this documentation for the {label} {entry.element_type} `{entry.name}`.

Original code:
```{fence}
{entry.source_code}
```

Generated documentation:
{entry.documentation}

Evaluate and respond with SCORE and FEEDBACK:"""


def parse_review(response: str) -> tuple[int, str]:
    """Extract score and feedback from Ollama's review response."""
    score_match = re.search(r"SCORE:\s*(\d+)", response, re.IGNORECASE)
    feedback_match = re.search(r"FEEDBACK:\s*(.+)", response, re.IGNORECASE | re.DOTALL)

    score = int(score_match.group(1)) if score_match else 5
    score = max(1, min(10, score))  # clamp to 1-10
    feedback = feedback_match.group(1).strip() if feedback_match else response.strip()
    return score, feedback


class ReviewerAgent(BaseAgent):
    def __init__(self, memory):
        super().__init__("ReviewerAgent", memory)

    def review(self, entry: DocEntry) -> bool:
        """Review a single entry. Returns True if approved."""
        self.log(f"Reviewing '{entry.name}'...")
        language = self.memory.language
        prompt = build_review_prompt(entry, language)
        response = call_ollama(prompt, system=_build_system_prompt(language))

        score, feedback = parse_review(response)
        entry.review_score = score
        entry.review_feedback = feedback

        if score >= APPROVAL_THRESHOLD:
            entry.approved = True
            self.log(f"  APPROVED (score: {score}/10)")
            return True
        else:
            self.log(f"  REJECTED (score: {score}/10) — {feedback}")
            return False

    def run(self) -> list[DocEntry]:
        """Review all pending entries. Returns list of rejected entries."""
        rejected = []
        for entry in self.memory.doc_entries:
            if not entry.approved and entry.documentation:
                approved = self.review(entry)
                if not approved:
                    if entry.retry_count >= MAX_RETRIES:
                        self.log(
                            f"  Max retries ({MAX_RETRIES}) reached for '{entry.name}'. "
                            "Approving with current documentation."
                        )
                        entry.approved = True
                    else:
                        entry.retry_count += 1
                        rejected.append(entry)
        return rejected
