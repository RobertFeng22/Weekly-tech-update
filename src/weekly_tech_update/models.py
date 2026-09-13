from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import AfterValidator, BaseModel, Field, model_validator


def _validate_source_url(value: str) -> str:
    """Validate URLs without emitting the unsupported JSON Schema `uri` format."""
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("source URL must be an absolute HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("source URL must not contain credentials")
    return value


SourceUrl = Annotated[str, AfterValidator(_validate_source_url)]


class Category(StrEnum):
    CAPABILITY = "capability_frontier"
    AGENTS = "agents_and_research"
    ECONOMICS = "ai_economics_and_infrastructure"
    INVESTMENT = "investment_and_market_impact"
    GOVERNANCE = "policy_and_governance"

    # Kept only so historical manifests remain readable.
    ENGINEERING = "engineering_practice"
    PAPER = "valuable_paper"
    TRICK = "practical_trick"


class AdmissionMode(StrEnum):
    FRONTIER_SHIFT = "frontier_shift"
    DIRECT_BUILD_LEVERAGE = "direct_build_leverage"
    STRATEGIC_CONSTRAINT = "strategic_constraint_or_threat"


class NeuralAlphaPriorityId(StrEnum):
    EVENT_INTELLIGENCE = "event_intelligence"
    SEMANTIC_STATE = "semantic_state_and_causal_mapping"
    EXPECTATION_REPRICING = "expectation_and_priced_in"
    FORECASTING = "forecasting_and_calibration"
    DECISION_REPLAY = "decision_replay_and_attribution"
    AGENTIC_RESEARCH = "agentic_research_and_control"
    PORTFOLIO_RISK = "portfolio_risk_and_execution"
    DATA_RIGHTS = "data_rights_and_auditability"
    AI_MARKET_OPPORTUNITY = "ai_market_and_event_opportunity"
    FUND_OPERATIONS = "fund_operations_and_regulation"


class ImpactType(StrEnum):
    CAPABILITY_ENABLER = "capability_enabler"
    ARCHITECTURE_CHOICE = "architecture_choice"
    EVALUATION_METHOD = "evaluation_method"
    RISK_CONTROL = "risk_control"
    ECONOMICS_OR_ACCESS = "economics_or_access"
    THREAT_OR_FAILURE_MODE = "threat_or_failure_mode"
    MARKET_OPPORTUNITY = "market_opportunity"
    REGULATORY_CONSTRAINT = "regulatory_constraint"


class ActionType(StrEnum):
    RUN_EVALUATION = "run_evaluation"
    CHANGE_BUILD_PRIORITY = "change_build_priority"
    CHANGE_ARCHITECTURE = "change_architecture"
    CHANGE_DATA_OR_VENDOR_PLAN = "change_data_or_vendor_plan"
    CHANGE_RISK_OR_GOVERNANCE = "change_risk_or_governance"
    UPDATE_INVESTMENT_THESIS = "update_investment_thesis"
    WATCH_WITH_TRIGGER = "watch_with_trigger"


class PriorityStatus(StrEnum):
    ACTIVE = "active"
    WATCH = "watch"
    DEFERRED = "deferred"


class NeuralAlphaPriority(BaseModel):
    priority_id: NeuralAlphaPriorityId
    label: str = Field(min_length=4, max_length=100)
    status: PriorityStatus
    weight: int = Field(ge=1, le=5)
    current_state: str = Field(min_length=30, max_length=500)
    current_need: str = Field(min_length=30, max_length=500)
    high_value_signals: list[str] = Field(min_length=1, max_length=8)
    false_friends: list[str] = Field(default_factory=list, max_length=8)


class NeuralAlphaSelectionContext(BaseModel):
    version: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,79}$")
    as_of: date
    public_safe: bool
    audience: str = Field(min_length=30, max_length=400)
    fund_identity: str = Field(min_length=30, max_length=500)
    strategy_wedge: str = Field(min_length=50, max_length=800)
    selection_objective: str = Field(min_length=50, max_length=800)
    priorities: list[NeuralAlphaPriority] = Field(min_length=1, max_length=16)
    global_non_goals: list[str] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def ensure_priority_ids_are_unique(self) -> "NeuralAlphaSelectionContext":
        ids = [priority.priority_id for priority in self.priorities]
        if len(ids) != len(set(ids)):
            raise ValueError("selection context contains duplicate priority IDs")
        if not self.public_safe:
            raise ValueError("selection context must be explicitly public-safe")
        return self

    def eligible_priority_ids(
        self, minimum_weight: int = 4
    ) -> set[NeuralAlphaPriorityId]:
        return {
            priority.priority_id
            for priority in self.priorities
            if priority.status is PriorityStatus.ACTIVE
            and priority.weight >= minimum_weight
        }


class RelevancePath(BaseModel):
    priority_id: NeuralAlphaPriorityId
    impact_type: ImpactType
    action_type: ActionType
    current_constraint: str = Field(min_length=40, max_length=500)
    external_delta: str = Field(min_length=40, max_length=500)
    transmission_mechanism: str = Field(min_length=60, max_length=700)
    decision_or_test: str = Field(min_length=40, max_length=500)


class VideoSceneKind(StrEnum):
    INTRO = "intro"
    FUNNEL = "evaluation_funnel"
    PROBLEM = "problem"
    MECHANISM = "mechanism"
    DEMO = "demo"
    EVIDENCE = "evidence_and_limits"
    DECISION = "decision_guide"


class VideoAccent(StrEnum):
    CYAN = "cyan"
    VIOLET = "violet"
    AMBER = "amber"


class Candidate(BaseModel):
    candidate_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=4, max_length=180)
    category: Category
    published_at: date
    summary: str = Field(min_length=40)
    novelty: str = Field(min_length=20)
    admission_mode: AdmissionMode
    capability_delta: str = Field(min_length=40)
    neural_alpha_relevance: str = Field(min_length=60)
    relevance_paths: list[RelevancePath] = Field(min_length=1, max_length=3)
    decision_takeaways: list[str] = Field(min_length=1, max_length=6)
    limitations: list[str] = Field(default_factory=list, max_length=6)
    source_urls: list[SourceUrl] = Field(min_length=1, max_length=8)
    primary_source_urls: list[SourceUrl] = Field(min_length=1, max_length=5)

    @model_validator(mode="before")
    @classmethod
    def migrate_engineering_brief_candidate(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        payload.setdefault(
            "admission_mode",
            (
                AdmissionMode.FRONTIER_SHIFT
                if payload.get("category")
                in {
                    Category.CAPABILITY,
                    Category.AGENTS,
                    Category.ECONOMICS,
                    Category.INVESTMENT,
                    Category.GOVERNANCE,
                    Category.CAPABILITY.value,
                    Category.AGENTS.value,
                    Category.ECONOMICS.value,
                    Category.INVESTMENT.value,
                    Category.GOVERNANCE.value,
                }
                else AdmissionMode.DIRECT_BUILD_LEVERAGE
            ),
        )
        payload.setdefault(
            "capability_delta",
            payload.get("novelty") or payload.get("summary"),
        )
        payload.setdefault(
            "neural_alpha_relevance",
            payload.get("practitioner_value") or payload.get("summary"),
        )
        payload.setdefault(
            "relevance_paths",
            [
                {
                    "priority_id": NeuralAlphaPriorityId.AGENTIC_RESEARCH,
                    "impact_type": ImpactType.CAPABILITY_ENABLER,
                    "action_type": ActionType.RUN_EVALUATION,
                    "current_constraint": (
                        "Historical edition predates the Neural Alpha relevance-path schema."
                    ),
                    "external_delta": payload.get("novelty") or payload.get("summary"),
                    "transmission_mechanism": (
                        payload.get("practitioner_value")
                        or payload.get("summary")
                        or "Historical relevance was not captured in structured form."
                    ),
                    "decision_or_test": (
                        "Retain historical readability without treating this "
                        "fallback as new evidence."
                    ),
                }
            ],
        )
        payload.setdefault(
            "decision_takeaways",
            payload.get("concrete_takeaways") or ["Re-evaluate the implication"],
        )
        return payload


class CandidateBatch(BaseModel):
    candidates: list[Candidate] = Field(min_length=1, max_length=20)


class Evaluation(BaseModel):
    candidate_id: str
    factual_accuracy: int = Field(ge=0, le=5)
    evidence_strength: int = Field(ge=0, le=5)
    frontier_significance: int = Field(ge=0, le=5)
    authoritative_primary_sufficient: bool
    admission_mode_supported: bool
    engineering_only: bool
    generic_relevance_only: bool
    validated_priority_ids: list[NeuralAlphaPriorityId] = Field(max_length=6)
    current_priority_relevance: int = Field(ge=0, le=5)
    strategy_impact: int = Field(ge=0, le=5)
    architecture_impact: int = Field(ge=0, le=5)
    relevance_path_quality: int = Field(ge=0, le=5)
    transfer_readiness: int = Field(ge=0, le=5)
    business_decision_value: int = Field(ge=0, le=5)
    strategic_magnitude: int = Field(ge=0, le=5)
    novelty: int = Field(ge=0, le=5)
    confidence: int = Field(ge=0, le=5)
    red_flags: list[str] = Field(default_factory=list, max_length=8)
    counter_evidence: list[str] = Field(default_factory=list, max_length=8)
    rationale: str = Field(min_length=30)
    verified_source_urls: list[SourceUrl] = Field(min_length=1, max_length=10)
    verified_primary_source_urls: list[SourceUrl] = Field(default_factory=list, max_length=6)

    @model_validator(mode="before")
    @classmethod
    def migrate_engineering_brief_evaluation(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        payload.setdefault("frontier_significance", payload.get("novelty"))
        payload.setdefault("authoritative_primary_sufficient", False)
        legacy_relevance = payload.get(
            "ai_native_fund_relevance", payload.get("practical_value")
        )
        payload.setdefault("admission_mode_supported", True)
        payload.setdefault("engineering_only", False)
        payload.setdefault("generic_relevance_only", False)
        payload.setdefault(
            "validated_priority_ids", [NeuralAlphaPriorityId.AGENTIC_RESEARCH]
        )
        payload.setdefault("current_priority_relevance", legacy_relevance)
        payload.setdefault("strategy_impact", legacy_relevance)
        payload.setdefault(
            "architecture_impact", payload.get("transferability", legacy_relevance)
        )
        payload.setdefault(
            "relevance_path_quality", payload.get("transferability", legacy_relevance)
        )
        payload.setdefault(
            "transfer_readiness", payload.get("transferability", legacy_relevance)
        )
        payload.setdefault("business_decision_value", payload.get("teachability"))
        payload.setdefault("strategic_magnitude", payload.get("transferability"))
        return payload

    @property
    def weighted_score(self) -> float:
        # Relevance is evaluated against the current Neural Alpha context. A
        # candidate may be strategy-relevant or architecture-relevant; it need
        # not be both, so use the stronger of the two rather than their average.
        raw = (
            self.factual_accuracy * 0.16
            + self.evidence_strength * 0.14
            + self.frontier_significance * 0.10
            + self.current_priority_relevance * 0.18
            + max(self.strategy_impact, self.architecture_impact) * 0.14
            + self.relevance_path_quality * 0.14
            + self.business_decision_value * 0.06
            + self.transfer_readiness * 0.04
            + self.strategic_magnitude * 0.02
            + self.confidence * 0.02
        )
        return round(raw / 5 * 100, 1)


class EvaluationBatch(BaseModel):
    evaluations: list[Evaluation] = Field(min_length=1, max_length=20)


class Topic(BaseModel):
    candidate_id: str
    title: str = Field(min_length=4, max_length=180)
    category: Category
    one_sentence_value: str = Field(min_length=20)
    why_now: str = Field(min_length=40)
    capability_boundary_change: str = Field(min_length=40)
    neural_alpha_priority_ids: list[NeuralAlphaPriorityId] = Field(
        min_length=1, max_length=3
    )
    neural_alpha_impact_chain: str = Field(min_length=100)
    business_brief: str = Field(min_length=200)
    decision_takeaways: list[str] = Field(min_length=2, max_length=8)
    what_to_watch: list[str] = Field(min_length=2, max_length=8)
    caveats: list[str] = Field(min_length=1, max_length=8)
    source_urls: list[SourceUrl] = Field(min_length=1, max_length=10)
    video_direction: str = Field(min_length=80)

    @model_validator(mode="before")
    @classmethod
    def migrate_engineering_brief_topic(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        lesson = payload.get("lesson") or payload.get("why_now") or ""
        payload.setdefault("capability_boundary_change", lesson)
        payload.setdefault(
            "neural_alpha_impact_chain",
            " ".join(
                part
                for part in [
                    payload.get("one_sentence_value"),
                    payload.get("why_now"),
                    payload.get("ai_native_fund_impact"),
                ]
                if isinstance(part, str)
            ),
        )
        payload.setdefault(
            "neural_alpha_priority_ids", [NeuralAlphaPriorityId.AGENTIC_RESEARCH]
        )
        payload.setdefault("business_brief", lesson)
        payload.setdefault(
            "decision_takeaways",
            payload.get("hands_on_demo") or ["Review the implication", "Define a test"],
        )
        payload.setdefault(
            "video_direction",
            (
                "Historical edition predates the structured video-direction field. "
                "Preserve its approved facts and caveats without adding new claims; "
                "use a plain evidence-and-decision visual treatment."
            ),
        )
        watch_items = [
            *payload.get("when_to_use", []),
            *payload.get("when_not_to_use", []),
            *payload.get("caveats", []),
        ]
        payload.setdefault("what_to_watch", watch_items[:8] or ["Evidence", "Adoption"])
        return payload


class WeeklyEdition(BaseModel):
    window_start: date
    window_end: date
    editorial_note: str = Field(min_length=40)
    topics: list[Topic] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def ensure_topic_ids_are_unique(self) -> "WeeklyEdition":
        ids = [topic.candidate_id for topic in self.topics]
        if len(ids) != len(set(ids)):
            raise ValueError("edition contains duplicate candidate IDs")
        return self


class VideoScene(BaseModel):
    scene_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,63}$")
    topic_id: str | None = None
    kind: VideoSceneKind
    accent: VideoAccent
    eyebrow: str = Field(min_length=2, max_length=48)
    title: str = Field(min_length=4, max_length=96)
    subtitle: str = Field(min_length=10, max_length=180)
    narration: str = Field(min_length=120, max_length=480)
    on_screen_points: list[str] = Field(min_length=1, max_length=4)
    visual_labels: list[str] = Field(default_factory=list, max_length=6)


class VideoPlan(BaseModel):
    window_start: date
    window_end: date
    title: str = Field(min_length=4, max_length=80)
    subtitle: str = Field(min_length=10, max_length=160)
    disclosure: str = Field(min_length=20, max_length=100)
    scenes: list[VideoScene] = Field(min_length=8, max_length=16)

    @model_validator(mode="after")
    def ensure_scene_structure(self) -> "VideoPlan":
        scene_ids = [scene.scene_id for scene in self.scenes]
        if len(scene_ids) != len(set(scene_ids)):
            raise ValueError("video plan contains duplicate scene IDs")
        if self.scenes[0].kind is not VideoSceneKind.INTRO:
            raise ValueError("video plan must start with an intro scene")
        if self.scenes[-1].kind is not VideoSceneKind.DECISION:
            raise ValueError("video plan must end with a decision guide")
        return self


class EvaluatedCandidate(BaseModel):
    candidate: Candidate
    evaluation: Evaluation
