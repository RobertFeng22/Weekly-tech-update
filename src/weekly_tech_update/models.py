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
    ENGINEERING = "engineering_practice"
    PAPER = "valuable_paper"
    TRICK = "practical_trick"


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
    practitioner_value: str = Field(min_length=20)
    concrete_takeaways: list[str] = Field(min_length=1, max_length=6)
    limitations: list[str] = Field(default_factory=list, max_length=6)
    source_urls: list[SourceUrl] = Field(min_length=1, max_length=8)
    primary_source_urls: list[SourceUrl] = Field(min_length=1, max_length=5)


class CandidateBatch(BaseModel):
    candidates: list[Candidate] = Field(min_length=1, max_length=20)


class Evaluation(BaseModel):
    candidate_id: str
    factual_accuracy: int = Field(ge=0, le=5)
    evidence_strength: int = Field(ge=0, le=5)
    practical_value: int = Field(ge=0, le=5)
    novelty: int = Field(ge=0, le=5)
    transferability: int = Field(ge=0, le=5)
    teachability: int = Field(ge=0, le=5)
    confidence: int = Field(ge=0, le=5)
    red_flags: list[str] = Field(default_factory=list, max_length=8)
    counter_evidence: list[str] = Field(default_factory=list, max_length=8)
    rationale: str = Field(min_length=30)
    verified_source_urls: list[SourceUrl] = Field(min_length=1, max_length=10)
    verified_primary_source_urls: list[SourceUrl] = Field(default_factory=list, max_length=6)

    @property
    def weighted_score(self) -> float:
        # Accuracy/evidence dominate; hype with weak verification cannot rank highly.
        weights = {
            "factual_accuracy": 0.22,
            "evidence_strength": 0.20,
            "practical_value": 0.20,
            "novelty": 0.12,
            "transferability": 0.10,
            "teachability": 0.10,
            "confidence": 0.06,
        }
        raw = sum(getattr(self, name) * weight for name, weight in weights.items())
        return round(raw / 5 * 100, 1)


class EvaluationBatch(BaseModel):
    evaluations: list[Evaluation] = Field(min_length=1, max_length=20)


class Topic(BaseModel):
    candidate_id: str
    title: str = Field(min_length=4, max_length=180)
    category: Category
    one_sentence_value: str = Field(min_length=20)
    why_now: str = Field(min_length=40)
    lesson: str = Field(min_length=200)
    hands_on_demo: list[str] = Field(min_length=2, max_length=10)
    when_to_use: list[str] = Field(min_length=1, max_length=6)
    when_not_to_use: list[str] = Field(min_length=1, max_length=6)
    caveats: list[str] = Field(min_length=1, max_length=8)
    source_urls: list[SourceUrl] = Field(min_length=1, max_length=10)
    video_direction: str = Field(min_length=80)


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
