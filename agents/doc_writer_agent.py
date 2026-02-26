"""
DocWriter Agent — generates Markdown documentation for each code element
by calling Ollama (codellama). Supports revision based on reviewer feedback.
"""

from agents.base_agent import BaseAgent
from memory.session_memory import DocEntry
from tools.ollama_tools import call_ollama

SYSTEM_PROMPT = """You are a technical documentation writer specializing in Python code.
Your task is to write clear, concise Markdown documentation for the given code element.
Always include: purpose, parameters (if any), return value (if any), and a usage example.
Write in English. Output only the documentation, no preamble."""


def build_prompt(entry: DocEntry, feedback: str = "") -> str:
    revision_note = ""
    if feedback:
        revision_note = f"""
A reviewer rated your previous documentation and gave this feedback:
\"\"\"{feedback}\"\"\"
Please revise the documentation to address the feedback.
"""

    return f"""Write Markdown documentation for the following Python {entry.element_type}.

Signature: `{entry.signature}`

Source code:
```python
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

        prompt = build_prompt(entry, feedback)
        documentation = call_ollama(prompt, system=SYSTEM_PROMPT)
        entry.documentation = documentation
        self.log(f"  Done. ({len(documentation)} chars)")

    def run(self):
        for entry in self.memory.doc_entries:
            if not entry.approved:
                self.write_for(entry)
