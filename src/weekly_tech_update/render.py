from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

from .models import (
    CandidateBatch,
    EvaluatedCandidate,
    EvaluationBatch,
    NeuralAlphaSelectionContext,
    WeeklyEdition,
)

if TYPE_CHECKING:
    from .pipeline import PipelineConfig


def _links(urls: list[object]) -> str:
    return "\n".join(f"- {url}" for url in urls)


def _selection_context_record(
    context: NeuralAlphaSelectionContext,
) -> dict[str, object]:
    snapshot = context.model_dump(mode="json")
    canonical = json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "version": context.version,
        "as_of": context.as_of.isoformat(),
        "sha256": hashlib.sha256(canonical).hexdigest(),
    }


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
                "### AI 能力边界发生了什么变化",
                "",
                topic.capability_boundary_change,
                "",
                "### 为什么是现在",
                "",
                topic.why_now,
                "",
                "### 命中的 Neural Alpha 当前 priorities",
                "",
                *[f"- `{priority_id}`" for priority_id in topic.neural_alpha_priority_ids],
                "",
                "### 对 Neural Alpha 的具体 impact chain",
                "",
                topic.neural_alpha_impact_chain,
                "",
                "### Business briefing",
                "",
                topic.business_brief,
                "",
                "### 决策与行动",
                "",
                *[f"- {item}" for item in topic.decision_takeaways],
                "",
                "### 接下来观察什么",
                "",
                *[f"- {item}" for item in topic.what_to_watch],
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


def render_video_source(edition: WeeklyEdition, score_by_id: dict[str, float]) -> str:
    sections = [
        f"# Remotion Video Source: AI Weekly {edition.window_start} — {edition.window_end}",
        "",
        (
            "本文件只包含通过证据门槛的主题。VideoPlan、OpenAI TTS 旁白与 "
            "Remotion 画面必须以本文件及 manifest 中的 verified evidence 为边界。"
        ),
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
                "### Capability boundary change",
                topic.capability_boundary_change,
                "",
                "### Why now",
                topic.why_now,
                "",
                "### Neural Alpha priority mapping",
                *[f"- `{priority_id}`" for priority_id in topic.neural_alpha_priority_ids],
                "",
                "### Neural Alpha impact chain",
                topic.neural_alpha_impact_chain,
                "",
                "### Business brief",
                topic.business_brief,
                "",
                "### Decisions and actions",
                *[f"- {item}" for item in topic.decision_takeaways],
                "",
                "### What to watch",
                *[f"- {item}" for item in topic.what_to_watch],
                "",
                "### Evidence limitations",
                *[f"- {item}" for item in topic.caveats],
                "",
                "### Source URLs",
                _links(topic.source_urls),
                "",
                "### Video direction",
                topic.video_direction,
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
    selection_context: NeuralAlphaSelectionContext,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    score_by_id = {
        item.candidate.candidate_id: item.evaluation.weighted_score for item in approved
    }
    (output_dir / "weekly-update.md").write_text(
        render_weekly_update(edition, score_by_id), encoding="utf-8"
    )
    (output_dir / "video-source.md").write_text(
        render_video_source(edition, score_by_id), encoding="utf-8"
    )
    manifest = {
        "edition": edition.model_dump(mode="json"),
        "candidates": candidates.model_dump(mode="json")["candidates"],
        "evaluations": evaluations.model_dump(mode="json")["evaluations"],
        "approved": [item.model_dump(mode="json") for item in approved],
        "gate_results": gate_results,
        "selection_context": _selection_context_record(selection_context),
        "candidate_count": len(candidates.candidates),
        "evaluation_count": len(evaluations.evaluations),
        "configuration": {
            "selection_profile": config.selection_profile,
            "max_topics": config.max_topics,
            "minimum_score": config.minimum_score,
            "minimum_verified_sources": config.minimum_verified_sources,
            "minimum_frontier_significance": config.minimum_frontier_significance,
            "minimum_current_priority_relevance": (
                config.minimum_current_priority_relevance
            ),
            "minimum_strategy_or_architecture_impact": (
                config.minimum_strategy_or_architecture_impact
            ),
            "minimum_relevance_path_quality": config.minimum_relevance_path_quality,
            "minimum_transfer_readiness": config.minimum_transfer_readiness,
            "minimum_strategic_constraint_magnitude": (
                config.minimum_strategic_constraint_magnitude
            ),
            "minimum_business_decision_value": (
                config.minimum_business_decision_value
            ),
            "minimum_priority_weight": config.minimum_priority_weight,
            "maximum_context_age_days": config.maximum_context_age_days,
            "discovery_max_tool_calls": config.discovery_max_tool_calls,
            "evaluation_max_tool_calls": config.evaluation_max_tool_calls,
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
    selection_context: NeuralAlphaSelectionContext,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "status": "failed_no_candidate_passed",
        "window_start": str(window_start),
        "window_end": str(window_end),
        "candidates": candidates.model_dump(mode="json")["candidates"],
        "evaluations": evaluations.model_dump(mode="json")["evaluations"],
        "gate_results": gate_results,
        "selection_context": _selection_context_record(selection_context),
        "configuration": {
            "selection_profile": config.selection_profile,
            "max_topics": config.max_topics,
            "minimum_score": config.minimum_score,
            "minimum_verified_sources": config.minimum_verified_sources,
            "minimum_frontier_significance": config.minimum_frontier_significance,
            "minimum_current_priority_relevance": (
                config.minimum_current_priority_relevance
            ),
            "minimum_strategy_or_architecture_impact": (
                config.minimum_strategy_or_architecture_impact
            ),
            "minimum_relevance_path_quality": config.minimum_relevance_path_quality,
            "minimum_transfer_readiness": config.minimum_transfer_readiness,
            "minimum_strategic_constraint_magnitude": (
                config.minimum_strategic_constraint_magnitude
            ),
            "minimum_business_decision_value": (
                config.minimum_business_decision_value
            ),
            "minimum_priority_weight": config.minimum_priority_weight,
            "maximum_context_age_days": config.maximum_context_age_days,
            "discovery_max_tool_calls": config.discovery_max_tool_calls,
            "evaluation_max_tool_calls": config.evaluation_max_tool_calls,
            "discovery_model": config.discovery_model,
            "evaluation_model": config.evaluation_model,
            "editor_model": config.editor_model,
        },
    }
    (output_dir / "failed-run-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
