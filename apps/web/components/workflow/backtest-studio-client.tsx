"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Award, Play, RefreshCw, TestTubeDiagonal } from "lucide-react";

import { ErrorState, FeedbackState, LoadingState } from "@/components/shell/feedback";
import { Button } from "@/components/ui/button";
import {
  createBacktest,
  getBacktest,
  getDatasets,
  getStrategies,
  getStrategyVersionBacktests,
  getStrategyVersions,
  type BacktestRun,
  type BacktestRunDetail,
  type StrategyVersion,
} from "@/lib/api-client";

type VersionOption = StrategyVersion & {
  strategy_name: string;
  dataset_name: string;
};

export function BacktestStudioClient() {
  const [versions, setVersions] = useState<VersionOption[]>([]);
  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [selectedRun, setSelectedRun] = useState<BacktestRunDetail | null>(null);
  const [startingBalance, setStartingBalance] = useState("10000");
  const [feeBps, setFeeBps] = useState("5");
  const [slippageBps, setSlippageBps] = useState("2");
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const verdict = selectedRun ? getVerdict(selectedRun) : null;

  async function loadWorkspace() {
    setLoading(true);
    setError(null);
    try {
      const [loadedStrategies, loadedDatasets] = await Promise.all([getStrategies(), getDatasets()]);
      const versionGroups = await Promise.all(
        loadedStrategies.map(async (strategy) => {
          const strategyVersions = await getStrategyVersions(strategy.id);
          return strategyVersions.map((version) => ({
            ...version,
            strategy_name: strategy.name,
            dataset_name: loadedDatasets.find((dataset) => dataset.id === version.dataset_id)?.name ?? "Dataset",
          }));
        }),
      );
      const loadedVersions = versionGroups.flat();
      setVersions(loadedVersions);
      setSelectedVersionId((current) => current || loadedVersions[0]?.id || "");
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load backtest workspace.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadWorkspace();
  }, []);

  useEffect(() => {
    if (!selectedVersionId) {
      setRuns([]);
      setSelectedRun(null);
      return;
    }

    async function loadRuns() {
      try {
        const loadedRuns = await getStrategyVersionBacktests(selectedVersionId);
        setRuns(loadedRuns);
        if (loadedRuns[0]) {
          setSelectedRun(await getBacktest(loadedRuns[0].id));
        } else {
          setSelectedRun(null);
        }
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load backtests.");
      }
    }

    void loadRuns();
  }, [selectedVersionId]);

  async function handleRunBacktest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedVersionId) {
      setError("Select a strategy version before running a backtest.");
      return;
    }
    setRunning(true);
    setError(null);
    try {
      const run = await createBacktest(selectedVersionId, {
        starting_balance: Number(startingBalance),
        fee_bps: Number(feeBps),
        slippage_bps: Number(slippageBps),
      });
      setSelectedRun(run);
      setRuns((current) => [run, ...current.filter((existing) => existing.id !== run.id)]);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Unable to run backtest.");
    } finally {
      setRunning(false);
    }
  }

  async function handleSelectRun(runId: string) {
    if (!runId) {
      setSelectedRun(null);
      return;
    }
    try {
      setSelectedRun(await getBacktest(runId));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load backtest.");
    }
  }

  const metricCards = useMemo(() => getMetricCards(selectedRun), [selectedRun]);

  return (
    <div className="space-y-6">
      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState label="Loading backtest workspace" /> : null}

      {!loading && versions.length === 0 ? (
        <FeedbackState
          icon={TestTubeDiagonal}
          title="No strategy versions yet"
          description="Create a strategy version and generate signals before running a backtest."
        />
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[380px_1fr]">
        <form onSubmit={handleRunBacktest} className="rounded-lg border bg-card p-5">
          <h2 className="text-base font-semibold">Run backtest</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Replay stored signals against dataset candles with simple long and flat execution.
          </p>
          <label className="mt-5 block text-sm font-medium" htmlFor="strategy-version">
            Strategy version
          </label>
          <select
            id="strategy-version"
            value={selectedVersionId}
            onChange={(event) => setSelectedVersionId(event.target.value)}
            className="mt-2 h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
            required
          >
            <option value="">Select version</option>
            {versions.map((version) => (
              <option key={version.id} value={version.id}>
                {version.strategy_name} v{version.version_number} - {version.dataset_name}
              </option>
            ))}
          </select>
          <div className="mt-4 grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
            <NumberField label="Starting balance" value={startingBalance} onChange={setStartingBalance} />
            <NumberField label="Fee bps" value={feeBps} onChange={setFeeBps} />
            <NumberField label="Slippage bps" value={slippageBps} onChange={setSlippageBps} />
          </div>
          <Button className="mt-5 w-full gap-2" type="submit" disabled={running || versions.length === 0}>
            <Play className="h-4 w-4" aria-hidden="true" />
            {running ? "Running" : "Run backtest"}
          </Button>
          <div className="mt-5 rounded-md border bg-background p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold">Previous runs</h3>
              <Button variant="outline" size="sm" className="gap-2" type="button" onClick={() => void loadWorkspace()}>
                <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                Refresh
              </Button>
            </div>
            {runs.length === 0 ? (
              <p className="mt-3 text-sm text-muted-foreground">No backtests for this version yet.</p>
            ) : (
              <select
                value={selectedRun?.id ?? ""}
                onChange={(event) => void handleSelectRun(event.target.value)}
                className="mt-3 h-10 w-full rounded-md border bg-card px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
              >
                {runs.map((run) => (
                  <option key={run.id} value={run.id}>
                    {new Date(run.created_at).toLocaleString()} - {run.status}
                  </option>
                ))}
              </select>
            )}
          </div>
        </form>

        <section className="space-y-4">
          {!selectedRun ? (
            <FeedbackState
              icon={TestTubeDiagonal}
              title="Run a backtest to see results"
              description="Results will show metrics, an equity curve, trades, and a plain-language verdict."
            />
          ) : (
            <>
              <section className="rounded-lg border bg-card p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h2 className="text-base font-semibold">Result metrics</h2>
                    <p className="mt-2 text-sm text-muted-foreground">
                      Run {selectedRun.id} finished as {selectedRun.status}.
                    </p>
                  </div>
                  {verdict ? (
                    <span className="rounded-md border px-3 py-1 text-sm font-medium">{verdict}</span>
                  ) : null}
                </div>
                <div className="mt-5 grid gap-3 md:grid-cols-5">
                  {metricCards.map((metric) => (
                    <div key={metric.label} className="rounded-md border bg-background p-4">
                      <p className="text-xs text-muted-foreground">{metric.label}</p>
                      <p className="mt-2 text-lg font-semibold">{metric.value}</p>
                    </div>
                  ))}
                </div>
              </section>
              <BacktestComparison runs={runs} selectedRunId={selectedRun.id} onSelectRun={handleSelectRun} />
              <PerformanceByRegime run={selectedRun} />
              <section className="rounded-lg border bg-card p-5">
                <h2 className="text-base font-semibold">Equity curve</h2>
                <EquityCurve snapshots={selectedRun.equity_curve} />
              </section>
              <section className="rounded-lg border bg-card p-5">
                <h2 className="text-base font-semibold">Trades</h2>
                {selectedRun.trades.length === 0 ? (
                  <p className="mt-3 text-sm text-muted-foreground">No completed trades were produced.</p>
                ) : (
                  <div className="mt-4 overflow-hidden rounded-md border">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-muted/50 text-xs text-muted-foreground">
                        <tr>
                          <th className="px-3 py-2 font-medium">Time</th>
                          <th className="px-3 py-2 font-medium">Symbol</th>
                          <th className="px-3 py-2 font-medium">Side</th>
                          <th className="px-3 py-2 font-medium">Entry</th>
                          <th className="px-3 py-2 font-medium">Exit</th>
                          <th className="px-3 py-2 font-medium">PnL</th>
                          <th className="px-3 py-2 font-medium">Reason</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedRun.trades.map((trade) => (
                          <tr key={trade.id} className="border-t">
                            <td className="px-3 py-2 text-muted-foreground">
                              {new Date(trade.timestamp).toLocaleString()}
                            </td>
                            <td className="px-3 py-2">{trade.symbol}</td>
                            <td className="px-3 py-2">{trade.side}</td>
                            <td className="px-3 py-2">{formatMoney(trade.entry_price)}</td>
                            <td className="px-3 py-2">{formatMoney(trade.exit_price)}</td>
                            <td className="px-3 py-2">{formatMoney(trade.pnl)}</td>
                            <td className="px-3 py-2 text-muted-foreground">{trade.reason}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            </>
          )}
        </section>
      </section>
    </div>
  );
}

function PerformanceByRegime({ run }: { run: BacktestRunDetail }) {
  const pnlByRegime = objectMetric(run, "pnl_by_regime");
  const tradeCountByRegime = objectMetric(run, "trade_count_by_regime");
  const winRateByRegime = objectMetric(run, "win_rate_by_regime");
  const coverage = objectMetric(run, "regime_coverage");
  const labels = Array.from(
    new Set([...Object.keys(pnlByRegime), ...Object.keys(tradeCountByRegime), ...Object.keys(winRateByRegime)]),
  );

  return (
    <section className="rounded-lg border bg-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-base font-semibold">Performance by Regime</h2>
        <span className="text-sm text-muted-foreground">
          Coverage {formatPercent(numberValue(coverage.coverage_ratio))}
        </span>
      </div>
      {labels.length === 0 ? (
        <p className="mt-3 text-sm text-muted-foreground">No completed trades could be mapped to regimes.</p>
      ) : (
        <div className="mt-4 overflow-x-auto rounded-md border">
          <table className="w-full text-left text-sm">
            <thead className="bg-muted/50 text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Regime</th>
                <th className="px-3 py-2 font-medium">PnL</th>
                <th className="px-3 py-2 font-medium">Trades</th>
                <th className="px-3 py-2 font-medium">Win rate</th>
              </tr>
            </thead>
            <tbody>
              {labels.map((label) => (
                <tr key={label} className="border-t">
                  <td className="px-3 py-2 font-medium">{label}</td>
                  <td className="px-3 py-2">{formatMoney(numberValue(pnlByRegime[label]))}</td>
                  <td className="px-3 py-2">{numberValue(tradeCountByRegime[label])}</td>
                  <td className="px-3 py-2">{formatPercent(numberValue(winRateByRegime[label]))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function BacktestComparison({
  runs,
  selectedRunId,
  onSelectRun,
}: {
  runs: BacktestRun[];
  selectedRunId: string;
  onSelectRun: (runId: string) => Promise<void>;
}) {
  const recentRuns = runs.slice(0, 5);
  if (recentRuns.length === 0) {
    return null;
  }
  const bestRun = [...recentRuns].sort(compareRuns)[0];

  return (
    <section className="rounded-lg border bg-card p-5">
      <div className="flex items-center gap-2">
        <Award className="h-4 w-4 text-primary" aria-hidden="true" />
        <h2 className="text-base font-semibold">Backtest comparison</h2>
      </div>
      <div className="mt-4 overflow-x-auto rounded-md border">
        <table className="min-w-[760px] w-full text-left text-sm">
          <thead className="bg-muted/50 text-xs text-muted-foreground">
            <tr>
              <th className="px-3 py-2 font-medium">Run</th>
              <th className="px-3 py-2 font-medium">Verdict</th>
              <th className="px-3 py-2 font-medium">Score</th>
              <th className="px-3 py-2 font-medium">Return</th>
              <th className="px-3 py-2 font-medium">Drawdown</th>
              <th className="px-3 py-2 font-medium">Trades</th>
              <th className="px-3 py-2 font-medium">Win rate</th>
              <th className="px-3 py-2 font-medium">Profit factor</th>
            </tr>
          </thead>
          <tbody>
            {recentRuns.map((run) => {
              const isBest = run.id === bestRun.id;
              const isSelected = run.id === selectedRunId;
              return (
                <tr
                  key={run.id}
                  className={isBest ? "border-t bg-accent/15" : isSelected ? "border-t bg-muted/40" : "border-t"}
                >
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      onClick={() => void onSelectRun(run.id)}
                      className="text-left font-medium hover:text-primary"
                    >
                      {new Date(run.created_at).toLocaleString()}
                    </button>
                    {isBest ? <span className="ml-2 text-xs text-muted-foreground">Best</span> : null}
                  </td>
                  <td className="px-3 py-2">{getVerdict(run)}</td>
                  <td className="px-3 py-2">{getRiskAdjustedScore(run).toFixed(2)}</td>
                  <td className="px-3 py-2">{formatPercent(numberMetric(run, "total_return"))}</td>
                  <td className="px-3 py-2">{formatPercent(numberMetric(run, "max_drawdown"))}</td>
                  <td className="px-3 py-2">{numberMetric(run, "trade_count")}</td>
                  <td className="px-3 py-2">{formatPercent(numberMetric(run, "win_rate"))}</td>
                  <td className="px-3 py-2">{numberMetric(run, "profit_factor").toFixed(2)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const id = label.toLowerCase().replaceAll(" ", "-");
  return (
    <label className="block text-sm font-medium" htmlFor={id}>
      {label}
      <input
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        type="number"
        step="any"
        min="0"
        className="mt-2 h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
      />
    </label>
  );
}

function EquityCurve({ snapshots }: { snapshots: BacktestRunDetail["equity_curve"] }) {
  if (snapshots.length === 0) {
    return <p className="mt-3 text-sm text-muted-foreground">No equity snapshots were produced.</p>;
  }
  const width = 720;
  const height = 180;
  const values = snapshots.map((snapshot) => snapshot.equity);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const points = snapshots
    .map((snapshot, index) => {
      const x = snapshots.length === 1 ? 0 : (index / (snapshots.length - 1)) * width;
      const y = height - ((snapshot.equity - min) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="mt-4 rounded-md border bg-background p-4">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-48 w-full" role="img" aria-label="Equity curve">
        <polyline fill="none" stroke="currentColor" strokeWidth="3" points={points} />
      </svg>
      <div className="mt-3 flex justify-between text-xs text-muted-foreground">
        <span>{formatMoney(values[0])}</span>
        <span>{formatMoney(values[values.length - 1])}</span>
      </div>
    </div>
  );
}

function getMetricCards(run: BacktestRunDetail | null) {
  if (!run) {
    return [];
  }
  return [
    { label: "Total return", value: formatPercent(numberMetric(run, "total_return")) },
    { label: "Max drawdown", value: formatPercent(numberMetric(run, "max_drawdown")) },
    { label: "Win rate", value: formatPercent(numberMetric(run, "win_rate")) },
    { label: "Trades", value: String(numberMetric(run, "trade_count")) },
    { label: "Profit factor", value: numberMetric(run, "profit_factor").toFixed(2) },
  ];
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

function getRiskAdjustedScore(run: BacktestRun) {
  return numberMetric(run, "total_return") / Math.max(Math.abs(numberMetric(run, "max_drawdown")), 0.01);
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

function numberMetric(run: BacktestRun, key: string) {
  const value = run.metrics[key];
  return typeof value === "number" ? value : 0;
}

function objectMetric(run: BacktestRun, key: string): Record<string, unknown> {
  const value = run.metrics[key];
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function numberValue(value: unknown) {
  return typeof value === "number" ? value : 0;
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}

function formatMoney(value: number) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value);
}
