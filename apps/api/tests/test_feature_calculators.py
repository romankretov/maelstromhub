from datetime import UTC, datetime, timedelta

from app.features.calculators import CandleInput, calculate_features


def make_candles(count: int) -> list[CandleInput]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    candles: list[CandleInput] = []
    for index in range(count):
        close = float(index + 1)
        candles.append(
            CandleInput(
                timestamp=start + timedelta(hours=index),
                open=close,
                high=close + 1,
                low=close - 1,
                close=close,
            )
        )
    return candles


def test_feature_calculators_known_values() -> None:
    features = calculate_features(make_candles(60))
    by_name = {}
    for feature in features:
        by_name.setdefault(feature.feature_name, []).append(feature)

    assert by_name["returns_1"][0].numeric_value == 1.0
    assert by_name["returns_5"][0].numeric_value == 5.0
    assert by_name["sma_20"][0].numeric_value == 10.5
    assert by_name["sma_50"][0].numeric_value == 25.5
    assert by_name["rsi_14"][0].numeric_value == 100.0
    assert by_name["atr_14"][0].numeric_value == 2.0
    assert len(by_name["volatility_20"]) == 40
