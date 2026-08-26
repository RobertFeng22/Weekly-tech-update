from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path

from openai import OpenAI

from .pipeline import PipelineConfig, WeeklyPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate an evidence-gated weekly AI update")
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--output-root", type=Path, default=Path("editions"))
    parser.add_argument("--max-topics", type=int, default=3)
    parser.add_argument("--minimum-score", type=float, default=70.0)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required")
    default_model = os.getenv("OPENAI_MODEL", "gpt-5.4")
    config = PipelineConfig(
        discovery_model=os.getenv("OPENAI_DISCOVERY_MODEL", default_model),
        evaluation_model=os.getenv("OPENAI_EVALUATION_MODEL", default_model),
        editor_model=os.getenv("OPENAI_EDITOR_MODEL", default_model),
        max_topics=args.max_topics,
        minimum_score=args.minimum_score,
    )
    output_dir = WeeklyPipeline(OpenAI(), config).run(
        as_of=args.as_of, output_root=args.output_root
    )
    print(output_dir)


if __name__ == "__main__":
    main()

