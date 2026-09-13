import struct
import wave
from datetime import date
from pathlib import Path

import pytest

from weekly_tech_update.models import (
    Category,
    NeuralAlphaPriorityId,
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
        title="A source-grounded capability frontier topic",
        category=Category.CAPABILITY,
        one_sentence_value="这项进展改变了复杂知识工作的可靠性边界，值得重新评估。",
        why_now="它在本周首次发布了可核验结果、明确的验证边界和可以复测的评估方法，因此值得及时纳入业务与投资判断。",
        capability_boundary_change=(
            "此前系统在跨来源推理中频繁失去证据链，这项进展显示它在受控条件下可以保持更完整的来源对应关系。"
        ),
        neural_alpha_priority_ids=[NeuralAlphaPriorityId.AGENTIC_RESEARCH],
        neural_alpha_impact_chain=(
            "如果独立复测成立，AI-native fund 可以把更多研究步骤交给系统，同时用明确审计点保留人类判断和风险控制。"
            "这会影响研究覆盖面的上限、分析师分工方式，以及机构应该把资源投入数据、evaluation 还是更多人工复核。"
        ),
        business_brief=(
            "关键不是某个工程组件变快，而是复杂知识工作从无法稳定委托，转向可以在有限边界内进行受控验证。"
            "对投资机构而言，这可能改变研究覆盖面、事件解释速度和分析师与 agent 的分工，但作者结果不能直接等同于真实投资环境。"
            "决策者应先定义内部高价值任务和失败成本，再建立与人工 baseline 对照的评估，记录来源完整性、错误类型和需要升级给人的节点。"
            "只有当质量、速度和可审计性同时改善，才值得扩大部署；否则这仍然只是值得跟踪的能力信号。"
        ),
        decision_takeaways=["定义内部高价值评估任务", "与人工 baseline 做盲测"],
        what_to_watch=["独立复现能否保持效果", "真实研究任务中的错误分布"],
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
            "本期只保留了同时通过证据、AI 能力边界和 AI-native fund 相关性门槛的主题，"
            "并要求每个结论保留来源、决策含义、失败模式和后续观察信号。"
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
        subtitle="Evidence-gated frontier briefing for an AI-native fund",
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


def test_streaming_wav_sentinel_uses_actual_payload_size(tmp_path: Path):
    path = tmp_path / "streaming.wav"
    _write_silent_wav(path, seconds=1.25)
    payload = bytearray(path.read_bytes())
    assert payload[36:40] == b"data"
    payload[4:8] = struct.pack("<I", 0xFFFFFFFF)
    payload[40:44] = struct.pack("<I", 0xFFFFFFFF)
    path.write_bytes(payload)
    assert wav_duration_seconds(path) == pytest.approx(1.25)


def test_release_url_is_stable():
    assert release_video_url("RobertFeng22/Weekly-tech-update", "2026-08-26") == (
        "https://github.com/RobertFeng22/Weekly-tech-update/releases/download/"
        "weekly-2026-08-26/ai-weekly-2026-08-26-zh.mp4"
    )
