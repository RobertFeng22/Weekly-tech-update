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


_REJECTION_LABELS = {
    "outside_reporting_window": "不在本周窗口",
    "insufficient_verified_sources": "来源核验不足",
    "candidate_primary_source_not_reverified": "primary source 未复核",
    "admission_mode_not_supported": "admission route 不成立",
    "engineering_only": "仅有工程实现价值",
    "generic_relevance_only": "与 Neural Alpha 只有泛相关",
    "no_validated_current_priority_match": "未命中当前高权重 priority",
    "unresolved_red_flags": "存在未解决 red flag",
    "weighted_score_below_threshold": "总分未达门槛",
}


def _render_rejection_summary(gate_results: list[dict[str, object]]) -> str:
    counts: dict[str, int] = {}
    for result in gate_results:
        if result.get("approved"):
            continue
        reasons = result.get("rejection_reasons", [])
        if not isinstance(reasons, list):
            continue
        for reason in reasons:
            if not isinstance(reason, str):
                continue
            label = _REJECTION_LABELS.get(reason)
            if label is None:
                if reason.startswith("current_priority_relevance_below_"):
                    label = "当前 priority 相关性不足"
                elif reason.startswith("strategy_or_architecture_impact_below_"):
                    label = "strategy / architecture impact 不足"
                elif reason.startswith("relevance_path_quality_below_"):
                    label = "relevance path 不完整"
                elif reason.startswith("business_decision_value_below_"):
                    label = "缺少决策价值"
                elif reason.startswith("frontier_significance_below_"):
                    label = "frontier significance 不足"
                elif reason.startswith("transfer_readiness_below_"):
                    label = "不可直接转化为内部 evaluation"
                elif reason.startswith("strategic_constraint_magnitude_below_"):
                    label = "战略约束影响不足"
                else:
                    label = reason
            counts[label] = counts.get(label, 0) + 1
    if not counts:
        return "没有候选被 hard gates 淘汰。"
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:4]
    return "；".join(f"{label}（{count}）" for label, count in ranked) + "。"


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


def render_weekly_update(
    edition: WeeklyEdition,
    score_by_id: dict[str, float],
    *,
    candidate_count: int,
    approved_count: int,
    gate_results: list[dict[str, object]],
) -> str:
    sections = [
        f"# Neural Alpha AI 决策 Brief · {edition.window_start} — {edition.window_end}",
        "",
        (
            f"> 本周评估 {candidate_count} 个候选，{approved_count} 个通过 "
            f"hard gates，最终选择 {len(edition.topics)} 个主题。"
        ),
        f"> 主要淘汰原因：{_render_rejection_summary(gate_results)}",
        "",
        edition.editorial_note,
    ]
    for index, topic in enumerate(edition.topics, start=1):
        sections.extend(
            [
                "",
                f"## {index}. {topic.title}",
                "",
                f"**核心判断：** {topic.thesis}",
                "",
                f"**Evaluation score：** {score_by_id[topic.candidate_id]:.1f}/100",
                "",
                "**命中的 Neural Alpha priorities：** "
                + "、".join(f"`{priority_id}`" for priority_id in topic.neural_alpha_priority_ids),
                "",
                "### 发生了什么",
                "",
                topic.what_changed,
                "",
                "### 为什么影响 Neural Alpha",
                "",
                topic.why_it_matters,
                "",
                "### 建议下一步",
                "",
                topic.recommended_next_step,
                "",
                "### 观察信号",
                "",
                *[f"- {item}" for item in topic.what_to_watch],
                "",
                "### Evidence boundary",
                "",
                *[f"- {item}" for item in topic.evidence_boundaries],
                "",
                "### Sources",
                "",
                _links(topic.source_urls),
            ]
        )
    sections.extend(
        [
            "",
            "## 本周组合判断",
            "",
            edition.portfolio_judgment,
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
        render_weekly_update(
            edition,
            score_by_id,
            candidate_count=len(candidates.candidates),
            approved_count=len(approved),
            gate_results=gate_results,
        ),
        encoding="utf-8",
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
