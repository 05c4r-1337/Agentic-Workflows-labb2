"""
Central configuration for the multi-agent documentation workflow.
All tunable constants live here so they stay in sync across agents.
"""

# Default Ollama model (used as fallback if no per-agent model is set)
MODEL = "gemma4:e4b"

# Per-agent model overrides (set to None to use the default MODEL)
DOC_WRITER_MODEL = "gemma4:e4b"
REVIEWER_MODEL = "gemma4:e4b"
FACT_CHECKER_MODEL = "gemma4:e4b"
SUMMARY_MODEL = "gemma4:e4b"

# Maximum number of revision attempts before a doc entry is force-approved
MAX_RETRIES = 6

# Minimum review score (1-10) required to approve a doc entry
APPROVAL_THRESHOLD = 7

# Maximum write/review cycles before the orchestrator force-approves remaining entries
MAX_CYCLES = 10

# Abstraction level of the generated document
ABSTRACTION = 1

# Per-agent temperature settings
DOC_WRITER_TEMPERATURE = 0.6
REVIEWER_TEMPERATURE = 0.1
FACT_CHECKER_TEMPERATURE = 0.0
SUMMARY_TEMPERATURE = 0.4

# Ollama request timeout in seconds
OLLAMA_TIMEOUT = 600
