"""Validate local Markdown/HTML link targets without network access."""
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"!?\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)")
HTML_LINK = re.compile(r"(?:src|href)=[\"']([^\"']+)[\"']", re.IGNORECASE)


def check():
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", "*.md"],
        cwd=ROOT, text=True).splitlines()
    problems, documents, links = [], 0, 0
    for name in sorted(set(names)):
        source = ROOT / name
        if not source.is_file():
            continue  # Removed files may remain in the index before staging.
        documents += 1
        text = re.sub(r"(?ms)^```.*?^```[^\n]*$", "", source.read_text())
        targets = [match.group(1).strip("<>") for match in MARKDOWN_LINK.finditer(text)]
        targets.extend(HTML_LINK.findall(text))
        for target in targets:
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            links += 1
            if not (source.parent / unquote(parsed.path)).exists():
                problems.append(f"{name}: missing {target}")
    for problem in problems:
        print(problem)
    print(f"Checked {documents} Markdown documents and {links} local link targets; {len(problems)} missing.")
    return bool(problems)


if __name__ == "__main__":
    raise SystemExit(check())
