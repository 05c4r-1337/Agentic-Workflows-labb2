"""Base class for all agents in the documentation workflow."""

from memory.session_memory import SessionMemory


class BaseAgent:
    def __init__(self, name: str, memory: SessionMemory):
        self.name = name
        self.memory = memory

    def log(self, message: str):
        self.memory.log(self.name, message)

    def run(self):
        raise NotImplementedError
