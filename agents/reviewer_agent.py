"""
Reviewer Agent — evaluates the quality of generated documentation.
Scores each DocEntry 1-10 and provides feedback. If score < 7,
the entry is sent back for revision by the DocWriter.
"""

import re
from agents.base_agent import BaseAgent
from agents.format_agent import FormattingAgent
from tools.ollama_tools import call_ollama
from config import APPROVAL_THRESHOLD, REVIEWER_MODEL, REVIEWER_TEMPERATURE

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
        "Your job is to evaluate documentation clarity and completeness — NEVER FACTUAL CORRECTNESS.\n"
        "Assume all technical details in the documentation are accurate.\n\n"

        "STEP 1 — CHECKLIST\n"
        "Go through each item below. Mark it PASS, FAIL, or N/A.\n"
        "N/A is only valid if the code structurally cannot have that item "
        "(e.g. a void method cannot have [C]; a method with no parameters cannot have [B]). "
        "Marking N/A because the documentation simply omits the item is a FAIL, not N/A.\n\n"
        "  [A] Purpose: FAIL if there is no clear statement of what the method or class does.\n"
        "  [B] Parameters: FAIL if any parameter has no explanation, or is described only by its type or name with no behavioural meaning.\n"
        "  [C] Return value: FAIL if a complex return type lists no fields, or a simple return type has no description of what it represents.\n"
        "  [D] Edge cases / exceptions: FAIL if notable failure modes or boundary conditions exist in the code but are not mentioned.\n"
        "  [E] Constants / templates: FAIL if internal constants or prompt templates that affect public behaviour are not documented.\n"
        "  [F] Default values: FAIL if default or fallback values for configuration exist in the code but are not documented.\n"
        "  [G] Scoring / calculation logic: FAIL if output depends on a formula or algorithm that is not explained.\n"
        "  [H] System-prompt persona: FAIL if a system prompt is used but its behavioural constraints are not described.\n\n"

        "STEP 2 — ANALYSIS\n"
        "For every FAIL, write one sentence using this pattern:\n"
        "  [Item X] — <what is absent> is not documented; a reader cannot determine <what they cannot do as a result>.\n"
        "If there are no FAILs, write: No issues found.\n"
        "Do not comment on factual correctness, code style, or formatting.\n\n"
    )


def _build_review_prompt(source_code: str, documentation: str, language: str) -> str:
    fence = _CODE_FENCES.get(language, "")
    return (
        f"Review the documentation for this entire {language} file.\n\n"
        f"Source code:\n```{fence}\n{source_code}\n```\n\n"
        f"Generated documentation:\n{documentation}"
    )

class ReviewerAgent(BaseAgent):
    def __init__(self, memory):
        super().__init__("ReviewerAgent", memory)

    def run(self, score_only: bool = False) -> bool:
        doc = self.memory.file_documentation
        if not doc:
            return False

        self.log("Reviewing full file documentation...")
        prompt = _build_review_prompt(self.memory.source_code, doc, self.memory.language)
        response = call_ollama(
            prompt,
            system=_build_system_prompt(self.memory.language),
            model=REVIEWER_MODEL,
            options={"temperature": REVIEWER_TEMPERATURE}
        )
        self.memory.file_feedback = response
        FormattingAgent(self.memory).run()
        score = self.memory.file_review_score
        self.memory.file_approved = score_only or score >= APPROVAL_THRESHOLD

        self.log(f"  {'APPROVED' if self.memory.file_approved else 'REJECTED'} (score: {score}/10)")
        return self.memory.file_approved