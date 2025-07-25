import logging
import os


def configure_logging():
    """Configure logging level from environment.

    Logging can be completely disabled by setting ``ENABLE_LOGGING`` to
    ``False``.
    """

    enable_logging = os.getenv("ENABLE_LOGGING", "True").lower() == "true"
    if not enable_logging:
        logging.disable(logging.CRITICAL)
        return

    level_name = os.getenv("LOGGING_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, force=True)
