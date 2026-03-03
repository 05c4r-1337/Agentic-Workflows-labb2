"""
Central configuration for the multi-agent documentation workflow.
All tunable constants live here so they stay in sync across agents.
"""

# Ollama model to use for all agents
MODEL = "codellama"

# Maximum number of revision attempts before a doc entry is force-approved
MAX_RETRIES = 3

# Minimum review score (1-10) required to approve a doc entry
APPROVAL_THRESHOLD = 9

# Maximum write/review cycles before the orchestrator force-approves remaining entries
MAX_CYCLES = 10

# Abstraction level of the generated document
ABSTRACTION = 10
