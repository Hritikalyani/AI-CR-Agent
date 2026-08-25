"""
The Agent: Gives the model a Goal and a Toolbox, then executes whatever it decides to call, untill its done.

The control flow in this file is NOT written by me, it emerges from the model's choices giving it 
an apt title of Agentic Ai. That's the difference 
"""

from google import genai
from google.genai import types
from src.config import GEMINI_API_KEY, GEMINI_MODEL

_client = genai.Client(api_key=GEMINI_API_KEY)

AGENT_SYSTEM_PROMPT = """
You are an autonomous code reviewer with access to tools for reading Pull Requests, reading files
and searching the codebase semantically.

Your approach:
1. Get the diff to see what happened
2. Judge wether the diff alone is enough. For trivial changes it often is - do not do unnecessary work.
3. When a change's correctness depends on code you cannot see, use search_codebase to find callers, related
   logic, or the definitions being used. Read full files when needed.
4. Form your review. Report only real issues. If the change is fine, say so briefly, do not manufacture 
   findings to appear thorough.
5. Post the review once, when complete.

Prefer fewer, higher-confidence findings over many speculative ones.
"""

def run_agent(goal: str, tools: list[dict], execute_tool, max_turns: int = 15) -> str:
    messages = [{"role": "user", "content": goal}]

    for turn in range(max_turns):
        response = _client.messages.create(
            model=GEMINI_MODEL,
            max_tokens=4000,
            system=AGENT_SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f" [turn {turn}] calling {block.name}")
            output = execute_tool(block.name, block.input)
            tool_results.append({
                "type": "tool_results",
                "tool_use_id": block.id,
                "content": output,
            })

        messages.append({"role": "user", "content": tool_results})

    return "Agent hit max turns without completing."

def build_tool_schemas() -> list[dict]:
    """ Gemini Tool format, Mirrors the MCP server's declaration"""
    return [
        {
            "name": "get_pr_diff",
            "description": "Fetch the diff from Github pull request. Use this first when reviewing the PR.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "repo": {"type": "STRING"},
                    "pr_number": {"type": "INTEGER"}
                },
                "required": ["repo", "pr_number"]
            }
        },
        {
            "name": "get_file_content",
            "description": "Read the full contents of the file from the local checkout. "
            "Use when a diff alone is insufficient to judge a change and you need surrounding code",
            "parameters": {
                "types": "OBJECT",
                "properties": {
                    "file_path": {"type": "STRING"}
                },
                "required": ["file_path"]
            }
        },
        {
            "name": "search_codebase",
            "description": "Semantic search over the indexed repository. Returns code chunks"
            "related in MEANING to the query, not just keyword matches. Use to find callers of "
            "a function, similar patterns, or related logic elsewhere.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {"type": "STRING",
                              "description": "Code or description to find related code for."},
                    "k": {
                        "type": "INTEGER",
                        "description": "Default is 5"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "post_review_comment",
            "description": "Post your finished review as a comment on the PR. Call this ONCE,only when your review is complete.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "repo": {"type": "STRING"},
                    "pr_number": {"type": "INTEGER"},
                    "body": {
                        "type": "STRING",
                        "description": "The review, in markdown"
                    }
                },
                "required": ["repo", "pr_number", "body"]
            }
        }
    ]