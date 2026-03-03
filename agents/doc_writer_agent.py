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

_CODE_FENCES = {
    "python": "python",
    "csharp": "csharp",
}


def _build_system_prompt(language: str) -> str:
    label = _LANGUAGE_LABELS.get(language, language)
    return (
        f"You are a technical documentation writer specializing in {label} code.\n"
        "Your task is to write clear, concise Markdown documentation for the given code element.\n"
        "Always include: purpose, parameters (if any), return value (if any), and a usage example.\n"
        "Write in English. Output only the documentation, no preamble. The abstraction level should be {ABSTRACTION}/10 with 10 being the highest abstraction"
    )


def _build_prompt(entry: DocEntry, language: str, feedback: str = "") -> str:
    label = _LANGUAGE_LABELS.get(language, language)
    fence = _CODE_FENCES.get(language, "")

    revision_note = ""
    if feedback:
        revision_note = f"""
A reviewer rated your previous documentation and gave this feedback:
\"\"\"{feedback}\"\"\"
Please revise the documentation to address the feedback.
"""

    return f"""Write Markdown documentation for the following {label} {entry.element_type}.

Signature: `{entry.signature}`

Source code:
```{fence}
{entry.source_code}
```
{revision_note}
Documentation:"""


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
