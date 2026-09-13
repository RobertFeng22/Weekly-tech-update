from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from openai import OpenAI

from .video import (
    VideoConfig,
    finalize_video_delivery,
    prepare_video,
    release_video_url,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate OpenAI TTS assets and Remotion props for an AI frontier briefing"
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--edition-dir", type=Path, required=True)
    prepare.add_argument("--public-root", type=Path, default=Path("public"))
    prepare.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY"))
    prepare.add_argument("--regenerate-plan", action="store_true")

    finalize = subparsers.add_parser("finalize")
    finalize.add_argument("--edition-dir", type=Path, required=True)
    finalize.add_argument("--video-path", type=Path, required=True)
    finalize.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY"))
    finalize.add_argument("--video-url")
    return parser


def _config() -> VideoConfig:
    default_model = os.getenv("OPENAI_MODEL", "gpt-5.4")
    return VideoConfig(
        director_model=os.getenv("OPENAI_VIDEO_MODEL", default_model),
        tts_model=os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
        voice=os.getenv("OPENAI_TTS_VOICE", "cedar"),
    )


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "prepare":
        if not os.environ.get("OPENAI_API_KEY"):
            raise SystemExit("OPENAI_API_KEY is required")
        result = prepare_video(
            client=OpenAI(),
            edition_dir=args.edition_dir,
            public_root=args.public_root,
            config=_config(),
            repository=args.repository,
            regenerate_plan=args.regenerate_plan,
        )
        print(json.dumps(result, ensure_ascii=False))
        return

    video_url = args.video_url
    if video_url is None:
        if not args.repository:
            raise SystemExit("--video-url or --repository is required")
        video_url = release_video_url(args.repository, args.edition_dir.name)
    result = finalize_video_delivery(
        edition_dir=args.edition_dir,
        video_path=args.video_path,
        video_url=video_url,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
