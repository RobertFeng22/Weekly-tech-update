import wave
from datetime import date
from pathlib import Path

import pytest

from weekly_tech_update.models import (
    Category,
    Topic,
    VideoAccent,
    VideoPlan,
    VideoScene,
    VideoSceneKind,
    WeeklyEdition,
)
from weekly_tech_update.video import (
    AI_VOICE_DISCLOSURE,
    EditionContext,
    VideoConfig,
    build_remotion_props,
    ensure_ai_voice_disclosure,
    normalize_global_scene_topic_ids,
    release_video_url,
    split_caption_chunks,
    validate_video_plan,
    wav_duration_seconds,
)


def _topic() -> Topic:
    return Topic(
        candidate_id="topic-1",
        title="A source-grounded engineering topic",
        category=Category.ENGINEERING,
        one_sentence_value="这是一个可以在下周直接设计实验验证的工程机制。",
        why_now="它在本周首次发布了可运行实现、明确的验证边界与可以复用的实验步骤，因此值得及时学习并在自己的工作负载上复测。",
        lesson="机制解释必须足够完整。" * 20,
        hands_on_demo=["建立 baseline", "运行 treatment", "比较结果"],
        when_to_use=["延迟是主要瓶颈"],
        when_not_to_use=["缺少可比 baseline"],
        caveats=["当前证据仍然有限"],
        source_urls=["https://example.com/source"],
        video_direction=(
            "解释问题、机制、实验步骤、失败条件和证据边界，并避免把作者数据当作独立复现。"
            "画面应该使用流程图、baseline 对比、实验步骤和限制卡片，所有事实只能来自 approved edition。"
        ),
    )


def _context() -> EditionContext:
    edition = WeeklyEdition(
        window_start=date(2026, 8, 19),
        window_end=date(2026, 8, 25),
        editorial_note=(
            "本期只保留了通过证据与实用价值硬门槛的工程主题，并要求每个结论保留来源、"
            "适用条件、失败模式和可以在团队内部复现的最小实验。"
        ),
        topics=[_topic()],
    )
    return EditionContext(
        edition=edition,
        score_by_id={"topic-1": 82.4},
        candidate_count=9,
        approved_count=1,
    )


def _scene(scene_id: str, kind: VideoSceneKind, topic_id: str | None) -> VideoScene:
    return VideoScene(
        scene_id=scene_id,
        topic_id=topic_id,
        kind=kind,
        accent=VideoAccent.CYAN,
        eyebrow="EVIDENCE-GATED",
        title=f"Scene {scene_id}",
        subtitle="这是一条用于测试 Remotion 动态画面结构的简短副标题。",
        narration="这段旁白只引用已经通过筛选的材料，并用自然的中文解释机制、实验和限制。" * 4,
        on_screen_points=["问题", "机制", "验证"],
        visual_labels=["Baseline", "Change", "Measure"],
    )


def _plan() -> VideoPlan:
    scenes = [
        _scene("intro", VideoSceneKind.INTRO, None),
        _scene("funnel", VideoSceneKind.FUNNEL, None),
        _scene("problem", VideoSceneKind.PROBLEM, "topic-1"),
        _scene("mechanism", VideoSceneKind.MECHANISM, "topic-1"),
        _scene("demo", VideoSceneKind.DEMO, "topic-1"),
        _scene("limits", VideoSceneKind.EVIDENCE, "topic-1"),
        _scene("recap", VideoSceneKind.EVIDENCE, "topic-1"),
        _scene("decision", VideoSceneKind.DECISION, None),
    ]
    return VideoPlan(
        window_start=date(2026, 8, 19),
        window_end=date(2026, 8, 25),
        title="AI Weekly",
        subtitle="Evidence-gated lessons for AI engineers",
        disclosure="旁白将由人工智能语音生成，并在画面中持续披露。",
        scenes=scenes,
    )


def _write_silent_wav(path: Path, seconds: float = 1.0) -> None:
    sample_rate = 24_000
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * int(sample_rate * seconds))


def test_caption_chunks_are_short_and_complete():
    text = "第一句解释机制。第二句包含更多细节，并且需要被拆分成便于阅读的字幕内容。"
    chunks = split_caption_chunks(text, max_chars=16)
    assert all(len(chunk) <= 16 for chunk in chunks)
    assert "".join(chunks).replace("，", "") == text.replace("，", "")


def test_video_plan_requires_grounded_topic_ids():
    plan = _plan()
    validate_video_plan(plan, _context())
    payload = plan.model_dump(mode="json")
    payload["scenes"][2]["topic_id"] = "unknown-topic"
    with pytest.raises(ValueError, match="unapproved topic_id"):
        validate_video_plan(VideoPlan.model_validate(payload), _context())


def test_disclosure_is_forced_into_intro_narration():
    plan = ensure_ai_voice_disclosure(_plan())
    assert plan.disclosure == AI_VOICE_DISCLOSURE
    assert plan.scenes[0].narration.startswith(AI_VOICE_DISCLOSURE)


def test_global_scene_topic_ids_are_normalized_without_relaxing_topic_allowlist():
    payload = _plan().model_dump(mode="json")
    payload["scenes"][-1]["topic_id"] = "topic-1"
    plan = normalize_global_scene_topic_ids(VideoPlan.model_validate(payload))
    assert plan.scenes[-1].topic_id is None
    validate_video_plan(plan, _context())


def test_wav_duration_drives_remotion_timeline(tmp_path: Path):
    public_root = tmp_path / "public"
    audio_dir = public_root / "generated" / "2026-08-26"
    audio_dir.mkdir(parents=True)
    audio_paths = []
    for index in range(8):
        path = audio_dir / f"{index}.wav"
        _write_silent_wav(path, seconds=1.0 + index / 10)
        audio_paths.append(path)

    assert wav_duration_seconds(audio_paths[0]) == pytest.approx(1.0)
    props = build_remotion_props(
        context=_context(),
        plan=_plan(),
        audio_paths=audio_paths,
        public_root=public_root,
        edition_key="2026-08-26",
        config=VideoConfig(),
    )
    assert props["scenes"][0]["audioSrc"].startswith("generated/2026-08-26/")
    assert props["scenes"][1]["startFrame"] == props["scenes"][0]["durationInFrames"]
    assert props["totalDurationInFrames"] == sum(
        scene["durationInFrames"] for scene in props["scenes"]
    )


def test_release_url_is_stable():
    assert release_video_url("RobertFeng22/Weekly-tech-update", "2026-08-26") == (
        "https://github.com/RobertFeng22/Weekly-tech-update/releases/download/"
        "weekly-2026-08-26/ai-weekly-2026-08-26-zh.mp4"
    )
