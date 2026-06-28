"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowRight, CircleDot, History, Rocket, ShieldCheck } from "lucide-react";

import { ErrorState, FeedbackState, LoadingState } from "@/components/shell/feedback";
import { Button } from "@/components/ui/button";
import {
  getAuditEvents,
  getStrategies,
  getStrategyVersionBacktests,
  getStrategyVersions,
  promoteStrategy,
  type AuditEvent,
  type BacktestRun,
  type Strategy,
} from "@/lib/api-client";
import { safetyNotes, workflowSteps } from "@/lib/product-shell";

type StrategyDashboardItem = {
  strategy: Strategy;
  latestBacktest: BacktestRun | null;
  bestBacktest: BacktestRun | null;
  versionCount: number;
};

export function DashboardClient() {
  const [strategyItems, setStrategyItems] = useState<StrategyDashboardItem[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [promotingId, setPromotingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [loadedStrategies, loadedAuditEvents] = await Promise.all([getStrategies(), getAuditEvents()]);
      const loadedItems = await Promise.all(
        loadedStrategies.map(async (strategy) => {
          const versions = await getStrategyVersions(strategy.id);
          const runGroups = await Promise.all(versions.map((version) => getStrategyVersionBacktests(version.id)));
          const runs = runGroups
            .flat()
            .sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at));
          const succeededRuns = runs.filter((run) => run.status === "succeeded");
          const bestBacktest = succeededRuns.length > 0 ? [...succeededRuns].sort(compareRuns)[0] : null;
          return {
            strategy,
            latestBacktest: runs[0] ?? null,
            bestBacktest,
            versionCount: versions.length,
          };
        }),
      );
      setStrategyItems(loadedItems);
      setAuditEvents(loadedAuditEvents.slice(0, 5));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load dashboard.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  async function handlePromote(strategyId: string) {
    setPromotingId(strategyId);
    setError(null);
    setNotice(null);
    try {
      const result = await promoteStrategy(strategyId);
      setNotice(result.promoted ? `${result.strategy.name} is now Backtested.` : result.reasons.join(" "));
      await loadDashboard();
    } catch (promoteError) {
      setError(promoteError instanceof Error ? promoteError.message : "Unable to promote strategy.");
    } finally {
      setPromotingId(null);
    }
  }

  return (
    <>
      <section className="grid gap-3 md:grid-cols-6">
        {workflowSteps.map((step, index) => (
          <div key={step} className="rounded-lg border bg-card p-4">
            <div className="flex items-center justify-between gap-3">
              <CircleDot className="h-4 w-4 text-primary" aria-hidden="true" />
              {index < workflowSteps.length - 1 ? (
                <ArrowRight className="hidden h-4 w-4 text-muted-foreground md:block" aria-hidden="true" />
              ) : null}
            </div>
            <p className="mt-4 text-sm font-medium">{step}</p>
          </div>
        ))}
      </section>

      {error ? <ErrorState message={error} /> : null}
      {notice ? (
        <section className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">{notice}</section>
      ) : null}
      {loading ? <LoadingState label="Loading dashboard" /> : null}

      {!loading ? (
        <section>
          <div className="mb-3 flex items-center justify-between gap-4">
            <h2 className="text-lg font-semibold">Strategies</h2>
            <p className="text-sm text-muted-foreground">Loaded from the API</p>
          </div>
          {strategyItems.length === 0 ? (
            <FeedbackState
              icon={ShieldCheck}
              title="No strategies yet"
              description="Create a draft strategy in Strategy Builder after capturing an idea or as a standalone research thread."
            />
          ) : (
            <div className="grid gap-4 lg:grid-cols-3">
              {strategyItems.map(({ strategy, latestBacktest, bestBacktest, versionCount }) => {
                const latestVerdict = latestBacktest ? getVerdict(latestBacktest) : "No backtest";
                const canPromote =
                  strategy.status === "Draft" && bestBacktest !== null && getVerdict(bestBacktest) === "Ready";
                const nextAction = getNextAction(strategy, latestBacktest, bestBacktest, versionCount);

                return (
                  <article key={strategy.id} className="rounded-lg border bg-card p-5 shadow-sm">
                    <div className="flex items-start justify-between gap-4">
                      <h3 className="font-semibold">{strategy.name}</h3>
                      <span className="rounded-md border px-2 py-1 text-xs text-muted-foreground">
                        {strategy.status}
                      </span>
                    </div>
                    <p className="mt-4 text-sm leading-6 text-muted-foreground">{strategy.description}</p>
                    <div className="mt-5 grid gap-3 text-sm">
                      <div className="rounded-md border bg-background p-3">
                        <p className="text-xs text-muted-foreground">Latest backtest verdict</p>
                        <p className="mt-1 font-medium">{latestVerdict}</p>
                      </div>
                      <div className="rounded-md border bg-background p-3">
                        <p className="text-xs text-muted-foreground">Next recommended action</p>
                        <p className="mt-1 font-medium">{nextAction}</p>
                      </div>
                    </div>
                    {canPromote ? (
                      <Button
                        className="mt-5 w-full gap-2"
                        type="button"
                        disabled={promotingId === strategy.id}
                        onClick={() => void handlePromote(strategy.id)}
                      >
                        <Rocket className="h-4 w-4" aria-hidden="true" />
                        {promotingId === strategy.id ? "Promoting" : "Promote"}
                      </Button>
                    ) : null}
                  </article>
                );
              })}
            </div>
          )}
        </section>
      ) : null}

      {!loading ? (
        <section className="grid gap-4 lg:grid-cols-[1fr_360px]">
          <div className="rounded-lg border bg-card p-5">
            <div className="flex items-center gap-2">
              <History className="h-4 w-4 text-primary" aria-hidden="true" />
              <h2 className="text-sm font-semibold">Recent audit events</h2>
            </div>
            {auditEvents.length === 0 ? (
              <p className="mt-4 text-sm text-muted-foreground">No audit events recorded yet.</p>
            ) : (
              <div className="mt-4 divide-y">
                {auditEvents.map((event) => (
                  <div key={event.id} className="py-3 text-sm">
                    <p className="font-medium">{event.action.replaceAll("_", " ")}</p>
                    <p className="mt-1 text-muted-foreground">
                      {event.actor} on {event.subject}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="grid gap-4">
            {safetyNotes.map((note) => {
              const Icon = note.icon ?? ShieldCheck;

              return (
                <div key={note.label} className="rounded-lg border bg-card p-4">
                  <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
                  <p className="mt-4 text-sm font-medium">{note.label}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{note.value}</p>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}
    </>
  );
}

function getNextAction(
  strategy: Strategy,
  latestBacktest: BacktestRun | null,
  bestBacktest: BacktestRun | null,
  versionCount: number,
) {
  if (strategy.status === "Backtested") {
    return "Hold in Backtested. Paper Trading is not enabled yet.";
  }
  if (strategy.status !== "Draft") {
    return "Review lifecycle status before taking the next step.";
  }
  if (versionCount === 0) {
    return "Create a strategy version and generate signals.";
  }
  if (!latestBacktest) {
    return "Run a backtest for this strategy version.";
  }
  if (bestBacktest && getVerdict(bestBacktest) === "Ready") {
    return "Promote to Backtested.";
  }
  if (getVerdict(latestBacktest) === "Review") {
    return "Review risk-adjusted performance before promotion.";
  }
  return "Tune the strategy and rerun the backtest.";
}

function getVerdict(run: BacktestRun) {
  const totalReturn = numberMetric(run, "total_return");
  const maxDrawdown = numberMetric(run, "max_drawdown");
  const tradeCount = numberMetric(run, "trade_count");
  if (run.status !== "succeeded" || maxDrawdown < -0.2 || totalReturn < -0.05 || tradeCount < 1) {
    return "Blocked";
  }
  if (totalReturn > 0 && getRiskAdjustedScore(run) >= 1) {
    return "Ready";
  }
  return "Review";
}

function compareRuns(left: BacktestRun, right: BacktestRun) {
  const verdictRank = { Blocked: 0, Review: 1, Ready: 2 };
  const leftVerdict = getVerdict(left);
  const rightVerdict = getVerdict(right);
  return (
    verdictRank[rightVerdict] - verdictRank[leftVerdict] ||
    getRiskAdjustedScore(right) - getRiskAdjustedScore(left)
  );
}

function getRiskAdjustedScore(run: BacktestRun) {
  return numberMetric(run, "total_return") / Math.max(Math.abs(numberMetric(run, "max_drawdown")), 0.01);
}

function numberMetric(run: BacktestRun, key: string) {
  const value = run.metrics[key];
  return typeof value === "number" ? value : 0;
}
