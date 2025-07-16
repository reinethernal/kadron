import os
import re


def parse_admin_ids(value: str | None = None) -> list[int]:
    """Return a list of admin IDs from string or ``ADMIN_IDS`` env variable."""
    if value is None:
        value = os.getenv("ADMIN_IDS", "")

    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]

    ids = re.findall(r"\d+", value)
    return [int(i) for i in ids]
