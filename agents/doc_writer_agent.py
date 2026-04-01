"""
DocWriter Agent — generates Markdown documentation for each code element
by calling Ollama (codellama). Supports revision based on reviewer feedback.
Language-aware: uses the language stored in session memory for prompts.
"""

from agents.base_agent import BaseAgent
from memory.session_memory import DocEntry
from tools.ollama_tools import call_ollama
from config import ABSTRACTION

_LANGUAGE_LABELS = {
    "python": "Python",
    "csharp": "C#",
}

_ABSTRACTION_ANCHORS = (
    f"Abstraction level: {ABSTRACTION}/10. "
    "At level 1, describe every implementation detail and internal behaviour. "
    "At level 5, describe what the code does and how to use it without explaining internals. "
    "At level 10, describe only the purpose and usage in plain language a non-developer could follow."
)

_CODE_FENCES = {
    "python": "python",
    "csharp": "csharp",
}

def _build_system_prompt(language: str) -> str:
    label = _LANGUAGE_LABELS.get(language, language)
    return (
        f"You are a technical documentation writer specialising in {label} code.\n"
        "Your task is to write clear Markdown documentation for a single code element.\n\n"
        "Always include:\n"
        "  - Purpose: what this element does and when to use it\n"
        "  - Parameters: name, type, and what each one controls (omit if none)\n"
        "  - Return value: type and what it represents (omit if void/None)\n"
        "  - Usage example: a minimal, realistic code snippet\n\n"
        f"{_ABSTRACTION_ANCHORS}\n\n"
        "Write in English. Output only the Markdown documentation. "
        "Do not include any preamble, explanation, or closing remarks."
    )


def _build_prompt(entry: DocEntry, language: str, feedback: str = "") -> str:
    fence = _CODE_FENCES.get(language, "")

    revision_section = ""
    if feedback:
        revision_section = (
            "\n\nYour previous attempt was reviewed and returned with this feedback:\n"
            f'"""{feedback}"""\n'
            "Rewrite the documentation to fully address the feedback above."
        )

    return (
        f"Signature: `{entry.signature}`\n\n"
        f"Source code:\n```{fence}\n{entry.source_code}\n```"
        f"{revision_section}"
    )


class DocWriterAgent(BaseAgent):
    def __init__(self, memory):
        super().__init__("DocWriterAgent", memory)

    def write_for(self, entry: DocEntry):
        feedback = entry.review_feedback or ""
        if entry.retry_count > 0:
            self.log(f"Revising docs for '{entry.name}' (attempt {entry.retry_count + 1})")
        else:
            self.log(f"Writing docs for '{entry.name}'")

        language = self.memory.language
        prompt = _build_prompt(entry, language, feedback)
        system = _build_system_prompt(language)
        documentation = call_ollama(prompt, system=system)
        entry.documentation = documentation
        self.log(f"  Done. ({len(documentation)} chars)")

    def run(self):
        for entry in self.memory.doc_entries:
            if not entry.approved:
                self.write_for(entry)
