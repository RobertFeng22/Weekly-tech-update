from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from .models import CandidateBatch, EvaluatedCandidate, EvaluationBatch, WeeklyEdition

if TYPE_CHECKING:
    from .pipeline import PipelineConfig


def _links(urls: list[object]) -> str:
    return "\n".join(f"- {url}" for url in urls)


def render_weekly_update(edition: WeeklyEdition, score_by_id: dict[str, float]) -> str:
    sections = [
        f"# AI Weekly · {edition.window_start} — {edition.window_end}",
        "",
        edition.editorial_note,
    ]
    for index, topic in enumerate(edition.topics, start=1):
        sections.extend(
            [
                "",
                f"## {index}. {topic.title}",
                "",
                f"**价值：** {topic.one_sentence_value}",
                "",
                f"**Evaluation score：** {score_by_id[topic.candidate_id]:.1f}/100",
                "",
                "### 为什么是现在",
                "",
                topic.why_now,
                "",
                "### 教学",
                "",
                topic.lesson,
                "",
                "### Hands-on demo",
                "",
                *[f"{i}. {step}" for i, step in enumerate(topic.hands_on_demo, start=1)],
                "",
                "### 适用 / 不适用",
                "",
                "适用：",
                *[f"- {item}" for item in topic.when_to_use],
                "",
                "不适用：",
                *[f"- {item}" for item in topic.when_not_to_use],
                "",
                "### Caveats",
                "",
                *[f"- {item}" for item in topic.caveats],
                "",
                "### Sources",
                "",
                _links(topic.source_urls),
            ]
        )
    return "\n".join(sections).strip() + "\n"


def render_notebooklm_source(edition: WeeklyEdition, score_by_id: dict[str, float]) -> str:
    sections = [
        f"# NotebookLM Source Pack: AI Weekly {edition.window_start} — {edition.window_end}",
        "",
        "本文件只包含通过证据门槛的主题。生成 Video Overview 时，要求所有事实仅来自本文件及所列 primary sources。",
    ]
    for index, topic in enumerate(edition.topics, start=1):
        sections.extend(
            [
                "",
                f"## Topic {index}: {topic.title}",
                "",
                f"Evaluation score: {score_by_id[topic.candidate_id]:.1f}/100",
                "",
                topic.one_sentence_value,
                "",
                topic.why_now,
                "",
                topic.lesson,
                "",
                "### Demo script",
                *[f"{i}. {step}" for i, step in enumerate(topic.hands_on_demo, start=1)],
                "",
                "### Limitations",
                *[f"- {item}" for item in topic.caveats],
                "",
                "### Source URLs",
                _links(topic.source_urls),
                "",
                "### Video steering prompt",
                topic.notebooklm_steering_prompt,
            ]
        )
    return "\n".join(sections).strip() + "\n"


def write_outputs(
    output_dir: Path,
    *,
    edition: WeeklyEdition,
    candidates: CandidateBatch,
    evaluations: EvaluationBatch,
    approved: list[EvaluatedCandidate],
    gate_results: list[dict[str, object]],
    config: "PipelineConfig",
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    score_by_id = {
        item.candidate.candidate_id: item.evaluation.weighted_score for item in approved
    }
    (output_dir / "weekly-update.md").write_text(
        render_weekly_update(edition, score_by_id), encoding="utf-8"
    )
    (output_dir / "notebooklm-source.md").write_text(
        render_notebooklm_source(edition, score_by_id), encoding="utf-8"
    )
    manifest = {
        "edition": edition.model_dump(mode="json"),
        "candidates": candidates.model_dump(mode="json")["candidates"],
        "evaluations": evaluations.model_dump(mode="json")["evaluations"],
        "approved": [item.model_dump(mode="json") for item in approved],
        "gate_results": gate_results,
        "candidate_count": len(candidates.candidates),
        "evaluation_count": len(evaluations.evaluations),
        "configuration": {
            "max_topics": config.max_topics,
            "minimum_score": config.minimum_score,
            "minimum_verified_sources": config.minimum_verified_sources,
            "discovery_model": config.discovery_model,
            "evaluation_model": config.evaluation_model,
            "editor_model": config.editor_model,
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_failure_audit(
    output_dir: Path,
    *,
    window_start: object,
    window_end: object,
    candidates: CandidateBatch,
    evaluations: EvaluationBatch,
    gate_results: list[dict[str, object]],
    config: "PipelineConfig",
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "status": "failed_no_candidate_passed",
        "window_start": str(window_start),
        "window_end": str(window_end),
        "candidates": candidates.model_dump(mode="json")["candidates"],
        "evaluations": evaluations.model_dump(mode="json")["evaluations"],
        "gate_results": gate_results,
        "configuration": {
            "max_topics": config.max_topics,
            "minimum_score": config.minimum_score,
            "minimum_verified_sources": config.minimum_verified_sources,
            "discovery_model": config.discovery_model,
            "evaluation_model": config.evaluation_model,
            "editor_model": config.editor_model,
        },
    }
    (output_dir / "failed-run-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
