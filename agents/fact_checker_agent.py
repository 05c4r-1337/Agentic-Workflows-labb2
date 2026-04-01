"""
FactCheckerAgent — verifies generated documentation against actual source code.

Runs inside the write/review loop after ReviewerAgent. If factual errors are
found, the entry is de-approved and sent back to DocWriterAgent for a rewrite,
with the issues stored in review_feedback so the writer can address them.
"""

from agents.base_agent import BaseAgent
from memory.session_memory import DocEntry
from tools.ollama_tools import call_ollama
from config import FACT_CHECKER_MODEL

_LANGUAGE_LABELS = {"python": "Python", "csharp": "C#"}
_CODE_FENCES = {"python": "python", "csharp": "csharp"}

SYSTEM_PROMPT = (
    "You are a strict code documentation fact-checker. "
    "You will be given source code and a documentation string written about it. "
    "Only flag issues you are completely certain about by reading the source code literally. "
    "Do NOT flag style issues, missing detail, vague descriptions, or anything you are unsure about. "
    "Only flag: parameter names that are definitively wrong, methods or classes that do not exist "
    "in the source code, or return types that are explicitly contradicted by the code. "
    "When in doubt, respond with ISSUES: None.\n"
    "RESPOND IN THIS EXACT FORMAT:\n"
    "ISSUES: <bullet list of definite false claims, or 'None'>"
)


def _build_prompt(entry: DocEntry, language: str) -> str:
    label = _LANGUAGE_LABELS.get(language, language)
    fence = _CODE_FENCES.get(language, "")
    return (
        f"Fact-check this {label} documentation against the actual source code.\n\n"
        f"Source code:\n```{fence}\n{entry.source_code}\n```\n\n"
        f"Documentation to check:\n{entry.documentation}\n\n"
    )


def _parse_issues(response: str) -> str:
    """Returns the issues string, or 'None' if no problems found."""
    if "ISSUES:" in response:
        parts = response.split("ISSUES:", 1)[1]
        issues = parts.split("CORRECTED:")[0].strip() if "CORRECTED:" in parts else parts.strip()
        return issues
    return "None"


class FactCheckerAgent(BaseAgent):
    def __init__(self, memory):
        super().__init__("FactCheckerAgent", memory)

    def check(self, entry: DocEntry) -> bool:
        """Check a single entry. Returns True if issues were found (entry sent back for rewrite)."""
        if entry.fact_check_retries >= 5:
            self.log(f"  Skipping '{entry.name}' (fact-check retry limit reached).")
            return False

        self.log(f"Checking '{entry.name}'...")
        language = self.memory.language
        prompt = _build_prompt(entry, language)
        response = call_ollama(prompt, system=SYSTEM_PROMPT, model=FACT_CHECKER_MODEL,
                               options={"num_predict": 2048, "num_ctx": 2048})

        issues = _parse_issues(response)

        if issues.lower() == "none":
            self.log(f"  No issues found.")
            entry.fact_check_issues = "None"
            return False

        entry.fact_check_issues = issues
        entry.fact_check_retries += 1
        entry.approved = False
        entry.documentation = None
        entry.review_feedback = f"Fact-check issues: {issues}"
        entry.retry_count += 1
        self.log(f"  Issues found, sent back for rewrite: {issues[:120]}...")
        return True

    def run(self) -> list[DocEntry]:
        """Fact-check all approved entries that haven't been checked yet. Returns list of entries sent back for rewrite."""
        approved = self.memory.get_approved()
        pending = [e for e in approved if e.fact_check_issues != "None" and e.documentation]
        self.log(f"Fact-checking {len(pending)} approved entries...")
        rejected = []
        for entry in pending:
            if self.check(entry):
                rejected.append(entry)
        return rejected
