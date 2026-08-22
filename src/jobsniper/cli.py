"""Command-line entry point.

Subcommands are added alongside the stages that implement them, not in advance.
"""

import argparse
from collections.abc import Sequence

from jobsniper import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jobsniper",
        description="Stateful job-search pipeline. Nothing sends without explicit approval.",
    )
    parser.add_argument("--version", action="version", version=f"jobsniper {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    # No subcommands yet — print usage rather than pretending to do work.
    parser.print_help()
    return 0
