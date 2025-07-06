import os
import re


def parse_admin_ids() -> list[int]:
    """Parse ADMIN_IDS from environment and return a list of ints."""
    ids = re.findall(r"\d+", os.environ.get("ADMIN_IDS", ""))
    return [int(x) for x in ids]
