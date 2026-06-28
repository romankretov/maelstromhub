from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    BacktestRunORM,
    BacktestTradeORM,
    CandleORM,
    EquityCurveSnapshotORM,
    MarketRegimeSnapshotORM,
    SignalORM,
    StrategyVersionORM,
)
from app.db.repositories import _new_id, create_audit_event
from maelstromhub_core import (
    BacktestRun,
    BacktestRunCreate,
    BacktestRunDetail,
    BacktestStatus,
    BacktestTrade,
    EquityCurveSnapshot,
    SignalSide,
)


@dataclass
class OpenPosition:
    symbol: str
    entry_timestamp: datetime
    entry_price: float
    quantity: float
    entry_fee: float
    reason: str


async def create_backtest_run(
    session: AsyncSession,
    version_id: UUID,
    payload: BacktestRunCreate,
) -> BacktestRunDetail:
    version = await _get_or_404(session, StrategyVersionORM, version_id)
    run = BacktestRunORM(
        id=_new_id(),
        strategy_version_id=version.id,
        dataset_id=version.dataset_id,
        status=BacktestStatus.STARTED.value,
        starting_balance=payload.starting_balance,
        fee_bps=payload.fee_bps,
        slippage_bps=payload.slippage_bps,
        metrics={},
    )
    session.add(run)
    await session.flush()
    await create_audit_event(session, actor="system", action="started_backtest", subject=run.id, flush=False)
    await session.commit()

    try:
        await _run_backtest(session, run, version)
        run.status = BacktestStatus.SUCCEEDED.value
        run.finished_at = datetime.now(UTC)
        await create_audit_event(session, actor="system", action="succeeded_backtest", subject=run.id, flush=False)
        await session.commit()
    except Exception as error:
        run.status = BacktestStatus.FAILED.value
        run.finished_at = datetime.now(UTC)
        run.metrics = {"error": str(error)}
        await create_audit_event(session, actor="system", action="failed_backtest", subject=run.id, flush=False)
        await session.commit()

    return await get_backtest_run(session, run.id)


async def list_strategy_version_backtests(session: AsyncSession, version_id: UUID) -> list[BacktestRun]:
    await _get_or_404(session, StrategyVersionORM, version_id)
    result = await session.execute(
        select(BacktestRunORM)
        .where(BacktestRunORM.strategy_version_id == version_id)
        .order_by(BacktestRunORM.created_at.desc())
    )
    return [_run_to_schema(run) for run in result.scalars()]


async def get_backtest_run(session: AsyncSession, backtest_id: UUID) -> BacktestRunDetail:
    run = await _get_or_404(session, BacktestRunORM, backtest_id)
    trades_result = await session.execute(
        select(BacktestTradeORM)
        .where(BacktestTradeORM.backtest_run_id == run.id)
        .order_by(BacktestTradeORM.timestamp.asc())
    )
    equity_result = await session.execute(
        select(EquityCurveSnapshotORM)
        .where(EquityCurveSnapshotORM.backtest_run_id == run.id)
        .order_by(EquityCurveSnapshotORM.timestamp.asc())
    )
    return BacktestRunDetail(
        **_run_to_schema(run).model_dump(),
        trades=[_trade_to_schema(trade) for trade in trades_result.scalars()],
        equity_curve=[_equity_to_schema(snapshot) for snapshot in equity_result.scalars()],
    )


async def _run_backtest(session: AsyncSession, run: BacktestRunORM, version: StrategyVersionORM) -> None:
    candles = await _load_candles(session, run.dataset_id)
    signals = await _load_signals_by_timestamp(session, version.id)
    regimes = await _load_regimes_by_timestamp(session, run.dataset_id)
    cash = float(run.starting_balance)
    fee_rate = float(run.fee_bps) / 10_000
    slippage_rate = float(run.slippage_bps) / 10_000
    max_equity = cash
    position: OpenPosition | None = None
    trades: list[BacktestTradeORM] = []
    equity_snapshots: list[EquityCurveSnapshot] = []

    for candle in candles:
        timestamp = candle.opened_at.astimezone(UTC)
        close = float(candle.close)
        signal = signals.get(timestamp)
        if signal is not None:
            side = SignalSide(signal.side)
            if side == SignalSide.LONG and position is None:
                position, cash = _open_long(signal, close, cash, fee_rate, slippage_rate)
            elif side != SignalSide.LONG and position is not None:
                trade, cash = _close_long(run.id, position, signal, close, cash, fee_rate, slippage_rate)
                trades.append(trade)
                position = None

        equity = _current_equity(cash, position, close)
        max_equity = max(max_equity, equity)
        drawdown = 0.0 if max_equity == 0 else (equity - max_equity) / max_equity
        snapshot = EquityCurveSnapshotORM(
            id=_new_id(),
            backtest_run_id=run.id,
            timestamp=timestamp,
            equity=equity,
            drawdown=drawdown,
        )
        session.add(snapshot)
        equity_snapshots.append(_equity_to_schema(snapshot))

    if position is not None and candles:
        final_candle = candles[-1]
        final_signal = signals.get(final_candle.opened_at.astimezone(UTC))
        trade, cash = _close_long(
            run.id,
            position,
            final_signal,
            float(final_candle.close),
            cash,
            fee_rate,
            slippage_rate,
            reason="final candle close",
        )
        trades.append(trade)

    for trade in trades:
        session.add(trade)

    ending_equity = cash if position is None else _current_equity(cash, position, float(candles[-1].close))
    run.metrics = _calculate_metrics(
        starting_balance=float(run.starting_balance),
        ending_equity=ending_equity,
        trades=trades,
        equity_snapshots=equity_snapshots,
        candles=candles,
        regimes=regimes,
    )
    await session.flush()


async def _load_candles(session: AsyncSession, dataset_id: UUID) -> list[CandleORM]:
    result = await session.execute(
        select(CandleORM).where(CandleORM.dataset_id == dataset_id).order_by(CandleORM.opened_at.asc())
    )
    return list(result.scalars())


async def _load_signals_by_timestamp(session: AsyncSession, version_id: UUID) -> dict[datetime, SignalORM]:
    result = await session.execute(
        select(SignalORM).where(SignalORM.strategy_version_id == version_id).order_by(SignalORM.timestamp.asc())
    )
    return {signal.timestamp.astimezone(UTC): signal for signal in result.scalars()}


async def _load_regimes_by_timestamp(session: AsyncSession, dataset_id: UUID) -> dict[datetime, MarketRegimeSnapshotORM]:
    result = await session.execute(
        select(MarketRegimeSnapshotORM)
        .where(MarketRegimeSnapshotORM.dataset_id == dataset_id)
        .order_by(MarketRegimeSnapshotORM.timestamp.asc())
    )
    return {snapshot.timestamp.astimezone(UTC): snapshot for snapshot in result.scalars()}


def _open_long(
    signal: SignalORM,
    close: float,
    cash: float,
    fee_rate: float,
    slippage_rate: float,
) -> tuple[OpenPosition, float]:
    suggested_size = max(0.0, min(float(signal.suggested_size), 1.0))
    gross_notional = cash * suggested_size
    entry_fee = gross_notional * fee_rate
    entry_price = close * (1 + slippage_rate)
    quantity = 0.0 if entry_price == 0 else (gross_notional - entry_fee) / entry_price
    return (
        OpenPosition(
            symbol=signal.symbol,
            entry_timestamp=signal.timestamp,
            entry_price=entry_price,
            quantity=quantity,
            entry_fee=entry_fee,
            reason=signal.reason,
        ),
        cash - gross_notional,
    )


def _close_long(
    run_id: UUID,
    position: OpenPosition,
    signal: SignalORM | None,
    close: float,
    cash: float,
    fee_rate: float,
    slippage_rate: float,
    reason: str | None = None,
) -> tuple[BacktestTradeORM, float]:
    exit_price = close * (1 - slippage_rate)
    gross_exit = position.quantity * exit_price
    exit_fee = gross_exit * fee_rate
    pnl = (exit_price - position.entry_price) * position.quantity - position.entry_fee - exit_fee
    fees = position.entry_fee + exit_fee
    trade = BacktestTradeORM(
        id=_new_id(),
        backtest_run_id=run_id,
        timestamp=signal.timestamp if signal else position.entry_timestamp,
        symbol=position.symbol,
        side=SignalSide.LONG.value,
        entry_price=position.entry_price,
        exit_price=exit_price,
        quantity=position.quantity,
        pnl=pnl,
        fees=fees,
        reason=reason or (signal.reason if signal else "closed"),
    )
    return trade, cash + gross_exit - exit_fee


def _current_equity(cash: float, position: OpenPosition | None, close: float) -> float:
    if position is None:
        return cash
    return cash + position.quantity * close


def _calculate_metrics(
    *,
    starting_balance: float,
    ending_equity: float,
    trades: list[BacktestTradeORM],
    equity_snapshots: list[EquityCurveSnapshot],
    candles: list[CandleORM],
    regimes: dict[datetime, MarketRegimeSnapshotORM],
) -> dict[str, object]:
    wins = [float(trade.pnl) for trade in trades if float(trade.pnl) > 0]
    losses = [abs(float(trade.pnl)) for trade in trades if float(trade.pnl) < 0]
    gross_profit = sum(wins)
    gross_loss = sum(losses)
    metrics: dict[str, object] = {
        "total_return": 0.0 if starting_balance == 0 else (ending_equity - starting_balance) / starting_balance,
        "max_drawdown": min((snapshot.drawdown for snapshot in equity_snapshots), default=0.0),
        "win_rate": 0.0 if not trades else len(wins) / len(trades),
        "trade_count": len(trades),
        "profit_factor": gross_profit if gross_loss == 0 else gross_profit / gross_loss,
    }
    metrics.update(_regime_metrics(candles=candles, trades=trades, regimes=regimes))
    return metrics


def _regime_metrics(
    *,
    candles: list[CandleORM],
    trades: list[BacktestTradeORM],
    regimes: dict[datetime, MarketRegimeSnapshotORM],
) -> dict[str, object]:
    total_candles = len(candles)
    covered_candles = sum(1 for candle in candles if candle.opened_at.astimezone(UTC) in regimes)
    per_regime: dict[str, dict[str, float | int]] = {}
    for trade in trades:
        regime = regimes.get(trade.timestamp.astimezone(UTC))
        label = regime.regime_label if regime is not None else "Unknown"
        bucket = per_regime.setdefault(label, {"pnl": 0.0, "trade_count": 0, "wins": 0, "win_rate": 0.0})
        pnl = float(trade.pnl)
        bucket["pnl"] = float(bucket["pnl"]) + pnl
        bucket["trade_count"] = int(bucket["trade_count"]) + 1
        if pnl > 0:
            bucket["wins"] = int(bucket["wins"]) + 1
    for bucket in per_regime.values():
        trade_count = int(bucket["trade_count"])
        wins = int(bucket.pop("wins"))
        bucket["win_rate"] = 0.0 if trade_count == 0 else wins / trade_count
    return {
        "regime_coverage": {
            "covered_candles": covered_candles,
            "total_candles": total_candles,
            "coverage_ratio": 0.0 if total_candles == 0 else covered_candles / total_candles,
        },
        "pnl_by_regime": {label: bucket["pnl"] for label, bucket in per_regime.items()},
        "trade_count_by_regime": {label: bucket["trade_count"] for label, bucket in per_regime.items()},
        "win_rate_by_regime": {label: bucket["win_rate"] for label, bucket in per_regime.items()},
    }


async def _get_or_404(session: AsyncSession, model: type[Any], item_id: UUID) -> Any:
    item = await session.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return item


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


def _trade_to_schema(trade: BacktestTradeORM) -> BacktestTrade:
    return BacktestTrade(
        id=trade.id,
        backtest_run_id=trade.backtest_run_id,
        timestamp=trade.timestamp,
        symbol=trade.symbol,
        side=trade.side,
        entry_price=float(trade.entry_price),
        exit_price=float(trade.exit_price),
        quantity=float(trade.quantity),
        pnl=float(trade.pnl),
        fees=float(trade.fees),
        reason=trade.reason,
    )


def _equity_to_schema(snapshot: EquityCurveSnapshotORM) -> EquityCurveSnapshot:
    return EquityCurveSnapshot(
        id=snapshot.id,
        backtest_run_id=snapshot.backtest_run_id,
        timestamp=snapshot.timestamp,
        equity=float(snapshot.equity),
        drawdown=float(snapshot.drawdown),
    )
