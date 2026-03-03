"""
Analyzer Agent — reads the target file and extracts all code elements.
Supports Python (AST) and C# (tree-sitter) via the parser factory.
Populates the shared session memory with DocEntry objects.
"""

from agents.base_agent import BaseAgent
from tools.code_tools import read_file
from tools.parsers import get_parser


class AnalyzerAgent(BaseAgent):
    def __init__(self, memory):
        super().__init__("AnalyzerAgent", memory)

    def run(self):
        self.log(f"Reading file: {self.memory.target_file}")
        source = read_file(self.memory.target_file)
        self.memory.source_code = source

        self.log(f"Parsing {self.memory.language} code...")
        parser = get_parser(self.memory.target_file)
        entries = parser.parse(source)
        self.memory.doc_entries = entries

        self.log(f"Found {len(entries)} elements to document:")
        for entry in entries:
            self.log(f"  [{entry.element_type}] {entry.name}")
