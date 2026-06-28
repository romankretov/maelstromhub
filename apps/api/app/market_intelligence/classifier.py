from dataclasses import dataclass
from datetime import datetime

from maelstromhub_core import LiquidityRegime, RiskRegime, TrendRegime, VolatilityRegime


@dataclass(frozen=True)
class RegimeThresholds:
    volatility_low: float
    volatility_high: float
    atr_low: float
    atr_high: float
    thin_liquidity_volume: float | None
    return_epsilon: float = 0.0


@dataclass(frozen=True)
class RegimeClassification:
    timestamp: datetime
    trend_regime: TrendRegime
    volatility_regime: VolatilityRegime
    liquidity_regime: LiquidityRegime
    risk_regime: RiskRegime
    regime_label: str
    confidence: float
    explanation: str
    metadata: dict[str, str | int | float | bool | None]


class RegimeClassifier:
    def classify(
        self,
        timestamp: datetime,
        features: dict[str, float],
        thresholds: RegimeThresholds,
    ) -> RegimeClassification:
        trend = self._classify_trend(features, thresholds.return_epsilon)
        volatility = self._classify_volatility(features, thresholds)
        liquidity = self._classify_liquidity(features, thresholds.thin_liquidity_volume)
        risk = self._classify_risk(features, trend, volatility, thresholds.return_epsilon)
        label = self._label(trend, volatility, risk)
        confidence = self._confidence(features, trend, volatility, liquidity, risk)
        explanation = self._explanation(features, trend, volatility, liquidity, risk)
        return RegimeClassification(
            timestamp=timestamp,
            trend_regime=trend,
            volatility_regime=volatility,
            liquidity_regime=liquidity,
            risk_regime=risk,
            regime_label=label,
            confidence=confidence,
            explanation=explanation,
            metadata={
                "returns_1": features.get("returns_1"),
                "returns_5": features.get("returns_5"),
                "sma_20": features.get("sma_20"),
                "sma_50": features.get("sma_50"),
                "volatility_20": features.get("volatility_20"),
                "rsi_14": features.get("rsi_14"),
                "atr_14": features.get("atr_14"),
            },
        )

    def _classify_trend(self, features: dict[str, float], epsilon: float) -> TrendRegime:
        returns_1 = features.get("returns_1", 0.0)
        returns_5 = features.get("returns_5", returns_1)
        sma_20 = features.get("sma_20")
        sma_50 = features.get("sma_50")
        if sma_20 is not None and sma_50 is not None and sma_20 > sma_50 and (returns_1 > epsilon or returns_5 > epsilon):
            return TrendRegime.UPTREND
        if sma_20 is not None and sma_50 is not None and sma_20 < sma_50 and (returns_1 < -epsilon or returns_5 < -epsilon):
            return TrendRegime.DOWNTREND
        return TrendRegime.SIDEWAYS

    def _classify_volatility(self, features: dict[str, float], thresholds: RegimeThresholds) -> VolatilityRegime:
        volatility = features.get("volatility_20", 0.0)
        atr = features.get("atr_14", 0.0)
        if volatility >= thresholds.volatility_high or atr >= thresholds.atr_high:
            return VolatilityRegime.HIGH
        if volatility <= thresholds.volatility_low and atr <= thresholds.atr_low:
            return VolatilityRegime.LOW
        return VolatilityRegime.NORMAL

    def _classify_liquidity(self, features: dict[str, float], thin_volume: float | None) -> LiquidityRegime:
        volume = features.get("volume")
        if volume is not None and thin_volume is not None and volume <= thin_volume:
            return LiquidityRegime.THIN
        return LiquidityRegime.NORMAL

    def _classify_risk(
        self,
        features: dict[str, float],
        trend: TrendRegime,
        volatility: VolatilityRegime,
        epsilon: float,
    ) -> RiskRegime:
        returns_1 = features.get("returns_1", 0.0)
        returns_5 = features.get("returns_5", returns_1)
        if volatility == VolatilityRegime.HIGH and (trend == TrendRegime.DOWNTREND or returns_1 < -epsilon or returns_5 < -epsilon):
            return RiskRegime.STRESSED
        return RiskRegime.NORMAL

    def _label(self, trend: TrendRegime, volatility: VolatilityRegime, risk: RiskRegime) -> str:
        trend_word = {
            TrendRegime.UPTREND: "Bull",
            TrendRegime.DOWNTREND: "Bear",
            TrendRegime.SIDEWAYS: "Range",
        }[trend]
        if trend == TrendRegime.SIDEWAYS and volatility == VolatilityRegime.HIGH:
            return "Choppy High Volatility"
        if trend == TrendRegime.SIDEWAYS and volatility == VolatilityRegime.LOW:
            return "Low Volatility Range"
        if volatility == VolatilityRegime.HIGH:
            return f"{trend_word} High Volatility"
        if risk == RiskRegime.STRESSED:
            return f"{trend_word} Stressed"
        if trend == TrendRegime.SIDEWAYS:
            return "Range"
        return f"{trend_word} Trend"

    def _confidence(
        self,
        features: dict[str, float],
        trend: TrendRegime,
        volatility: VolatilityRegime,
        liquidity: LiquidityRegime,
        risk: RiskRegime,
    ) -> float:
        score = 0.55
        sma_20 = features.get("sma_20")
        sma_50 = features.get("sma_50")
        close_proxy = max(abs(sma_50 or 0.0), 1.0)
        if sma_20 is not None and sma_50 is not None:
            score += min(abs(sma_20 - sma_50) / close_proxy, 0.20)
        score += min(abs(features.get("returns_5", features.get("returns_1", 0.0))) * 2, 0.15)
        if volatility != VolatilityRegime.NORMAL:
            score += 0.05
        if liquidity == LiquidityRegime.THIN or risk == RiskRegime.STRESSED:
            score -= 0.05
        if trend == TrendRegime.SIDEWAYS:
            score -= 0.03
        return max(0.35, min(score, 0.98))

    def _explanation(
        self,
        features: dict[str, float],
        trend: TrendRegime,
        volatility: VolatilityRegime,
        liquidity: LiquidityRegime,
        risk: RiskRegime,
    ) -> str:
        parts: list[str] = []
        if trend == TrendRegime.UPTREND:
            parts.append("The 20-period average remains above the 50-period average and recent returns are positive.")
        elif trend == TrendRegime.DOWNTREND:
            parts.append("The 20-period average remains below the 50-period average and recent returns are negative.")
        else:
            parts.append("Trend signals are mixed, so the market is best treated as range-bound.")

        parts.append(
            {
                VolatilityRegime.LOW: "Volatility is muted.",
                VolatilityRegime.NORMAL: "Volatility is moderate.",
                VolatilityRegime.HIGH: "Volatility is elevated.",
            }[volatility]
        )
        if liquidity == LiquidityRegime.THIN:
            parts.append("Liquidity appears thin compared with recent history.")
        if risk == RiskRegime.STRESSED:
            parts.append("High volatility with negative returns marks the tape as stressed.")
        elif features.get("returns_1", 0.0) > 0 or features.get("returns_5", 0.0) > 0:
            parts.append("Recent returns are positive.")
        return " ".join(parts)
