"""Ищет потенциально опасные паттерны в коде MiniWiki."""
import re
import sys
from pathlib import Path

PATTERNS = [
    (r"execute\s*\(\s*f[\"']", "SQL через f-string — риск инъекции"),
    (r"\.format\(.*SELECT|SELECT.*\.format\(", "SQL через .format — риск инъекции"),
    (r"\|\s*safe", "Jinja2 |safe — проверь, что данные очищены"),
    (r"password\s*=\s*[\"'][^\"']+[\"']", "Возможный хардкод пароля"),
    (r"(SECRET|API_KEY|TOKEN)\s*=\s*[\"'][^\"']+[\"']", "Возможный хардкод секрета"),
    (r"render_markdown\((?!.*clean)", "Проверь, что render_markdown вызывает nh3.clean"),
]

def main():
    root = Path("app")
    if not root.exists():
        print("Нет каталога app/"); return 0
    issues = 0
    for f in root.rglob("*.py"):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for pat, msg in PATTERNS:
                if re.search(pat, line):
                    print(f"{f}:{i}: [{msg}] {line.strip()}")
                    issues += 1
    print(f"\nИтого срабатываний: {issues}")
    return 0

if __name__ == "__main__":
    sys.exit(main())