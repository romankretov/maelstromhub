from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AssetORM,
    DatasetORM,
    FeatureSnapshotORM,
    SignalORM,
    StrategyORM,
    StrategyTemplateORM,
    StrategyVersionORM,
)
from app.db.repositories import _new_id, create_audit_event
from maelstromhub_core import (
    Signal,
    SignalRunResult,
    SignalSide,
    StrategyParameterValue,
    StrategyTemplate,
    StrategyVersion,
    StrategyVersionCreate,
)


TEMPLATE_DEFINITIONS = [
    StrategyTemplate(
        id="sma_crossover",
        name="SMA crossover",
        description="Compares short and long moving averages to emit long, short, or flat directional signals.",
        required_features=["sma_20", "sma_50"],
        parameters={
            "fast_window": StrategyParameterValue.NUMBER.value,
            "slow_window": StrategyParameterValue.NUMBER.value,
            "confidence": StrategyParameterValue.NUMBER.value,
            "suggested_size": StrategyParameterValue.NUMBER.value,
        },
        default_parameters={
            "fast_window": 20,
            "slow_window": 50,
            "confidence": 0.7,
            "suggested_size": 1.0,
        },
    ),
    StrategyTemplate(
        id="rsi_mean_reversion",
        name="RSI mean reversion",
        description="Uses RSI thresholds to look for stretched markets that may mean revert.",
        required_features=["rsi_14"],
        parameters={
            "oversold": StrategyParameterValue.NUMBER.value,
            "overbought": StrategyParameterValue.NUMBER.value,
            "confidence": StrategyParameterValue.NUMBER.value,
            "suggested_size": StrategyParameterValue.NUMBER.value,
        },
        default_parameters={
            "oversold": 30,
            "overbought": 70,
            "confidence": 0.65,
            "suggested_size": 1.0,
        },
    ),
]


@dataclass(frozen=True)
class GeneratedSignal:
    timestamp: datetime
    side: SignalSide
    confidence: float
    reason: str
    suggested_size: float
    metadata: dict[str, str | int | float | bool | None]


async def list_strategy_templates(session: AsyncSession) -> list[StrategyTemplate]:
    await ensure_strategy_templates(session)
    result = await session.execute(select(StrategyTemplateORM).order_by(StrategyTemplateORM.name.asc()))
    return [StrategyTemplate.model_validate(template) for template in result.scalars()]


async def create_strategy_version(
    session: AsyncSession,
    strategy_id: str,
    payload: StrategyVersionCreate,
) -> StrategyVersion:
    await ensure_strategy_templates(session)
    strategy = await _get_or_404(session, StrategyORM, strategy_id)
    template = await _get_or_404(session, StrategyTemplateORM, payload.template_id)
    await _get_or_404(session, DatasetORM, payload.dataset_id)

    next_number_result = await session.execute(
        select(func.max(StrategyVersionORM.version_number)).where(StrategyVersionORM.strategy_id == strategy.id)
    )
    next_number = int(next_number_result.scalar_one_or_none() or 0) + 1
    parameters = {**template.default_parameters, **payload.parameters}
    version = StrategyVersionORM(
        id=_new_id("strategy-version"),
        strategy_id=strategy.id,
        template_id=template.id,
        dataset_id=payload.dataset_id,
        version_number=next_number,
        parameters=parameters,
    )
    session.add(version)
    await session.flush()
    await create_audit_event(
        session,
        actor="system",
        action="created_strategy_version",
        subject=version.id,
        flush=False,
    )
    await session.commit()
    await session.refresh(version)
    return StrategyVersion.model_validate(version)


async def list_strategy_versions(session: AsyncSession, strategy_id: str) -> list[StrategyVersion]:
    await _get_or_404(session, StrategyORM, strategy_id)
    result = await session.execute(
        select(StrategyVersionORM)
        .where(StrategyVersionORM.strategy_id == strategy_id)
        .order_by(StrategyVersionORM.version_number.desc())
    )
    return [StrategyVersion.model_validate(version) for version in result.scalars()]


async def run_strategy_version_signals(session: AsyncSession, version_id: str) -> SignalRunResult:
    version = await _get_or_404(session, StrategyVersionORM, version_id)
    template = await _get_or_404(session, StrategyTemplateORM, version.template_id)
    dataset = await _get_or_404(session, DatasetORM, version.dataset_id)
    asset = await _get_or_404(session, AssetORM, dataset.asset_id)
    snapshots = await _load_aligned_snapshots(session, dataset.id, template.required_features)
    generated = _run_template(
        template_id=template.id,
        parameters=version.parameters,
        snapshots=snapshots,
    )
    written = await _upsert_signals(
        session,
        version=version,
        symbol=asset.symbol,
        generated_signals=generated,
    )
    await create_audit_event(
        session,
        actor="system",
        action="ran_strategy_signals",
        subject=version.id,
        flush=False,
    )
    await session.commit()
    return SignalRunResult(
        strategy_version_id=version.id,
        signals_written=written,
        total_signals=len(await list_strategy_version_signals(session, version.id)),
    )


async def list_strategy_version_signals(session: AsyncSession, version_id: str) -> list[Signal]:
    await _get_or_404(session, StrategyVersionORM, version_id)
    result = await session.execute(
        select(SignalORM).where(SignalORM.strategy_version_id == version_id).order_by(SignalORM.timestamp.desc())
    )
    return [_signal_to_schema(signal) for signal in result.scalars()]


async def ensure_strategy_templates(session: AsyncSession) -> None:
    changed = False
    for definition in TEMPLATE_DEFINITIONS:
        template = await session.get(StrategyTemplateORM, definition.id)
        values = definition.model_dump(exclude={"created_at"})
        if template is None:
            session.add(StrategyTemplateORM(**values))
            changed = True
        else:
            template.name = definition.name
            template.description = definition.description
            template.required_features = definition.required_features
            template.parameters = definition.parameters
            template.default_parameters = definition.default_parameters
            changed = True
    if changed:
        await session.commit()


async def _get_or_404(session: AsyncSession, model: type[Any], item_id: str) -> Any:
    item = await session.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return item


async def _load_aligned_snapshots(
    session: AsyncSession,
    dataset_id: str,
    required_features: list[str],
) -> list[tuple[datetime, dict[str, float]]]:
    result = await session.execute(
        select(FeatureSnapshotORM)
        .where(
            FeatureSnapshotORM.dataset_id == dataset_id,
            FeatureSnapshotORM.feature_name.in_(required_features),
        )
        .order_by(FeatureSnapshotORM.timestamp.asc())
    )
    by_timestamp: dict[datetime, dict[str, float]] = {}
    for snapshot in result.scalars():
        by_timestamp.setdefault(snapshot.timestamp, {})[snapshot.feature_name] = float(snapshot.numeric_value)
    return [
        (timestamp, values)
        for timestamp, values in sorted(by_timestamp.items())
        if all(feature_name in values for feature_name in required_features)
    ]


def _run_template(
    *,
    template_id: str,
    parameters: dict[str, object],
    snapshots: list[tuple[datetime, dict[str, float]]],
) -> list[GeneratedSignal]:
    if template_id == "sma_crossover":
        return [_run_sma_crossover(timestamp, values, parameters) for timestamp, values in snapshots]
    if template_id == "rsi_mean_reversion":
        return [_run_rsi_mean_reversion(timestamp, values, parameters) for timestamp, values in snapshots]
    raise HTTPException(status_code=400, detail=f"Unsupported strategy template: {template_id}")


def _run_sma_crossover(
    timestamp: datetime,
    values: dict[str, float],
    parameters: dict[str, object],
) -> GeneratedSignal:
    fast = values["sma_20"]
    slow = values["sma_50"]
    if fast > slow:
        side = SignalSide.LONG
    elif fast < slow:
        side = SignalSide.SHORT
    else:
        side = SignalSide.FLAT
    return GeneratedSignal(
        timestamp=timestamp,
        side=side,
        confidence=_number_parameter(parameters, "confidence", 0.7),
        reason=f"sma_20={fast:.4f}, sma_50={slow:.4f}",
        suggested_size=_number_parameter(parameters, "suggested_size", 1.0),
        metadata={
            "template": "sma_crossover",
            "fast_window": _number_parameter(parameters, "fast_window", 20),
            "slow_window": _number_parameter(parameters, "slow_window", 50),
            "sma_20": fast,
            "sma_50": slow,
        },
    )


def _run_rsi_mean_reversion(
    timestamp: datetime,
    values: dict[str, float],
    parameters: dict[str, object],
) -> GeneratedSignal:
    rsi = values["rsi_14"]
    oversold = _number_parameter(parameters, "oversold", 30)
    overbought = _number_parameter(parameters, "overbought", 70)
    if rsi <= oversold:
        side = SignalSide.LONG
    elif rsi >= overbought:
        side = SignalSide.SHORT
    else:
        side = SignalSide.FLAT
    return GeneratedSignal(
        timestamp=timestamp,
        side=side,
        confidence=_number_parameter(parameters, "confidence", 0.65),
        reason=f"rsi_14={rsi:.4f}, oversold={oversold:.2f}, overbought={overbought:.2f}",
        suggested_size=_number_parameter(parameters, "suggested_size", 1.0),
        metadata={
            "template": "rsi_mean_reversion",
            "oversold": oversold,
            "overbought": overbought,
            "rsi_14": rsi,
        },
    )


async def _upsert_signals(
    session: AsyncSession,
    *,
    version: StrategyVersionORM,
    symbol: str,
    generated_signals: list[GeneratedSignal],
) -> int:
    written = 0
    for generated in generated_signals:
        timestamp = generated.timestamp.astimezone(UTC)
        existing_result = await session.execute(
            select(SignalORM).where(
                SignalORM.strategy_version_id == version.id,
                SignalORM.timestamp == timestamp,
            )
        )
        existing = existing_result.scalar_one_or_none()
        values = {
            "strategy_id": version.strategy_id,
            "dataset_id": version.dataset_id,
            "symbol": symbol,
            "side": generated.side.value,
            "confidence": generated.confidence,
            "reason": generated.reason,
            "suggested_size": generated.suggested_size,
            "metadata_json": generated.metadata,
        }
        if existing is None:
            session.add(
                SignalORM(
                    id=_new_id("signal"),
                    strategy_version_id=version.id,
                    timestamp=timestamp,
                    **values,
                )
            )
        else:
            for key, value in values.items():
                setattr(existing, key, value)
        written += 1
    await session.flush()
    return written


def _signal_to_schema(signal: SignalORM) -> Signal:
    return Signal(
        id=signal.id,
        strategy_version_id=signal.strategy_version_id,
        strategy_id=signal.strategy_id,
        dataset_id=signal.dataset_id,
        timestamp=signal.timestamp,
        symbol=signal.symbol,
        side=SignalSide(signal.side),
        confidence=float(signal.confidence),
        reason=signal.reason,
        suggested_size=float(signal.suggested_size),
        metadata=signal.metadata_json,
        created_at=signal.created_at,
    )


def _number_parameter(parameters: dict[str, object], key: str, fallback: float) -> float:
    value = parameters.get(key, fallback)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return fallback
