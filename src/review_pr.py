"""
Mode 1: review-pr
Fetch a PR's diff -> send to the LLM -> return the review
"""

from src.github_client import get_pr_diff
from src.llm_client import ask_llm

REVIEW_SYSTEM_PROMPT = """
You are a senior software engineer doing a code review.
Given a PR diff,  identify:
1. Bugs or logic errors
2. Security vulnerabilities
3. Style/Convention issues worth flagging
4.Missing test coverage (if evident from the diff)
5. Performance issues or enhancements

Be specific - reference file names and line context from the diff. skip
nitpicks that dont matter. If the diff looks solid, say so briefly instead 
of inventing issues.
"""

def review_pr(repo: str, pr_number: int, token: str, use_rag: bool = True, repo_path: str | None = None) -> str:
    from src.indexer import retrieve_related
    diff = get_pr_diff(repo, pr_number, token)
    if not diff.strip():
        return "No diff content found -- is the PR number correct?"

    if use_rag and repo_path:
        query = _extract_query_text(diff)
        related = retrieve_related(query)
        from src.scan_repo import _format_context
        user_content = (
            f"Pull request diff:\n\n{diff}\n\n"
            f"Related code from the repository:\n\n"
            f"{_format_context(related)}"
        )
    else:
        user_content = diff

    return ask_llm(system_prompt=REVIEW_SYSTEM_PROMPT, user_content=user_content)

def _extract_query_text(diff: str) -> str:
    """ Pull just the added/modifies lines out of the diff for querying"""
    lines = []
    for line in diff.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines)