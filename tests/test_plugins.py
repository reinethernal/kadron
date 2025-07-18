import importlib
import subprocess
import sys
from pathlib import Path
import pytest

PLUGIN_DIRS = [
    Path(__file__).resolve().parents[1] / "plugins_admin",
    Path(__file__).resolve().parents[1] / "plugins_surveys",
]

plugin_files = [p for d in PLUGIN_DIRS for p in d.glob("*_plugin.py") if p.is_file()]


@pytest.mark.parametrize(
    "plugin_file",
    plugin_files,
    ids=[f"{p.parent.name}.{p.stem}" for p in plugin_files],
)
def test_import_and_compile(plugin_file):
    module_name = f"{plugin_file.parent.name}.{plugin_file.stem}"
    importlib.import_module(module_name)
    subprocess.run([sys.executable, "-m", "py_compile", str(plugin_file)], check=True)
