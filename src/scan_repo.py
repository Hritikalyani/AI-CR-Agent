"""
Mode 2: Scan-repo
Walk a local repo, scan each source file for bugs/vulnerabilities.

Phase-1 limitations ON PURPOSE: each file is scanned in isolation.
This is the "before" picture for the RAG comparison in Phase 2.
"""

import os
from pathlib import Path

from src.config import SCANNABLE_EXTENSIONS, SKIP_DIRS
from src.llm_client import ask_llm

SCAN_SYSTEM_PROMPT = """
You are a senior software engineer doing a code review on a single source file
in isolation (you do not have the rest of the codebase).
Identify:
1. Bugs or logic errors
2. Risky coding patterns (e.g. bare excepts, resource leaks, hardcoded values, unsafe data handling)
3. Obvious bad practices that reduce reliability or maintainability

Be concise. If nothing significant stands out, say "No significant issues found"
rather than inventing minor nitpicks. Since you only see this one file, flag anything
that *might* be a cross-file issue as "needs broader context to confirm" rather than
asserting it's a problem.
"""

def _find_scannable_files(repo_path: str) -> list[Path]:
    root = Path(repo_path).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Invalid repo path: {repo_path}")
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if Path(fname).suffix in SCANNABLE_EXTENSIONS:
                found.append(Path(dirpath) / fname)
    return found

def scan_repo(repo_path: str, max_files: int = 25) -> dict[str, str]:
    files = _find_scannable_files(repo_path)[:max_files]
    results = {}

    for file_path in files:
        try:
            content = file_path.read_text(errors="ignore")
        except Exception as e:
            results[str(file_path)] = f"could not read file: {e}"
            continue

        if not content.strip():
            continue

        review = ask_llm(
            system_prompt=SCAN_SYSTEM_PROMPT,
            user_content=f"File: {file_path}\n\n{content}",
        )
        results[str(file_path)] = review

    return results

    