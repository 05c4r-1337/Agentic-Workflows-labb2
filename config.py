"""
Central configuration for the multi-agent documentation workflow.
All tunable constants live here so they stay in sync across agents.
"""

# Default Ollama model (used as fallback if no per-agent model is set)
MODEL = "gemma3:12b"

# Per-agent model overrides (set to None to use the default MODEL)
DOC_WRITER_MODEL = "gemma3:12b"
REVIEWER_MODEL = "llama3.1:8b"
FACT_CHECKER_MODEL = "qwen3.5:latest"
SUMMARY_MODEL = "gemma3:12b"

# Maximum number of revision attempts before a doc entry is force-approved
MAX_RETRIES = 3

# Minimum review score (1-10) required to approve a doc entry
APPROVAL_THRESHOLD = 7

# Maximum write/review cycles before the orchestrator force-approves remaining entries
MAX_CYCLES = 10

# Abstraction level of the generated document
ABSTRACTION = 10

# Ollama request timeout in seconds
OLLAMA_TIMEOUT = 600
