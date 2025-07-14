import os
import re

def parse_admin_ids(value: str) -> list[int]:
    """Парсит строку вида '123,456' в список int"""
    return [int(x.strip()) for x in value.split(",") if x.strip().isdigit()]
