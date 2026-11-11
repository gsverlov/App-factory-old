"""Factory-wide configuration: env vars, paths, constants."""

import os
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Directories
MEMORY_DIR = Path("memory")
AUDIT_DIR = Path("audit")
TEMPLATE_PATH = MEMORY_DIR / "_template.md"
SKILLS_DIR = Path(".claude/skills")
# Project-specific skill files the PM agent writes, one folder per ticket
GENERATED_SKILLS_DIR = Path(".claude/skills-generated")
DB_PATH = "factory.db"

# API keys and secrets
LINEAR_API_KEY = os.getenv("LINEAR_API_KEY", "")
LINEAR_WEBHOOK_SECRET = os.getenv("LINEAR_WEBHOOK_SECRET", "")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

GITHUB_ORG = os.getenv("GITHUB_ORG", "ashtilawat")
WORKSPACE_DIR = Path("/app/workspace")

# Parallel dev agents — the decompose step may never start more than this
MAX_DEV_AGENTS = 6

# Timeouts
AGENT_TIMEOUT = 3600  # 30 minutes

# Logging
logger = logging.getLogger("factory")
logging.basicConfig(level=logging.INFO)
