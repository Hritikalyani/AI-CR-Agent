"""
The Agent: Gives the model a Goal and a Toolbox, then executes whatever it decides to call, untill its done.

The control flow in this file is NOT written by me, it emerges from the model's choices giving it 
an apt title of Agentic Ai. That's the difference 
"""

import time
time.sleep(12)

import json
from pathlib import Path
from google import genai
from google.genai import types
from src.config import GEMINI_API_KEY, GEMINI_MODEL, GITHUB_TOKEN
from src.github_client import get_pr_diff, post_pr_comment
from src.indexer import retrieve_related


_client = genai.Client(api_key=GEMINI_API_KEY)

AGENT_SYSTEM_PROMPT = """
You are an autonomous code reviewer with access to tools for reading Pull Requests, reading files
and searching the codebase semantically.

Your approach:
1. Get the diff to see what happened
2. Judge whether the diff alone is enough. For trivial changes (such as README edits, typos, or standalone documentation), 
   DO NOT search the codebase or read extra files.
3. When a change's correctness depends on code you cannot see, use search_codebase to find callers, related
   logic, or the definitions being used. Read full files when needed.
4. Form your review. Report only real issues. If the change is fine, say so briefly, do not manufacture 
   findings to appear thorough.
5. Call `post_review_comment` ONCE when complete, then finish. Do not make duplicate tool calls.
Prefer fewer, higher-confidence findings over many speculative ones.
"""

def execute_tool(name: str, arguments: dict) -> str:
    """Executes local tool functions matching the tool declarations."""
    try:
        if name == "get_pr_diff":
            return get_pr_diff(arguments["repo"], int(arguments["pr_number"]), GITHUB_TOKEN)
        
        elif name == "get_file_content":
            p = Path(arguments["file_path"])
            return p.read_text(errors="ignore")
        
        elif name == "search_codebase":
            k = int(arguments.get("k", 5))
            chunks = retrieve_related(arguments["query"], k=k)
            return json.dumps([
                {
                    "file": c["meta"]["file_path"],
                    "lines": f"{c['meta']['start_line']}-{c['meta']['end_line']}",
                    "symbol": c["meta"]["symbol"],
                    "code": c["content"]
                }
                for c in chunks
            ], indent=2)
            
        elif name == "post_review_comment":
            post_pr_comment(arguments["repo"], int(arguments["pr_number"]), arguments["body"], GITHUB_TOKEN)
            return "Comment posted successfully."
            
        else:
            return f"Unknown tool: {name}"
            
    except Exception as e:
        return f"Tool {name} failed: {e}"


def run_agent(goal: str, tools: list[dict], execute_tool_fn, max_turns: int = 15) -> str:
    chat = _client.chats.create(
        model=GEMINI_MODEL,
        config=types.GenerateContentConfig(
            system_instruction=AGENT_SYSTEM_PROMPT,
            tools=tools,
            temperature=0.2,
        )
    )

    response = chat.send_message(goal)

    for turn in range(max_turns):
        if not response.function_calls:
            return response.text

        tool_responses = []
        for call in response.function_calls:
            print(f" [turn {turn}] calling {call.name}")
            tool_output = execute_tool_fn(call.name, call.args)
            
            tool_responses.append(
                types.Part.from_function_response(
                    name=call.name,
                    response={"result": tool_output}
                )
            )

        response = chat.send_message(tool_responses)

    return "Agent hit max turns without completing."


def build_tool_schemas() -> list[dict]:
    """Gemini Tool format, Mirrors the MCP server's declaration"""
    return [
        {
            "function_declarations": [
                {
                    "name": "get_pr_diff",
                    "description": "Fetch the diff from Github pull request. Use this first when reviewing the PR.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "repo": {"type": "STRING", "description": "Repository owner/name"},
                            "pr_number": {"type": "INTEGER", "description": "PR number"}
                        },
                        "required": ["repo", "pr_number"]
                    }
                },
                {
                    "name": "get_file_content",
                    "description": "Read the full contents of a file from local checkout. Use when diff is insufficient.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "file_path": {"type": "STRING", "description": "Relative path to file"}
                        },
                        "required": ["file_path"]
                    }
                },
                {
                    "name": "search_codebase",
                    "description": "Semantic search over the repository. Use ONLY when code changes require checking external references or dependencies."
                    "Skip for documentation or trivial edits.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "query": {"type": "STRING", "description": "Search query"},
                            "k": {"type": "INTEGER", "description": "Number of results (default 5)"}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "post_review_comment",
    "description": "Post your finished review as a comment on the PR. Call this ONCE, only when your review is complete, and stop.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "repo": {"type": "STRING"},
                            "pr_number": {"type": "INTEGER"},
                            "body": {"type": "STRING", "description": "Markdown review text"}
                        },
                        "required": ["repo", "pr_number", "body"]
                    }
                }
            ]
        }
    ]