"""Base class for all agents in the documentation workflow."""

from memory.session_memory import SessionMemory


class BaseAgent:
    def __init__(self, name: str, memory: SessionMemory):
        self.name = name
        self.memory = memory

    def log(self, message: str):
        self.memory.log(self.name, message)

    def log_output(self, label: str, content: str):
        self.memory.log_output(self.name, label, content)

    def run(self):
        raise NotImplementedError
