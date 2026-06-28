from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.backtest_repositories import (
    create_backtest_run,
    get_backtest_run,
    list_strategy_version_backtests,
)
from app.db.paper_repositories import (
    create_paper_account,
    create_paper_deployment,
    get_paper_deployment,
    list_paper_accounts,
    list_paper_deployments,
    pause_paper_deployment,
    step_paper_deployment,
    stop_paper_deployment,
)
from app.db.repositories import (
    create_idea,
    create_strategy,
    list_audit_events,
    list_ideas,
    list_strategies,
)
from app.db.session import get_session
from app.db.strategy_repositories import (
    create_strategy_version,
    list_strategy_templates,
    list_strategy_version_signals,
    list_strategy_versions,
    promote_strategy,
    run_strategy_version_signals,
)
from maelstromhub_core import (
    AuditEvent,
    BacktestRun,
    BacktestRunCreate,
    BacktestRunDetail,
    Idea,
    IdeaCreate,
    PaperAccount,
    PaperAccountCreate,
    PaperDeployment,
    PaperDeploymentCreate,
    PaperStepResult,
    Signal,
    SignalRunResult,
    Strategy,
    StrategyCreate,
    StrategyPromotionResult,
    StrategyTemplate,
    StrategyVersion,
    StrategyVersionCreate,
)

router = APIRouter()

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get("/ideas")
async def get_ideas(session: SessionDependency) -> dict[str, list[Idea]]:
    return {"ideas": await list_ideas(session)}


@router.post("/ideas", status_code=201)
async def post_idea(payload: IdeaCreate, session: SessionDependency) -> Idea:
    return await create_idea(session, payload)


@router.get("/strategies")
async def get_strategies(session: SessionDependency) -> dict[str, list[Strategy]]:
    return {"strategies": await list_strategies(session)}


@router.post("/strategies", status_code=201)
async def post_strategy(payload: StrategyCreate, session: SessionDependency) -> Strategy:
    return await create_strategy(session, payload)


@router.post("/strategies/{strategy_id}/promote")
async def post_strategy_promote(strategy_id: UUID, session: SessionDependency) -> StrategyPromotionResult:
    return await promote_strategy(session, strategy_id)


@router.get("/strategy-templates")
async def get_strategy_templates(session: SessionDependency) -> dict[str, list[StrategyTemplate]]:
    return {"strategy_templates": await list_strategy_templates(session)}


@router.post("/strategies/{strategy_id}/versions", status_code=201)
async def post_strategy_version(
    strategy_id: UUID,
    payload: StrategyVersionCreate,
    session: SessionDependency,
) -> StrategyVersion:
    return await create_strategy_version(session, strategy_id, payload)


@router.get("/strategies/{strategy_id}/versions")
async def get_strategy_versions(strategy_id: UUID, session: SessionDependency) -> dict[str, list[StrategyVersion]]:
    return {"strategy_versions": await list_strategy_versions(session, strategy_id)}


@router.post("/strategy-versions/{version_id}/run-signals")
async def post_strategy_version_signals(version_id: UUID, session: SessionDependency) -> SignalRunResult:
    return await run_strategy_version_signals(session, version_id)


@router.get("/strategy-versions/{version_id}/signals")
async def get_strategy_version_signals(version_id: UUID, session: SessionDependency) -> dict[str, list[Signal]]:
    return {"signals": await list_strategy_version_signals(session, version_id)}


@router.post("/strategy-versions/{version_id}/backtests", status_code=201)
async def post_strategy_version_backtest(
    version_id: UUID,
    payload: BacktestRunCreate,
    session: SessionDependency,
) -> BacktestRunDetail:
    return await create_backtest_run(session, version_id, payload)


@router.get("/strategy-versions/{version_id}/backtests")
async def get_strategy_version_backtests(version_id: UUID, session: SessionDependency) -> dict[str, list[BacktestRun]]:
    return {"backtests": await list_strategy_version_backtests(session, version_id)}


@router.get("/backtests/{backtest_id}")
async def get_backtest(backtest_id: UUID, session: SessionDependency) -> BacktestRunDetail:
    return await get_backtest_run(session, backtest_id)


@router.post("/paper/accounts", status_code=201)
async def post_paper_account(payload: PaperAccountCreate, session: SessionDependency) -> PaperAccount:
    return await create_paper_account(session, payload)


@router.get("/paper/accounts")
async def get_paper_accounts(session: SessionDependency) -> dict[str, list[PaperAccount]]:
    return {"paper_accounts": await list_paper_accounts(session)}


@router.post("/paper/deployments", status_code=201)
async def post_paper_deployment(payload: PaperDeploymentCreate, session: SessionDependency) -> PaperDeployment:
    return await create_paper_deployment(session, payload)


@router.get("/paper/deployments")
async def get_paper_deployments(session: SessionDependency) -> dict[str, list[PaperDeployment]]:
    return {"paper_deployments": await list_paper_deployments(session)}


@router.get("/paper/deployments/{deployment_id}")
async def get_paper_deployment_detail(deployment_id: UUID, session: SessionDependency) -> PaperDeployment:
    return await get_paper_deployment(session, deployment_id)


@router.post("/paper/deployments/{deployment_id}/step")
async def post_paper_deployment_step(deployment_id: UUID, session: SessionDependency) -> PaperStepResult:
    return await step_paper_deployment(session, deployment_id)


@router.post("/paper/deployments/{deployment_id}/pause")
async def post_paper_deployment_pause(deployment_id: UUID, session: SessionDependency) -> PaperDeployment:
    return await pause_paper_deployment(session, deployment_id)


@router.post("/paper/deployments/{deployment_id}/stop")
async def post_paper_deployment_stop(deployment_id: UUID, session: SessionDependency) -> PaperDeployment:
    return await stop_paper_deployment(session, deployment_id)


@router.get("/audit-events")
async def get_audit_events(session: SessionDependency) -> dict[str, list[AuditEvent]]:
    return {"audit_events": await list_audit_events(session)}
