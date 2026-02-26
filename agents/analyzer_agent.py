"""
Analyzer Agent — reads the target file and extracts all code elements
using AST analysis. Populates the shared session memory with DocEntry objects.
"""

from agents.base_agent import BaseAgent
from tools.code_tools import read_file, parse_code


class AnalyzerAgent(BaseAgent):
    def __init__(self, memory):
        super().__init__("AnalyzerAgent", memory)

    def run(self):
        self.log(f"Reading file: {self.memory.target_file}")
        source = read_file(self.memory.target_file)
        self.memory.source_code = source

        self.log("Parsing code with AST...")
        entries = parse_code(source)
        self.memory.doc_entries = entries

        self.log(f"Found {len(entries)} elements to document:")
        for entry in entries:
            self.log(f"  [{entry.element_type}] {entry.name}")
