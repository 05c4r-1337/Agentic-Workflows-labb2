"""
Reviewer Agent — evaluates the quality of generated documentation.
Scores each DocEntry 1-10 and provides feedback. If score < 7,
the entry is sent back for revision by the DocWriter.
"""

import re
from agents.base_agent import BaseAgent
from memory.session_memory import DocEntry
from tools.ollama_tools import call_ollama
from config import APPROVAL_THRESHOLD, MAX_RETRIES, REVIEWER_MODEL

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
        f"You are a technical documentation quality reviewer for {label} code.\n"
        "Your job is to evaluate how well the documentation is written — not whether its facts are correct.\n"
        "Assume all technical details in the documentation are accurate. Do not verify them against the source code.\n\n"
        "Score the documentation from 1 to 10 using these anchors:\n"
        "  9-10 — Exceptionally clear and complete. Purpose, parameters, return value, and behaviour are all described in a way any developer could understand without reading the source.\n"
        "  7-8  — Mostly clear with minor gaps (e.g. a parameter's purpose is vague, or an important edge case is unmentioned).\n"
        "  5-6  — Partially useful but a reader would still need to read the source code to understand how to use it.\n"
        "  3-4  — Hard to follow or missing critical sections such as parameters or return value entirely.\n"
        "  1-2  — Essentially useless: empty, incomprehensible, or a single throwaway sentence.\n\n"
        "When writing feedback, name the exact section or parameter description that needs improving and explain why it is unclear or incomplete. "
        "Do not comment on factual correctness, code style, or formatting.\n\n"
        "Respond in this exact format:\n"
        "SCORE: <number 1-10>\n"
        "FEEDBACK: <specific feedback on clarity and completeness, or 'None' if score is 9 or above>"
    )

def build_review_prompt(entry: DocEntry, language: str = "python") -> str:
    label = _LANGUAGE_LABELS.get(language, language)
    fence = _CODE_FENCES.get(language, "")
    return (
        f"Review the documentation for this {label} {entry.element_type} `{entry.name}`.\n\n"
        f"Source code:\n```{fence}\n{entry.source_code}\n```\n\n"
        f"Generated documentation:\n{entry.documentation}"
    )


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
        response = call_ollama(prompt, system=_build_system_prompt(language), model=REVIEWER_MODEL)

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

    def run(self, score_only: bool = False) -> list[DocEntry]:
        """Review all pending entries. Returns list of rejected entries.

        score_only: if True, record scores but approve all entries regardless
        of score (used in baseline mode).
        """
        rejected = []
        for entry in self.memory.doc_entries:
            if not entry.approved and entry.documentation:
                approved = self.review(entry)
                if score_only:
                    entry.approved = True
                elif not approved:
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
