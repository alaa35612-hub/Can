"""Authoritative causal hypothesis and precursor decision path."""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Iterable, Sequence

from .adaptive import AdaptiveFeatureEngine, FeatureSnapshot, finite, percentile
from .config import ScannerConfig
from .models import (
    CampaignState,
    Confidence,
    EvidenceItem,
    Hypothesis,
    HypothesisAssessment,
    MarketBar,
    QualityReport,
    Readiness,
    Reliability,
    RuleStatus,
    SignalAssessment,
)
from .quality import DataQualityChecker

ACTIVE_STATES = {"ELEVATED", "SHOCK", "EXTREME"}
SHOCK_STATES = {"SHOCK", "EXTREME"}
FAILURE_HYPOTHESES = {
    Hypothesis.TRANSIENT_EXECUTION_SPIKE,
    Hypothesis.FAILED_FLASH,
    Hypothesis.SHORT_COVERING_ONLY,
    Hypothesis.LATE_CROWDING,
    Hypothesis.DISTRIBUTION,
}
RULE_SCOPE: dict[Hypothesis, tuple[RuleStatus, str]] = {
    Hypothesis.QUIET_ACCUMULATION: (RuleStatus.BACKGROUND_CONCEPT, "generic adaptive hypothesis; cross-symbol controls required"),
    Hypothesis.OI_RESET_ABSORPTION_REBUILD: (RuleStatus.RESEARCH_HYPOTHESIS, "repository mechanism; production sufficiency unproven"),
    Hypothesis.PRICE_LED_BASE_IGNITION: (RuleStatus.RESEARCH_HYPOTHESIS, "ordered price/execution/OI context; independent validation pending"),
    Hypothesis.PRICE_LED_VACUUM_IGNITION: (RuleStatus.RESEARCH_HYPOTHESIS, "exception path; OI non-expansion is not confirmation"),
    Hypothesis.HIGH_OI_COMPRESSION: (RuleStatus.BACKGROUND_CONCEPT, "context pattern, not directional proof"),
    Hypothesis.WHALE_DIVERGENCE_BUILD: (RuleStatus.RESEARCH_HYPOTHESIS, "positioning divergence is ambiguous without acceptance"),
    Hypothesis.COLD_START_OI_IGNITION: (RuleStatus.RESEARCH_HYPOTHESIS, "sparse-history path with confidence cap"),
    Hypothesis.POST_IGNITION_FUEL_RETENTION: (RuleStatus.RESEARCH_HYPOTHESIS, "TLM-restricted context; no cross-symbol promotion"),
    Hypothesis.SHORT_COVERING_ONLY: (RuleStatus.REJECTED_RULE, "rejected as an outcome discriminator in TLM replay"),
    Hypothesis.TRANSIENT_EXECUTION_SPIKE: (RuleStatus.RESEARCH_HYPOTHESIS, "TLM-restricted failure warning"),
    Hypothesis.LATE_CROWDING: (RuleStatus.BACKGROUND_CONCEPT, "risk overlay"),
    Hypothesis.DISTRIBUTION: (RuleStatus.BACKGROUND_CONCEPT, "risk overlay"),
    Hypothesis.FAILED_FLASH: (RuleStatus.RESEARCH_HYPOTHESIS, "failure/noise explanation"),
    Hypothesis.NEW_UNIDENTIFIED_STRUCTURE: (RuleStatus.RESEARCH_HYPOTHESIS, "mandatory abstention hypothesis"),
}


@dataclass(frozen=True, slots=True)
class StructuralContext:
    segment: int
    base_detected: bool
    base_high: float
    base_low: float
    breakout: bool
    accepted: bool
    close_to_footprint: bool
    distance_rank: float | None
    recent_oi_flush: bool
    oi_reload: bool
    price_leads_oi: bool
    execution_confirmed: bool
    top_position_retained: bool | None
    crowd_compressing: bool | None
    prior_execution_shock: bool
    prior_price_shock: bool


def _active(metric: object) -> bool:
    return getattr(metric, "state", "UNKNOWN") in ACTIVE_STATES


def _shock(metric: object) -> bool:
    return getattr(metric, "state", "UNKNOWN") in SHOCK_STATES


def _median(values: Iterable[float | None]) -> float | None:
    data = [float(value) for value in values if finite(value)]
    return statistics.median(data) if data else None


def _evidence(category: str, observation: str, timestamp_ms: int, strength: str = "CONTEXT", status: RuleStatus = RuleStatus.RESEARCH_HYPOTHESIS) -> EvidenceItem:
    return EvidenceItem(category, observation, timestamp_ms, strength, status)


class CausalUpsideDetector:
    """Single final decision path shared by live scan and blind replay."""

    def __init__(self, config: ScannerConfig):
        self.config = config.validate()
        self.features = AdaptiveFeatureEngine(config)
        self.quality = DataQualityChecker(config)

    def _context(self, bars: Sequence[MarketBar], current: FeatureSnapshot, timeline: Sequence[FeatureSnapshot]) -> StructuralContext:
        segment = max(4, int(math.sqrt(len(bars))))
        pre = list(bars[-2 * segment : -segment]) if len(bars) >= 2 * segment else list(bars[:-segment])
        pre = pre or list(bars[:-1])
        ranges = [(bar.high - bar.low) / abs(bar.close) for bar in bars[:-1] if bar.close]
        pre_ranges = [(bar.high - bar.low) / abs(bar.close) for bar in pre if bar.close]
        base_detected = (
            _median(pre_ranges) is not None
            and _median(ranges) is not None
            and float(_median(pre_ranges)) <= float(_median(ranges))
            and current.compression_persistence is not None
            and current.compression_persistence >= 0.5
        )
        base_high = max((bar.high for bar in pre), default=bars[-2].high)
        base_low = min((bar.low for bar in pre), default=bars[-2].low)
        breakout = bars[-1].close > base_high
        locations = [
            (bar.close - bar.low) / (bar.high - bar.low)
            for bar in bars[:-1]
            if bar.high > bar.low
        ]
        location_rank = percentile(locations, current.close_location) if locations and current.close_location is not None else None
        accepted = breakout and location_rank is not None and location_rank >= 0.5
        distance = abs(bars[-1].close - base_high) / abs(bars[-1].close) if bars[-1].close else None
        distance_rank = percentile(ranges, distance) if ranges and distance is not None else None
        recent = list(timeline[-2 * segment :])
        flush_positions = [
            index for index, item in enumerate(recent)
            if item.oi_return.direction == "DOWN" and _shock(item.oi_return)
        ]
        recent_oi_flush = bool(flush_positions)
        oi_reload = recent_oi_flush and current.oi_slope is not None and current.oi_slope > 0 and current.oi_return.direction == "UP"
        price_leads_oi = current.price_return.direction == "UP" and _active(current.price_return) and not (
            current.oi_return.direction == "UP" and _active(current.oi_return)
        )
        top_history = [bar.top_position_ls for bar in bars[:-1] if finite(bar.top_position_ls)]
        retained = None
        if finite(bars[-1].top_position_ls) and top_history:
            retained = float(bars[-1].top_position_ls) >= statistics.median(float(value) for value in top_history)
            retained = retained and not (current.top_position_ls_change.direction == "DOWN" and _shock(current.top_position_ls_change))
        crowd = None
        if finite(bars[-1].global_ls) and finite(bars[-1].top_account_ls):
            crowd = current.global_ls_change.direction == "DOWN" and current.top_account_ls_change.direction == "DOWN"
        return StructuralContext(
            segment=segment,
            base_detected=base_detected,
            base_high=base_high,
            base_low=base_low,
            breakout=breakout,
            accepted=accepted,
            close_to_footprint=distance_rank is None or distance_rank < self.config.adaptive_quantiles[1],
            distance_rank=distance_rank,
            recent_oi_flush=recent_oi_flush,
            oi_reload=oi_reload,
            price_leads_oi=price_leads_oi,
            execution_confirmed=_active(current.trades) and _active(current.quote_volume),
            top_position_retained=retained,
            crowd_compressing=crowd,
            prior_execution_shock=any(_shock(item.trades) and _shock(item.quote_volume) for item in recent[:-1]),
            prior_price_shock=any(item.price_return.direction == "UP" and _shock(item.price_return) for item in recent[:-1]),
        )

    def _candidate(
        self,
        hypothesis: Hypothesis,
        timestamp_ms: int,
        checks: Sequence[tuple[bool | None, str, str, str, str]],
        *,
        invalidated: bool = False,
    ) -> HypothesisAssessment:
        status, scope = RULE_SCOPE[hypothesis]
        supporting: list[EvidenceItem] = []
        opposing: list[EvidenceItem] = []
        missing: list[str] = []
        for condition, category, positive, negative, strength in checks:
            if condition is True:
                supporting.append(_evidence(category, positive, timestamp_ms, strength, status))
            elif condition is False:
                opposing.append(_evidence(category, negative, timestamp_ms, "CONTEXT", status))
            else:
                missing.append(positive)
        return HypothesisAssessment(
            hypothesis=hypothesis,
            rule_status=status,
            supporting=tuple(supporting),
            opposing=tuple(opposing),
            missing=tuple(sorted(set(missing))),
            invalidated=invalidated,
            research_scope=scope,
        )

    def _hypotheses(self, bars: Sequence[MarketBar], feature: FeatureSnapshot, context: StructuralContext) -> list[HypothesisAssessment]:
        timestamp = bars[-1].timestamp_ms
        price_up = feature.price_return.direction == "UP" and _active(feature.price_return)
        oi_up = feature.oi_return.direction == "UP" and _active(feature.oi_return)
        oi_down = feature.oi_return.direction == "DOWN"
        price_resilient = feature.price_slope is not None and feature.price_slope >= 0
        high_oi = _active(feature.oi_level)
        execution_retained = None if feature.execution_retention is None else feature.execution_retention >= 0
        close_below_base = bars[-1].close < context.base_low
        candidates = [
            self._candidate(Hypothesis.QUIET_ACCUMULATION, timestamp, [
                (context.base_detected, "price", "persistent symbol-relative compression", "no persistent compression base", "STRONG"),
                (None if feature.oi_slope is None else feature.oi_slope >= 0, "oi", "OI stable or rising through base", "OI contracts through base", "CONTEXT"),
                (context.top_position_retained, "positioning", "top-position exposure retained", "top-position exposure did not retain", "CONTEXT"),
            ], invalidated=context.breakout),
            self._candidate(Hypothesis.OI_RESET_ABSORPTION_REBUILD, timestamp, [
                (context.recent_oi_flush, "oi", "recent symbol-relative OI flush", "no recent OI flush", "STRONG"),
                (price_resilient, "price", "price remained resilient or recovered after reset", "price has not recovered", "STRONG"),
                (None if feature.oi_slope is None else context.oi_reload, "oi", "OI reload followed the flush", "no constructive OI reload", "STRONG"),
            ]),
            self._candidate(Hypothesis.PRICE_LED_BASE_IGNITION, timestamp, [
                (context.base_detected, "price", "ignition emerged from a compression base", "no causal base", "STRONG"),
                (context.breakout, "price", "closed above the causal base high", "no closed breakout", "STRONG"),
                (price_up, "price", "upward move is exceptional to symbol history", "price move is not exceptional", "STRONG"),
                (context.execution_confirmed, "execution", "trade count and quote value confirm activation", "execution lacks two-channel confirmation", "STRONG"),
                (context.price_leads_oi or oi_up, "oi", "OI lagged price or reloaded constructively", "OI path is destructive or unresolved", "CONTEXT"),
                (context.accepted, "acceptance", "close location accepted the breakout", "breakout was not accepted", "STRONG"),
            ], invalidated=close_below_base),
            self._candidate(Hypothesis.PRICE_LED_VACUUM_IGNITION, timestamp, [
                (context.base_detected, "price", "vacuum path started from a base", "no causal base", "CONTEXT"),
                (context.breakout and price_up, "price", "price led the break", "no price-led break", "STRONG"),
                (context.execution_confirmed, "execution", "notional execution confirms activity", "execution lacks confirmation", "STRONG"),
                (oi_down and not _shock(feature.oi_return), "oi", "OI stayed slightly lower without a flush", "OI path does not match vacuum context", "CONTEXT"),
                (context.accepted, "acceptance", "price accepted above the base", "price did not accept above base", "STRONG"),
            ], invalidated=close_below_base),
            self._candidate(Hypothesis.HIGH_OI_COMPRESSION, timestamp, [
                (context.base_detected, "price", "price remains compressed", "price is not compressed", "STRONG"),
                (None if feature.oi_level.value is None else high_oi, "oi", "OI level is elevated relative to symbol history", "OI level is not elevated", "STRONG"),
            ], invalidated=context.breakout),
            self._candidate(Hypothesis.WHALE_DIVERGENCE_BUILD, timestamp, [
                (context.crowd_compressing, "positioning", "global and top-account ratios contracted", "crowd/account ratios are not compressing", "STRONG"),
                (context.top_position_retained, "positioning", "top-position ratio retained during account compression", "top-position exposure did not retain", "STRONG"),
                (price_resilient, "price", "price remained resilient during positioning divergence", "price weakened during divergence", "CONTEXT"),
            ]),
            self._candidate(Hypothesis.COLD_START_OI_IGNITION, timestamp, [
                (not feature.oi_return.warm, "quality", "OI history is in cold-start warm-up", "OI history is mature", "CONTEXT"),
                (context.breakout and price_up, "price", "price ignition is visible despite immature OI history", "no price ignition", "STRONG"),
                (context.execution_confirmed, "execution", "execution confirms cold-start activity", "execution lacks confirmation", "STRONG"),
            ]),
            self._candidate(Hypothesis.POST_IGNITION_FUEL_RETENTION, timestamp, [
                (context.accepted, "acceptance", "ignition remains accepted", "no accepted ignition", "STRONG"),
                (None if feature.price_slope is None else feature.price_slope > 0, "price", "price trajectory retains fuel", "price trajectory lost fuel", "CONTEXT"),
                (None if feature.oi_slope is None else feature.oi_slope > 0, "oi", "OI trajectory retains fuel", "OI trajectory lost fuel", "CONTEXT"),
                (execution_retained, "execution", "execution has not decayed below baseline", "execution decayed after activation", "CONTEXT"),
            ]),
            self._candidate(Hypothesis.SHORT_COVERING_ONLY, timestamp, [
                (price_up and oi_down, "mechanism", "price rose while OI contracted", "price/OI path is not short-covering-only", "STRONG"),
                (None if feature.execution_retention is None else feature.execution_retention < 0, "execution", "execution decayed during the rise", "execution did not decay", "CONTEXT"),
            ]),
            self._candidate(Hypothesis.TRANSIENT_EXECUTION_SPIKE, timestamp, [
                (context.prior_execution_shock, "execution", "recent execution shock was observed", "no recent execution shock", "STRONG"),
                (not context.accepted and not oi_up, "failure", "shock lacks price acceptance and OI support", "price acceptance or OI support survived", "STRONG"),
                (None if feature.execution_retention is None else feature.execution_retention < 0, "execution", "execution decayed after the spike", "execution retained", "STRONG"),
            ]),
            self._candidate(Hypothesis.LATE_CROWDING, timestamp, [
                (None if context.distance_rank is None else context.distance_rank >= self.config.adaptive_quantiles[1], "freshness", "price is extended from the original footprint", "price remains near the footprint", "STRONG"),
                (high_oi and feature.global_ls_change.direction == "UP", "crowding", "OI and crowd participation expanded late", "no late OI/crowd expansion", "STRONG"),
            ]),
            self._candidate(Hypothesis.FAILED_FLASH, timestamp, [
                (context.prior_price_shock and not context.accepted, "failure", "prior price shock failed to retain base acceptance", "no rejected flash sequence", "STRONG"),
                (None if feature.execution_retention is None else feature.execution_retention < 0, "execution", "post-shock execution retention is negative", "execution retained", "STRONG"),
            ]),
        ]
        status, scope = RULE_SCOPE[Hypothesis.NEW_UNIDENTIFIED_STRUCTURE]
        candidates.append(HypothesisAssessment(
            hypothesis=Hypothesis.NEW_UNIDENTIFIED_STRUCTURE,
            rule_status=status,
            supporting=(_evidence("governance", "unidentified structure remains an active alternative", timestamp),),
            research_scope=scope,
        ))
        return candidates

    @staticmethod
    def _select(candidates: Sequence[HypothesisAssessment]) -> tuple[HypothesisAssessment, tuple[HypothesisAssessment, ...], HypothesisAssessment]:
        usable = [candidate for candidate in candidates if not candidate.invalidated]
        unidentified = next(candidate for candidate in candidates if candidate.hypothesis == Hypothesis.NEW_UNIDENTIFIED_STRUCTURE)
        failures = [candidate for candidate in usable if candidate.hypothesis in FAILURE_HYPOTHESES]
        positives = [candidate for candidate in usable if candidate.hypothesis not in FAILURE_HYPOTHESES and candidate.hypothesis != Hypothesis.NEW_UNIDENTIFIED_STRUCTURE]
        failure = max(failures, key=lambda item: item.evidence_balance, default=unidentified)
        ordered = sorted(positives, key=lambda item: item.evidence_balance, reverse=True)
        if not ordered or ordered[0].evidence_balance[1] <= 0:
            dominant = unidentified
        elif len(ordered) > 1 and ordered[0].evidence_balance == ordered[1].evidence_balance:
            dominant = unidentified
        elif failure.evidence_balance > ordered[0].evidence_balance:
            dominant = unidentified
        else:
            dominant = ordered[0]
        alternatives = tuple(
            candidate for candidate in sorted(usable, key=lambda item: item.evidence_balance, reverse=True)
            if candidate.hypothesis != dominant.hypothesis
        )[:3]
        return dominant, alternatives, failure

    @staticmethod
    def _decision(dominant: HypothesisAssessment, failure: HypothesisAssessment, context: StructuralContext, quality: QualityReport) -> tuple[CampaignState, Readiness, str, str, str, str, str | None]:
        if not quality.usable:
            return CampaignState.UNRESOLVED, Readiness.UNRESOLVED, "UNRESOLVED", "LOW", "WAIT_FOR_VALID_DATA", "restore valid chronological closed-bar coverage", "data quality is unusable"
        if dominant.hypothesis == Hypothesis.NEW_UNIDENTIFIED_STRUCTURE:
            return CampaignState.UNRESOLVED, Readiness.UNRESOLVED, "UNRESOLVED", "LOW", "WAIT", "wait for a discriminating ordered sequence", "no hypothesis dominates materially"
        if failure.hypothesis in {Hypothesis.TRANSIENT_EXECUTION_SPIKE, Hypothesis.FAILED_FLASH} and failure.evidence_balance[0] >= 2:
            return CampaignState.FAILURE, Readiness.FAILED, "FAILURE_RISK", "HIGH", "AVOID", "price acceptance and execution/OI retention must recover", None
        mapping = {
            Hypothesis.QUIET_ACCUMULATION: (CampaignState.EARLY_BUILD, Readiness.EARLY_BUILD, "EARLY_BULLISH_STRUCTURE", "MEDIUM", "WAIT_FOR_CONFIRMATION"),
            Hypothesis.HIGH_OI_COMPRESSION: (CampaignState.CONFIRMED_BUILD, Readiness.CONFIRMED_BUILD, "NEUTRAL_TO_BULLISH_COMPRESSION", "MEDIUM", "WAIT_FOR_DIRECTION"),
            Hypothesis.WHALE_DIVERGENCE_BUILD: (CampaignState.CONFIRMED_BUILD, Readiness.CONFIRMED_BUILD, "EARLY_BULLISH_STRUCTURE", "MEDIUM", "WAIT_FOR_ACCEPTANCE"),
            Hypothesis.OI_RESET_ABSORPTION_REBUILD: (CampaignState.REBUILD, Readiness.CONFIRMED_BUILD, "EARLY_BULLISH_STRUCTURE", "HIGH", "WAIT_FOR_IGNITION"),
            Hypothesis.PRICE_LED_BASE_IGNITION: (CampaignState.ACCEPTED_IGNITION if context.accepted else CampaignState.IGNITION_CANDIDATE, Readiness.ACCEPTED if context.accepted else Readiness.LIVE_IGNITION, "BULLISH_IGNITION_CONTEXT", "HIGH", "CONDITIONAL_NEAR_FOOTPRINT"),
            Hypothesis.PRICE_LED_VACUUM_IGNITION: (CampaignState.ACCEPTED_IGNITION if context.accepted else CampaignState.IGNITION_CANDIDATE, Readiness.ACCEPTED if context.accepted else Readiness.LIVE_IGNITION, "EVENT_DRIVEN_BULLISH_CONTEXT", "HIGH", "HIGHER_RISK_OI_UNCONFIRMED"),
            Hypothesis.COLD_START_OI_IGNITION: (CampaignState.IGNITION_CANDIDATE, Readiness.LIVE_IGNITION, "BULLISH_COLD_START_CONTEXT", "HIGH", "HIGHER_RISK_SPARSE_HISTORY"),
            Hypothesis.POST_IGNITION_FUEL_RETENTION: (CampaignState.CONTINUATION_RELOAD, Readiness.CONTINUATION, "BULLISH_CONTINUATION_CONTEXT", "HIGH", "NO_CHASE_IF_EXTENDED"),
        }
        state, readiness, bias, importance, safety = mapping.get(dominant.hypothesis, (CampaignState.UNRESOLVED, Readiness.UNRESOLVED, "UNRESOLVED", "LOW", "WAIT"))
        if not context.close_to_footprint and readiness in {Readiness.LIVE_IGNITION, Readiness.ACCEPTED, Readiness.CONTINUATION}:
            readiness, safety = Readiness.LATE_NO_CHASE, "LATE_NO_CHASE"
        return state, readiness, bias, importance, safety, "confirm ordered price acceptance, execution retention, and non-destructive OI behavior", None

    @staticmethod
    def _confidence(candidate: HypothesisAssessment, quality: QualityReport) -> Confidence:
        if candidate.hypothesis == Hypothesis.NEW_UNIDENTIFIED_STRUCTURE:
            raw = Confidence.LOW
        elif candidate.evidence_balance[0] >= 3 and not candidate.opposing:
            raw = Confidence.HIGH
        elif candidate.evidence_balance[0] >= 2:
            raw = Confidence.MEDIUM_HIGH
        else:
            raw = Confidence.MEDIUM
        order = [Confidence.LOW, Confidence.MEDIUM, Confidence.MEDIUM_HIGH, Confidence.HIGH]
        if candidate.rule_status in {RuleStatus.BACKGROUND_CONCEPT, RuleStatus.RESEARCH_HYPOTHESIS, RuleStatus.REJECTED_RULE} and raw == Confidence.HIGH:
            raw = Confidence.MEDIUM_HIGH
        if len(candidate.opposing) >= 2 and order.index(raw) > order.index(Confidence.MEDIUM):
            raw = Confidence.MEDIUM
        return order[min(order.index(raw), order.index(quality.confidence_cap))]

    def analyze(self, bars: Sequence[MarketBar], *, source_flags: Sequence[str] = ()) -> SignalAssessment:
        ordered = sorted((bar for bar in bars if bar.is_closed), key=lambda bar: bar.timestamp_ms)
        quality = self.quality.check(ordered, source_flags=source_flags)
        minimum = max(2, self.config.minimum_baseline_observations + 1)
        if len(ordered) < minimum:
            latest = ordered[-1] if ordered else None
            return SignalAssessment(
                symbol=latest.symbol if latest else "UNKNOWN",
                timeframe=latest.timeframe if latest else self.config.timeframe,
                cutoff_ms=latest.close_time_ms if latest else 0,
                campaign_state=CampaignState.UNRESOLVED,
                dominant_hypothesis=Hypothesis.NEW_UNIDENTIFIED_STRUCTURE,
                alternative_hypotheses=(),
                failure_hypothesis=Hypothesis.NEW_UNIDENTIFIED_STRUCTURE,
                structural_bias="UNRESOLVED",
                signal_importance="LOW",
                readiness=Readiness.UNRESOLVED,
                entry_safety="WAIT_FOR_HISTORY",
                confidence=Confidence.LOW,
                data_reliability=quality.reliability,
                supporting_evidence=(),
                opposing_evidence=(),
                missing_evidence=("causal warm-up history",),
                next_discriminator="accumulate more closed bars without gaps",
                invalidation="not applicable before warm-up",
                abstention_reason="insufficient causal baseline",
                research_status=RuleStatus.RESEARCH_HYPOTHESIS,
                campaign_age_bars=0,
                distance_from_footprint_rank=None,
                quality_flags=quality.flags,
            )
        timeline = self.features.timeline(ordered)
        context = self._context(ordered, timeline[-1], timeline)
        dominant, alternatives, failure = self._select(self._hypotheses(ordered, timeline[-1], context))
        state, readiness, bias, importance, safety, discriminator, abstention = self._decision(dominant, failure, context, quality)
        effective = failure if state in {CampaignState.FAILURE, CampaignState.DISTRIBUTION} else dominant
        missing = tuple(sorted(set(effective.missing + (() if quality.reliability == Reliability.HIGH else ("higher data reliability",)))))
        return SignalAssessment(
            symbol=ordered[-1].symbol,
            timeframe=ordered[-1].timeframe,
            cutoff_ms=ordered[-1].close_time_ms,
            campaign_state=state,
            dominant_hypothesis=effective.hypothesis,
            alternative_hypotheses=tuple(candidate.hypothesis for candidate in alternatives),
            failure_hypothesis=failure.hypothesis,
            structural_bias=bias,
            signal_importance=importance,
            readiness=readiness,
            entry_safety=safety,
            confidence=self._confidence(effective, quality),
            data_reliability=quality.reliability,
            supporting_evidence=effective.supporting,
            opposing_evidence=effective.opposing,
            missing_evidence=missing,
            next_discriminator=discriminator,
            invalidation=f"closed price below causal base low {context.base_low:.12g} or independent failure evidence dominates",
            abstention_reason=abstention,
            research_status=effective.rule_status,
            campaign_age_bars=min(len(ordered), max(1, 2 * context.segment)),
            distance_from_footprint_rank=context.distance_rank,
            quality_flags=quality.flags,
        )
