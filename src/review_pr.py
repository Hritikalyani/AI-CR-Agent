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

def review_pr(repo: str, pr_number: int, token: str) -> str:
    diff = get_pr_diff(repo, pr_number, token)
    if not diff.strip():
        return "No diff found for this PR.-- is the PR number correct?"
    return ask_llm(system_prompt=REVIEW_SYSTEM_PROMPT, user_content=diff)