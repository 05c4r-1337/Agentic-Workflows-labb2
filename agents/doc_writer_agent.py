"""
DocWriter Agent — generates Markdown documentation for each code element
by calling Ollama (codellama). Supports revision based on reviewer feedback.
Language-aware: uses the language stored in session memory for prompts.
"""

from agents.base_agent import BaseAgent
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
        "Your task is to write clear Markdown documentation for the entire source file provided.\n\n"
        "OUTPUT RULES — follow these exactly:\n"
        "  1. Output raw Markdown only. Do NOT wrap your output in a ```markdown fence.\n"
        "  2. Document each class, method, and interface you find in the source.\n"
        "  3. Use a Markdown pipe table for parameters (columns: Parameter, Type, Description).\n"
        "  4. Use a Markdown pipe table for return value (columns: Type, Description).\n"
        "  5. Include code examples in " + f"```{fence}``` " + "blocks where useful.\n"
        "  6. No preamble, no closing remarks, no meta-commentary.\n\n"
        f"{_ABSTRACTION_ANCHORS}\n\n"
        "Write in English"
    )


def _build_prompt(source_code: str, language: str, feedback: str = "", existing_doc: str = "") -> str:
    fence = _CODE_FENCES.get(language, "")

    revision_section = ""
    if feedback:
        revision_section = (
            f"\n\nYour previous documentation was reviewed. This was the document"
            f'"""{existing_doc}"""\n\n'
            "Specific issues to fix:\n"
            f'"""{feedback}"""\n\n'
            "Rewrite the MARKDOWN DOCUMENTATION for the C# source file above to fix only these issues. "
            "DO NOT CHANGE ANYTHING THAT ISNT STATED IN THE FEEDBACK. Do not write code, analysis, or commentary."
        )

    return (
        f"Source code:\n```{fence}\n{source_code}\n```"
        f"{revision_section}"
    )


class DocWriterAgent(BaseAgent):
    def __init__(self, memory):
        super().__init__("DocWriterAgent", memory)

    def run(self):
        feedback = self.memory.file_review_formatted or ""
        language = self.memory.language
        if feedback:
            self.log("Rewriting documentation with feedback:")
        else:
            self.log("Writing documentation")        
        prompt = _build_prompt(self.memory.source_code, language, feedback, self.memory.file_documentation)
        system = _build_system_prompt(language)
        documentation = call_ollama(
            prompt, system=system,
            model=DOC_WRITER_MODEL,
            options={"temperature": DOC_WRITER_TEMPERATURE}
        )
        self.memory.file_documentation = documentation
        self.log(f"Done. ({len(documentation)} chars)")
        self.log_output("Generated documentation", documentation)