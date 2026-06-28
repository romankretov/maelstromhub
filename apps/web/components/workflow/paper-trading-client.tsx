"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Activity, Pause, Play, Plus, RefreshCw, Square, StepForward } from "lucide-react";

import { ErrorState, FeedbackState, LoadingState } from "@/components/shell/feedback";
import { Button } from "@/components/ui/button";
import {
  createPaperAccount,
  createPaperDeployment,
  getDatasets,
  getDatasetMarketIntelligence,
  getPaperDeployments,
  getPaperAccounts,
  getStrategies,
  getStrategyVersions,
  pausePaperDeployment,
  stepPaperDeployment,
  stopPaperDeployment,
  type PaperAccount,
  type PaperDeployment,
  type MarketRegimeSnapshot,
  type Strategy,
  type StrategyVersion,
} from "@/lib/api-client";

type VersionOption = StrategyVersion & {
  strategy_name: string;
  strategy_status: Strategy["status"];
  dataset_name: string;
};

export function PaperTradingClient() {
  const [accounts, setAccounts] = useState<PaperAccount[]>([]);
  const [deployments, setDeployments] = useState<PaperDeployment[]>([]);
  const [versions, setVersions] = useState<VersionOption[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState("");
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [selectedDeploymentId, setSelectedDeploymentId] = useState("");
  const [accountName, setAccountName] = useState("Paper rehearsal");
  const [startingBalance, setStartingBalance] = useState("10000");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [currentRegime, setCurrentRegime] = useState<MarketRegimeSnapshot | null>(null);

  const selectedVersion = versions.find((version) => version.id === selectedVersionId);
  const selectedDeployment = deployments.find((deployment) => deployment.id === selectedDeploymentId) ?? null;

  async function loadWorkspace() {
    setLoading(true);
    setError(null);
    try {
      const [loadedAccounts, loadedDeployments, loadedStrategies, loadedDatasets] = await Promise.all([
        getPaperAccounts(),
        getPaperDeployments(),
        getStrategies(),
        getDatasets(),
      ]);
      const eligibleStrategies = loadedStrategies.filter((strategy) =>
        ["Backtested", "Paper Trading"].includes(strategy.status),
      );
      const versionGroups = await Promise.all(
        eligibleStrategies.map(async (strategy) => {
          const strategyVersions = await getStrategyVersions(strategy.id);
          return strategyVersions.map((version) => ({
            ...version,
            strategy_name: strategy.name,
            strategy_status: strategy.status,
            dataset_name: loadedDatasets.find((dataset) => dataset.id === version.dataset_id)?.name ?? "Dataset",
          }));
        }),
      );
      const loadedVersions = versionGroups.flat();
      setAccounts(loadedAccounts);
      setDeployments(loadedDeployments);
      setVersions(loadedVersions);
      setSelectedAccountId((current) => current || loadedAccounts[0]?.id || "");
      setSelectedVersionId((current) => current || loadedVersions[0]?.id || "");
      setSelectedDeploymentId((current) => current || loadedDeployments[0]?.id || "");
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load paper deploy workspace.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadWorkspace();
  }, []);

  useEffect(() => {
    if (!selectedDeployment) {
      setCurrentRegime(null);
      return;
    }
    const deployment = selectedDeployment;
    async function loadRegime() {
      try {
        const intelligence = await getDatasetMarketIntelligence(deployment.dataset_id);
        setCurrentRegime(intelligence.regime);
      } catch {
        setCurrentRegime(null);
      }
    }
    void loadRegime();
  }, [selectedDeployment]);

  async function handleCreateAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const account = await createPaperAccount({
        name: accountName,
        starting_balance: Number(startingBalance),
      });
      setAccounts((current) => [account, ...current]);
      setSelectedAccountId(account.id);
      setNotice(`${account.name} is ready for paper deploy.`);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to create paper account.");
    } finally {
      setBusy(false);
    }
  }

  async function handleStartDeployment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedAccountId || !selectedVersion) {
      setError("Choose a paper account and approved strategy version.");
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const deployment = await createPaperDeployment({
        strategy_id: selectedVersion.strategy_id,
        strategy_version_id: selectedVersion.id,
        paper_account_id: selectedAccountId,
      });
      setDeployments((current) => [deployment, ...current]);
      setSelectedDeploymentId(deployment.id);
      setNotice("Paper deploy started.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to start paper deploy.");
    } finally {
      setBusy(false);
    }
  }

  async function handleStep() {
    if (!selectedDeploymentId) {
      setError("Select a deployment before stepping.");
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const result = await stepPaperDeployment(selectedDeploymentId);
      setDeployments((current) => [
        result.deployment,
        ...current.filter((existing) => existing.id !== result.deployment.id),
      ]);
      setNotice(result.message);
    } catch (stepError) {
      setError(stepError instanceof Error ? stepError.message : "Unable to step paper deploy.");
    } finally {
      setBusy(false);
    }
  }

  async function handlePause() {
    await updateDeploymentStatus(() => pausePaperDeployment(selectedDeploymentId), "Paper deploy paused.");
  }

  async function handleStop() {
    await updateDeploymentStatus(() => stopPaperDeployment(selectedDeploymentId), "Paper deploy stopped.");
  }

  async function updateDeploymentStatus(action: () => Promise<PaperDeployment>, message: string) {
    if (!selectedDeploymentId) {
      setError("Select a paper deploy first.");
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const deployment = await action();
      setDeployments((current) => [deployment, ...current.filter((existing) => existing.id !== deployment.id)]);
      setNotice(message);
    } catch (statusError) {
      setError(statusError instanceof Error ? statusError.message : "Unable to update paper deploy.");
    } finally {
      setBusy(false);
    }
  }

  const metrics = useMemo(() => getDeploymentMetrics(selectedDeployment), [selectedDeployment]);

  return (
    <div className="space-y-6">
      {error ? <ErrorState message={error} /> : null}
      {notice ? (
        <section className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">{notice}</section>
      ) : null}
      {loading ? <LoadingState label="Loading paper deploy workspace" /> : null}

      <section className="grid gap-6 xl:grid-cols-[360px_1fr]">
        <div className="space-y-4">
          <form onSubmit={handleCreateAccount} className="rounded-lg border bg-card p-5">
            <h2 className="text-base font-semibold">Create paper account</h2>
            <label className="mt-5 block text-sm font-medium" htmlFor="paper-account-name">
              Name
              <input
                id="paper-account-name"
                value={accountName}
                onChange={(event) => setAccountName(event.target.value)}
                className="mt-2 h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
                required
              />
            </label>
            <label className="mt-4 block text-sm font-medium" htmlFor="paper-starting-balance">
              Starting balance
              <input
                id="paper-starting-balance"
                value={startingBalance}
                onChange={(event) => setStartingBalance(event.target.value)}
                type="number"
                min="0"
                step="any"
                className="mt-2 h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
                required
              />
            </label>
            <Button className="mt-5 w-full gap-2" type="submit" disabled={busy}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              Create account
            </Button>
          </form>

          <form onSubmit={handleStartDeployment} className="rounded-lg border bg-card p-5">
            <h2 className="text-base font-semibold">Start Paper Deploy</h2>
            <label className="mt-5 block text-sm font-medium" htmlFor="paper-account">
              Paper account
              <select
                id="paper-account"
                value={selectedAccountId}
                onChange={(event) => setSelectedAccountId(event.target.value)}
                className="mt-2 h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
                required
              >
                <option value="">Select account</option>
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name} - {formatMoney(account.equity)}
                  </option>
                ))}
              </select>
            </label>
            <label className="mt-4 block text-sm font-medium" htmlFor="paper-version">
              Approved strategy version
              <select
                id="paper-version"
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
            </label>
            <Button className="mt-5 w-full gap-2" type="submit" disabled={busy || accounts.length === 0 || versions.length === 0}>
              <Play className="h-4 w-4" aria-hidden="true" />
              Start Paper Deploy
            </Button>
          </form>
        </div>

        <section className="space-y-4">
          <section className="rounded-lg border bg-card p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" aria-hidden="true" />
                <h2 className="text-base font-semibold">Paper Deploy</h2>
              </div>
              <Button variant="outline" size="sm" className="gap-2" type="button" onClick={() => void loadWorkspace()}>
                <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                Refresh
              </Button>
            </div>
            {deployments.length === 0 ? (
              <FeedbackState
                icon={Activity}
                title="No paper deploys"
                description="Create an account, choose a Backtested strategy version, and start a manual paper deploy."
              />
            ) : (
              <>
                <select
                  value={selectedDeploymentId}
                  onChange={(event) => setSelectedDeploymentId(event.target.value)}
                  className="mt-4 h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
                >
                  {deployments.map((deployment) => {
                    const version = versions.find((item) => item.id === deployment.strategy_version_id);
                    return (
                      <option key={deployment.id} value={deployment.id}>
                        {version?.strategy_name ?? deployment.strategy_id} - {deployment.status}
                      </option>
                    );
                  })}
                </select>
                {selectedDeployment ? (
                  <>
                    <div className="mt-5 grid gap-3 md:grid-cols-4">
                      {metrics.map((metric) => (
                        <div key={metric.label} className="rounded-md border bg-background p-4">
                          <p className="text-xs text-muted-foreground">{metric.label}</p>
                          <p className="mt-2 text-lg font-semibold">{metric.value}</p>
                        </div>
                      ))}
                    </div>
                    <div className="mt-5 flex flex-wrap gap-2">
                      <Button className="gap-2" type="button" disabled={busy || selectedDeployment.status !== "running"} onClick={() => void handleStep()}>
                        <StepForward className="h-4 w-4" aria-hidden="true" />
                        Step
                      </Button>
                      <Button variant="outline" className="gap-2" type="button" disabled={busy || selectedDeployment.status !== "running"} onClick={() => void handlePause()}>
                        <Pause className="h-4 w-4" aria-hidden="true" />
                        Pause
                      </Button>
                      <Button variant="outline" className="gap-2" type="button" disabled={busy || selectedDeployment.status === "stopped"} onClick={() => void handleStop()}>
                        <Square className="h-4 w-4" aria-hidden="true" />
                        Stop
                      </Button>
                    </div>
                  </>
                ) : null}
              </>
            )}
          </section>

          {selectedDeployment ? (
            <>
              <PaperRegimePanel
                regime={currentRegime}
                version={versions.find((version) => version.id === selectedDeployment.strategy_version_id) ?? null}
              />
              <PositionPanel deployment={selectedDeployment} />
              <TradesPanel deployment={selectedDeployment} />
            </>
          ) : null}
        </section>
      </section>
    </div>
  );
}

function PaperRegimePanel({
  regime,
  version,
}: {
  regime: MarketRegimeSnapshot | null;
  version: VersionOption | null;
}) {
  const allowedRegimes = version?.allowed_regimes ?? [];
  const blocked = Boolean(regime && allowedRegimes.length > 0 && !allowedRegimes.includes(regime.regime_label));
  return (
    <section className="rounded-lg border bg-card p-5">
      <h2 className="text-base font-semibold">Current regime</h2>
      {regime ? (
        <>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <p className="text-lg font-semibold">{regime.regime_label}</p>
            <span className="rounded-md border px-2 py-1 text-sm text-muted-foreground">
              {(regime.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">{regime.explanation}</p>
          {blocked ? (
            <p className="mt-3 rounded-md border bg-background p-3 text-sm text-muted-foreground">
              Strategy is paused for execution because {regime.regime_label} is not an allowed regime.
            </p>
          ) : null}
        </>
      ) : (
        <p className="mt-3 text-sm text-muted-foreground">No current regime is available for this deployment.</p>
      )}
    </section>
  );
}

function PositionPanel({ deployment }: { deployment: PaperDeployment }) {
  if (deployment.positions.length === 0) {
    return (
      <section className="rounded-lg border bg-card p-5">
        <h2 className="text-base font-semibold">Position</h2>
        <p className="mt-3 text-sm text-muted-foreground">No simulated position has been opened yet.</p>
      </section>
    );
  }
  return (
    <section className="rounded-lg border bg-card p-5">
      <h2 className="text-base font-semibold">Position</h2>
      <div className="mt-4 overflow-hidden rounded-md border">
        <table className="w-full text-left text-sm">
          <thead className="bg-muted/50 text-xs text-muted-foreground">
            <tr>
              <th className="px-3 py-2 font-medium">Symbol</th>
              <th className="px-3 py-2 font-medium">Quantity</th>
              <th className="px-3 py-2 font-medium">Average entry</th>
              <th className="px-3 py-2 font-medium">Unrealized</th>
              <th className="px-3 py-2 font-medium">Realized</th>
            </tr>
          </thead>
          <tbody>
            {deployment.positions.map((position) => (
              <tr key={position.id} className="border-t">
                <td className="px-3 py-2">{position.symbol}</td>
                <td className="px-3 py-2">{position.quantity.toFixed(6)}</td>
                <td className="px-3 py-2">{formatMoney(position.average_entry_price)}</td>
                <td className="px-3 py-2">{formatMoney(position.unrealized_pnl)}</td>
                <td className="px-3 py-2">{formatMoney(position.realized_pnl)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function TradesPanel({ deployment }: { deployment: PaperDeployment }) {
  return (
    <section className="rounded-lg border bg-card p-5">
      <h2 className="text-base font-semibold">Trades</h2>
      {deployment.trades.length === 0 ? (
        <p className="mt-3 text-sm text-muted-foreground">No simulated trades have been generated yet.</p>
      ) : (
        <div className="mt-4 overflow-hidden rounded-md border">
          <table className="w-full text-left text-sm">
            <thead className="bg-muted/50 text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Time</th>
                <th className="px-3 py-2 font-medium">Symbol</th>
                <th className="px-3 py-2 font-medium">Side</th>
                <th className="px-3 py-2 font-medium">Price</th>
                <th className="px-3 py-2 font-medium">Quantity</th>
                <th className="px-3 py-2 font-medium">PnL</th>
                <th className="px-3 py-2 font-medium">Reason</th>
              </tr>
            </thead>
            <tbody>
              {deployment.trades.map((trade) => (
                <tr key={trade.id} className="border-t">
                  <td className="px-3 py-2 text-muted-foreground">{new Date(trade.timestamp).toLocaleString()}</td>
                  <td className="px-3 py-2">{trade.symbol}</td>
                  <td className="px-3 py-2">{trade.side}</td>
                  <td className="px-3 py-2">{formatMoney(trade.price)}</td>
                  <td className="px-3 py-2">{trade.quantity.toFixed(6)}</td>
                  <td className="px-3 py-2">{formatMoney(trade.pnl)}</td>
                  <td className="px-3 py-2 text-muted-foreground">{trade.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function getDeploymentMetrics(deployment: PaperDeployment | null) {
  if (!deployment) {
    return [];
  }
  const account = deployment.account;
  return [
    { label: "Status", value: deployment.status },
    { label: "Cash", value: account ? formatMoney(account.cash_balance) : "-" },
    { label: "Equity", value: account ? formatMoney(account.equity) : "-" },
    { label: "Last step", value: deployment.last_processed_at ? new Date(deployment.last_processed_at).toLocaleString() : "Not started" },
  ];
}

function formatMoney(value: number) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value);
}
