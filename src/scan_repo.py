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
You are a senior software engineer / Security focused Code Editor doing a code review on a single source file
in isolation (you do not have the rest of the codebase).
Identify:
1. Clear Bugs or logic errors
2. Risky coding patterns (e.g. bare excepts, resource leaks, hardcoded values, unsafe data handling)
3. Obvious bad practices that reduce reliability or maintainability
4. Security vulnerabilities, especially ones only visible across files (unsanitized input reaching a sink, contract violations by callers, 
   misuse of a helper defined elsewhere

Be concise. If nothing significant stands out, say "No significant issues found"
rather than inventing minor nitpicks. Since you only see this one file, flag anything
that *might* be a cross-file issue as "needs broader context to confirm" rather than
asserting it's a problem.
"""

SCAN_SYSTEM_PROMPT_RAG = """
You are a senior Software Engineer / Security focused Code Auditor/reviewer. You are given a file under review, plus related code retrieved 
from elsewhere in the same repository. Use the related code to judge whether issues in the file under review are actually reachable and exploitable.
Identify:
1. Security Vulnerabilities especially ones visiable across files (Unsanitized input reaching a sink, contract violations by callers,
   misuse of a helper defined elsewhere)
2. Clear bugs or logic errors
3. Obvious Bad practices
4. Risky coding patterns (e.g. bare excepts, resource leaks, hardcoded values, unsafe data handling)

Report issues ONLY in the file under review. The related code is context, not a target for review.

Be concise. If nothing significant stands out, say "No significant issues found"
rather than inventing minor nitpicks. When the realted code confirms or refutes a concern,
say which and why.
"""

def _find_scannable_files(repo_path: str) -> list[Path]:
    root = Path(repo_path).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Invalid repo path: {repo_path}")
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            # amazonq-ignore-next-line
            if Path(fname).suffix.lower() in SCANNABLE_EXTENSIONS:
                # amazonq-ignore-next-line
                found.append(Path(dirpath) / fname)
    return found

def scan_repo(repo_path: str, max_files: int = 25, use_rag: bool = True) -> dict[str, str]:

    from src.indexer import build_index, retrieve_related

    if use_rag:
        n = build_index(repo_path)
        print(f"Indexed {n} chunks.")

    files = _find_scannable_files(repo_path)[:max_files]
    results = {}

    for file_path in files:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            results[str(file_path)] = f"could not read file: {e}"
            continue

        if not content.strip():
            continue

        if use_rag:
            related = retrieve_related(content, exclude_file=str(file_path))
            user_content = (
                f"File under review: {file_path}\n\n{content}\n\n"
                f"Related code from elsewhere in this repository:\n\n"
                f"{_format_context(related)}"
            )
            prompt = SCAN_SYSTEM_PROMPT_RAG
        else:
            user_content = f"File: {file_path}\n\n{content}"
            prompt = SCAN_SYSTEM_PROMPT

        results[str(file_path)] = ask_llm(system_prompt=prompt, user_content=user_content)

    return results

def _format_context(related: list[dict]) -> str:
    if not related:
        return ("No related code retrieved.")
    parts = []
    for r in related:
        m = r["meta"]
        label = f"{m['file_path']} lines {m['start_line']} - {m['end_line']}"
        if m.get("symbol"):
            label += f" ({m['symbol']})"
        parts.append(f"--- {label} ---\n{r['content']}")
    return "\n\n".join(parts)