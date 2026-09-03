from __future__ import annotations

import hashlib
import json
import math
import re
import struct
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI

from .models import (
    Evaluation,
    VideoPlan,
    VideoSceneKind,
    WeeklyEdition,
)
from .prompts import VIDEO_DIRECTOR_INSTRUCTIONS

AI_VOICE_DISCLOSURE = "本视频旁白由 OpenAI 的人工智能语音生成，并非真人录音。"
VIDEO_SECTION_START = "<!-- WEEKLY_VIDEO_START -->"
VIDEO_SECTION_END = "<!-- WEEKLY_VIDEO_END -->"
_CAPTION_BREAK = re.compile(r"(?<=[。！？；])")
TTS_INSTRUCTIONS = (
    "Use natural, professional Standard Mandarin. Sound like a senior AI "
    "engineering educator: calm, precise, conversational, and energetic "
    "at key contrasts. Preserve English technical terms and code identifiers, "
    "use short pauses between ideas, and never sound like a commercial."
)


@dataclass(frozen=True)
class VideoConfig:
    director_model: str = "gpt-5.4"
    tts_model: str = "gpt-4o-mini-tts"
    voice: str = "cedar"
    fps: int = 30
    width: int = 1920
    height: int = 1080
    tail_padding_seconds: float = 0.8


@dataclass(frozen=True)
class EditionContext:
    edition: WeeklyEdition
    score_by_id: dict[str, float]
    candidate_count: int
    approved_count: int


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _edition_digest(context: EditionContext) -> str:
    payload = {
        "edition": context.edition.model_dump(mode="json"),
        "scores": context.score_by_id,
        "candidate_count": context.candidate_count,
        "approved_count": context.approved_count,
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_edition_context(edition_dir: Path) -> EditionContext:
    manifest_path = edition_dir / "manifest.json"
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    edition_data = raw["edition"]

    # Editions generated before the Remotion migration used a NotebookLM-specific
    # field. Convert it only in memory so historical manifests remain immutable.
    for topic in edition_data.get("topics", []):
        if "video_direction" not in topic and "notebooklm_steering_prompt" in topic:
            topic["video_direction"] = topic["notebooklm_steering_prompt"]

    edition = WeeklyEdition.model_validate(edition_data)
    score_by_id: dict[str, float] = {}
    for item in raw.get("approved", []):
        evaluation = Evaluation.model_validate(item["evaluation"])
        score_by_id[item["candidate"]["candidate_id"]] = evaluation.weighted_score
    return EditionContext(
        edition=edition,
        score_by_id=score_by_id,
        candidate_count=int(raw.get("candidate_count", len(raw.get("candidates", [])))),
        approved_count=len(raw.get("approved", [])),
    )


def validate_video_plan(plan: VideoPlan, context: EditionContext) -> None:
    edition = context.edition
    if (plan.window_start, plan.window_end) != (
        edition.window_start,
        edition.window_end,
    ):
        raise ValueError("video director changed the edition reporting window")

    allowed_topic_ids = {topic.candidate_id for topic in edition.topics}
    global_kinds = {
        VideoSceneKind.INTRO,
        VideoSceneKind.FUNNEL,
        VideoSceneKind.DECISION,
    }
    for scene in plan.scenes:
        if scene.kind in global_kinds and scene.topic_id is not None:
            raise ValueError(f"global scene {scene.scene_id} must not have a topic_id")
        if scene.kind not in global_kinds and scene.topic_id not in allowed_topic_ids:
            raise ValueError(f"scene {scene.scene_id} has an unapproved topic_id")

    for topic_id in allowed_topic_ids:
        kinds = {scene.kind for scene in plan.scenes if scene.topic_id == topic_id}
        if VideoSceneKind.PROBLEM not in kinds:
            raise ValueError(f"topic {topic_id} has no problem scene")
        if VideoSceneKind.MECHANISM not in kinds:
            raise ValueError(f"topic {topic_id} has no mechanism scene")
        if not ({VideoSceneKind.DEMO, VideoSceneKind.EVIDENCE} & kinds):
            raise ValueError(f"topic {topic_id} has no demo or evidence scene")


def ensure_ai_voice_disclosure(plan: VideoPlan) -> VideoPlan:
    payload = plan.model_dump(mode="json")
    payload["disclosure"] = AI_VOICE_DISCLOSURE
    first_narration = payload["scenes"][0]["narration"]
    if not first_narration.startswith(AI_VOICE_DISCLOSURE):
        available = 480 - len(AI_VOICE_DISCLOSURE) - 1
        payload["scenes"][0]["narration"] = (
            f"{AI_VOICE_DISCLOSURE}{first_narration[:available]}"
        )
    return VideoPlan.model_validate(payload)


def normalize_global_scene_topic_ids(plan: VideoPlan) -> VideoPlan:
    """Remove harmless topic associations from edition-level scenes.

    Structured generation can occasionally attach the last discussed topic to
    the decision guide. These scene kinds are edition-level by definition, so
    clearing the association is deterministic and does not relax the allowlist
    for topic-specific scenes.
    """
    payload = plan.model_dump(mode="json")
    global_kinds = {
        VideoSceneKind.INTRO.value,
        VideoSceneKind.FUNNEL.value,
        VideoSceneKind.DECISION.value,
    }
    for scene in payload["scenes"]:
        if scene["kind"] in global_kinds:
            scene["topic_id"] = None
    return VideoPlan.model_validate(payload)


class VideoDirector:
    def __init__(self, client: OpenAI, config: VideoConfig) -> None:
        self.client = client
        self.config = config

    def create_plan(self, context: EditionContext) -> VideoPlan:
        edition = context.edition
        payload = {
            "candidate_count": context.candidate_count,
            "approved_count": context.approved_count,
            "scores": context.score_by_id,
            "edition": edition.model_dump(mode="json"),
        }
        response = self.client.responses.parse(
            model=self.config.director_model,
            instructions=VIDEO_DIRECTOR_INSTRUCTIONS,
            input=(
                "Create the source-grounded Remotion video plan from this approved "
                f"edition:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
            ),
            text_format=VideoPlan,
            store=False,
        )
        if response.output_parsed is None:
            raise RuntimeError("video director returned no structured output")
        plan = normalize_global_scene_topic_ids(
            ensure_ai_voice_disclosure(response.output_parsed)
        )
        validate_video_plan(plan, context)
        return plan


def split_caption_chunks(text: str, *, max_chars: int = 34) -> list[str]:
    chunks: list[str] = []
    for sentence in _CAPTION_BREAK.split(text.strip()):
        sentence = sentence.strip()
        while len(sentence) > max_chars:
            split_at = max(
                sentence.rfind("，", 0, max_chars + 1),
                sentence.rfind(",", 0, max_chars + 1),
                sentence.rfind(" ", 0, max_chars + 1),
            )
            if split_at < max_chars // 2:
                split_at = max_chars
            chunks.append(sentence[:split_at].strip("，, "))
            sentence = sentence[split_at:].lstrip("，, ")
        if sentence:
            chunks.append(sentence)
    return chunks or [text]


def wav_duration_seconds(path: Path) -> float:
    """Return duration from actual WAV payload bytes.

    Streaming WAV encoders may put ``0xFFFFFFFF`` in the RIFF and data chunk
    sizes because the final length is unknown when the header is emitted. The
    stdlib ``wave`` module exposes that sentinel as a huge frame count, so walk
    the chunks and cap the data length at the bytes actually present on disk.
    """
    file_size = path.stat().st_size
    with path.open("rb") as wav_file:
        header = wav_file.read(12)
        if len(header) != 12 or header[:4] not in {b"RIFF", b"RF64"}:
            raise ValueError(f"unsupported WAV header: {path}")
        if header[8:] != b"WAVE":
            raise ValueError(f"invalid WAV container: {path}")

        byte_rate: int | None = None
        while wav_file.tell() + 8 <= file_size:
            chunk_id = wav_file.read(4)
            chunk_size_raw = wav_file.read(4)
            if len(chunk_size_raw) != 4:
                break
            chunk_size = struct.unpack("<I", chunk_size_raw)[0]
            chunk_start = wav_file.tell()

            if chunk_id == b"fmt ":
                fmt = wav_file.read(min(chunk_size, 16))
                if len(fmt) < 16:
                    raise ValueError(f"incomplete WAV fmt chunk: {path}")
                byte_rate = struct.unpack("<I", fmt[8:12])[0]
            elif chunk_id == b"data":
                if not byte_rate:
                    raise ValueError(f"WAV data chunk precedes fmt chunk: {path}")
                available_bytes = max(file_size - chunk_start, 0)
                data_bytes = (
                    available_bytes
                    if chunk_size == 0xFFFFFFFF
                    else min(chunk_size, available_bytes)
                )
                return data_bytes / byte_rate

            if chunk_size == 0xFFFFFFFF:
                break
            next_chunk = chunk_start + chunk_size + (chunk_size % 2)
            wav_file.seek(min(next_chunk, file_size))

    raise ValueError(f"WAV file has no readable data chunk: {path}")


def synthesize_scene_audio(
    client: OpenAI,
    *,
    plan: VideoPlan,
    output_dir: Path,
    config: VideoConfig,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, scene in enumerate(plan.scenes, start=1):
        audio_key = hashlib.sha256(
            json.dumps(
                {
                    "narration": scene.narration,
                    "model": config.tts_model,
                    "voice": config.voice,
                    "instructions": TTS_INSTRUCTIONS,
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:12]
        output_path = output_dir / f"{index:02d}-{scene.scene_id}-{audio_key}.wav"
        if output_path.exists() and wav_duration_seconds(output_path) > 0.5:
            paths.append(output_path)
            continue

        temporary_path = output_path.with_suffix(".tmp.wav")
        try:
            with client.audio.speech.with_streaming_response.create(
                model=config.tts_model,
                voice=config.voice,
                input=scene.narration,
                instructions=TTS_INSTRUCTIONS,
                response_format="wav",
            ) as response:
                response.stream_to_file(temporary_path)
            temporary_path.replace(output_path)
        finally:
            temporary_path.unlink(missing_ok=True)
        paths.append(output_path)
    return paths


def build_remotion_props(
    *,
    context: EditionContext,
    plan: VideoPlan,
    audio_paths: list[Path],
    public_root: Path,
    edition_key: str,
    config: VideoConfig,
) -> dict[str, Any]:
    if len(audio_paths) != len(plan.scenes):
        raise ValueError("every video scene must have exactly one audio file")

    start_frame = 0
    scene_props: list[dict[str, Any]] = []
    topic_index = {
        topic.candidate_id: index
        for index, topic in enumerate(context.edition.topics, start=1)
    }
    for scene, audio_path in zip(plan.scenes, audio_paths, strict=True):
        audio_seconds = wav_duration_seconds(audio_path)
        if not 0.5 < audio_seconds <= 180:
            raise ValueError(
                f"scene {scene.scene_id} has implausible audio duration: "
                f"{audio_seconds:.3f}s"
            )
        duration_in_frames = max(
            math.ceil((audio_seconds + config.tail_padding_seconds) * config.fps),
            config.fps * 4,
        )
        scene_props.append(
            {
                **scene.model_dump(mode="json"),
                "topicIndex": topic_index.get(scene.topic_id),
                "audioSrc": audio_path.relative_to(public_root).as_posix(),
                "audioDurationSeconds": round(audio_seconds, 3),
                "startFrame": start_frame,
                "durationInFrames": duration_in_frames,
                "captionChunks": split_caption_chunks(scene.narration),
            }
        )
        start_frame += duration_in_frames

    return {
        "editionDate": edition_key,
        "windowStart": str(plan.window_start),
        "windowEnd": str(plan.window_end),
        "title": plan.title,
        "subtitle": plan.subtitle,
        "disclosure": plan.disclosure,
        "candidateCount": context.candidate_count,
        "approvedCount": len(context.edition.topics),
        "fps": config.fps,
        "width": config.width,
        "height": config.height,
        "totalDurationInFrames": start_frame,
        "scenes": scene_props,
    }


def release_video_url(repository: str, edition_key: str) -> str:
    file_name = f"ai-weekly-{edition_key}-zh.mp4"
    return (
        f"https://github.com/{repository}/releases/download/"
        f"weekly-{edition_key}/{file_name}"
    )


def prepare_video(
    *,
    client: OpenAI,
    edition_dir: Path,
    public_root: Path,
    config: VideoConfig,
    repository: str | None = None,
    regenerate_plan: bool = False,
) -> dict[str, Any]:
    context = load_edition_context(edition_dir)
    edition_sha256 = _edition_digest(context)
    plan_path = edition_dir / "video-plan.json"
    manifest_path = edition_dir / "video-manifest.json"
    previous_manifest: dict[str, Any] = {}
    if manifest_path.exists():
        previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    reuse_plan = (
        plan_path.exists()
        and not regenerate_plan
        and previous_manifest.get("edition_sha256") == edition_sha256
    )
    if reuse_plan:
        plan = VideoPlan.model_validate_json(plan_path.read_text(encoding="utf-8"))
        validate_video_plan(plan, context)
    else:
        plan = VideoDirector(client, config).create_plan(context)
        _write_json(plan_path, plan.model_dump(mode="json"))

    audio_dir = public_root / "generated" / edition_dir.name
    audio_paths = synthesize_scene_audio(
        client, plan=plan, output_dir=audio_dir, config=config
    )
    props = build_remotion_props(
        context=context,
        plan=plan,
        audio_paths=audio_paths,
        public_root=public_root,
        edition_key=edition_dir.name,
        config=config,
    )
    props_path = edition_dir / "remotion-props.json"
    _write_json(props_path, props)

    video_url = release_video_url(repository, edition_dir.name) if repository else None
    manifest = {
        "status": "prepared",
        "edition_sha256": edition_sha256,
        "video_url": video_url,
        "video_file": f"ai-weekly-{edition_dir.name}-zh.mp4",
        "duration_seconds": round(props["totalDurationInFrames"] / config.fps, 2),
        "scene_count": len(plan.scenes),
        "director_model": config.director_model,
        "tts_model": config.tts_model,
        "tts_voice": config.voice,
        "ai_voice_disclosure": AI_VOICE_DISCLOSURE,
        "remotion": {
            "composition": "WeeklyAI",
            "fps": config.fps,
            "width": config.width,
            "height": config.height,
            "props": props_path.name,
        },
    }
    _write_json(manifest_path, manifest)
    return {
        "plan": str(plan_path),
        "props": str(props_path),
        "manifest": str(manifest_path),
        "audio_dir": str(audio_dir),
        "video_url": video_url,
    }


def finalize_video_delivery(
    *,
    edition_dir: Path,
    video_path: Path,
    video_url: str,
) -> dict[str, Any]:
    manifest_path = edition_dir / "video-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        status="rendered",
        video_url=video_url,
        video_file=video_path.name,
        video_bytes=video_path.stat().st_size,
        sha256=_sha256_file(video_path),
    )
    _write_json(manifest_path, manifest)

    weekly_path = edition_dir / "weekly-update.md"
    weekly = weekly_path.read_text(encoding="utf-8")
    section = "\n".join(
        [
            VIDEO_SECTION_START,
            "## 教学视频",
            "",
            f"[观看 Remotion 教学视频]({video_url})",
            "",
            f"> {AI_VOICE_DISCLOSURE}",
            VIDEO_SECTION_END,
        ]
    )
    if VIDEO_SECTION_START in weekly and VIDEO_SECTION_END in weekly:
        prefix, remainder = weekly.split(VIDEO_SECTION_START, maxsplit=1)
        _, suffix = remainder.split(VIDEO_SECTION_END, maxsplit=1)
        weekly = f"{prefix}{section}{suffix}"
    else:
        weekly = weekly.rstrip() + "\n\n" + section + "\n"
    weekly_path.write_text(weekly, encoding="utf-8")
    return manifest
