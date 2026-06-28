from dataclasses import dataclass, field
from datetime import datetime
from math import sqrt


@dataclass(frozen=True)
class CandleInput:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class FeatureValue:
    timestamp: datetime
    feature_name: str
    numeric_value: float
    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)


DEFAULT_FEATURES = [
    "returns_1",
    "returns_5",
    "sma_20",
    "sma_50",
    "volatility_20",
    "rsi_14",
    "atr_14",
]


def calculate_features(
    candles: list[CandleInput],
    feature_names: list[str] | None = None,
) -> list[FeatureValue]:
    ordered = sorted(candles, key=lambda candle: candle.timestamp)
    requested = feature_names or DEFAULT_FEATURES
    values: list[FeatureValue] = []

    for feature_name in requested:
        if feature_name == "returns_1":
            values.extend(_returns(ordered, 1))
        elif feature_name == "returns_5":
            values.extend(_returns(ordered, 5))
        elif feature_name == "sma_20":
            values.extend(_sma(ordered, 20))
        elif feature_name == "sma_50":
            values.extend(_sma(ordered, 50))
        elif feature_name == "volatility_20":
            values.extend(_volatility(ordered, 20))
        elif feature_name == "rsi_14":
            values.extend(_rsi(ordered, 14))
        elif feature_name == "atr_14":
            values.extend(_atr(ordered, 14))
        else:
            raise ValueError(f"Unknown feature calculator: {feature_name}")

    return values


def _returns(candles: list[CandleInput], period: int) -> list[FeatureValue]:
    results: list[FeatureValue] = []
    for index in range(period, len(candles)):
        previous = candles[index - period].close
        if previous == 0:
            continue
        results.append(
            FeatureValue(
                timestamp=candles[index].timestamp,
                feature_name=f"returns_{period}",
                numeric_value=(candles[index].close / previous) - 1,
                metadata={"period": period},
            )
        )
    return results


def _sma(candles: list[CandleInput], window: int) -> list[FeatureValue]:
    results: list[FeatureValue] = []
    for index in range(window - 1, len(candles)):
        closes = [candle.close for candle in candles[index - window + 1 : index + 1]]
        results.append(
            FeatureValue(
                timestamp=candles[index].timestamp,
                feature_name=f"sma_{window}",
                numeric_value=sum(closes) / window,
                metadata={"window": window},
            )
        )
    return results


def _volatility(candles: list[CandleInput], window: int) -> list[FeatureValue]:
    returns = _returns(candles, 1)
    results: list[FeatureValue] = []
    for index in range(window - 1, len(returns)):
        sample = [item.numeric_value for item in returns[index - window + 1 : index + 1]]
        mean = sum(sample) / window
        variance = sum((value - mean) ** 2 for value in sample) / window
        results.append(
            FeatureValue(
                timestamp=returns[index].timestamp,
                feature_name=f"volatility_{window}",
                numeric_value=sqrt(variance),
                metadata={"window": window},
            )
        )
    return results


def _rsi(candles: list[CandleInput], window: int) -> list[FeatureValue]:
    results: list[FeatureValue] = []
    for index in range(window, len(candles)):
        changes = [candles[i].close - candles[i - 1].close for i in range(index - window + 1, index + 1)]
        gains = [change for change in changes if change > 0]
        losses = [-change for change in changes if change < 0]
        average_gain = sum(gains) / window
        average_loss = sum(losses) / window
        if average_loss == 0:
            rsi = 100.0
        else:
            relative_strength = average_gain / average_loss
            rsi = 100 - (100 / (1 + relative_strength))
        results.append(
            FeatureValue(
                timestamp=candles[index].timestamp,
                feature_name=f"rsi_{window}",
                numeric_value=rsi,
                metadata={"window": window},
            )
        )
    return results


def _atr(candles: list[CandleInput], window: int) -> list[FeatureValue]:
    true_ranges: list[tuple[datetime, float]] = []
    for index, candle in enumerate(candles):
        if index == 0:
            true_range = candle.high - candle.low
        else:
            previous_close = candles[index - 1].close
            true_range = max(
                candle.high - candle.low,
                abs(candle.high - previous_close),
                abs(candle.low - previous_close),
            )
        true_ranges.append((candle.timestamp, true_range))

    results: list[FeatureValue] = []
    for index in range(window - 1, len(true_ranges)):
        window_values = [item[1] for item in true_ranges[index - window + 1 : index + 1]]
        results.append(
            FeatureValue(
                timestamp=true_ranges[index][0],
                feature_name=f"atr_{window}",
                numeric_value=sum(window_values) / window,
                metadata={"window": window},
            )
        )
    return results
