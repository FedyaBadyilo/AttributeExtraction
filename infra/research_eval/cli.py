import argparse
from collections.abc import Callable
from typing import Any, Type

from infra.research_eval.runner import evaluate_experiment
from infra.research_eval.types import BaseEvalAdapter


def run_eval_cli(
    adapter_cls: Type[BaseEvalAdapter],
    *,
    configure_parser: Callable[[argparse.ArgumentParser], None] | None = None,
    adapter_kwargs_from_args: Callable[[argparse.Namespace], dict[str, Any]] | None = None,
) -> None:
    parser = argparse.ArgumentParser(description="Run step evaluation experiment")
    parser.add_argument("--source", required=True, help="Evaluation input (opaque to baseline)")
    parser.add_argument("--name", required=True, help="MLflow run name")
    if configure_parser is not None:
        configure_parser(parser)
    args = parser.parse_args()

    adapter_kwargs = (
        adapter_kwargs_from_args(args) if adapter_kwargs_from_args is not None else {}
    )
    evaluate_experiment(
        adapter_cls=adapter_cls,
        source=args.source,
        name=args.name,
        adapter_kwargs=adapter_kwargs,
    )
