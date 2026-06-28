from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import (
    AssetORM,
    BacktestRunORM,
    DatasetORM,
    FeatureSnapshotORM,
    MarketRegimeSnapshotORM,
    SignalORM,
    StrategyORM,
    StrategyTemplateORM,
    StrategyVersionORM,
)
from app.db.repositories import _new_id, create_audit_event
from maelstromhub_core import (
    BacktestEvaluation,
    BacktestRun,
    BacktestStatus,
    BacktestVerdict,
    Signal,
    SignalRunResult,
    SignalSide,
    Strategy,
    StrategyParameterValue,
    StrategyPromotionResult,
    StrategyStatus,
    StrategyTemplate,
    StrategyVersion,
    StrategyVersionCreate,
)


SMA_CROSSOVER_TEMPLATE_ID = UUID("3af69744-0317-49ec-8850-b8494d40a1be")
RSI_MEAN_REVERSION_TEMPLATE_ID = UUID("fc33a083-aabc-4e37-bd46-eb31ac5d5a3c")

TEMPLATE_KEYS = {
    SMA_CROSSOVER_TEMPLATE_ID: "sma_crossover",
    RSI_MEAN_REVERSION_TEMPLATE_ID: "rsi_mean_reversion",
}

TEMPLATE_DEFINITIONS = [
    StrategyTemplate(
        id=SMA_CROSSOVER_TEMPLATE_ID,
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
        id=RSI_MEAN_REVERSION_TEMPLATE_ID,
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
    strategy_id: UUID,
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
        id=_new_id(),
        strategy_id=strategy.id,
        template_id=template.id,
        dataset_id=payload.dataset_id,
        version_number=next_number,
        parameters=parameters,
        allowed_regimes=payload.allowed_regimes,
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


async def list_strategy_versions(session: AsyncSession, strategy_id: UUID) -> list[StrategyVersion]:
    await _get_or_404(session, StrategyORM, strategy_id)
    result = await session.execute(
        select(StrategyVersionORM)
        .where(StrategyVersionORM.strategy_id == strategy_id)
        .order_by(StrategyVersionORM.version_number.desc())
    )
    return [StrategyVersion.model_validate(version) for version in result.scalars()]


async def promote_strategy(session: AsyncSession, strategy_id: UUID) -> StrategyPromotionResult:
    strategy = await _get_or_404(session, StrategyORM, strategy_id)
    from_status = StrategyStatus(strategy.status)
    if from_status == StrategyStatus.DRAFT:
        return await _promote_draft_to_backtested(session, strategy, from_status)
    if from_status == StrategyStatus.BACKTESTED:
        return await _promote_backtested_to_paper_trading(session, strategy, from_status)
    return await _block_strategy_promotion(
        session,
        strategy,
        from_status,
        from_status,
        [f"Promotion from {from_status.value} is not supported by the current lifecycle gate."],
    )


async def run_strategy_version_signals(session: AsyncSession, version_id: UUID) -> SignalRunResult:
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
    if version.allowed_regimes:
        regimes = await _load_regimes_by_timestamp(session, dataset.id)
        generated = _apply_regime_filter(generated, version.allowed_regimes, regimes)
        if any(signal.metadata.get("skipped") is True for signal in generated):
            await create_audit_event(
                session,
                actor="system",
                action="blocked_strategy_by_regime",
                subject=version.id,
                flush=False,
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


async def list_strategy_version_signals(session: AsyncSession, version_id: UUID) -> list[Signal]:
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


async def _get_or_404(session: AsyncSession, model: type[Any], item_id: UUID) -> Any:
    item = await session.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return item


async def _load_aligned_snapshots(
    session: AsyncSession,
    dataset_id: UUID,
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


async def _load_regimes_by_timestamp(session: AsyncSession, dataset_id: UUID) -> dict[datetime, MarketRegimeSnapshotORM]:
    result = await session.execute(
        select(MarketRegimeSnapshotORM)
        .where(MarketRegimeSnapshotORM.dataset_id == dataset_id)
        .order_by(MarketRegimeSnapshotORM.timestamp.asc())
    )
    return {snapshot.timestamp.astimezone(UTC): snapshot for snapshot in result.scalars()}


def _apply_regime_filter(
    generated_signals: list[GeneratedSignal],
    allowed_regimes: list[str],
    regimes: dict[datetime, MarketRegimeSnapshotORM],
) -> list[GeneratedSignal]:
    allowed = set(allowed_regimes)
    filtered: list[GeneratedSignal] = []
    for generated in generated_signals:
        regime = regimes.get(generated.timestamp.astimezone(UTC))
        if regime is None or regime.regime_label in allowed:
            metadata = {**generated.metadata}
            if regime is not None:
                metadata["regime_label"] = regime.regime_label
            filtered.append(GeneratedSignal(**{**generated.__dict__, "metadata": metadata}))
            continue
        filtered.append(
            GeneratedSignal(
                timestamp=generated.timestamp,
                side=SignalSide.FLAT,
                confidence=0.0,
                reason=f"Blocked by regime filter. Current regime {regime.regime_label} is not allowed.",
                suggested_size=0.0,
                metadata={
                    **generated.metadata,
                    "skipped": True,
                    "skip_reason": "Blocked by regime filter.",
                    "regime_label": regime.regime_label,
                    "original_side": generated.side.value,
                },
            )
        )
    return filtered


def _run_template(
    *,
    template_id: UUID,
    parameters: dict[str, object],
    snapshots: list[tuple[datetime, dict[str, float]]],
) -> list[GeneratedSignal]:
    template_key = TEMPLATE_KEYS.get(template_id)
    if template_key == "sma_crossover":
        return [_run_sma_crossover(timestamp, values, parameters) for timestamp, values in snapshots]
    if template_key == "rsi_mean_reversion":
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
                    id=_new_id(),
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


async def _promote_draft_to_backtested(
    session: AsyncSession,
    strategy: StrategyORM,
    from_status: StrategyStatus,
) -> StrategyPromotionResult:
    runs = await _list_succeeded_backtests_for_strategy(session, strategy.id)
    if not runs:
        return await _block_strategy_promotion(
            session,
            strategy,
            from_status,
            StrategyStatus.BACKTESTED,
            ["Run at least one successful backtest before promoting this draft."],
        )

    evaluated = [(run, _evaluate_backtest_run(run)) for run in runs]
    passing = [(run, evaluation) for run, evaluation in evaluated if evaluation.verdict == BacktestVerdict.READY]
    selected_run, selected_evaluation = max(
        passing or evaluated,
        key=lambda item: (_verdict_rank(item[1].verdict), item[1].risk_adjusted_score),
    )
    if not passing:
        return await _block_strategy_promotion(
            session,
            strategy,
            from_status,
            StrategyStatus.BACKTESTED,
            selected_evaluation.reasons,
            backtest_run=_run_to_schema(selected_run),
            evaluation=selected_evaluation,
        )

    strategy.status = StrategyStatus.BACKTESTED.value
    await create_audit_event(
        session,
        actor="system",
        action="promoted_strategy_to_backtested",
        subject=strategy.id,
        flush=False,
    )
    await session.commit()
    await session.refresh(strategy)
    return StrategyPromotionResult(
        strategy=Strategy.model_validate(strategy),
        promoted=True,
        from_status=from_status,
        to_status=StrategyStatus.BACKTESTED,
        reasons=[],
        backtest_run=_run_to_schema(selected_run),
        evaluation=selected_evaluation,
    )


async def _promote_backtested_to_paper_trading(
    session: AsyncSession,
    strategy: StrategyORM,
    from_status: StrategyStatus,
) -> StrategyPromotionResult:
    runs = await _list_succeeded_backtests_for_strategy(session, strategy.id)
    if not runs:
        return await _block_strategy_promotion(
            session,
            strategy,
            from_status,
            StrategyStatus.PAPER_TRADING,
            ["Run at least one successful backtest before promoting this strategy to Paper Trading."],
        )

    latest_run = runs[0]
    evaluation = _evaluate_backtest_run(latest_run)
    if evaluation.verdict == BacktestVerdict.BLOCKED:
        return await _block_strategy_promotion(
            session,
            strategy,
            from_status,
            StrategyStatus.PAPER_TRADING,
            ["Latest backtest verdict is too risky for Paper Trading.", *evaluation.reasons],
            backtest_run=_run_to_schema(latest_run),
            evaluation=evaluation,
        )

    strategy.status = StrategyStatus.PAPER_TRADING.value
    await create_audit_event(
        session,
        actor="system",
        action="promoted_strategy_to_paper_trading",
        subject=strategy.id,
        flush=False,
    )
    await session.commit()
    await session.refresh(strategy)
    return StrategyPromotionResult(
        strategy=Strategy.model_validate(strategy),
        promoted=True,
        from_status=from_status,
        to_status=StrategyStatus.PAPER_TRADING,
        reasons=[],
        backtest_run=_run_to_schema(latest_run),
        evaluation=evaluation,
    )


async def _block_strategy_promotion(
    session: AsyncSession,
    strategy: StrategyORM,
    from_status: StrategyStatus,
    to_status: StrategyStatus,
    reasons: list[str],
    *,
    backtest_run: BacktestRun | None = None,
    evaluation: BacktestEvaluation | None = None,
) -> StrategyPromotionResult:
    await create_audit_event(
        session,
        actor="system",
        action="blocked_strategy_promotion",
        subject=strategy.id,
        flush=False,
    )
    await session.commit()
    await session.refresh(strategy)
    return StrategyPromotionResult(
        strategy=Strategy.model_validate(strategy),
        promoted=False,
        from_status=from_status,
        to_status=to_status,
        reasons=reasons,
        backtest_run=backtest_run,
        evaluation=evaluation,
    )


async def _list_succeeded_backtests_for_strategy(session: AsyncSession, strategy_id: UUID) -> list[BacktestRunORM]:
    result = await session.execute(
        select(BacktestRunORM)
        .join(StrategyVersionORM, StrategyVersionORM.id == BacktestRunORM.strategy_version_id)
        .where(
            StrategyVersionORM.strategy_id == strategy_id,
            BacktestRunORM.status == BacktestStatus.SUCCEEDED.value,
        )
        .order_by(BacktestRunORM.created_at.desc())
    )
    return list(result.scalars())


def _evaluate_backtest_run(run: BacktestRunORM) -> BacktestEvaluation:
    total_return = _metric(run, "total_return")
    max_drawdown = _metric(run, "max_drawdown")
    trade_count = int(_metric(run, "trade_count"))
    reasons: list[str] = []
    if max_drawdown < settings.promotion_max_drawdown_threshold:
        reasons.append(
            "Max drawdown is too deep: "
            f"{max_drawdown:.2%} is worse than the {settings.promotion_max_drawdown_threshold:.2%} limit."
        )
    if trade_count < settings.promotion_min_trade_count:
        reasons.append(
            "Trade count is too low: "
            f"{trade_count} completed trades is below the minimum of {settings.promotion_min_trade_count}."
        )
    if total_return < settings.promotion_min_total_return:
        reasons.append(
            "Total return is catastrophically negative: "
            f"{total_return:.2%} is below the {settings.promotion_min_total_return:.2%} floor."
        )
    score = _risk_adjusted_score(total_return, max_drawdown)
    if reasons:
        verdict = BacktestVerdict.BLOCKED
    elif total_return <= 0 or score < 1:
        verdict = BacktestVerdict.REVIEW
    else:
        verdict = BacktestVerdict.READY
    return BacktestEvaluation(
        verdict=verdict,
        risk_adjusted_score=score,
        reasons=reasons,
        thresholds={
            "max_drawdown": settings.promotion_max_drawdown_threshold,
            "min_trade_count": settings.promotion_min_trade_count,
            "min_total_return": settings.promotion_min_total_return,
        },
    )


def _metric(run: BacktestRunORM, key: str) -> float:
    value = run.metrics.get(key)
    return float(value) if isinstance(value, int | float | str) else 0.0


def _risk_adjusted_score(total_return: float, max_drawdown: float) -> float:
    return total_return / max(abs(max_drawdown), 0.01)


def _verdict_rank(verdict: BacktestVerdict) -> int:
    return {
        BacktestVerdict.BLOCKED: 0,
        BacktestVerdict.REVIEW: 1,
        BacktestVerdict.READY: 2,
    }[verdict]


def _run_to_schema(run: BacktestRunORM) -> BacktestRun:
    return BacktestRun(
        id=run.id,
        strategy_version_id=run.strategy_version_id,
        dataset_id=run.dataset_id,
        status=BacktestStatus(run.status),
        starting_balance=float(run.starting_balance),
        fee_bps=float(run.fee_bps),
        slippage_bps=float(run.slippage_bps),
        created_at=run.created_at,
        finished_at=run.finished_at,
        metrics=run.metrics,
    )


def _number_parameter(parameters: dict[str, object], key: str, fallback: float) -> float:
    value = parameters.get(key, fallback)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return fallback
