import logging
import os
from dotenv import load_dotenv


def configure_logging():
    """Load env vars and configure logging level."""
    load_dotenv()
    level_name = os.getenv("LOGGING_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, force=True)

