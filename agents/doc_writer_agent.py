"""
DocWriter Agent — generates Markdown documentation for each code element
by calling Ollama (codellama). Supports revision based on reviewer feedback.
Language-aware: uses the language stored in session memory for prompts.
"""

from agents.base_agent import BaseAgent
from memory.session_memory import DocEntry
from tools.ollama_tools import call_ollama
from config import ABSTRACTION, DOC_WRITER_MODEL, DOC_WRITER_TEMPERATURE

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
    fence = _CODE_FENCES.get(language, language)
    return (
        f"You are a technical documentation writer specialising in {label} code.\n"
        "Your task is to write clear Markdown documentation for a single code element.\n\n"
        "OUTPUT RULES — follow these exactly:\n"
        "  1. Output raw Markdown only. Do NOT wrap your output in a ```markdown fence or any other code fence.\n"
        "  2. Do NOT start with a heading. The heading is added automatically — begin directly with the content.\n"
        "  3. Use a Markdown pipe table for parameters (columns: Parameter, Type, Description). Omit if none.\n"
        "  4. Use a Markdown pipe table for return value (columns: Type, Description). Omit if void/None.\n"
        "  5. Include a minimal, realistic code example in a " + f"```{fence}``` " + "block only when it meaningfully illustrates usage. Skip it for trivial getters or constructors.\n"
        "  6. No preamble, no closing remarks, no meta-commentary about the documentation.\n\n"
        "CONTENT — include in this order (omit sections that don't apply):\n"
        "  - One concise paragraph describing the purpose and when to use this element.\n"
        "  - A 'Parameters' section with a pipe table (columns: Parameter, Type, Description). Include what each parameter controls, not just its type.\n"
        "  - A 'Return value' section with a pipe table (columns: Field, Type, Description). If the return type is a complex object, document its fields too.\n"
        "  - If the element has internal constants, templates, or configuration that meaningfully affect its public behaviour, describe that behaviour in a dedicated section.\n"
        "  - An 'Example' section with a code block (when genuinely useful — skip for trivial getters or constructors).\n\n"
        f"{_ABSTRACTION_ANCHORS}\n\n"
        "Write in English."
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
        documentation = call_ollama(prompt, system=system, model=DOC_WRITER_MODEL,
                                    options={"temperature": DOC_WRITER_TEMPERATURE})
        entry.documentation = documentation
        self.log(f"  Done. ({len(documentation)} chars)")

    def run(self):
        for entry in self.memory.doc_entries:
            if not entry.approved:
                self.write_for(entry)
