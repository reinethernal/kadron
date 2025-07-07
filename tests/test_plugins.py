import importlib
import subprocess
import sys
from pathlib import Path
import pytest

PLUGIN_DIR = Path(__file__).resolve().parents[1] / "plugins"

plugin_files = [p for p in PLUGIN_DIR.glob("*_plugin.py") if p.is_file()]


@pytest.mark.parametrize(
    "plugin_file", plugin_files, ids=[p.stem for p in plugin_files]
)
def test_import_and_compile(plugin_file):
    module_name = f"plugins.{plugin_file.stem}"
    importlib.import_module(module_name)
    subprocess.run([sys.executable, "-m", "py_compile", str(plugin_file)], check=True)
