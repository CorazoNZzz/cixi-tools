"""Command line interface for the simplified VOC source tracing report generator."""

from __future__ import annotations

import argparse
import sys

from .report import DEFAULT_ACTIONS, create_docx_report, generate_report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a simplified source tracing report from incident notes.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to a text file containing the raw incident description. If omitted, stdin is used.",
    )
    parser.add_argument(
        "--docx",
        metavar="PATH",
        help="If provided, also export the report to the given .docx file.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.input:
        try:
            with open(args.input, "r", encoding="utf-8") as stream:
                raw_text = stream.read()
        except OSError as exc:  # pragma: no cover - argparse already handles messaging
            parser.error(str(exc))
            return 2
    else:
        raw_text = sys.stdin.read()

    report = generate_report(raw_text, actions=DEFAULT_ACTIONS)
    if args.docx:
        create_docx_report(raw_text, args.docx, actions=DEFAULT_ACTIONS)
        print(f"Report saved to {args.docx}")
    print(report)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
