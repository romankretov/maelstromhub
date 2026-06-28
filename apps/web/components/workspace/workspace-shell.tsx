"use client";

import type { FormEvent, ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  Bot,
  Braces,
  Clock3,
  LineChart,
  ListFilter,
  Loader2,
  NotebookText,
  Play,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Terminal,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  getWorkspaceState,
  loadWorkspaceMarket,
  type Candle,
  type WorkspaceRange,
  type WorkspaceState,
} from "@/lib/api-client";
import { cn } from "@/lib/utils";

const markets = ["BTC", "ETH", "SOL", "HYPE", "Manual"] as const;
const timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"] as const;
const ranges = ["7d", "30d", "90d", "180d", "1y"] as const satisfies readonly WorkspaceRange[];
const tabs = ["Strategy", "Backtests", "Optimisation", "Notes", "Logs"] as const;

type Market = (typeof markets)[number];
type Timeframe = (typeof timeframes)[number];
type Range = (typeof ranges)[number];
type Tab = (typeof tabs)[number];
type WorkspaceStatus = "idle" | "loading" | "queued" | "running" | "ready" | "error";

export function WorkspaceShell() {
  const [market, setMarket] = useState<Market>("BTC");
  const [manualMarket, setManualMarket] = useState("");
  const [timeframe, setTimeframe] = useState<Timeframe>("1h");
  const [range, setRange] = useState<Range>("90d");
  const [activeTab, setActiveTab] = useState<Tab>("Strategy");
  const [state, setState] = useState<WorkspaceState | null>(null);
  const [status, setStatus] = useState<WorkspaceStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshAt, setLastRefreshAt] = useState<string | null>(null);

  const displayMarket = useMemo(() => {
    if (market !== "Manual") return market;
    return manualMarket.trim().toUpperCase();
  }, [manualMarket, market]);

  const selectedSymbol = displayMarket || "CUSTOM";
  const stats = useMemo(() => computeChartStats(state?.latest_candles ?? []), [state?.latest_candles]);
  const stateStage = getStateStage(state, status, error);

  const refreshState = useCallback(async () => {
    if (!displayMarket) return;
    try {
      const nextState = await getWorkspaceState({ symbol: displayMarket, timeframe, range });
      setState(nextState);
      setError(null);
      setStatus(statusFromState(nextState));
    } catch (loadError) {
      setStatus("error");
      setError(errorMessage(loadError, "Unable to load workspace state."));
    }
  }, [displayMarket, timeframe, range]);

  useEffect(() => {
    if (!state || status === "idle" || status === "error") return;
    const shouldPoll =
      state.data_health.status === "queued" ||
      state.data_health.status === "running" ||
      state.candle_summary.total_candles === 0 ||
      state.feature_summary === null ||
      state.feature_summary.total_snapshots === 0 ||
      state.current_regime === null;
    if (!shouldPoll) return;

    const timer = window.setInterval(() => {
      void refreshState();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [refreshState, state, status]);

  async function handleRefresh(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!displayMarket) {
      setStatus("error");
      setError("Enter a market symbol before refreshing data.");
      return;
    }
    setStatus("loading");
    setError(null);
    try {
      const nextState = await loadWorkspaceMarket({ symbol: displayMarket, timeframe, range });
      setState(nextState);
      setStatus(statusFromState(nextState));
      setLastRefreshAt(new Date().toISOString());
    } catch (loadError) {
      setStatus("error");
      setError(errorMessage(loadError, "Unable to refresh workspace data."));
    }
  }

  return (
    <div className="min-h-screen bg-[#050608] text-zinc-100">
      <form onSubmit={handleRefresh} className="border-b border-zinc-800 bg-[#090b0f] px-4 py-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex h-10 items-center gap-2 rounded-md border border-zinc-800 bg-black px-3 text-sm">
            <Terminal className="h-4 w-4 text-emerald-300" aria-hidden="true" />
            <span className="font-medium">Maelstrom Workspace</span>
          </div>

          <label className="flex h-10 items-center gap-2 rounded-md border border-zinc-800 bg-[#0d1017] px-3 text-xs text-zinc-400">
            Market
            <select
              value={market}
              onChange={(event) => {
                setMarket(event.target.value as Market);
                setState(null);
                setStatus("idle");
              }}
              className="bg-transparent text-sm font-medium text-zinc-100 outline-none"
            >
              {markets.map((item) => (
                <option key={item} value={item} className="bg-zinc-950">
                  {item}
                </option>
              ))}
            </select>
          </label>

          {market === "Manual" ? (
            <label className="flex h-10 min-w-40 items-center gap-2 rounded-md border border-zinc-800 bg-[#0d1017] px-3 text-xs text-zinc-400">
              <Search className="h-4 w-4" aria-hidden="true" />
              <input
                value={manualMarket}
                onChange={(event) => {
                  setManualMarket(event.target.value);
                  setState(null);
                  setStatus("idle");
                }}
                placeholder="Enter symbol"
                className="w-full bg-transparent text-sm font-medium uppercase text-zinc-100 outline-none placeholder:text-zinc-600"
              />
            </label>
          ) : null}

          <SegmentedControl
            label="Timeframe"
            value={timeframe}
            options={timeframes}
            onChange={(value) => {
              setTimeframe(value as Timeframe);
              setState(null);
              setStatus("idle");
            }}
          />
          <SegmentedControl
            label="Range"
            value={range}
            options={ranges}
            onChange={(value) => {
              setRange(value as Range);
              setState(null);
              setStatus("idle");
            }}
          />

          <Button
            type="submit"
            disabled={status === "loading" || !displayMarket}
            className="ml-auto h-10 gap-2 border border-emerald-500/30 bg-emerald-500/10 text-emerald-200 shadow-none hover:bg-emerald-500/20"
          >
            {status === "loading" ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
            )}
            Refresh Data
          </Button>
        </div>
      </form>

      <div className="grid min-h-[calc(100vh-65px)] grid-cols-1 grid-rows-[auto_1fr_auto] xl:grid-cols-[220px_minmax(0,1fr)_320px] xl:grid-rows-[1fr_auto]">
        <MarketRail
          selectedSymbol={selectedSymbol}
          state={state}
          onSelect={(symbol) => {
            setMarket(symbol as Exclude<Market, "Manual">);
            setState(null);
            setStatus("idle");
          }}
        />

        <main className="min-w-0 bg-[#050608]">
          <section className="border-b border-zinc-800 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase text-zinc-500">Market / Chart</p>
                <h1 className="mt-1 text-xl font-semibold tracking-normal text-zinc-50">
                  {selectedSymbol} / USD Perpetual
                </h1>
                <p className="mt-1 text-sm text-zinc-500">
                  {state ? `${state.market.timeframe} candles over ${state.market.range}` : "Select a market and refresh data to load workspace state."}
                </p>
              </div>
              <MetricStrip state={state} stats={stats} />
            </div>
          </section>

          <section className="p-4">
            <div className="relative min-h-[360px] overflow-hidden rounded-md border border-zinc-800 bg-black md:min-h-[440px]">
              <div className="absolute inset-x-0 top-0 z-10 flex items-center justify-between border-b border-zinc-900 bg-[#07090d]/95 px-4 py-3">
                <div className="flex items-center gap-2 text-sm text-zinc-300">
                  <LineChart className="h-4 w-4 text-emerald-300" aria-hidden="true" />
                  Candle view
                </div>
                <div className="flex items-center gap-2 text-xs text-zinc-500">
                  <Clock3 className="h-4 w-4" aria-hidden="true" />
                  {lastRefreshAt ? `Last refresh ${formatDateTime(lastRefreshAt)}` : "Not refreshed"}
                </div>
              </div>
              <CandleChart candles={state?.latest_candles ?? []} stage={stateStage} />
            </div>
          </section>
        </main>

        <IntelligencePanel state={state} stats={stats} stage={stateStage} error={error} />

        <section className="border-t border-zinc-800 bg-[#080a0e] xl:col-span-3">
          <div className="flex overflow-x-auto border-b border-zinc-800 px-3">
            {tabs.map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={cn(
                  "flex h-11 shrink-0 items-center gap-2 border-b-2 px-4 text-sm transition-colors",
                  activeTab === tab
                    ? "border-emerald-300 text-emerald-200"
                    : "border-transparent text-zinc-500 hover:text-zinc-200",
                )}
              >
                <TabIcon tab={tab} />
                {tab}
              </button>
            ))}
          </div>
          <BottomPanel activeTab={activeTab} market={selectedSymbol} timeframe={timeframe} state={state} />
        </section>
      </div>
    </div>
  );
}

function MarketRail({
  selectedSymbol,
  state,
  onSelect,
}: {
  selectedSymbol: string;
  state: WorkspaceState | null;
  onSelect: (symbol: string) => void;
}) {
  return (
    <aside className="border-b border-zinc-800 bg-[#080a0e] p-3 xl:border-b-0 xl:border-r">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase text-zinc-500">Watchlist</p>
        <ListFilter className="h-4 w-4 text-zinc-500" aria-hidden="true" />
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-1">
        {["BTC", "ETH", "SOL", "HYPE"].map((symbol) => (
          <button
            key={symbol}
            type="button"
            onClick={() => onSelect(symbol)}
            className={cn(
              "rounded-md border p-3 text-left transition-colors",
              selectedSymbol === symbol
                ? "border-emerald-400/50 bg-emerald-400/10"
                : "border-zinc-800 bg-[#0d1017] hover:border-zinc-700",
            )}
          >
            <div className="flex items-center justify-between gap-3">
              <span className="font-medium text-zinc-100">{symbol}</span>
              <span className="text-xs text-zinc-500">hyperliquid</span>
            </div>
            <p className="mt-2 text-sm text-zinc-300">
              {state?.market.symbol === symbol && state.latest_candles.length > 0
                ? formatPrice(state.latest_candles[state.latest_candles.length - 1]?.close)
                : "--"}
            </p>
            <p className="mt-1 text-xs text-zinc-500">
              {state?.market.symbol === symbol ? state.data_health.status : "not loaded"}
            </p>
          </button>
        ))}
      </div>

      <div className="mt-4 rounded-md border border-zinc-800 bg-black p-3">
        <p className="text-xs font-medium uppercase text-zinc-500">Pipeline</p>
        <ol className="mt-3 space-y-2 text-xs text-zinc-400">
          {pipelineSteps(state).map((item, index) => (
            <li key={item.label} className="flex items-center gap-2">
              <span
                className={cn(
                  "flex h-5 w-5 items-center justify-center rounded border text-[10px]",
                  item.ready ? "border-emerald-400/40 text-emerald-200" : "border-zinc-700 text-zinc-500",
                )}
              >
                {index + 1}
              </span>
              {item.label}
            </li>
          ))}
        </ol>
      </div>
    </aside>
  );
}

function MetricStrip({ state, stats }: { state: WorkspaceState | null; stats: ChartStats }) {
  const metrics = [
    { label: "Latest Price", value: stats.latestPrice !== null ? formatPrice(stats.latestPrice) : "--", tone: "text-zinc-100" },
    { label: "Period Return", value: stats.periodReturn !== null ? formatPercent(stats.periodReturn) : "--", tone: stats.periodReturn !== null && stats.periodReturn >= 0 ? "text-emerald-300" : "text-red-300" },
    { label: "Volatility", value: stats.volatility !== null ? formatPercent(stats.volatility) : "--", tone: "text-sky-300" },
    { label: "Candles", value: String(state?.candle_summary.total_candles ?? 0), tone: "text-zinc-300" },
    { label: "Latest Candle", value: state?.candle_summary.latest_candle_timestamp ? formatDateTime(state.candle_summary.latest_candle_timestamp) : "--", tone: "text-zinc-300" },
  ];

  return (
    <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
      {metrics.map((metric) => (
        <div key={metric.label} className="min-w-28 rounded-md border border-zinc-800 bg-[#0d1017] px-3 py-2">
          <p className="text-[11px] uppercase text-zinc-500">{metric.label}</p>
          <p className={cn("mt-1 text-sm font-medium", metric.tone)}>{metric.value}</p>
        </div>
      ))}
    </div>
  );
}

function IntelligencePanel({
  state,
  stats,
  stage,
  error,
}: {
  state: WorkspaceState | null;
  stats: ChartStats;
  stage: StageState;
  error: string | null;
}) {
  const regime = state?.current_regime;
  return (
    <aside className="border-t border-zinc-800 bg-[#080a0e] p-4 xl:border-l xl:border-t-0">
      <div className="flex items-center gap-2">
        <Bot className="h-4 w-4 text-sky-300" aria-hidden="true" />
        <p className="text-sm font-medium">Assistant / Intelligence</p>
      </div>

      <div className="mt-4 space-y-3">
        <IntelligenceBlock
          icon={Activity}
          title="Data Health"
          value={stage.title}
          detail={error ?? stage.detail}
          tone={stage.tone}
        />
        <IntelligenceBlock
          icon={TrendingUp}
          title="Current Regime"
          value={regime?.regime_label ?? "Not computed"}
          detail={regime?.explanation ?? regimeMissingDetail(state)}
          tone={regime ? "emerald" : "amber"}
        />
        <IntelligenceBlock
          icon={BarChart3}
          title="Stats"
          value={stats.latestPrice !== null ? `${formatPrice(stats.latestPrice)} last` : "Waiting for candles"}
          detail={`Return ${stats.periodReturn !== null ? formatPercent(stats.periodReturn) : "--"}; volatility ${stats.volatility !== null ? formatPercent(stats.volatility) : "--"}.`}
          tone="sky"
        />
      </div>
    </aside>
  );
}

function SegmentedControl({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: readonly string[];
  onChange: (value: string) => void;
}) {
  return (
    <fieldset className="flex min-h-10 items-center gap-1 rounded-md border border-zinc-800 bg-[#0d1017] px-2">
      <legend className="sr-only">{label}</legend>
      <span className="px-1 text-xs text-zinc-500">{label}</span>
      {options.map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          className={cn(
            "h-7 rounded px-2 text-xs font-medium transition-colors",
            value === option ? "bg-zinc-100 text-zinc-950" : "text-zinc-500 hover:bg-zinc-900 hover:text-zinc-200",
          )}
        >
          {option}
        </button>
      ))}
    </fieldset>
  );
}

function CandleChart({ candles, stage }: { candles: Candle[]; stage: StageState }) {
  if (candles.length === 0) {
    return (
      <div className="flex min-h-[360px] items-center justify-center px-6 pt-12 text-center md:min-h-[440px]">
        <div>
          <p className="text-lg font-semibold text-zinc-100">{stage.title}</p>
          <p className="mt-2 max-w-md text-sm leading-6 text-zinc-500">{stage.detail}</p>
        </div>
      </div>
    );
  }

  const width = 900;
  const height = 360;
  const padding = { top: 58, right: 24, bottom: 42, left: 42 };
  const prices = candles.flatMap((candle) => [candle.high, candle.low]);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const priceRange = Math.max(maxPrice - minPrice, 1);
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const candleWidth = Math.max(3, Math.min(10, innerWidth / candles.length / 1.8));
  const volumeMax = Math.max(...candles.map((candle) => candle.volume), 1);

  function x(index: number) {
    if (candles.length === 1) return padding.left + innerWidth / 2;
    return padding.left + (index / (candles.length - 1)) * innerWidth;
  }

  function y(price: number) {
    return padding.top + ((maxPrice - price) / priceRange) * innerHeight;
  }

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-[360px] w-full md:h-[440px]" role="img" aria-label="Market candle chart">
      <defs>
        <pattern id="workspace-grid" width="44" height="44" patternUnits="userSpaceOnUse">
          <path d="M 44 0 L 0 0 0 44" fill="none" stroke="#18181b" strokeWidth="0.8" />
        </pattern>
      </defs>
      <rect width={width} height={height} fill="#020304" />
      <rect width={width} height={height} fill="url(#workspace-grid)" />
      {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
        const price = maxPrice - ratio * priceRange;
        return (
          <g key={ratio}>
            <line x1={padding.left} x2={width - padding.right} y1={y(price)} y2={y(price)} stroke="#27272a" strokeWidth="1" />
            <text x={8} y={y(price) + 4} fill="#71717a" fontSize="10">
              {formatPrice(price)}
            </text>
          </g>
        );
      })}
      {candles.map((candle, index) => {
        const up = candle.close >= candle.open;
        const color = up ? "#34d399" : "#fb7185";
        const center = x(index);
        const bodyY = Math.min(y(candle.open), y(candle.close));
        const bodyHeight = Math.max(2, Math.abs(y(candle.open) - y(candle.close)));
        const volumeHeight = (candle.volume / volumeMax) * 42;
        return (
          <g key={candle.id}>
            <rect
              x={center - candleWidth / 2}
              y={height - padding.bottom - volumeHeight}
              width={candleWidth}
              height={volumeHeight}
              fill="#3f3f46"
              opacity="0.45"
            />
            <line x1={center} x2={center} y1={y(candle.high)} y2={y(candle.low)} stroke={color} strokeWidth="1.4" />
            <rect
              x={center - candleWidth / 2}
              y={bodyY}
              width={candleWidth}
              height={bodyHeight}
              fill={color}
              opacity="0.92"
              rx="1"
            />
          </g>
        );
      })}
      <text x={padding.left} y={height - 14} fill="#71717a" fontSize="10">
        {candles.length} latest candles
      </text>
    </svg>
  );
}

function IntelligenceBlock({
  icon: Icon,
  title,
  value,
  detail,
  tone,
}: {
  icon: LucideIcon;
  title: string;
  value: string;
  detail: string;
  tone: "emerald" | "amber" | "sky" | "red";
}) {
  const toneClass = {
    emerald: "text-emerald-300 border-emerald-400/20 bg-emerald-400/5",
    amber: "text-amber-300 border-amber-400/20 bg-amber-400/5",
    sky: "text-sky-300 border-sky-400/20 bg-sky-400/5",
    red: "text-red-300 border-red-400/20 bg-red-400/5",
  }[tone];

  return (
    <section className={cn("rounded-md border p-3", toneClass)}>
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4" aria-hidden="true" />
        <p className="text-xs font-medium uppercase text-zinc-500">{title}</p>
      </div>
      <p className="mt-3 text-lg font-semibold text-zinc-100">{value}</p>
      <p className="mt-2 text-sm leading-5 text-zinc-400">{detail}</p>
    </section>
  );
}

function TabIcon({ tab }: { tab: Tab }) {
  const className = "h-4 w-4";
  if (tab === "Strategy") return <Settings2 className={className} aria-hidden="true" />;
  if (tab === "Backtests") return <BarChart3 className={className} aria-hidden="true" />;
  if (tab === "Optimisation") return <SlidersHorizontal className={className} aria-hidden="true" />;
  if (tab === "Notes") return <NotebookText className={className} aria-hidden="true" />;
  return <Terminal className={className} aria-hidden="true" />;
}

function BottomPanel({
  activeTab,
  market,
  timeframe,
  state,
}: {
  activeTab: Tab;
  market: string;
  timeframe: Timeframe;
  state: WorkspaceState | null;
}) {
  if (activeTab === "Strategy") {
    return (
      <PanelGrid>
        <PanelItem icon={Braces} label="Templates" value={`${state?.available_strategy_templates.length ?? 0} available`} />
        <PanelItem icon={Settings2} label="Parameters" value="Backtest orchestration pending" />
        <PanelItem icon={ShieldCheck} label="Allowed Regimes" value={state?.current_regime?.regime_label ?? "Compute regime first"} />
        <PanelItem icon={Play} label="Ready State" value={`Configure ${market} ${timeframe}`} />
      </PanelGrid>
    );
  }

  if (activeTab === "Backtests") {
    return (
      <PanelGrid>
        <PanelItem icon={BarChart3} label="Latest Runs" value={`${state?.latest_backtests.length ?? 0} found`} />
        <PanelItem icon={TrendingUp} label="Total Return" value="Run backtest next" />
        <PanelItem icon={Activity} label="Trade Count" value="--" />
        <PanelItem icon={ShieldCheck} label="Promotion Gate" value="Waiting for backtest" />
      </PanelGrid>
    );
  }

  if (activeTab === "Optimisation") {
    return (
      <PanelGrid>
        <PanelItem icon={SlidersHorizontal} label="Objective" value="Risk-adjusted score" />
        <PanelItem icon={BarChart3} label="Grid Runs" value="0 queued" />
        <PanelItem icon={TrendingUp} label="Best Candidate" value="Not available" />
        <PanelItem icon={Play} label="Action" value="Backtest orchestration pending" />
      </PanelGrid>
    );
  }

  if (activeTab === "Notes") {
    return (
      <div className="p-4">
        <div className="rounded-md border border-zinc-800 bg-black p-4 text-sm leading-6 text-zinc-400">
          Notes will capture research observations for the active workspace. Market data is now loaded through the
          workspace API; strategy and backtest orchestration come later.
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="font-mono text-xs leading-6 text-zinc-400">
        <p>[workspace] selected market={market}</p>
        <p>[workspace] selected timeframe={timeframe}</p>
        <p>[workspace] dataset_id={state?.dataset_id ?? "none"}</p>
        <p>[workspace] data_health={state?.data_health.status ?? "idle"}</p>
      </div>
    </div>
  );
}

function PanelGrid({ children }: { children: ReactNode }) {
  return <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-4">{children}</div>;
}

function PanelItem({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-800 bg-black p-3">
      <div className="flex items-center gap-2 text-xs uppercase text-zinc-500">
        <Icon className="h-4 w-4" aria-hidden="true" />
        {label}
      </div>
      <p className="mt-3 text-sm font-medium text-zinc-100">{value}</p>
    </div>
  );
}

type ChartStats = {
  latestPrice: number | null;
  periodReturn: number | null;
  volatility: number | null;
};

type StageState = {
  title: string;
  detail: string;
  tone: "emerald" | "amber" | "sky" | "red";
};

function computeChartStats(candles: Candle[]): ChartStats {
  if (candles.length === 0) return { latestPrice: null, periodReturn: null, volatility: null };
  const first = candles[0];
  const latest = candles[candles.length - 1];
  const returns = candles.slice(1).map((candle, index) => {
    const previous = candles[index];
    return previous.close === 0 ? 0 : candle.close / previous.close - 1;
  });
  const mean = returns.reduce((sum, value) => sum + value, 0) / Math.max(returns.length, 1);
  const variance = returns.reduce((sum, value) => sum + (value - mean) ** 2, 0) / Math.max(returns.length, 1);
  return {
    latestPrice: latest.close,
    periodReturn: first.close === 0 ? null : latest.close / first.close - 1,
    volatility: returns.length > 0 ? Math.sqrt(variance) : null,
  };
}

function getStateStage(state: WorkspaceState | null, status: WorkspaceStatus, error: string | null): StageState {
  if (status === "error") return { title: "Error", detail: error ?? "Workspace request failed.", tone: "red" };
  if (status === "loading") return { title: "Loading", detail: "Resolving market data and requesting workspace state.", tone: "sky" };
  if (!state) return { title: "No market loaded", detail: "Select a market, timeframe, and range, then refresh data.", tone: "amber" };
  if (state.data_health.status === "queued") return { title: "Ingestion queued", detail: state.data_health.detail, tone: "amber" };
  if (state.data_health.status === "running") return { title: "Ingestion running", detail: state.data_health.detail, tone: "sky" };
  if (state.data_health.status === "failed") return { title: "Data load failed", detail: state.data_health.detail, tone: "red" };
  if (state.candle_summary.total_candles === 0) return { title: "No candles", detail: "Refresh data to fetch candles for this market.", tone: "amber" };
  if (!state.feature_summary || state.feature_summary.total_snapshots === 0) return { title: "Features missing", detail: "Candles are loaded; workspace stats are being computed.", tone: "amber" };
  if (!state.current_regime) return { title: "Regime missing", detail: "Stats are ready; market regime is being computed.", tone: "amber" };
  return { title: "Ready", detail: state.data_health.detail, tone: "emerald" };
}

function statusFromState(state: WorkspaceState): WorkspaceStatus {
  if (state.data_health.status === "queued") return "queued";
  if (state.data_health.status === "running") return "running";
  return "ready";
}

function pipelineSteps(state: WorkspaceState | null) {
  return [
    { label: "Market", ready: Boolean(state?.market.symbol) },
    { label: "Candles", ready: (state?.candle_summary.total_candles ?? 0) > 0 },
    { label: "Stats", ready: (state?.feature_summary?.total_snapshots ?? 0) > 0 },
    { label: "Regime", ready: Boolean(state?.current_regime) },
    { label: "Backtest", ready: (state?.latest_backtests.length ?? 0) > 0 },
    { label: "Deploy", ready: false },
  ];
}

function regimeMissingDetail(state: WorkspaceState | null) {
  if (!state) return "Load a market to compute regime from feature snapshots.";
  if (state.candle_summary.total_candles === 0) return "Candles are required before regime detection.";
  if (!state.feature_summary || state.feature_summary.total_snapshots === 0) return "Stats are required before regime detection.";
  return "Regime computation is pending.";
}

function formatPrice(value: number | undefined | null) {
  if (value === null || value === undefined) return "--";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: value >= 100 ? 1 : 4 }).format(value);
}

function formatPercent(value: number) {
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString();
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}
