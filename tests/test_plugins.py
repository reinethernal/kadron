import importlib
import subprocess
import sys
from pathlib import Path
import pytest

PLUGIN_DIR = Path(__file__).resolve().parents[1] / "plugins"

plugin_files = [p for p in PLUGIN_DIR.rglob("*_plugin.py") if p.is_file()]


@pytest.mark.parametrize(
    "plugin_file", plugin_files, ids=[p.stem for p in plugin_files]
)
def test_import_and_compile(plugin_file):
    rel = plugin_file.relative_to(PLUGIN_DIR).with_suffix("")
    module_name = f"plugins.{'.'.join(rel.parts)}"
    importlib.import_module(module_name)
    subprocess.run([sys.executable, "-m", "py_compile", str(plugin_file)], check=True)
