"""
Summarywriter Agent — generates a summary for the document.
"""

from agents.base_agent import BaseAgent
from memory.session_memory import DocEntry
from tools.ollama_tools import call_ollama

SUMMARY_SYSTEM_PROMPT = """You are a technical documentation writer.
Your task is to write a short, high-level summary of a Python file based on its documented elements.
Write 2-4 sentences in English. Output only the summary, no preamble."""


class SummaryWriterAgent(BaseAgent):
    def __init__(self, memory):
        super().__init__("SummaryWriterAgent", memory)

    def run(self):
        self.log("Generating file summary...")
        names = [f"{e.element_type} '{e.name}'" for e in self.memory.doc_entries]
        element_list = "\n".join(f"- {n}" for n in names)

        prompt = f"""The following Python file has been documented: `{self.memory.target_file}`

It contains these elements:
{element_list}

Write a short high-level summary of what this file does."""

        summary = call_ollama(prompt, system=SUMMARY_SYSTEM_PROMPT)
        self.memory.file_summary = summary
        self.log(f"  Done. ({len(summary)} chars)")