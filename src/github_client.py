"""
Thin wrapper around the github REST API
Each function is small and single-purposed because 
in phase 3 each one becomes exactly one MCP tool.
"""

import requests

GITHUB_API = "https://api.github.com"

def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

def get_pr_diff(repo: str, pr_number: int, token: str) -> str:
    url = f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}"
    headers = _headers(token)
    headers["ACCEPT"] = "application/vnd.github.v3.diff"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text

def post_pr_comment(repo: str, pr_number: int, token: str, body: str) -> dict:
    url = f"{GITHUB_API}/repos/{repo}/issues/{pr_number}/comments"
    resp = requests.post(url, headers=_headers(token), json={"body": body}, timeout=30)
    resp.raise_for_status()
    return resp.json()