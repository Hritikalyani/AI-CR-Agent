"""
MCP server exposing code-review capabilities as tools.
Each tool here wraps a fucntion that already exists in github_client.py
or indexer.py.  The server's job is schema + dispatch not logic.
"""

import json
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.config import GITHUB_TOKEN
from src.github_client import get_pr_diff, post_pr_comment
from src.indexer import retrieve_related

app = Server("code-review-agent")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_pr_diff",
            description=(
                "Fetch the diff for a github Pull request. Use this "
                "first when reviewing a PR, to see what changed."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {"type": "string",
                             "description": "Repository as owner/name"},
                    "pr_number": {"type": "integer"},
                },
                "required": ["repo", "pr_number"],
            },
        ),
        Tool(
            name="get_file_content",
            description=(
                "Read the full contents of the file from the local "
                "checkout. When the diff alone is insufficient to "
                "judge a change and you need a surrounding code."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="search_codebase",
            description=(
                "Semantic search over the indexed repository. Returns "
                "code chunks related to the MEANING to the query, not just "
                "keyword matches. Use to find callers of a function, "
                "similar patterns, or related logic elsewhere."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "code or description to find related code for",
                    },
                    "k": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="post_review_comment",
            description=(
                "Post your finished review as a comment on the PR. Call "
                "this ONCE, only when your review is complete."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {"type": "string"},
                    "pr_number": {"type": "string"},
                    "body": {"type": "string",
                             "description": "The review, in Markdown"},
                },
                "required": ["repo", "pr_number", "body"],
            },
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "get_pr_diff":
            result = get_pr_diff(arguments["repo"], arguments["pr_number"], GITHUB_TOKEN)

        elif name == "get_file_content":
            p = Path(arguments["file_path"])
            result = p.read_text(errors="ignore")

        elif name == "search_codebase":
            chunks = retrieve_related(arguments["query"], k=arguments.get("k", 5))
            result = json.dumps([{
                "file": c["meta"]["file_path"],
                "lines": f"{c['meta']['start_line']} - {c['meta']['end_line']}",
                "symbol": c["meta"]["symbol"],
                "code": c["content"]
            } for c in chunks], indent=2)

        elif name == "post_review_comment":
            post_pr_comment(arguments["repo"], arguments["pr_number"], arguments["body"], GITHUB_TOKEN)
            result = "Comment Posted Succefully."

        else:
            result = f"Unknown tool: {name}"

        return [TextContent(type="text", text=result)]

    except Exception as e:
        return [TextContent(type="text", text=f"Tool '{name}' failed: {e}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())