"""
Formatting Agent — distills the reviewer's raw response into a compact,
structured summary.

Output format:
    Issues: None          (if no issues were found)
    Issues:               (if issues exist)
    - <issue 1>
    - <issue 2>
    Score: <1-10>
"""

import re
from agents.base_agent import BaseAgent
from tools.ollama_tools import call_ollama
from config import FORMATTER_MODEL, FORMATTER_TEMPERATURE

_SYSTEM_PROMPT = (
    "You are a documentation review formatter.\n"
    "You will receive a raw documentation review. Your only job is to reformat and score it.\n\n"

    "SCORE\n"
    "Count your FAIL results (ignore N/A). Critical items are A, B, C. All others are minor.\n"
    "  0 FAIL  → 9 (or 10 if the documentation includes a concrete usage example)\n"
    "  1 FAIL  → 7 if the failed item is critical; 8 if minor\n"
    "  2 FAIL  → 5 if any critical item failed; 6 if both are minor\n"
    "  3 FAIL  → 4\n"
    "  4+ FAIL → 1\n\n"


    "OUTPUT RULES — follow them exactly, no deviation:\n"
    "1. If there are issues, output:\n"
    "   Issues:\n"
    "   - <concise description of issue 1>\n"
    "   - <concise description of issue 2>\n"
    "   (one bullet per issue, keep each under 15 words)\n\n"
    "2. If there are no issues, output:\n"
    "   Issues: None\n\n"
    "3. You MUST end your entire response with this exact line and nothing after it:\n"
    "FINAL SCORE: <integer 1-10>"
    "Do not output anything else — no preamble, no explanation, no extra lines."
)


def _build_format_prompt(raw_review: str) -> str:
    return (
        "Reformat the following review into the required output format.\n\n"
        f"Raw review:\n{raw_review}"
    )


def _parse_formatted(response: str) -> tuple[list[str], int]:
    """Extract issues list and score from the formatted response."""
    issues: list[str] = []

    issues_none = re.search(r"Issues:\s*None", response, re.IGNORECASE)
    if not issues_none:
        issues = re.findall(r"^\s*[-•]\s*(.+)", response, re.MULTILINE)

    score_match = re.search(r"Score:\s*(\d+)", response, re.IGNORECASE)
    score = int(score_match.group(1)) if score_match else 0
    score = max(1, min(10, score))

    return issues, score


class FormattingAgent(BaseAgent):
    def __init__(self, memory):
        super().__init__("FormattingAgent", memory)

    def run(self) -> str | None:
        raw_review = self.memory.file_feedback
        if not raw_review:
            self.log("No review found in memory, skipping.")
            return None

        self.log("Formatting review output...")
        prompt = _build_format_prompt(raw_review)
        response = call_ollama(
            prompt,
            system=_SYSTEM_PROMPT,
            model=FORMATTER_MODEL,
            options={"temperature": FORMATTER_TEMPERATURE}
        )

        issues, score = _parse_formatted(response)
        self.memory.file_review_formatted = response.strip()
        self.memory.file_review_score = score  # <-- write score to memory

        if issues:
            self.log(f"  {len(issues)} issue(s) found — Score: {score}/10")
        else:
            self.log(f"  No issues — Score: {score}/10")

        return self.memory.file_review_formatted