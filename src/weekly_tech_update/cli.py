from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path

from openai import OpenAI
from pydantic import ValidationError

from .models import NeuralAlphaSelectionContext
from .pipeline import PipelineConfig, WeeklyPipeline, load_selection_context


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a Neural Alpha context-gated weekly AI decision brief"
    )
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--output-root", type=Path, default=Path("editions"))
    parser.add_argument("--max-topics", type=int, default=2)
    parser.add_argument("--minimum-score", type=float, default=70.0)
    parser.add_argument(
        "--selection-context",
        type=Path,
        default=Path(".local/neural-alpha-selection-context.json"),
    )
    return parser


def _load_private_selection_context(path: Path) -> NeuralAlphaSelectionContext:
    raw_context = os.environ.get("NEURAL_ALPHA_SELECTION_CONTEXT_JSON")
    if raw_context:
        try:
            return NeuralAlphaSelectionContext.model_validate_json(raw_context)
        except ValidationError as exc:
            raise SystemExit(
                "NEURAL_ALPHA_SELECTION_CONTEXT_JSON is not a valid selection context"
            ) from exc
    if not path.exists():
        raise SystemExit(
            "Neural Alpha selection context is required. Set the encrypted "
            "NEURAL_ALPHA_SELECTION_CONTEXT_JSON secret or create the ignored local "
            f"file at {path}."
        )
    return load_selection_context(path)


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
    selection_context = _load_private_selection_context(args.selection_context)
    output_dir = WeeklyPipeline(OpenAI(), config, selection_context).run(
        as_of=args.as_of, output_root=args.output_root
    )
    print(output_dir)


if __name__ == "__main__":
    main()
