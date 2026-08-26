from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from .models import (
    Candidate,
    CandidateBatch,
    EvaluatedCandidate,
    Evaluation,
    EvaluationBatch,
    WeeklyEdition,
)
from .prompts import DISCOVERY_INSTRUCTIONS, EDITOR_INSTRUCTIONS, EVALUATION_INSTRUCTIONS
from .render import write_failure_audit, write_outputs

SchemaT = TypeVar("SchemaT", bound=BaseModel)


@dataclass(frozen=True)
class PipelineConfig:
    discovery_model: str = "gpt-5.4"
    evaluation_model: str = "gpt-5.4"
    editor_model: str = "gpt-5.4"
    max_topics: int = 3
    minimum_score: float = 70.0
    minimum_verified_sources: int = 2

    def __post_init__(self) -> None:
        if not 1 <= self.max_topics <= 3:
            raise ValueError("max_topics must be between 1 and 3")


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
    if evaluation.red_flags:
        reasons.append("unresolved_red_flags")
    if evaluation.weighted_score < minimum_score:
        reasons.append("weighted_score_below_threshold")
    return reasons


class WeeklyPipeline:
    def __init__(self, client: OpenAI, config: PipelineConfig) -> None:
        self.client = client
        self.config = config

    def _parse(
        self,
        *,
        model: str,
        instructions: str,
        prompt: str,
        schema: type[SchemaT],
        use_web: bool,
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
                max_tool_calls=24,
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
                f"through {window_end.isoformat()}, inclusive. Use exact publication dates."
            ),
            schema=CandidateBatch,
            use_web=True,
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
                f"{window_end.isoformat()}. Candidate claims:\n"
                f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
            ),
            schema=EvaluationBatch,
            use_web=True,
        )

    def edit(
        self,
        approved: list[EvaluatedCandidate],
        window_start: date,
        window_end: date,
    ) -> WeeklyEdition:
        shortlist = approved[: max(self.config.max_topics * 2, self.config.max_topics)]
        if not shortlist:
            raise RuntimeError("no candidate passed the evidence and usefulness gates")
        edition = self._parse(
            model=self.config.editor_model,
            instructions=EDITOR_INSTRUCTIONS,
            prompt=(
                f"Create the edition for {window_start.isoformat()} through "
                f"{window_end.isoformat()}. Select no more than "
                f"{self.config.max_topics} topics from:\n"
                f"{json.dumps([item.model_dump(mode='json') for item in shortlist], ensure_ascii=False, indent=2)}"
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
        return edition

    def run(self, *, as_of: date, output_root: Path) -> Path:
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
                    )
                ),
                "rejection_reasons": reasons,
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
            )
            raise RuntimeError(
                "no candidate passed the evidence and usefulness gates; "
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
        )
        return edition_dir
