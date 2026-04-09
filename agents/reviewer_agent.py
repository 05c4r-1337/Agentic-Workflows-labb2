"""
Reviewer Agent — evaluates the quality of generated documentation.
Scores each DocEntry 1-10 and provides feedback. If score < 7,
the entry is sent back for revision by the DocWriter.
"""

import re
from agents.base_agent import BaseAgent
from tools.ollama_tools import call_ollama
from config import APPROVAL_THRESHOLD, MAX_RETRIES, REVIEWER_MODEL, REVIEWER_TEMPERATURE

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
        "Assume all technical details in the documentation are accurate.\n\n"
        "Score the documentation from 1 to 10 using these anchors:\n"
        "  9-10 — Exceptionally clear and complete. Purpose, parameters, return value, and behaviour are all described in a way any developer could understand without reading the source.\n"
        "  7-8  — Mostly clear with minor gaps (e.g. a parameter's purpose is vague, or an important edge case is unmentioned).\n"
        "  5-6  — Partially useful but a reader would still need to read the source code to understand how to use it.\n"
        "  3-4  — Hard to follow or missing critical sections such as parameters or return value entirely.\n"
        "  1-2  — Essentially useless: empty, incomprehensible, or a single throwaway sentence.\n\n"
        "When reviewing, do a regular check, and then check for these common omissions and penalise if missing:\n"
        "  - Internal constants or templates that affect public behaviour (e.g. system prompts, prompt templates)\n"
        "  - Default values for configuration (e.g. fallback model names, default thresholds)\n"
        "  - Return type fields: if a method returns a complex object, its fields should be documented\n"
        "  - Scoring or calculation logic that affects output (e.g. how relevance scores are computed)\n"
        "  - The persona or behavioural constraints imposed by any system prompts\n\n"
        "When writing feedback, name the exact section or parameter that needs improving and explain why. "
        "Do not comment on factual correctness, code style, or formatting.\n\n"
        "Respond in this exact format:\n"
        "SCORE: <number 1-10>\n"
        "FEEDBACK: <specific feedback on clarity and completeness, or 'None' if score is 9 or above>"
    )

def build_review_prompt(source_code: str, documentation: str, language: str) -> str:
    fence = _CODE_FENCES.get(language, "")
    return (
        f"Review the documentation for this entire {language} file.\n\n"
        f"Source code:\n```{fence}\n{source_code}\n```\n\n"
        f"Generated documentation:\n{documentation}"
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
    def run(self, score_only: bool = False) -> bool:
        doc = self.memory.file_documentation
        if not doc:
            return False

        self.log("Reviewing full file documentation...")
        prompt = build_review_prompt(self.memory.source_code, doc, self.memory.language)
        response = call_ollama(prompt, system=_build_system_prompt(self.memory.language),
                               model=REVIEWER_MODEL, options={"temperature": REVIEWER_TEMPERATURE})

        score, feedback = parse_review(response)
        self.memory.file_review_score = score
        self.memory.file_feedback = feedback
        self.memory.file_approved = score_only or score >= APPROVAL_THRESHOLD

        self.log(f"  {'APPROVED' if self.memory.file_approved else 'REJECTED'} (score: {score}/10)")
        return self.memory.file_approved
