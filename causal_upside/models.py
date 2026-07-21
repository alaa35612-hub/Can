"""Typed domain models for causal upside-precursor research."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class CampaignState(str, Enum):
    LATENT = "LATENT"
    EARLY_BUILD = "EARLY_BUILD"
    CONFIRMED_BUILD = "CONFIRMED_BUILD"
    ARMED = "ARMED"
    IGNITION_CANDIDATE = "IGNITION_CANDIDATE"
    ACCEPTED_IGNITION = "ACCEPTED_IGNITION"
    EXPANSION = "EXPANSION"
    CONTINUATION_RELOAD = "CONTINUATION_RELOAD"
    COOLING = "COOLING"
    FAILURE = "FAILURE"
    DISTRIBUTION = "DISTRIBUTION"
    RESET = "RESET"
    REBUILD = "REBUILD"
    UNRESOLVED = "UNRESOLVED"


class Hypothesis(str, Enum):
    QUIET_ACCUMULATION = "QUIET_ACCUMULATION"
    OI_RESET_ABSORPTION_REBUILD = "OI_RESET_ABSORPTION_REBUILD"
    PRICE_LED_BASE_IGNITION = "PRICE_LED_BASE_IGNITION"
    PRICE_LED_VACUUM_IGNITION = "PRICE_LED_VACUUM_IGNITION"
    HIGH_OI_COMPRESSION = "HIGH_OI_COMPRESSION"
    WHALE_DIVERGENCE_BUILD = "WHALE_DIVERGENCE_BUILD"
    COLD_START_OI_IGNITION = "COLD_START_OI_IGNITION"
    POST_IGNITION_FUEL_RETENTION = "POST_IGNITION_FUEL_RETENTION"
    SHORT_COVERING_ONLY = "SHORT_COVERING_ONLY"
    TRANSIENT_EXECUTION_SPIKE = "TRANSIENT_EXECUTION_SPIKE"
    LATE_CROWDING = "LATE_CROWDING"
    DISTRIBUTION = "DISTRIBUTION"
    FAILED_FLASH = "FAILED_FLASH"
    NEW_UNIDENTIFIED_STRUCTURE = "NEW_UNIDENTIFIED_STRUCTURE"


class RuleStatus(str, Enum):
    BACKGROUND_CONCEPT = "BACKGROUND_CONCEPT"
    RESEARCH_HYPOTHESIS = "RESEARCH_HYPOTHESIS"
    SUPPORTED_PATTERN = "SUPPORTED_PATTERN"
    CONDITIONAL_RULE = "CONDITIONAL_RULE"
    DURABLE_RULE = "DURABLE_RULE"
    REJECTED_RULE = "REJECTED_RULE"
    DEPRECATED = "DEPRECATED"


class Readiness(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    EARLY_BUILD = "EARLY_BUILD"
    CONFIRMED_BUILD = "CONFIRMED_BUILD"
    ARMED = "ARMED"
    LIVE_IGNITION = "LIVE_IGNITION"
    ACCEPTED = "ACCEPTED"
    CONTINUATION = "CONTINUATION"
    COOLING = "COOLING"
    LATE_NO_CHASE = "LATE_NO_CHASE"
    FAILED = "FAILED"


class Confidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    MEDIUM_HIGH = "MEDIUM_HIGH"
    HIGH = "HIGH"


class Reliability(str, Enum):
    UNUSABLE = "UNUSABLE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True, slots=True)
class MarketBar:
    """One causally observable, closed market bar.

    Optional positioning values remain ``None`` when unavailable. Missing evidence
    is never silently converted to zero or a neutral ratio.
    """

    symbol: str
    timeframe: str
    timestamp_ms: int
    close_time_ms: int
    is_closed: bool
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
    quote_volume: float | None = None
    trades: float | None = None
    taker_buy_quote: float | None = None
    oi: float | None = None
    global_ls: float | None = None
    top_account_ls: float | None = None
    top_position_ls: float | None = None
    funding_rate: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AdaptiveMetric:
    name: str
    value: float | None
    median: float | None
    mad: float | None
    percentile: float | None
    robust_z: float | None
    direction: str
    state: str
    baseline_count: int
    warm: bool


@dataclass(frozen=True, slots=True)
class QualityReport:
    flags: tuple[str, ...]
    reliability: Reliability
    confidence_cap: Confidence
    usable: bool
    closed_bars: int
    expected_interval_ms: int


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    category: str
    observation: str
    timestamp_ms: int
    strength: str = "CONTEXT"
    rule_status: RuleStatus = RuleStatus.RESEARCH_HYPOTHESIS


@dataclass(frozen=True, slots=True)
class HypothesisAssessment:
    hypothesis: Hypothesis
    rule_status: RuleStatus
    supporting: tuple[EvidenceItem, ...] = ()
    opposing: tuple[EvidenceItem, ...] = ()
    missing: tuple[str, ...] = ()
    invalidated: bool = False
    research_scope: str = "cross-symbol validation pending"

    @property
    def evidence_balance(self) -> tuple[int, int, int]:
        """Transparent ordering key, not a probability or profit score."""
        strong = sum(item.strength == "STRONG" for item in self.supporting)
        return (strong, len(self.supporting) - len(self.opposing), -len(self.missing))


@dataclass(frozen=True, slots=True)
class SignalAssessment:
    symbol: str
    timeframe: str
    cutoff_ms: int
    campaign_state: CampaignState
    dominant_hypothesis: Hypothesis
    alternative_hypotheses: tuple[Hypothesis, ...]
    failure_hypothesis: Hypothesis
    structural_bias: str
    signal_importance: str
    readiness: Readiness
    entry_safety: str
    confidence: Confidence
    data_reliability: Reliability
    supporting_evidence: tuple[EvidenceItem, ...]
    opposing_evidence: tuple[EvidenceItem, ...]
    missing_evidence: tuple[str, ...]
    next_discriminator: str
    invalidation: str
    abstention_reason: str | None
    research_status: RuleStatus
    campaign_age_bars: int
    distance_from_footprint_rank: float | None
    quality_flags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["campaign_state"] = self.campaign_state.value
        value["dominant_hypothesis"] = self.dominant_hypothesis.value
        value["alternative_hypotheses"] = [item.value for item in self.alternative_hypotheses]
        value["failure_hypothesis"] = self.failure_hypothesis.value
        value["readiness"] = self.readiness.value
        value["confidence"] = self.confidence.value
        value["data_reliability"] = self.data_reliability.value
        value["research_status"] = self.research_status.value
        for key in ("supporting_evidence", "opposing_evidence"):
            for item in value[key]:
                item["rule_status"] = item["rule_status"].value if isinstance(item["rule_status"], RuleStatus) else item["rule_status"]
        return value


@dataclass(slots=True)
class CampaignLedger:
    schema_version: int
    symbol: str
    timeframe: str
    campaign_id: str
    state: CampaignState
    birth_ms: int
    last_observed_ms: int
    first_detection_ms: int | None = None
    first_warning_ms: int | None = None
    armed_ms: int | None = None
    ignition_ms: int | None = None
    acceptance_ms: int | None = None
    expansion_ms: int | None = None
    weakness_ms: int | None = None
    failure_ms: int | None = None
    reset_ms: int | None = None
    rebuild_ms: int | None = None
    dominant_hypothesis: Hypothesis = Hypothesis.NEW_UNIDENTIFIED_STRUCTURE
    alternatives: list[Hypothesis] = field(default_factory=list)
    contradiction_streak: int = 0
    transition_history: list[dict[str, Any]] = field(default_factory=list)
    last_assessment: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["state"] = self.state.value
        value["dominant_hypothesis"] = self.dominant_hypothesis.value
        value["alternatives"] = [item.value for item in self.alternatives]
        return value
