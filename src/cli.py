"""
Entrypoint: python -m src.cli <mode> [options]
"""

import argparse
import sys

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

    args = parser.parse_args()

    if args.mode == "review_pr":
        if not GITHUB_TOKEN:
            print("Missing Github Token in .env", file=sys.stderr)
            sys.exit(1)

        review = review_pr(args.repo, args.pr, GITHUB_TOKEN)
        print("\n=== PR Review ===\n")
        print(review)

    elif args.mode == "scan_repo":
        results = scan_repo(args.path, max_files=args.max_files)
        print(f"\n=== Repo Scan: {len(results)} files reviewed ===\n")
        for file_path, review in results.items():
            print(f"\n--- {file_path} ---\n")
            print(review)

if __name__ == "__main__":
    main()
