import json
from datetime import date

import pytest
from pydantic import ValidationError

from weekly_tech_update.models import (
    Candidate,
    CandidateBatch,
    Category,
    Evaluation,
    EvaluationBatch,
    VideoPlan,
    WeeklyEdition,
)
from weekly_tech_update.pipeline import (
    PipelineConfig,
    apply_hard_gates,
    gate_rejection_reasons,
    weekly_window,
)


def candidate(**overrides):
    data = {
        "candidate_id": "item-1",
        "title": "A useful new inference technique",
        "category": Category.ENGINEERING,
        "published_at": "2026-08-20",
        "summary": "A concrete production technique with a measurable operational benefit.",
        "novelty": "It combines two mechanisms in a newly reproducible way.",
        "practitioner_value": "Teams can test it against their current serving stack next week.",
        "concrete_takeaways": ["Run the published benchmark"],
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
        "practical_value": 5,
        "novelty": 4,
        "transferability": 4,
        "teachability": 5,
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
    assert not apply_hard_gates([candidate()], [evaluation(red_flags=["No reproduction"])], **common)
    assert not apply_hard_gates(
        [candidate(published_at="2026-08-16")], [evaluation()], **common
    )


def test_max_topics_cannot_exceed_three():
    try:
        PipelineConfig(max_topics=4)
    except ValueError as exc:
        assert "max_topics" in str(exc)
    else:
        raise AssertionError("expected max_topics validation to fail")


def test_openai_response_schemas_do_not_emit_unsupported_uri_format():
    for schema_type in (CandidateBatch, EvaluationBatch, WeeklyEdition, VideoPlan):
        schema_json = json.dumps(schema_type.model_json_schema())
        assert '"format": "uri"' not in schema_json


def test_source_urls_still_fail_closed_after_schema_compatibility_change():
    with pytest.raises(ValidationError, match="absolute HTTP\\(S\\) URL"):
        candidate(source_urls=["not-a-url"])
    with pytest.raises(ValidationError, match="must not contain credentials"):
        candidate(source_urls=["https://user:secret@example.com/source"])


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
