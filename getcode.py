import os
from pathlib import Path
from subprocess import run, PIPE

def list_py_files(base_path: Path, exclude_dirs=('venv',)):
    py_files = []
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith('.py'):
                full_path = Path(root) / file
                py_files.append(full_path)
    return py_files

def get_tree_structure(base_path: Path, exclude_dirs=('venv',)):
    result = run(["tree", "-I", "|".join(exclude_dirs), "-P", "*.py"], cwd=base_path, stdout=PIPE, text=True)
    return result.stdout

def collect_all_py_contents(base_path: Path, py_files):
    content = []
    for file_path in py_files:
        relative_path = file_path.relative_to(base_path)
        content.append(f"# === FILE: {relative_path} ===")
        content.append(file_path.read_text(encoding='utf-8', errors='ignore'))
        content.append("\n")
    return "\n".join(content)

def main():
    base_path = Path(__file__).parent.resolve()
    py_files = list_py_files(base_path)
    tree_output = get_tree_structure(base_path)
    py_contents = collect_all_py_contents(base_path, py_files)

    output_path = base_path / "fullcode.txt"
    with open(output_path, "w", encoding='utf-8') as f:
        f.write("# === STRUCTURE ===\n")
        f.write(tree_output)
        f.write("\n# === PYTHON FILE CONTENTS ===\n")
        f.write(py_contents)

if __name__ == '__main__':
    main()



