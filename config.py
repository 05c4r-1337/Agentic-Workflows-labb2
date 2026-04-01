"""
Central configuration for the multi-agent documentation workflow.
All tunable constants live here so they stay in sync across agents.
"""

# Default Ollama model (used as fallback if no per-agent model is set)
MODEL = "llama3.1:8b"

# Per-agent model overrides (set to None to use the default MODEL)
DOC_WRITER_MODEL = None
REVIEWER_MODEL = None
FACT_CHECKER_MODEL = None
SUMMARY_MODEL = None

# Maximum number of revision attempts before a doc entry is force-approved
MAX_RETRIES = 3

# Minimum review score (1-10) required to approve a doc entry
APPROVAL_THRESHOLD = 7

# Maximum write/review cycles before the orchestrator force-approves remaining entries
MAX_CYCLES = 10

# Abstraction level of the generated document
ABSTRACTION = 10
