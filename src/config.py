"""Pipeline configuration with environment variable overrides."""
import os

BATCH_SIZE = int(os.environ.get("BATCH_SIZE", 20))
MAX_SUBAGENTS = int(os.environ.get("MAX_SUBAGENTS", 2))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", 3))
