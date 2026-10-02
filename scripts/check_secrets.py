"""Deterministic tracked-file secret checks without displaying matched values."""

import re
import subprocess
from pathlib import Path

PATTERNS = [
    re.compile(r"sk-(?:ant-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(
        r"(?im)^[ \t]*(?:OPENAI_API_KEY|ANTHROPIC_API_KEY|SERPER_API_KEY)[ \t]*=[ \t]*[^\s#]+"
    ),
]


def main():
    tracked = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    candidates = set(p for p in tracked if p)
    untracked = (
        subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "-z"])
        .decode()
        .split("\0")
    )
    candidates.update(p for p in untracked if p)
    failures = []
    for name in sorted(candidates):
        path = Path(name)
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in PATTERNS):
            failures.append(name)
    if ".env" in candidates:
        failures.append(".env must not be tracked")
    ignored = subprocess.run(["git", "check-ignore", "-q", ".env"], check=False).returncode == 0
    if not ignored:
        failures.append(".env is not ignored")
    example = Path(".env.example").read_text(encoding="utf-8")
    for line in example.splitlines():
        if "API_KEY=" in line and line.split("=", 1)[1].strip():
            failures.append(".env.example contains a nonempty API key")
    if failures:
        print("Secret checks failed in: " + ", ".join(sorted(set(failures))))
        raise SystemExit(1)
    print(
        f"Secret checks passed: {len(candidates)} files scanned; .env ignored and untracked; example keys empty."
    )


if __name__ == "__main__":
    main()
