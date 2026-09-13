from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from .models import (
    AdmissionMode,
    Candidate,
    CandidateBatch,
    EvaluatedCandidate,
    Evaluation,
    EvaluationBatch,
    NeuralAlphaPriorityId,
    NeuralAlphaSelectionContext,
    WeeklyEdition,
)
from .prompts import DISCOVERY_INSTRUCTIONS, EDITOR_INSTRUCTIONS, EVALUATION_INSTRUCTIONS
from .render import write_failure_audit, write_outputs

SchemaT = TypeVar("SchemaT", bound=BaseModel)


@dataclass(frozen=True)
class PipelineConfig:
    selection_profile: str = "neural_alpha_contextual_intelligence_v2"
    discovery_model: str = "gpt-5.4"
    evaluation_model: str = "gpt-5.4"
    editor_model: str = "gpt-5.4"
    discovery_max_tool_calls: int = 24
    evaluation_max_tool_calls: int = 40
    max_topics: int = 3
    minimum_score: float = 70.0
    minimum_verified_sources: int = 2
    minimum_frontier_significance: int = 4
    minimum_current_priority_relevance: int = 4
    minimum_strategy_or_architecture_impact: int = 4
    minimum_relevance_path_quality: int = 4
    minimum_transfer_readiness: int = 4
    minimum_strategic_constraint_magnitude: int = 4
    minimum_business_decision_value: int = 3
    minimum_priority_weight: int = 4
    maximum_context_age_days: int = 60

    def __post_init__(self) -> None:
        if not 1 <= self.max_topics <= 3:
            raise ValueError("max_topics must be between 1 and 3")
        for field_name in (
            "minimum_frontier_significance",
            "minimum_current_priority_relevance",
            "minimum_strategy_or_architecture_impact",
            "minimum_relevance_path_quality",
            "minimum_transfer_readiness",
            "minimum_strategic_constraint_magnitude",
            "minimum_business_decision_value",
            "minimum_priority_weight",
        ):
            value = getattr(self, field_name)
            if not 0 <= value <= 5:
                raise ValueError(f"{field_name} must be between 0 and 5")
        if self.maximum_context_age_days < 1:
            raise ValueError("maximum_context_age_days must be positive")
        if self.discovery_max_tool_calls < 1 or self.evaluation_max_tool_calls < 1:
            raise ValueError("web-search tool-call budgets must be positive")


def load_selection_context(path: Path) -> NeuralAlphaSelectionContext:
    return NeuralAlphaSelectionContext.model_validate_json(path.read_text(encoding="utf-8"))


def validate_selection_context_freshness(
    context: NeuralAlphaSelectionContext,
    *,
    as_of: date,
    maximum_age_days: int,
) -> None:
    age_days = (as_of - context.as_of).days
    if age_days > maximum_age_days:
        raise RuntimeError(
            f"selection context {context.version} is {age_days} days old; "
            "refresh the reviewed snapshot from Neural Alpha's current strategy "
            "and architecture context before generating another edition"
        )


def weekly_window(as_of: date) -> tuple[date, date]:
    """Return the seven completed calendar days ending yesterday."""
    return as_of - timedelta(days=7), as_of - timedelta(days=1)


def _url_set(values: list[Any]) -> set[str]:
    return {str(value).rstrip("/") for value in values}


def apply_hard_gates(
    candidates: list[Candidate],
    evaluations: list[Evaluation],
    *,
    window_start: date,
    window_end: date,
    minimum_score: float,
    minimum_verified_sources: int,
    selection_context: NeuralAlphaSelectionContext | None = None,
    minimum_frontier_significance: int = 4,
    minimum_current_priority_relevance: int = 4,
    minimum_strategy_or_architecture_impact: int = 4,
    minimum_relevance_path_quality: int = 4,
    minimum_transfer_readiness: int = 4,
    minimum_strategic_constraint_magnitude: int = 4,
    minimum_business_decision_value: int = 3,
    minimum_priority_weight: int = 4,
) -> list[EvaluatedCandidate]:
    by_id = {evaluation.candidate_id: evaluation for evaluation in evaluations}
    approved: list[EvaluatedCandidate] = []
    for candidate in candidates:
        evaluation = by_id.get(candidate.candidate_id)
        reasons = gate_rejection_reasons(
            candidate,
            evaluation,
            window_start=window_start,
            window_end=window_end,
            minimum_score=minimum_score,
            minimum_verified_sources=minimum_verified_sources,
            selection_context=selection_context,
            minimum_frontier_significance=minimum_frontier_significance,
            minimum_current_priority_relevance=minimum_current_priority_relevance,
            minimum_strategy_or_architecture_impact=(
                minimum_strategy_or_architecture_impact
            ),
            minimum_relevance_path_quality=minimum_relevance_path_quality,
            minimum_transfer_readiness=minimum_transfer_readiness,
            minimum_strategic_constraint_magnitude=(
                minimum_strategic_constraint_magnitude
            ),
            minimum_business_decision_value=minimum_business_decision_value,
            minimum_priority_weight=minimum_priority_weight,
        )
        if reasons:
            continue
        assert evaluation is not None
        approved.append(EvaluatedCandidate(candidate=candidate, evaluation=evaluation))
    return sorted(approved, key=lambda item: item.evaluation.weighted_score, reverse=True)


def gate_rejection_reasons(
    candidate: Candidate,
    evaluation: Evaluation | None,
    *,
    window_start: date,
    window_end: date,
    minimum_score: float,
    minimum_verified_sources: int,
    selection_context: NeuralAlphaSelectionContext | None = None,
    minimum_frontier_significance: int = 4,
    minimum_current_priority_relevance: int = 4,
    minimum_strategy_or_architecture_impact: int = 4,
    minimum_relevance_path_quality: int = 4,
    minimum_transfer_readiness: int = 4,
    minimum_strategic_constraint_magnitude: int = 4,
    minimum_business_decision_value: int = 3,
    minimum_priority_weight: int = 4,
) -> list[str]:
    reasons: list[str] = []
    if evaluation is None:
        return ["missing_evaluation"]
    if not window_start <= candidate.published_at <= window_end:
        reasons.append("outside_reporting_window")
    verified = _url_set(evaluation.verified_source_urls)
    primary = _url_set(evaluation.verified_primary_source_urls)
    cited_primary = _url_set(candidate.primary_source_urls)
    if len(verified) < minimum_verified_sources:
        reasons.append("insufficient_verified_sources")
    if not primary or not (primary & cited_primary):
        reasons.append("candidate_primary_source_not_reverified")
    if evaluation.factual_accuracy < 4:
        reasons.append("factual_accuracy_below_4")
    if evaluation.evidence_strength < 3:
        reasons.append("evidence_strength_below_3")
    if not evaluation.admission_mode_supported:
        reasons.append("admission_mode_not_supported")
    if evaluation.engineering_only:
        reasons.append("engineering_only")
    if evaluation.generic_relevance_only:
        reasons.append("generic_relevance_only")

    candidate_priority_ids = {
        path.priority_id for path in candidate.relevance_paths
    }
    validated_priority_ids = set(evaluation.validated_priority_ids)
    eligible_priority_ids = (
        selection_context.eligible_priority_ids(minimum_priority_weight)
        if selection_context is not None
        else set(NeuralAlphaPriorityId)
    )
    matched_priority_ids = (
        candidate_priority_ids & validated_priority_ids & eligible_priority_ids
    )
    if not matched_priority_ids:
        reasons.append("no_validated_current_priority_match")

    if evaluation.current_priority_relevance < minimum_current_priority_relevance:
        reasons.append(
            f"current_priority_relevance_below_{minimum_current_priority_relevance}"
        )
    if (
        max(evaluation.strategy_impact, evaluation.architecture_impact)
        < minimum_strategy_or_architecture_impact
    ):
        reasons.append(
            "strategy_or_architecture_impact_below_"
            f"{minimum_strategy_or_architecture_impact}"
        )
    if evaluation.relevance_path_quality < minimum_relevance_path_quality:
        reasons.append(
            f"relevance_path_quality_below_{minimum_relevance_path_quality}"
        )
    if evaluation.business_decision_value < minimum_business_decision_value:
        reasons.append(
            f"business_decision_value_below_{minimum_business_decision_value}"
        )

    if (
        candidate.admission_mode is AdmissionMode.FRONTIER_SHIFT
        and evaluation.frontier_significance < minimum_frontier_significance
    ):
        reasons.append(
            f"frontier_significance_below_{minimum_frontier_significance}"
        )
    elif (
        candidate.admission_mode is AdmissionMode.DIRECT_BUILD_LEVERAGE
        and evaluation.transfer_readiness < minimum_transfer_readiness
    ):
        reasons.append(
            f"transfer_readiness_below_{minimum_transfer_readiness}"
        )
    elif (
        candidate.admission_mode is AdmissionMode.STRATEGIC_CONSTRAINT
        and evaluation.strategic_magnitude
        < minimum_strategic_constraint_magnitude
    ):
        reasons.append(
            "strategic_constraint_magnitude_below_"
            f"{minimum_strategic_constraint_magnitude}"
        )
    if evaluation.red_flags:
        reasons.append("unresolved_red_flags")
    if evaluation.weighted_score < minimum_score:
        reasons.append("weighted_score_below_threshold")
    return reasons


class WeeklyPipeline:
    def __init__(
        self,
        client: OpenAI,
        config: PipelineConfig,
        selection_context: NeuralAlphaSelectionContext,
    ) -> None:
        self.client = client
        self.config = config
        self.selection_context = selection_context

    def _selection_context_payload(self) -> str:
        return json.dumps(
            self.selection_context.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )

    def _parse(
        self,
        *,
        model: str,
        instructions: str,
        prompt: str,
        schema: type[SchemaT],
        use_web: bool,
        max_tool_calls: int = 24,
    ) -> SchemaT:
        kwargs: dict[str, Any] = {
            "model": model,
            "instructions": instructions,
            "input": prompt,
            "text_format": schema,
            "store": False,
        }
        if use_web:
            kwargs.update(
                tools=[{"type": "web_search"}],
                include=["web_search_call.action.sources"],
                max_tool_calls=max_tool_calls,
            )
        response = self.client.responses.parse(**kwargs)
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("model returned no structured output")
        return parsed

    def discover(self, window_start: date, window_end: date) -> CandidateBatch:
        return self._parse(
            model=self.config.discovery_model,
            instructions=DISCOVERY_INSTRUCTIONS,
            prompt=(
                f"Research AI developments published from {window_start.isoformat()} "
                f"through {window_end.isoformat()}, inclusive. Use exact publication dates.\n\n"
                "The following reviewed Neural Alpha context is authoritative for "
                "relevance. It is not evidence for external factual claims. Every "
                "candidate must map to at least one active priority with a complete "
                "relevance path:\n"
                f"{self._selection_context_payload()}"
            ),
            schema=CandidateBatch,
            use_web=True,
            max_tool_calls=self.config.discovery_max_tool_calls,
        )

    def evaluate(
        self, batch: CandidateBatch, window_start: date, window_end: date
    ) -> EvaluationBatch:
        payload = batch.model_dump(mode="json")
        return self._parse(
            model=self.config.evaluation_model,
            instructions=EVALUATION_INSTRUCTIONS,
            prompt=(
                f"Evaluation window: {window_start.isoformat()} through "
                f"{window_end.isoformat()}. Independently validate each claimed "
                "priority mapping against this authoritative private context. Do "
                "not reproduce its wording in publishable fields:\n"
                f"{self._selection_context_payload()}\n\nCandidate claims:\n"
                f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
            ),
            schema=EvaluationBatch,
            use_web=True,
            max_tool_calls=self.config.evaluation_max_tool_calls,
        )

    def edit(
        self,
        approved: list[EvaluatedCandidate],
        window_start: date,
        window_end: date,
    ) -> WeeklyEdition:
        shortlist = approved[: max(self.config.max_topics * 2, self.config.max_topics)]
        if not shortlist:
            raise RuntimeError("no candidate passed the evidence and Neural Alpha gates")
        shortlist_payload = json.dumps(
            [item.model_dump(mode="json") for item in shortlist],
            ensure_ascii=False,
            indent=2,
        )
        edition = self._parse(
            model=self.config.editor_model,
            instructions=EDITOR_INSTRUCTIONS,
            prompt=(
                f"Create the edition for {window_start.isoformat()} through "
                f"{window_end.isoformat()}. Select no more than "
                f"{self.config.max_topics} topics. Use this current Neural Alpha "
                "context to explain the exact strategy/architecture impact and do "
                "not generalize it into generic AI-fund relevance:\n"
                f"{self._selection_context_payload()}\n\nApproved candidates:\n"
                f"{shortlist_payload}"
            ),
            schema=WeeklyEdition,
            use_web=False,
        )
        if len(edition.topics) > self.config.max_topics:
            raise RuntimeError("editor exceeded configured topic limit")
        if (edition.window_start, edition.window_end) != (window_start, window_end):
            raise RuntimeError("editor changed the requested reporting window")
        allowed_ids = {item.candidate.candidate_id for item in shortlist}
        if any(topic.candidate_id not in allowed_ids for topic in edition.topics):
            raise RuntimeError("editor introduced a topic outside the approved shortlist")
        allowed_urls = {
            item.candidate.candidate_id: (
                _url_set(item.candidate.source_urls)
                | _url_set(item.evaluation.verified_source_urls)
            )
            for item in shortlist
        }
        for topic in edition.topics:
            if not _url_set(topic.source_urls) <= allowed_urls[topic.candidate_id]:
                raise RuntimeError("editor introduced an unverified source URL")
            item = next(
                item
                for item in shortlist
                if item.candidate.candidate_id == topic.candidate_id
            )
            allowed_priority_ids = {
                path.priority_id for path in item.candidate.relevance_paths
            } & set(item.evaluation.validated_priority_ids)
            if not set(topic.neural_alpha_priority_ids) <= allowed_priority_ids:
                raise RuntimeError(
                    "editor introduced an unvalidated Neural Alpha priority mapping"
                )
        return edition

    def run(self, *, as_of: date, output_root: Path) -> Path:
        validate_selection_context_freshness(
            self.selection_context,
            as_of=as_of,
            maximum_age_days=self.config.maximum_context_age_days,
        )
        window_start, window_end = weekly_window(as_of)
        candidates = self.discover(window_start, window_end)
        evaluations = self.evaluate(candidates, window_start, window_end)
        approved = apply_hard_gates(
            candidates.candidates,
            evaluations.evaluations,
            window_start=window_start,
            window_end=window_end,
            minimum_score=self.config.minimum_score,
            minimum_verified_sources=self.config.minimum_verified_sources,
            selection_context=self.selection_context,
            minimum_frontier_significance=self.config.minimum_frontier_significance,
            minimum_current_priority_relevance=(
                self.config.minimum_current_priority_relevance
            ),
            minimum_strategy_or_architecture_impact=(
                self.config.minimum_strategy_or_architecture_impact
            ),
            minimum_relevance_path_quality=self.config.minimum_relevance_path_quality,
            minimum_transfer_readiness=self.config.minimum_transfer_readiness,
            minimum_strategic_constraint_magnitude=(
                self.config.minimum_strategic_constraint_magnitude
            ),
            minimum_business_decision_value=(
                self.config.minimum_business_decision_value
            ),
            minimum_priority_weight=self.config.minimum_priority_weight,
        )
        evaluation_by_id = {
            evaluation.candidate_id: evaluation for evaluation in evaluations.evaluations
        }
        gate_results = [
            {
                "candidate_id": candidate.candidate_id,
                "approved": not (
                    reasons := gate_rejection_reasons(
                        candidate,
                        evaluation_by_id.get(candidate.candidate_id),
                        window_start=window_start,
                        window_end=window_end,
                        minimum_score=self.config.minimum_score,
                        minimum_verified_sources=self.config.minimum_verified_sources,
                        selection_context=self.selection_context,
                        minimum_frontier_significance=(
                            self.config.minimum_frontier_significance
                        ),
                        minimum_current_priority_relevance=(
                            self.config.minimum_current_priority_relevance
                        ),
                        minimum_strategy_or_architecture_impact=(
                            self.config.minimum_strategy_or_architecture_impact
                        ),
                        minimum_relevance_path_quality=(
                            self.config.minimum_relevance_path_quality
                        ),
                        minimum_transfer_readiness=(
                            self.config.minimum_transfer_readiness
                        ),
                        minimum_strategic_constraint_magnitude=(
                            self.config.minimum_strategic_constraint_magnitude
                        ),
                        minimum_business_decision_value=(
                            self.config.minimum_business_decision_value
                        ),
                        minimum_priority_weight=self.config.minimum_priority_weight,
                    )
                ),
                "rejection_reasons": reasons,
                "matched_priority_ids": sorted(
                    str(priority_id)
                    for priority_id in (
                        {path.priority_id for path in candidate.relevance_paths}
                        & set(
                            evaluation_by_id.get(candidate.candidate_id).validated_priority_ids
                            if evaluation_by_id.get(candidate.candidate_id)
                            else []
                        )
                        & self.selection_context.eligible_priority_ids(
                            self.config.minimum_priority_weight
                        )
                    )
                ),
            }
            for candidate in candidates.candidates
        ]
        edition_dir = output_root / as_of.isoformat()
        if not approved:
            write_failure_audit(
                edition_dir,
                window_start=window_start,
                window_end=window_end,
                candidates=candidates,
                evaluations=evaluations,
                gate_results=gate_results,
                config=self.config,
                selection_context=self.selection_context,
            )
            raise RuntimeError(
                "no candidate passed the evidence and Neural Alpha context gates; "
                f"see {edition_dir / 'failed-run-manifest.json'}"
            )
        edition = self.edit(approved, window_start, window_end)
        write_outputs(
            edition_dir,
            edition=edition,
            candidates=candidates,
            evaluations=evaluations,
            approved=approved,
            gate_results=gate_results,
            config=self.config,
            selection_context=self.selection_context,
        )
        return edition_dir
