from collections import defaultdict
from datetime import datetime

from app.config import settings
from app.market_intelligence.classifier import RegimeClassification, RegimeClassifier, RegimeThresholds

REQUIRED_REGIME_FEATURES = ["returns_1", "returns_5", "sma_20", "sma_50", "volatility_20", "rsi_14", "atr_14"]


class RegimeEngine:
    def __init__(self, classifier: RegimeClassifier | None = None) -> None:
        self.classifier = classifier or RegimeClassifier()

    def compute(self, snapshots: list[tuple[datetime, str, float]]) -> list[RegimeClassification]:
        aligned = self._align(snapshots)
        if not aligned:
            return []
        thresholds = self._thresholds([features for _, features in aligned])
        return [self.classifier.classify(timestamp, features, thresholds) for timestamp, features in aligned]

    def _align(self, snapshots: list[tuple[datetime, str, float]]) -> list[tuple[datetime, dict[str, float]]]:
        by_timestamp: dict[datetime, dict[str, float]] = defaultdict(dict)
        for timestamp, feature_name, value in snapshots:
            by_timestamp[timestamp][feature_name] = value
        return [
            (timestamp, values)
            for timestamp, values in sorted(by_timestamp.items())
            if all(feature_name in values for feature_name in REQUIRED_REGIME_FEATURES)
        ]

    def _thresholds(self, rows: list[dict[str, float]]) -> RegimeThresholds:
        volatility_values = [row["volatility_20"] for row in rows]
        atr_values = [row["atr_14"] for row in rows]
        volume_values = [row["volume"] for row in rows if "volume" in row]
        thin_volume = (
            self._percentile(volume_values, settings.regime_thin_liquidity_volume_percentile)
            if volume_values
            else None
        )
        return RegimeThresholds(
            volatility_low=self._percentile(volatility_values, settings.regime_volatility_low_percentile),
            volatility_high=self._percentile(volatility_values, settings.regime_volatility_high_percentile),
            atr_low=self._percentile(atr_values, settings.regime_atr_low_percentile),
            atr_high=self._percentile(atr_values, settings.regime_atr_high_percentile),
            thin_liquidity_volume=thin_volume,
            return_epsilon=settings.regime_return_epsilon,
        )

    def _percentile(self, values: list[float], percentile: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        index = min(max(round((len(ordered) - 1) * percentile), 0), len(ordered) - 1)
        return ordered[index]
