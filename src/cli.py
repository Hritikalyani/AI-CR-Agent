"""
Entrypoint: python -m src.cli <mode> [options]
"""

import argparse
import sys
import requests

from src.config import GITHUB_TOKEN
from src.review_pr import review_pr
from src.scan_repo import scan_repo

def main():
    parser = argparse.ArgumentParser(
        description="AI code Review Agent (Phase 1)")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    pr_parser = subparsers.add_parser("review_pr", help="Review a GitHub PR diff")
    pr_parser.add_argument("--repo", required=True, help="owner/name")
    pr_parser.add_argument("--pr", required=True, type=int, help="PR number")

    scan_parser = subparsers.add_parser("scan_repo", help="scan a local repo")
    scan_parser.add_argument("--path", required=True, help="path to local repo")
    scan_parser.add_argument("--max-files", type=int, default=25)
    scan_parser.add_argument("--no-rag", action="store_true", help="Disable retrieval (Phase 1 Baseline)")

    agent_parser = subparsers.add_parser("agent-review", help="Autonomous Agentic PR review (Phase 3)")
    agent_parser.add_argument("--repo", required=True)
    agent_parser.add_argument("--pr", required=True, type=int)

    args = parser.parse_args()

    if args.mode == "review_pr" and args.repo.count("/") != 1:
        print(f"--repo must be owner/name, got: {args.repo}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.mode == "review_pr":
            if not GITHUB_TOKEN:
                print("Missing Github Token in .env", file=sys.stderr)
                sys.exit(1)

            review = review_pr(args.repo, args.pr, GITHUB_TOKEN)
            print("\n=== PR Review ===\n")
            print(review)

        elif args.mode == "scan_repo":
            results = scan_repo(args.path, max_files=args.max_files, use_rag=not args.no_rag)
            print(f"\n=== Repo Scan: {len(results)} files reviewed ===\n")
            for file_path, review in results.items():
                print(f"\n--- {file_path} ---\n")
                print(review)

        elif args.mode == "agent-review":
            from src.agent import run_agent, build_tool_schemas, execute_tool
            goal = (f"Review Pull Request #{args.pr} in the repository"
                    f"{args.repo}. Post your review when done.")
            print(run_agent(goal, build_tool_schemas, execute_tool))


    except requests.exceptions.RequestException as e:
        print(f"GitHub API error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Invalid input: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
