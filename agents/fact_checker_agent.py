"""
FactCheckerAgent — verifies generated documentation against actual source code.

Runs inside the write/review loop after ReviewerAgent. If factual errors are
found, the entry is de-approved and sent back to DocWriterAgent for a rewrite,
with the issues stored in review_feedback so the writer can address them.
"""

from agents.base_agent import BaseAgent
from tools.ollama_tools import call_ollama
from config import FACT_CHECKER_MODEL, FACT_CHECKER_TEMPERATURE, MAX_RETRIES

_LANGUAGE_LABELS = {"python": "Python", "csharp": "C#"}
_CODE_FENCES = {"python": "python", "csharp": "csharp"}

SYSTEM_PROMPT = (
    "You are a code documentation fact-checker. "
    "You will be given source code and documentation written about it. "
    "Your job is to find claims in the documentation that are contradicted by or absent from the source code.\n\n"
    "Flag any of the following:\n"
    "  - Parameter names or types that differ from the source code\n"
    "  - Methods, properties, or classes referenced in the documentation that do not exist in the source\n"
    "  - Return types or field names that contradict what the code actually returns\n"
    "  - Described behaviour that the source code clearly does not implement\n"
    "  - Sorting or ordering logic that contradicts the actual implementation\n"
    "  - Algorithmic details (calculations, conditions, thresholds) that differ from the source\n"
    "  - Terminology swaps that change the meaning (e.g. 'relevance score' vs 'distance')\n\n"
    "Be thorough — read every descriptive claim and verify it against the source code line by line.\n"
    "RESPOND IN THIS EXACT FORMAT!!!:\n"
    "ISSUES: <bullet list of false or unsupported claims> or <No issues found>"
)


def _build_prompt(source_code: str, documentation: str, language: str) -> str:
    fence = _CODE_FENCES.get(language, "")
    return (
        f"Fact-check this {language} documentation against the actual source code.\n\n"
        f"Source code:\n```{fence}\n{source_code}\n```\n\n"
        f"Documentation to check:\n{documentation}\n\n"
    )


def _parse_issues(response: str) -> str:
    """Returns the issues string, or 'None' if no problems found."""
    if "no issues found" in response.lower():
        return "none"
    if "ISSUES:" in response:
        parts = response.split("ISSUES:", 1)[1]
        issues = parts.split("CORRECTED:")[0].strip() if "CORRECTED:" in parts else parts.strip()
        return issues
    return "None"


class FactCheckerAgent(BaseAgent):
    def __init__(self, memory):
        super().__init__("FactCheckerAgent", memory)
    def run(self) -> bool:
        if not self.memory.file_documentation:
            return False
        if getattr(self.memory, 'fact_check_retries', 0) >= MAX_RETRIES:
            self.log("Fact-check retry limit reached, skipping.")
            return False

        self.log("Fact-checking full file documentation...")
        prompt = _build_prompt(self.memory.source_code, self.memory.file_documentation, self.memory.language)
        response = call_ollama(prompt, system=SYSTEM_PROMPT, model=FACT_CHECKER_MODEL,
                               options={"num_predict": 2048, "num_ctx": 16384,
                                        "temperature": FACT_CHECKER_TEMPERATURE})
        issues = _parse_issues(response)
        self.log_output("Fact-check response", response)
        if issues.lower() == "none":
            self.log("No issues found.")
            self.memory.file_fact_check_issues = "None"
            return False

        self.memory.file_fact_check_issues = issues
        self.memory.fact_check_retries = getattr(self.memory, 'fact_check_retries', 0) + 1
        self.memory.file_approved = False
        existing = self.memory.file_review_formatted or ""
        self.memory.file_review_formatted = f"{existing}\nFact-check issues:\n{issues}".strip()
        self.log(f"Issues found, sent back for rewrite: {issues[:120]}...")
        return True