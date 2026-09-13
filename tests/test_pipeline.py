import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from weekly_tech_update.models import (
    ActionType,
    AdmissionMode,
    Candidate,
    CandidateBatch,
    Category,
    Evaluation,
    EvaluationBatch,
    ImpactType,
    NeuralAlphaPriorityId,
    VideoPlan,
    WeeklyEdition,
)
from weekly_tech_update.pipeline import (
    PipelineConfig,
    apply_hard_gates,
    gate_rejection_reasons,
    load_selection_context,
    validate_selection_context_freshness,
    weekly_window,
)
from weekly_tech_update.render import write_failure_audit


CONTEXT_FIXTURE = Path("config/neural-alpha-selection-context.example.json")


def relevance_path(
    priority_id: NeuralAlphaPriorityId = NeuralAlphaPriorityId.AGENTIC_RESEARCH,
):
    return {
        "priority_id": priority_id,
        "impact_type": ImpactType.EVALUATION_METHOD,
        "action_type": ActionType.RUN_EVALUATION,
        "current_constraint": (
            "Current agent research quality needs task-level failure accounting."
        ),
        "external_delta": "The release provides a new source-grounded evaluation and baseline.",
        "transmission_mechanism": (
            "Its task and error taxonomy can be transferred into the existing "
            "dataset evaluation contract."
        ),
        "decision_or_test": (
            "Run a bounded comparison against the current single-agent research "
            "baseline."
        ),
    }


def candidate(**overrides):
    data = {
        "candidate_id": "item-1",
        "title": "A meaningful new capability boundary",
        "category": Category.CAPABILITY,
        "published_at": "2026-08-20",
        "summary": "A verified capability change with a measurable effect on knowledge work.",
        "novelty": "It crosses a previously documented reliability boundary.",
        "admission_mode": AdmissionMode.FRONTIER_SHIFT,
        "capability_delta": (
            "The system can now complete a decision-relevant task that previously "
            "failed."
        ),
        "neural_alpha_relevance": (
            "The method directly tests Neural Alpha's source-grounded agent research "
            "and control priority."
        ),
        "relevance_paths": [relevance_path()],
        "decision_takeaways": ["Commission a source-grounded internal evaluation"],
        "limitations": ["Hardware dependent"],
        "source_urls": ["https://example.com/primary", "https://example.org/check"],
        "primary_source_urls": ["https://example.com/primary"],
    }
    data.update(overrides)
    return Candidate.model_validate(data)


def evaluation(**overrides):
    data = {
        "candidate_id": "item-1",
        "factual_accuracy": 5,
        "evidence_strength": 4,
        "frontier_significance": 5,
        "authoritative_primary_sufficient": False,
        "admission_mode_supported": True,
        "engineering_only": False,
        "generic_relevance_only": False,
        "validated_priority_ids": [NeuralAlphaPriorityId.AGENTIC_RESEARCH],
        "current_priority_relevance": 5,
        "strategy_impact": 3,
        "architecture_impact": 5,
        "relevance_path_quality": 5,
        "transfer_readiness": 5,
        "business_decision_value": 4,
        "strategic_magnitude": 4,
        "novelty": 4,
        "confidence": 4,
        "red_flags": [],
        "counter_evidence": ["Benefit shrinks on older accelerators"],
        "rationale": "Primary evidence and an independent reproduction support the narrow claim.",
        "verified_source_urls": [
            "https://example.com/primary",
            "https://example.org/check",
        ],
        "verified_primary_source_urls": ["https://example.com/primary"],
    }
    data.update(overrides)
    return Evaluation.model_validate(data)


def test_weekly_window_uses_seven_completed_days():
    assert weekly_window(date(2026, 8, 24)) == (date(2026, 8, 17), date(2026, 8, 23))


def test_hard_gates_approve_verified_high_value_candidate():
    approved = apply_hard_gates(
        [candidate()],
        [evaluation()],
        window_start=date(2026, 8, 17),
        window_end=date(2026, 8, 23),
        minimum_score=70,
        minimum_verified_sources=2,
    )
    assert [item.candidate.candidate_id for item in approved] == ["item-1"]


def test_hard_gates_reject_red_flags_and_out_of_window_items():
    common = dict(
        window_start=date(2026, 8, 17),
        window_end=date(2026, 8, 23),
        minimum_score=70,
        minimum_verified_sources=2,
    )
    assert not apply_hard_gates(
        [candidate()], [evaluation(red_flags=["No reproduction"])], **common
    )
    assert not apply_hard_gates(
        [candidate(published_at="2026-08-16")], [evaluation()], **common
    )


def test_complete_authoritative_primary_can_satisfy_source_gate():
    approved = apply_hard_gates(
        [
            candidate(
                source_urls=["https://example.com/primary"],
                primary_source_urls=["https://example.com/primary"],
            )
        ],
        [
            evaluation(
                authoritative_primary_sufficient=True,
                verified_source_urls=["https://example.com/primary"],
                verified_primary_source_urls=["https://example.com/primary"],
            )
        ],
        window_start=date(2026, 8, 17),
        window_end=date(2026, 8, 23),
        minimum_score=70,
        minimum_verified_sources=2,
    )
    assert [item.candidate.candidate_id for item in approved] == ["item-1"]


def test_single_primary_exception_fails_when_evidence_is_not_strong():
    reasons = gate_rejection_reasons(
        candidate(
            source_urls=["https://example.com/primary"],
            primary_source_urls=["https://example.com/primary"],
        ),
        evaluation(
            evidence_strength=3,
            authoritative_primary_sufficient=True,
            verified_source_urls=["https://example.com/primary"],
            verified_primary_source_urls=["https://example.com/primary"],
        ),
        window_start=date(2026, 8, 17),
        window_end=date(2026, 8, 23),
        minimum_score=70,
        minimum_verified_sources=2,
    )
    assert "insufficient_verified_sources" in reasons


def test_narrow_engineering_update_fails_audience_fit_gates():
    reasons = gate_rejection_reasons(
        candidate(
            category=Category.ENGINEERING,
            admission_mode=AdmissionMode.DIRECT_BUILD_LEVERAGE,
        ),
        evaluation(
            frontier_significance=2,
            current_priority_relevance=1,
            strategy_impact=1,
            architecture_impact=1,
            relevance_path_quality=2,
            transfer_readiness=2,
            business_decision_value=2,
            engineering_only=True,
        ),
        window_start=date(2026, 8, 17),
        window_end=date(2026, 8, 23),
        minimum_score=70,
        minimum_verified_sources=2,
    )
    assert "current_priority_relevance_below_4" in reasons
    assert "strategy_or_architecture_impact_below_4" in reasons
    assert "relevance_path_quality_below_4" in reasons
    assert "transfer_readiness_below_4" in reasons
    assert "business_decision_value_below_3" in reasons
    assert "engineering_only" in reasons


def test_generic_copilot_governance_fails_without_a_current_priority_path():
    reasons = gate_rejection_reasons(
        candidate(
            title="Enterprise Copilot default-model routing",
            category=Category.GOVERNANCE,
            neural_alpha_relevance=(
                "A generic claim that every knowledge-work company should review "
                "its software defaults."
            ),
        ),
        evaluation(validated_priority_ids=[], generic_relevance_only=True),
        window_start=date(2026, 8, 17),
        window_end=date(2026, 8, 23),
        minimum_score=70,
        minimum_verified_sources=2,
    )
    assert "no_validated_current_priority_match" in reasons
    assert "generic_relevance_only" in reasons


def test_direct_build_leverage_can_pass_without_broad_frontier_shift():
    approved = apply_hard_gates(
        [candidate(admission_mode=AdmissionMode.DIRECT_BUILD_LEVERAGE)],
        [evaluation(frontier_significance=2, transfer_readiness=5)],
        window_start=date(2026, 8, 17),
        window_end=date(2026, 8, 23),
        minimum_score=70,
        minimum_verified_sources=2,
    )
    assert [item.candidate.candidate_id for item in approved] == ["item-1"]


def test_evaluator_cannot_validate_a_different_priority_than_the_candidate():
    reasons = gate_rejection_reasons(
        candidate(),
        evaluation(
            validated_priority_ids=[NeuralAlphaPriorityId.EXPECTATION_REPRICING]
        ),
        window_start=date(2026, 8, 17),
        window_end=date(2026, 8, 23),
        minimum_score=70,
        minimum_verified_sources=2,
    )
    assert "no_validated_current_priority_match" in reasons


def test_max_topics_cannot_exceed_three():
    try:
        PipelineConfig(max_topics=4)
    except ValueError as exc:
        assert "max_topics" in str(exc)
    else:
        raise AssertionError("expected max_topics validation to fail")


def test_audience_fit_thresholds_must_be_valid_scores():
    with pytest.raises(ValueError, match="minimum_current_priority_relevance"):
        PipelineConfig(minimum_current_priority_relevance=6)


def test_public_safe_selection_context_loads_and_excludes_watch_priorities():
    context = load_selection_context(
        CONTEXT_FIXTURE
    )
    eligible = context.eligible_priority_ids(minimum_weight=4)
    assert NeuralAlphaPriorityId.AGENTIC_RESEARCH in eligible
    assert NeuralAlphaPriorityId.FUND_OPERATIONS not in eligible


def test_watch_only_priority_cannot_pass_the_current_context_gate():
    context = load_selection_context(
        CONTEXT_FIXTURE
    )
    reasons = gate_rejection_reasons(
        candidate(
            relevance_paths=[
                relevance_path(NeuralAlphaPriorityId.FUND_OPERATIONS)
            ]
        ),
        evaluation(
            validated_priority_ids=[NeuralAlphaPriorityId.FUND_OPERATIONS]
        ),
        window_start=date(2026, 8, 17),
        window_end=date(2026, 8, 23),
        minimum_score=70,
        minimum_verified_sources=2,
        selection_context=context,
    )
    assert "no_validated_current_priority_match" in reasons


def test_stale_selection_context_fails_closed():
    context = load_selection_context(
        CONTEXT_FIXTURE
    )
    with pytest.raises(RuntimeError, match="refresh the reviewed snapshot"):
        validate_selection_context_freshness(
            context,
            as_of=date(2027, 1, 1),
            maximum_age_days=60,
        )


def test_failure_audit_freezes_selection_context_version_and_hash(tmp_path):
    context = load_selection_context(
        CONTEXT_FIXTURE
    )
    write_failure_audit(
        tmp_path,
        window_start=date(2026, 8, 17),
        window_end=date(2026, 8, 23),
        candidates=CandidateBatch(candidates=[candidate()]),
        evaluations=EvaluationBatch(evaluations=[evaluation()]),
        gate_results=[],
        config=PipelineConfig(),
        selection_context=context,
    )
    payload = json.loads((tmp_path / "failed-run-manifest.json").read_text())
    assert payload["selection_context"]["version"] == context.version
    assert len(payload["selection_context"]["sha256"]) == 64
    assert "snapshot" not in payload["selection_context"]


def test_openai_response_schemas_do_not_emit_unsupported_uri_format():
    for schema_type in (CandidateBatch, EvaluationBatch, WeeklyEdition, VideoPlan):
        schema_json = json.dumps(schema_type.model_json_schema())
        assert '"format": "uri"' not in schema_json


def test_source_urls_still_fail_closed_after_schema_compatibility_change():
    with pytest.raises(ValidationError, match="absolute HTTP\\(S\\) URL"):
        candidate(source_urls=["not-a-url"])
    with pytest.raises(ValidationError, match="must not contain credentials"):
        candidate(source_urls=["https://user:secret@example.com/source"])


def test_committed_historical_editions_remain_readable():
    for manifest_path in sorted(Path("editions").glob("*/manifest.json")):
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        CandidateBatch.model_validate({"candidates": payload["candidates"]})
        EvaluationBatch.model_validate({"evaluations": payload["evaluations"]})
        WeeklyEdition.model_validate(payload["edition"])


def test_gate_rejection_reasons_are_auditable():
    reasons = gate_rejection_reasons(
        candidate(published_at="2026-08-16"),
        evaluation(
            verified_source_urls=["https://example.com/primary"],
            red_flags=["Central claim contradicted"],
        ),
        window_start=date(2026, 8, 17),
        window_end=date(2026, 8, 23),
        minimum_score=70,
        minimum_verified_sources=2,
    )
    assert reasons == [
        "outside_reporting_window",
        "insufficient_verified_sources",
        "unresolved_red_flags",
    ]
