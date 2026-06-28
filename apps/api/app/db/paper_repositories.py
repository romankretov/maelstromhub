from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CandleORM,
    MarketRegimeSnapshotORM,
    PaperAccountORM,
    PaperDeploymentORM,
    PaperPositionORM,
    PaperTradeORM,
    SignalORM,
    StrategyORM,
    StrategyVersionORM,
)
from app.db.repositories import _new_id, create_audit_event
from maelstromhub_core import (
    PaperAccount,
    PaperAccountCreate,
    PaperAccountStatus,
    PaperDeployment,
    PaperDeploymentCreate,
    PaperDeploymentStatus,
    PaperPosition,
    PaperStepResult,
    PaperTrade,
    SignalSide,
    StrategyStatus,
)


async def create_paper_account(session: AsyncSession, payload: PaperAccountCreate) -> PaperAccount:
    account = PaperAccountORM(
        id=_new_id("paper-account"),
        name=payload.name,
        starting_balance=payload.starting_balance,
        cash_balance=payload.starting_balance,
        equity=payload.starting_balance,
        status=PaperAccountStatus.ACTIVE.value,
    )
    session.add(account)
    await session.flush()
    await create_audit_event(
        session,
        actor="system",
        action="created_paper_account",
        subject=account.id,
        flush=False,
    )
    await session.commit()
    await session.refresh(account)
    return _account_to_schema(account)


async def list_paper_accounts(session: AsyncSession) -> list[PaperAccount]:
    result = await session.execute(select(PaperAccountORM).order_by(PaperAccountORM.created_at.desc()))
    return [_account_to_schema(account) for account in result.scalars()]


async def create_paper_deployment(session: AsyncSession, payload: PaperDeploymentCreate) -> PaperDeployment:
    strategy = await _get_or_404(session, StrategyORM, payload.strategy_id)
    if StrategyStatus(strategy.status) not in {StrategyStatus.BACKTESTED, StrategyStatus.PAPER_TRADING}:
        raise HTTPException(status_code=400, detail="Only Backtested or Paper Trading strategies can be deployed.")
    version = await _get_or_404(session, StrategyVersionORM, payload.strategy_version_id)
    if version.strategy_id != strategy.id:
        raise HTTPException(status_code=400, detail="Strategy version does not belong to this strategy.")
    account = await _get_or_404(session, PaperAccountORM, payload.paper_account_id)
    if account.status != PaperAccountStatus.ACTIVE.value:
        raise HTTPException(status_code=400, detail="Paper account is not active.")

    deployment = PaperDeploymentORM(
        id=_new_id("paper-deployment"),
        strategy_id=strategy.id,
        strategy_version_id=version.id,
        dataset_id=version.dataset_id,
        paper_account_id=account.id,
        status=PaperDeploymentStatus.RUNNING.value,
    )
    session.add(deployment)
    await session.flush()
    await create_audit_event(
        session,
        actor="system",
        action="started_paper_deployment",
        subject=deployment.id,
        flush=False,
    )
    await session.commit()
    return await get_paper_deployment(session, deployment.id)


async def list_paper_deployments(session: AsyncSession) -> list[PaperDeployment]:
    result = await session.execute(select(PaperDeploymentORM).order_by(PaperDeploymentORM.started_at.desc()))
    return [await _deployment_to_schema(session, deployment) for deployment in result.scalars()]


async def get_paper_deployment(session: AsyncSession, deployment_id: str) -> PaperDeployment:
    deployment = await _get_or_404(session, PaperDeploymentORM, deployment_id)
    return await _deployment_to_schema(session, deployment)


async def step_paper_deployment(session: AsyncSession, deployment_id: str) -> PaperStepResult:
    deployment = await _get_or_404(session, PaperDeploymentORM, deployment_id)
    if deployment.status != PaperDeploymentStatus.RUNNING.value:
        return PaperStepResult(
            deployment=await _deployment_to_schema(session, deployment),
            advanced=False,
            message=f"Deployment is {deployment.status}. Resume is not implemented in Paper Trading v1.",
        )
    account = await _get_or_404(session, PaperAccountORM, deployment.paper_account_id)
    candle = await _next_candle(session, deployment)
    if candle is None:
        deployment.status = PaperDeploymentStatus.STOPPED.value
        deployment.stopped_at = datetime.now(UTC)
        await create_audit_event(
            session,
            actor="system",
            action="stopped_paper_deployment",
            subject=deployment.id,
            flush=False,
        )
        await session.commit()
        return PaperStepResult(
            deployment=await get_paper_deployment(session, deployment.id),
            advanced=False,
            message="No more candles are available. Deployment stopped.",
        )

    timestamp = candle.opened_at.astimezone(UTC)
    signal = await _signal_at(session, deployment.strategy_version_id, timestamp)
    close = float(candle.close)
    position = await _load_position(session, deployment.id)
    if signal is not None:
        version = await _get_or_404(session, StrategyVersionORM, deployment.strategy_version_id)
        regime = await _regime_at(session, deployment.dataset_id, timestamp)
        if _is_blocked_by_regime(version.allowed_regimes, regime):
            _mark_account(account, position, close)
            deployment.last_processed_at = timestamp
            await create_audit_event(
                session,
                actor="system",
                action="skipped_paper_trade_by_regime",
                subject=deployment.id,
                flush=False,
            )
            await session.commit()
            return PaperStepResult(
                deployment=await get_paper_deployment(session, deployment.id),
                advanced=True,
                message=f"Skipped {timestamp.isoformat()}: blocked by regime filter.",
            )
        side = SignalSide(signal.side)
        if side == SignalSide.LONG and position is None:
            await _open_long(session, deployment, account, signal, close)
            position = await _load_position(session, deployment.id)
        elif side != SignalSide.LONG and position is not None and float(position.quantity) > 0:
            await _close_position(session, deployment, account, position, signal, close)
            position = await _load_position(session, deployment.id)

    _mark_account(account, position, close)
    deployment.last_processed_at = timestamp
    await create_audit_event(
        session,
        actor="system",
        action="executed_paper_step",
        subject=deployment.id,
        flush=False,
    )
    await session.commit()
    return PaperStepResult(
        deployment=await get_paper_deployment(session, deployment.id),
        advanced=True,
        message=f"Processed {timestamp.isoformat()}.",
    )


async def pause_paper_deployment(session: AsyncSession, deployment_id: str) -> PaperDeployment:
    deployment = await _get_or_404(session, PaperDeploymentORM, deployment_id)
    if deployment.status == PaperDeploymentStatus.RUNNING.value:
        deployment.status = PaperDeploymentStatus.PAUSED.value
        await create_audit_event(
            session,
            actor="system",
            action="paused_paper_deployment",
            subject=deployment.id,
            flush=False,
        )
        await session.commit()
    return await get_paper_deployment(session, deployment.id)


async def stop_paper_deployment(session: AsyncSession, deployment_id: str) -> PaperDeployment:
    deployment = await _get_or_404(session, PaperDeploymentORM, deployment_id)
    if deployment.status != PaperDeploymentStatus.STOPPED.value:
        deployment.status = PaperDeploymentStatus.STOPPED.value
        deployment.stopped_at = datetime.now(UTC)
        await create_audit_event(
            session,
            actor="system",
            action="stopped_paper_deployment",
            subject=deployment.id,
            flush=False,
        )
        await session.commit()
    return await get_paper_deployment(session, deployment.id)


async def _next_candle(session: AsyncSession, deployment: PaperDeploymentORM) -> CandleORM | None:
    conditions = [CandleORM.dataset_id == deployment.dataset_id]
    if deployment.last_processed_at is not None:
        conditions.append(CandleORM.opened_at > deployment.last_processed_at)
    result = await session.execute(select(CandleORM).where(*conditions).order_by(CandleORM.opened_at.asc()).limit(1))
    return result.scalar_one_or_none()


async def _signal_at(session: AsyncSession, version_id: str, timestamp: datetime) -> SignalORM | None:
    result = await session.execute(
        select(SignalORM).where(
            SignalORM.strategy_version_id == version_id,
            SignalORM.timestamp == timestamp,
        )
    )
    return result.scalar_one_or_none()


async def _regime_at(session: AsyncSession, dataset_id: str, timestamp: datetime) -> MarketRegimeSnapshotORM | None:
    result = await session.execute(
        select(MarketRegimeSnapshotORM).where(
            MarketRegimeSnapshotORM.dataset_id == dataset_id,
            MarketRegimeSnapshotORM.timestamp == timestamp,
        )
    )
    return result.scalar_one_or_none()


def _is_blocked_by_regime(
    allowed_regimes: list[str] | None,
    regime: MarketRegimeSnapshotORM | None,
) -> bool:
    if not allowed_regimes or regime is None:
        return False
    return regime.regime_label not in set(allowed_regimes)


async def _load_position(session: AsyncSession, deployment_id: str) -> PaperPositionORM | None:
    result = await session.execute(select(PaperPositionORM).where(PaperPositionORM.deployment_id == deployment_id))
    return result.scalar_one_or_none()


async def _open_long(
    session: AsyncSession,
    deployment: PaperDeploymentORM,
    account: PaperAccountORM,
    signal: SignalORM,
    price: float,
) -> None:
    suggested_size = max(0.0, min(float(signal.suggested_size), 1.0))
    notional = float(account.cash_balance) * suggested_size
    quantity = 0.0 if price == 0 else notional / price
    account.cash_balance = float(account.cash_balance) - notional
    session.add(
        PaperPositionORM(
            id=_new_id("paper-position"),
            deployment_id=deployment.id,
            symbol=signal.symbol,
            quantity=quantity,
            average_entry_price=price,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
        )
    )
    session.add(
        PaperTradeORM(
            id=_new_id("paper-trade"),
            deployment_id=deployment.id,
            timestamp=signal.timestamp,
            symbol=signal.symbol,
            side="buy",
            price=price,
            quantity=quantity,
            fees=0.0,
            pnl=0.0,
            reason=signal.reason,
        )
    )
    await session.flush()


async def _close_position(
    session: AsyncSession,
    deployment: PaperDeploymentORM,
    account: PaperAccountORM,
    position: PaperPositionORM,
    signal: SignalORM,
    price: float,
) -> None:
    quantity = float(position.quantity)
    gross_exit = quantity * price
    pnl = (price - float(position.average_entry_price)) * quantity
    account.cash_balance = float(account.cash_balance) + gross_exit
    position.quantity = 0.0
    position.unrealized_pnl = 0.0
    position.realized_pnl = float(position.realized_pnl) + pnl
    session.add(
        PaperTradeORM(
            id=_new_id("paper-trade"),
            deployment_id=deployment.id,
            timestamp=signal.timestamp,
            symbol=position.symbol,
            side="sell",
            price=price,
            quantity=quantity,
            fees=0.0,
            pnl=pnl,
            reason=signal.reason,
        )
    )
    await session.flush()


def _mark_account(account: PaperAccountORM, position: PaperPositionORM | None, close: float) -> None:
    if position is None or float(position.quantity) == 0:
        account.equity = float(account.cash_balance)
        return
    position.unrealized_pnl = (close - float(position.average_entry_price)) * float(position.quantity)
    account.equity = float(account.cash_balance) + float(position.quantity) * close


async def _deployment_to_schema(session: AsyncSession, deployment: PaperDeploymentORM) -> PaperDeployment:
    account = await _get_or_404(session, PaperAccountORM, deployment.paper_account_id)
    trades_result = await session.execute(
        select(PaperTradeORM)
        .where(PaperTradeORM.deployment_id == deployment.id)
        .order_by(PaperTradeORM.timestamp.asc())
    )
    positions_result = await session.execute(select(PaperPositionORM).where(PaperPositionORM.deployment_id == deployment.id))
    return PaperDeployment(
        id=deployment.id,
        strategy_id=deployment.strategy_id,
        strategy_version_id=deployment.strategy_version_id,
        dataset_id=deployment.dataset_id,
        paper_account_id=deployment.paper_account_id,
        status=PaperDeploymentStatus(deployment.status),
        started_at=deployment.started_at,
        stopped_at=deployment.stopped_at,
        last_processed_at=deployment.last_processed_at,
        account=_account_to_schema(account),
        positions=[_position_to_schema(position) for position in positions_result.scalars()],
        trades=[_trade_to_schema(trade) for trade in trades_result.scalars()],
    )


def _account_to_schema(account: PaperAccountORM) -> PaperAccount:
    return PaperAccount(
        id=account.id,
        name=account.name,
        starting_balance=float(account.starting_balance),
        cash_balance=float(account.cash_balance),
        equity=float(account.equity),
        status=PaperAccountStatus(account.status),
        created_at=account.created_at,
    )


def _position_to_schema(position: PaperPositionORM) -> PaperPosition:
    return PaperPosition(
        id=position.id,
        deployment_id=position.deployment_id,
        symbol=position.symbol,
        quantity=float(position.quantity),
        average_entry_price=float(position.average_entry_price),
        unrealized_pnl=float(position.unrealized_pnl),
        realized_pnl=float(position.realized_pnl),
    )


def _trade_to_schema(trade: PaperTradeORM) -> PaperTrade:
    return PaperTrade(
        id=trade.id,
        deployment_id=trade.deployment_id,
        timestamp=trade.timestamp,
        symbol=trade.symbol,
        side=trade.side,
        price=float(trade.price),
        quantity=float(trade.quantity),
        fees=float(trade.fees),
        pnl=float(trade.pnl),
        reason=trade.reason,
    )


async def _get_or_404(session: AsyncSession, model: type[Any], item_id: str) -> Any:
    item = await session.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return item
