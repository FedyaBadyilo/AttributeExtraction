from __future__ import annotations

import argparse

from infra.research_eval.cli import run_eval_cli
from research.steps.extraction.eval.adapter import ExtractionEvalAdapter


def _configure_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--unit-matching",
        action="store_true",
        help=(
            "Include unit comparison in is_match when GT rows have an explicit "
            "'unit' field. Default: off."
        ),
    )


def _adapter_kwargs_from_args(args: argparse.Namespace) -> dict[str, bool]:
    return {"unit_matching_enabled": args.unit_matching}


if __name__ == "__main__":
    run_eval_cli(
        adapter_cls=ExtractionEvalAdapter,
        configure_parser=_configure_parser,
        adapter_kwargs_from_args=_adapter_kwargs_from_args,
    )
