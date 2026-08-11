"""Command-line interface.

    groundgate verify --answer "..." --context ctx.txt
    groundgate mcp
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .gate import verify
from .mcp_server import serve


def _load_context(value: str) -> str | list:
    """Context argument: inline text, a text file, or a JSON file of sources."""
    path = Path(value)
    if path.is_file():
        raw = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            return json.loads(raw)
        return raw
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="groundgate",
        description="Runtime faithfulness gate for RAG answers.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_parser = subparsers.add_parser(
        "verify", help="Verify an answer against retrieved context."
    )
    verify_parser.add_argument("--answer", required=True, help="Answer text to verify.")
    verify_parser.add_argument(
        "--context",
        required=True,
        help="Context: inline text, a .txt file, or a .json file of {id, text} sources.",
    )
    verify_parser.add_argument(
        "--require-citations",
        action="store_true",
        help="Fail claims that carry no citation marker.",
    )

    subparsers.add_parser("mcp", help="Run the MCP server on stdio.")

    args = parser.parse_args(argv)

    if args.command == "mcp":
        serve()
        return 0

    verdict = verify(
        args.answer,
        _load_context(args.context),
        require_citations=args.require_citations,
    )
    json.dump(verdict.to_dict(), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if verdict.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
