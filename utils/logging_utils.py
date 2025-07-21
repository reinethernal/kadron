import logging
import os


def configure_logging():
    """Configure logging level from environment."""
    level_name = os.getenv("LOGGING_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, force=True)
