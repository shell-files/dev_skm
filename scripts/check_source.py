"""Check committed source for unresolved merges and invalid Python syntax."""
import ast
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parents[1]
paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
errors = []
python_count = 0
for name in filter(None, paths):
    path = root / name
    if path.suffix not in {".py", ".js", ".jsx", ".md", ".toml", ".yml", ".yaml"}:
        continue
    text = path.read_text(encoding="utf-8-sig")
    if re.search(r"^(?:<{7} |={7}$|>{7} )", text, re.MULTILINE):
        errors.append(f"{name}: unresolved merge conflict")
    if path.suffix == ".py":
        python_count += 1
        try:
            ast.parse(text, filename=name)
        except SyntaxError as exc:
            errors.append(f"{name}:{exc.lineno}: {exc.msg}")
for error in errors:
    print(error)
print(f"Checked {python_count} Python files; {len(errors)} errors")
raise SystemExit(bool(errors))
