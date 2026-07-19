"""CLI: page-wise VLM Markdown snapshot for document_parsing eval reuse.

Example smoke::

    python -m research.lab.scripts.vlm_bench \\
      --model-key vlm_bench_35b \\
      --dpi 96 \\
      --case-id catalog-belimo-p020

Full bench (then score separately)::

    python -m research.lab.scripts.vlm_bench --model-key vlm_bench_35b --dpi 96
    python -m research.benchmarks.document_parsing.eval.run \\
      --source research/lab/output/vlm_bench/<run_id> \\
      --mode reuse \\
      --name e007-vlm-35b-dpi96
"""

from __future__ import annotations

import argparse
import logging
import sys

from infra.config import config_logger
from research.lab.scripts.vlm_bench.runner import DEFAULT_OUTPUT_ROOT, run_vlm_bench


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-key",
        required=True,
        help="MODELS key in config.yaml (e.g. vlm_bench_35b, vlm_bench_27b)",
    )
    parser.add_argument("--dpi", type=int, default=96)
    parser.add_argument(
        "--run-id",
        default=None,
        help="Output folder name under research/lab/output/vlm_bench/",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        default=None,
        dest="case_ids",
        help="Limit to one or more case_ids (repeatable). Smoke / partial runs.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip cases that already have complete artifacts in the run dir",
    )
    parser.add_argument(
        "--output-root",
        type=type(DEFAULT_OUTPUT_ROOT),
        default=DEFAULT_OUTPUT_ROOT,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    config_logger()
    # Keep tqdm intact: HTTP client INFO lines otherwise rewrite the bar each request.
    for noisy in ("httpx", "httpcore", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    args = _parse_args(argv)
    output_dir = run_vlm_bench(
        model_key=args.model_key,
        dpi=args.dpi,
        run_id=args.run_id,
        case_ids=args.case_ids,
        resume=args.resume,
        output_root=args.output_root,
    )
    print(f"snapshot written: {output_dir}")
    print(
        "score with:\n"
        f"  python -m research.benchmarks.document_parsing.eval.run "
        f"--source {output_dir} --mode reuse --name <run-name>"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
