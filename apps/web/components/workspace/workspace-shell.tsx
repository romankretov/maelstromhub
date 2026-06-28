"use client";

import type { FormEvent } from "react";
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
  Plus,
  RefreshCw,
  Save,
  Search,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Terminal,
  Trash2,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  getWorkspaceState,
  getWorkspaceNotes,
  loadWorkspaceMarket,
  optimiseWorkspace,
  runWorkspaceBacktest,
  createWorkspaceNote,
  deleteWorkspaceNote,
  updateWorkspaceNote,
  type Candle,
  type StrategyParameterValue,
  type StrategyTemplate,
  type WorkspaceBacktestResult,
  type WorkspaceNote,
  type WorkspaceOptimisationResult,
  type WorkspaceRange,
  type WorkspaceState,
} from "@/lib/api-client";
import { cn } from "@/lib/utils";

const markets = ["BTC", "ETH", "SOL", "HYPE", "Manual"] as const;
const timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"] as const;
const ranges = ["7d", "30d", "90d", "180d", "1y"] as const satisfies readonly WorkspaceRange[];
const tabs = ["Strategy", "Backtests", "Optimisation", "Notes", "Logs"] as const;
const allowedRegimeOptions = [
  "Bull Trend",
  "Bear Trend",
  "Range",
  "Bull High Volatility",
  "Bear High Volatility",
  "Choppy High Volatility",
  "Low Volatility Range",
];

type Market = (typeof markets)[number];
type Timeframe = (typeof timeframes)[number];
type Range = (typeof ranges)[number];
type Tab = (typeof tabs)[number];
type WorkspaceStatus = "idle" | "loading" | "queued" | "running" | "ready" | "error";
type OptimisationRange = { start: number; end: number; step: number };

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
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [strategyParameters, setStrategyParameters] = useState<Record<string, StrategyParameterValue>>({});
  const [allowedRegimes, setAllowedRegimes] = useState<string[]>([]);
  const [startingBalance, setStartingBalance] = useState(10_000);
  const [feeBps, setFeeBps] = useState(5);
  const [slippageBps, setSlippageBps] = useState(2);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [backtestResult, setBacktestResult] = useState<WorkspaceBacktestResult | null>(null);
  const [backtestStatus, setBacktestStatus] = useState<"idle" | "running" | "error">("idle");
  const [backtestError, setBacktestError] = useState<string | null>(null);
  const [optimisationRanges, setOptimisationRanges] = useState<Record<string, OptimisationRange>>({
    fast_window: { start: 10, end: 30, step: 10 },
    slow_window: { start: 40, end: 80, step: 20 },
    rsi_period: { start: 14, end: 14, step: 1 },
    oversold: { start: 25, end: 35, step: 5 },
    overbought: { start: 65, end: 75, step: 5 },
  });
  const [optimisationResult, setOptimisationResult] = useState<WorkspaceOptimisationResult | null>(null);
  const [optimisationStatus, setOptimisationStatus] = useState<"idle" | "running" | "error">("idle");
  const [optimisationError, setOptimisationError] = useState<string | null>(null);
  const [notes, setNotes] = useState<WorkspaceNote[]>([]);
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const [noteTitle, setNoteTitle] = useState("Research note");
  const [noteBody, setNoteBody] = useState(defaultNoteBody());
  const [notesStatus, setNotesStatus] = useState<"idle" | "loading" | "saving" | "error">("idle");
  const [notesError, setNotesError] = useState<string | null>(null);

  const displayMarket = useMemo(() => {
    if (market !== "Manual") return market;
    return manualMarket.trim().toUpperCase();
  }, [manualMarket, market]);

  const selectedSymbol = displayMarket || "CUSTOM";
  const stats = useMemo(() => computeChartStats(state?.latest_candles ?? []), [state?.latest_candles]);
  const stateStage = getStateStage(state, status, error);
  const selectedTemplate = useMemo(
    () => state?.available_strategy_templates.find((template) => template.id === selectedTemplateId) ?? null,
    [selectedTemplateId, state?.available_strategy_templates],
  );

  useEffect(() => {
    const templates = state?.available_strategy_templates ?? [];
    if (templates.length === 0) return;
    const nextTemplate = templates.find((template) => template.id === selectedTemplateId) ?? templates[0];
    if (nextTemplate.id !== selectedTemplateId) {
      setSelectedTemplateId(nextTemplate.id);
      setStrategyParameters(nextTemplate.default_parameters);
      return;
    }
    setStrategyParameters((current) =>
      Object.keys(current).length === 0 ? nextTemplate.default_parameters : current,
    );
  }, [selectedTemplateId, state?.available_strategy_templates]);

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

  useEffect(() => {
    if (!displayMarket) return;
    let cancelled = false;
    setNotesStatus("loading");
    getWorkspaceNotes({ symbol: displayMarket, timeframe })
      .then((items) => {
        if (cancelled) return;
        setNotes(items);
        setSelectedNoteId(items[0]?.id ?? null);
        setNoteTitle(items[0]?.title ?? "Research note");
        setNoteBody(items[0]?.body ?? defaultNoteBody());
        setNotesStatus("idle");
        setNotesError(null);
      })
      .catch((loadError) => {
        if (cancelled) return;
        setNotesStatus("error");
        setNotesError(errorMessage(loadError, "Unable to load workspace notes."));
      });
    return () => {
      cancelled = true;
    };
  }, [displayMarket, timeframe]);

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

  async function handleRunBacktest() {
    if (!displayMarket || !selectedTemplate) {
      setBacktestStatus("error");
      setBacktestError("Select a market and strategy template before running a backtest.");
      return;
    }
    setBacktestStatus("running");
    setBacktestError(null);
    try {
      const result = await runWorkspaceBacktest({
        symbol: displayMarket,
        timeframe,
        range,
        template_id: selectedTemplate.id,
        parameters: strategyParameters,
        starting_balance: startingBalance,
        fee_bps: feeBps,
        slippage_bps: slippageBps,
        allowed_regimes: allowedRegimes.length > 0 ? allowedRegimes : null,
      });
      setBacktestResult(result);
      setState(result.workspace_state);
      setActiveTab("Backtests");
      setBacktestStatus("idle");
    } catch (runError) {
      setBacktestStatus("error");
      setBacktestError(errorMessage(runError, "Unable to run workspace backtest."));
    }
  }

  async function handleRunOptimisation() {
    if (!displayMarket || !selectedTemplate) {
      setOptimisationStatus("error");
      setOptimisationError("Select a market and strategy template before running optimisation.");
      return;
    }
    setOptimisationStatus("running");
    setOptimisationError(null);
    try {
      const result = await optimiseWorkspace({
        symbol: displayMarket,
        timeframe,
        range,
        template_id: selectedTemplate.id,
        parameter_grid: optimisationGridForTemplate(selectedTemplate, optimisationRanges),
        starting_balance: startingBalance,
        fee_bps: feeBps,
        slippage_bps: slippageBps,
        allowed_regimes: allowedRegimes.length > 0 ? allowedRegimes : null,
      });
      setOptimisationResult(result);
      setState(result.workspace_state);
      setOptimisationStatus("idle");
    } catch (runError) {
      setOptimisationStatus("error");
      setOptimisationError(errorMessage(runError, "Unable to run workspace optimisation."));
    }
  }

  function handleSelectNote(note: WorkspaceNote) {
    setSelectedNoteId(note.id);
    setNoteTitle(note.title);
    setNoteBody(note.body);
    setNotesError(null);
  }

  function handleNewNote() {
    setSelectedNoteId(null);
    setNoteTitle("Research note");
    setNoteBody(defaultNoteBody());
    setNotesError(null);
  }

  async function handleSaveNote() {
    if (!displayMarket) return;
    setNotesStatus("saving");
    setNotesError(null);
    try {
      const saved = selectedNoteId
        ? await updateWorkspaceNote(selectedNoteId, { title: noteTitle, body: noteBody })
        : await createWorkspaceNote({ symbol: displayMarket, timeframe, title: noteTitle, body: noteBody });
      setSelectedNoteId(saved.id);
      setNoteTitle(saved.title);
      setNoteBody(saved.body);
      setNotes((current) => [saved, ...current.filter((note) => note.id !== saved.id)]);
      setNotesStatus("idle");
    } catch (saveError) {
      setNotesStatus("error");
      setNotesError(errorMessage(saveError, "Unable to save workspace note."));
    }
  }

  async function handleDeleteNote(noteId: string) {
    setNotesStatus("saving");
    setNotesError(null);
    try {
      await deleteWorkspaceNote(noteId);
      setNotes((current) => {
        const remaining = current.filter((note) => note.id !== noteId);
        const next = remaining[0] ?? null;
        setSelectedNoteId(next?.id ?? null);
        setNoteTitle(next?.title ?? "Research note");
        setNoteBody(next?.body ?? defaultNoteBody());
        return remaining;
      });
      setNotesStatus("idle");
    } catch (deleteError) {
      setNotesStatus("error");
      setNotesError(errorMessage(deleteError, "Unable to delete workspace note."));
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
          <BottomPanel
            activeTab={activeTab}
            market={selectedSymbol}
            timeframe={timeframe}
            state={state}
            selectedTemplate={selectedTemplate}
            selectedTemplateId={selectedTemplateId}
            onTemplateChange={(templateId) => {
              const template = state?.available_strategy_templates.find((item) => item.id === templateId);
              setSelectedTemplateId(templateId);
              setStrategyParameters(template?.default_parameters ?? {});
            }}
            parameters={strategyParameters}
            onParameterChange={(key, value) => setStrategyParameters((current) => ({ ...current, [key]: value }))}
            allowedRegimes={allowedRegimes}
            onAllowedRegimeToggle={(label) =>
              setAllowedRegimes((current) =>
                current.includes(label) ? current.filter((item) => item !== label) : [...current, label],
              )
            }
            startingBalance={startingBalance}
            feeBps={feeBps}
            slippageBps={slippageBps}
            onStartingBalanceChange={setStartingBalance}
            onFeeBpsChange={setFeeBps}
            onSlippageBpsChange={setSlippageBps}
            advancedOpen={advancedOpen}
            onAdvancedOpenChange={setAdvancedOpen}
            backtestResult={backtestResult}
            backtestStatus={backtestStatus}
            backtestError={backtestError}
            onRunBacktest={handleRunBacktest}
            optimisationRanges={optimisationRanges}
            onOptimisationRangeChange={(key, field, value) =>
              setOptimisationRanges((current) => ({
                ...current,
                [key]: { ...(current[key] ?? { start: 0, end: 0, step: 1 }), [field]: value },
              }))
            }
            optimisationResult={optimisationResult}
            optimisationStatus={optimisationStatus}
            optimisationError={optimisationError}
            onRunOptimisation={handleRunOptimisation}
            notes={notes}
            selectedNoteId={selectedNoteId}
            noteTitle={noteTitle}
            noteBody={noteBody}
            notesStatus={notesStatus}
            notesError={notesError}
            onSelectNote={handleSelectNote}
            onNewNote={handleNewNote}
            onNoteTitleChange={setNoteTitle}
            onNoteBodyChange={setNoteBody}
            onSaveNote={handleSaveNote}
            onDeleteNote={handleDeleteNote}
          />
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
  selectedTemplate,
  selectedTemplateId,
  onTemplateChange,
  parameters,
  onParameterChange,
  allowedRegimes,
  onAllowedRegimeToggle,
  startingBalance,
  feeBps,
  slippageBps,
  onStartingBalanceChange,
  onFeeBpsChange,
  onSlippageBpsChange,
  advancedOpen,
  onAdvancedOpenChange,
  backtestResult,
  backtestStatus,
  backtestError,
  onRunBacktest,
  optimisationRanges,
  onOptimisationRangeChange,
  optimisationResult,
  optimisationStatus,
  optimisationError,
  onRunOptimisation,
  notes,
  selectedNoteId,
  noteTitle,
  noteBody,
  notesStatus,
  notesError,
  onSelectNote,
  onNewNote,
  onNoteTitleChange,
  onNoteBodyChange,
  onSaveNote,
  onDeleteNote,
}: {
  activeTab: Tab;
  market: string;
  timeframe: Timeframe;
  state: WorkspaceState | null;
  selectedTemplate: StrategyTemplate | null;
  selectedTemplateId: string;
  onTemplateChange: (templateId: string) => void;
  parameters: Record<string, StrategyParameterValue>;
  onParameterChange: (key: string, value: StrategyParameterValue) => void;
  allowedRegimes: string[];
  onAllowedRegimeToggle: (label: string) => void;
  startingBalance: number;
  feeBps: number;
  slippageBps: number;
  onStartingBalanceChange: (value: number) => void;
  onFeeBpsChange: (value: number) => void;
  onSlippageBpsChange: (value: number) => void;
  advancedOpen: boolean;
  onAdvancedOpenChange: (open: boolean) => void;
  backtestResult: WorkspaceBacktestResult | null;
  backtestStatus: "idle" | "running" | "error";
  backtestError: string | null;
  onRunBacktest: () => void;
  optimisationRanges: Record<string, OptimisationRange>;
  onOptimisationRangeChange: (key: string, field: keyof OptimisationRange, value: number) => void;
  optimisationResult: WorkspaceOptimisationResult | null;
  optimisationStatus: "idle" | "running" | "error";
  optimisationError: string | null;
  onRunOptimisation: () => void;
  notes: WorkspaceNote[];
  selectedNoteId: string | null;
  noteTitle: string;
  noteBody: string;
  notesStatus: "idle" | "loading" | "saving" | "error";
  notesError: string | null;
  onSelectNote: (note: WorkspaceNote) => void;
  onNewNote: () => void;
  onNoteTitleChange: (value: string) => void;
  onNoteBodyChange: (value: string) => void;
  onSaveNote: () => void;
  onDeleteNote: (noteId: string) => void;
}) {
  if (activeTab === "Strategy") {
    const essentialKeys = selectedTemplate ? essentialParameterKeys(selectedTemplate) : [];
    const advancedKeys = selectedTemplate
      ? Object.keys(selectedTemplate.default_parameters).filter((key) => !essentialKeys.includes(key))
      : [];
    const canRun = Boolean(state?.dataset_id && selectedTemplate && state.candle_summary.total_candles > 0);

    return (
      <div className="grid gap-4 p-4 xl:grid-cols-[360px_minmax(0,1fr)_280px]">
        <section className="rounded-md border border-zinc-800 bg-black p-4">
          <div className="flex items-center gap-2 text-xs uppercase text-zinc-500">
            <Braces className="h-4 w-4" aria-hidden="true" />
            Template
          </div>
          <select
            value={selectedTemplateId}
            onChange={(event) => onTemplateChange(event.target.value)}
            className="mt-3 h-10 w-full rounded-md border border-zinc-700 bg-[#0d1017] px-3 text-sm text-zinc-100 outline-none"
          >
            {(state?.available_strategy_templates ?? []).map((template) => (
              <option key={template.id} value={template.id} className="bg-zinc-950">
                {template.name}
              </option>
            ))}
          </select>
          <p className="mt-3 text-sm leading-5 text-zinc-400">
            {selectedTemplate?.description ?? "Load a market to fetch strategy templates."}
          </p>
        </section>

        <section className="rounded-md border border-zinc-800 bg-black p-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs uppercase text-zinc-500">
              <Settings2 className="h-4 w-4" aria-hidden="true" />
              Parameters
            </div>
            <button
              type="button"
              onClick={() => onAdvancedOpenChange(!advancedOpen)}
              className="text-xs text-zinc-400 hover:text-zinc-100"
            >
              {advancedOpen ? "Hide advanced" : "Advanced"}
            </button>
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {essentialKeys.map((key) => (
              <ParameterInput key={key} paramKey={key} value={parameters[key]} onChange={onParameterChange} />
            ))}
            {advancedOpen
              ? advancedKeys.map((key) => (
                  <ParameterInput key={key} paramKey={key} value={parameters[key]} onChange={onParameterChange} />
                ))
              : null}
          </div>
        </section>

        <section className="rounded-md border border-zinc-800 bg-black p-4">
          <div className="flex items-center gap-2 text-xs uppercase text-zinc-500">
            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            Regime Filter
          </div>
          <div className="mt-3 grid max-h-36 gap-2 overflow-y-auto pr-1 text-sm">
            {allowedRegimeOptions.map((label) => (
              <label key={label} className="flex items-center gap-2 text-zinc-300">
                <input
                  type="checkbox"
                  checked={allowedRegimes.includes(label)}
                  onChange={() => onAllowedRegimeToggle(label)}
                  className="h-4 w-4 accent-emerald-400"
                />
                {label}
              </label>
            ))}
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2">
            <SmallNumberInput label="Balance" value={startingBalance} onChange={onStartingBalanceChange} />
            <SmallNumberInput label="Fee bps" value={feeBps} onChange={onFeeBpsChange} />
            <SmallNumberInput label="Slip bps" value={slippageBps} onChange={onSlippageBpsChange} />
          </div>
          {backtestStatus === "error" ? <p className="mt-3 text-sm text-red-300">{backtestError}</p> : null}
          <Button
            type="button"
            disabled={!canRun || backtestStatus === "running"}
            onClick={onRunBacktest}
            className="mt-4 h-10 w-full gap-2 border border-emerald-500/30 bg-emerald-500/10 text-emerald-200 shadow-none hover:bg-emerald-500/20"
          >
            {backtestStatus === "running" ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Play className="h-4 w-4" aria-hidden="true" />
            )}
            Run Backtest
          </Button>
        </section>
      </div>
    );
  }

  if (activeTab === "Backtests") {
    const backtest = backtestResult?.backtest;
    const metrics = backtest?.metrics ?? state?.latest_backtests[0]?.metrics ?? {};
    return (
      <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="rounded-md border border-zinc-800 bg-black p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase text-zinc-500">Latest Backtest</p>
              <h2 className="mt-1 text-lg font-semibold text-zinc-100">
                {backtest ? `${market} ${timeframe}` : "No workspace backtest yet"}
              </h2>
            </div>
            <span className="rounded border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-sm text-emerald-200">
              {backtestResult?.evaluation.verdict ?? "Waiting"}
            </span>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-5">
            <MetricBox label="Return" value={metricPercent(metrics["total_return"])} />
            <MetricBox label="Max Drawdown" value={metricPercent(metrics["max_drawdown"])} />
            <MetricBox label="Win Rate" value={metricPercent(metrics["win_rate"])} />
            <MetricBox label="Profit Factor" value={metricNumber(metrics["profit_factor"])} />
            <MetricBox label="Trades" value={String(metricRaw(metrics["trade_count"]) ?? "--")} />
          </div>
          {backtest ? <EquityCurveChart snapshots={backtest.equity_curve} /> : null}
          {backtest ? <TradeTable trades={backtest.trades} /> : null}
        </section>

        <section className="rounded-md border border-zinc-800 bg-black p-4">
          <div className="flex items-center gap-2 text-xs uppercase text-zinc-500">
            <Activity className="h-4 w-4" aria-hidden="true" />
            Regime Performance
          </div>
          <RegimePerformance metrics={metrics} />
          <div className="mt-4 rounded-md border border-zinc-800 bg-[#0d1017] p-3">
            <p className="text-xs uppercase text-zinc-500">Signals</p>
            <p className="mt-2 text-sm text-zinc-300">
              {backtestResult
                ? `${backtestResult.signals_written} written / ${backtestResult.total_signals} total`
                : "Run a workspace backtest to generate signals."}
            </p>
          </div>
        </section>
      </div>
    );
  }

  if (activeTab === "Optimisation") {
    const optimisationKeys = selectedTemplate ? optimisationKeysForTemplate(selectedTemplate) : [];
    const canRun = Boolean(state?.dataset_id && selectedTemplate && state.candle_summary.total_candles > 0);
    const best = optimisationResult?.results[0] ?? null;
    return (
      <div className="grid gap-4 p-4 xl:grid-cols-[340px_minmax(0,1fr)]">
        <section className="rounded-md border border-zinc-800 bg-black p-4">
          <div className="flex items-center gap-2 text-xs uppercase text-zinc-500">
            <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
            Parameter Ranges
          </div>
          <div className="mt-3 space-y-3">
            {optimisationKeys.map((key) => (
              <RangeInputRow
                key={key}
                paramKey={key}
                value={optimisationRanges[key]}
                onChange={onOptimisationRangeChange}
              />
            ))}
          </div>
          {optimisationStatus === "error" ? <p className="mt-3 text-sm text-red-300">{optimisationError}</p> : null}
          <Button
            type="button"
            disabled={!canRun || optimisationStatus === "running"}
            onClick={onRunOptimisation}
            className="mt-4 h-10 w-full gap-2 border border-sky-500/30 bg-sky-500/10 text-sky-200 shadow-none hover:bg-sky-500/20"
          >
            {optimisationStatus === "running" ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Play className="h-4 w-4" aria-hidden="true" />
            )}
            Run Optimisation
          </Button>
        </section>

        <section className="rounded-md border border-zinc-800 bg-black p-4">
          <div className="grid gap-3 md:grid-cols-4">
            <MetricBox label="Grid Runs" value={String(optimisationResult?.total_combinations ?? 0)} />
            <MetricBox label="Best Return" value={metricPercent(best?.backtest.metrics["total_return"])} />
            <MetricBox label="Best Drawdown" value={metricPercent(best?.backtest.metrics["max_drawdown"])} />
            <MetricBox label="Best Score" value={metricNumber(best?.evaluation.risk_adjusted_score)} />
          </div>
          <OptimisationResultsTable result={optimisationResult} />
        </section>
      </div>
    );
  }

  if (activeTab === "Notes") {
    return (
      <div className="grid gap-4 p-4 xl:grid-cols-[300px_minmax(0,1fr)]">
        <section className="rounded-md border border-zinc-800 bg-black p-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs uppercase text-zinc-500">
              <NotebookText className="h-4 w-4" aria-hidden="true" />
              Notes
            </div>
            <button
              type="button"
              onClick={onNewNote}
              className="flex h-8 w-8 items-center justify-center rounded border border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:text-zinc-100"
              aria-label="New note"
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
          <div className="mt-3 max-h-64 space-y-2 overflow-auto pr-1">
            {notes.length === 0 ? (
              <p className="rounded-md border border-zinc-800 bg-[#0d1017] p-3 text-sm text-zinc-500">
                No notes for {market} {timeframe}.
              </p>
            ) : (
              notes.map((note) => (
                <button
                  key={note.id}
                  type="button"
                  onClick={() => onSelectNote(note)}
                  className={cn(
                    "w-full rounded-md border p-3 text-left text-sm transition-colors",
                    selectedNoteId === note.id
                      ? "border-emerald-400/40 bg-emerald-400/10"
                      : "border-zinc-800 bg-[#0d1017] hover:border-zinc-700",
                  )}
                >
                  <span className="block font-medium text-zinc-100">{note.title}</span>
                  <span className="mt-1 block text-xs text-zinc-500">Updated {formatDateTime(note.updated_at)}</span>
                </button>
              ))
            )}
          </div>
        </section>

        <section className="rounded-md border border-zinc-800 bg-black p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs uppercase text-zinc-500">
              {market} {timeframe} / Markdown
            </p>
            <div className="flex items-center gap-2">
              {selectedNoteId ? (
                <button
                  type="button"
                  onClick={() => onDeleteNote(selectedNoteId)}
                  disabled={notesStatus === "saving"}
                  className="flex h-9 w-9 items-center justify-center rounded border border-red-500/30 text-red-300 hover:bg-red-500/10 disabled:opacity-50"
                  aria-label="Delete note"
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </button>
              ) : null}
              <Button
                type="button"
                onClick={onSaveNote}
                disabled={notesStatus === "saving"}
                className="h-9 gap-2 border border-emerald-500/30 bg-emerald-500/10 text-emerald-200 shadow-none hover:bg-emerald-500/20"
              >
                {notesStatus === "saving" ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <Save className="h-4 w-4" aria-hidden="true" />
                )}
                Save
              </Button>
            </div>
          </div>
          <input
            value={noteTitle}
            onChange={(event) => onNoteTitleChange(event.target.value)}
            className="mt-3 h-10 w-full rounded-md border border-zinc-700 bg-[#0d1017] px-3 text-sm font-medium text-zinc-100 outline-none"
            placeholder="Note title"
          />
          <textarea
            value={noteBody}
            onChange={(event) => onNoteBodyChange(event.target.value)}
            className="mt-3 min-h-64 w-full resize-y rounded-md border border-zinc-700 bg-[#050608] p-3 font-mono text-sm leading-6 text-zinc-100 outline-none placeholder:text-zinc-600"
            placeholder="Write markdown notes..."
          />
          {notesStatus === "loading" ? <p className="mt-2 text-sm text-zinc-500">Loading notes...</p> : null}
          {notesStatus === "error" ? <p className="mt-2 text-sm text-red-300">{notesError}</p> : null}
        </section>
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

function ParameterInput({
  paramKey,
  value,
  onChange,
}: {
  paramKey: string;
  value: StrategyParameterValue;
  onChange: (key: string, value: StrategyParameterValue) => void;
}) {
  return (
    <label className="text-xs uppercase text-zinc-500">
      {formatParamLabel(paramKey)}
      <input
        type="number"
        value={typeof value === "number" ? value : ""}
        onChange={(event) => onChange(paramKey, Number(event.target.value))}
        className="mt-1 h-9 w-full rounded-md border border-zinc-700 bg-[#0d1017] px-3 text-sm text-zinc-100 outline-none"
      />
    </label>
  );
}

function SmallNumberInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="text-[11px] uppercase text-zinc-500">
      {label}
      <input
        type="number"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-1 h-8 w-full rounded-md border border-zinc-700 bg-[#0d1017] px-2 text-xs text-zinc-100 outline-none"
      />
    </label>
  );
}

function RangeInputRow({
  paramKey,
  value,
  onChange,
}: {
  paramKey: string;
  value: OptimisationRange | undefined;
  onChange: (key: string, field: keyof OptimisationRange, value: number) => void;
}) {
  const range = value ?? { start: 0, end: 0, step: 1 };
  return (
    <div className="rounded-md border border-zinc-800 bg-[#0d1017] p-3">
      <p className="text-xs uppercase text-zinc-500">{formatParamLabel(paramKey)}</p>
      <div className="mt-2 grid grid-cols-3 gap-2">
        {(["start", "end", "step"] as const).map((field) => (
          <label key={field} className="text-[11px] uppercase text-zinc-500">
            {field}
            <input
              type="number"
              value={range[field]}
              onChange={(event) => onChange(paramKey, field, Number(event.target.value))}
              className="mt-1 h-8 w-full rounded-md border border-zinc-700 bg-black px-2 text-xs text-zinc-100 outline-none"
            />
          </label>
        ))}
      </div>
    </div>
  );
}

function MetricBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-800 bg-[#0d1017] p-3">
      <p className="text-[11px] uppercase text-zinc-500">{label}</p>
      <p className="mt-2 text-sm font-medium text-zinc-100">{value}</p>
    </div>
  );
}

function OptimisationResultsTable({ result }: { result: WorkspaceOptimisationResult | null }) {
  const rows = result?.results.slice(0, 10) ?? [];
  if (rows.length === 0) {
    return <p className="mt-4 text-sm text-zinc-500">Run optimisation to rank parameter combinations.</p>;
  }
  return (
    <div className="mt-4 overflow-auto rounded-md border border-zinc-800">
      <table className="w-full text-left text-xs">
        <thead className="bg-[#0d1017] text-zinc-500">
          <tr>
            <th className="px-3 py-2 font-medium">Rank</th>
            <th className="px-3 py-2 font-medium">Parameters</th>
            <th className="px-3 py-2 font-medium">Return</th>
            <th className="px-3 py-2 font-medium">Drawdown</th>
            <th className="px-3 py-2 font-medium">Trades</th>
            <th className="px-3 py-2 font-medium">Score</th>
            <th className="px-3 py-2 font-medium">Verdict</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-900 text-zinc-300">
          {rows.map((candidate) => (
            <tr key={candidate.backtest.id} className={candidate.rank === 1 ? "bg-emerald-400/5" : undefined}>
              <td className="px-3 py-2 text-zinc-100">{candidate.rank}</td>
              <td className="px-3 py-2">{formatParameters(candidate.parameters)}</td>
              <td className="px-3 py-2">{metricPercent(candidate.backtest.metrics["total_return"])}</td>
              <td className="px-3 py-2">{metricPercent(candidate.backtest.metrics["max_drawdown"])}</td>
              <td className="px-3 py-2">{metricRaw(candidate.backtest.metrics["trade_count"]) ?? 0}</td>
              <td className="px-3 py-2">{metricNumber(candidate.evaluation.risk_adjusted_score)}</td>
              <td className="px-3 py-2">{candidate.evaluation.verdict}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EquityCurveChart({ snapshots }: { snapshots: WorkspaceBacktestResult["backtest"]["equity_curve"] }) {
  if (snapshots.length === 0) {
    return <p className="mt-4 text-sm text-zinc-500">No equity curve snapshots were generated.</p>;
  }
  const width = 760;
  const height = 160;
  const values = snapshots.map((snapshot) => snapshot.equity);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 1);
  const points = values
    .map((value, index) => {
      const x = snapshots.length === 1 ? width / 2 : (index / (snapshots.length - 1)) * width;
      const y = height - ((value - min) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="mt-4 h-40 w-full rounded-md border border-zinc-800 bg-[#050608]">
      <polyline points={points} fill="none" stroke="#34d399" strokeWidth="2" />
    </svg>
  );
}

function TradeTable({ trades }: { trades: WorkspaceBacktestResult["backtest"]["trades"] }) {
  if (trades.length === 0) return <p className="mt-4 text-sm text-zinc-500">No completed trades in this run.</p>;
  return (
    <div className="mt-4 max-h-44 overflow-auto rounded-md border border-zinc-800">
      <table className="w-full text-left text-xs">
        <thead className="sticky top-0 bg-[#0d1017] text-zinc-500">
          <tr>
            <th className="px-3 py-2 font-medium">Time</th>
            <th className="px-3 py-2 font-medium">Side</th>
            <th className="px-3 py-2 font-medium">Entry</th>
            <th className="px-3 py-2 font-medium">Exit</th>
            <th className="px-3 py-2 font-medium">PnL</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-900 text-zinc-300">
          {trades.slice(0, 20).map((trade) => (
            <tr key={trade.id}>
              <td className="px-3 py-2">{formatDateTime(trade.timestamp)}</td>
              <td className="px-3 py-2">{trade.side}</td>
              <td className="px-3 py-2">{formatPrice(trade.entry_price)}</td>
              <td className="px-3 py-2">{formatPrice(trade.exit_price)}</td>
              <td className={cn("px-3 py-2", trade.pnl >= 0 ? "text-emerald-300" : "text-red-300")}>
                {formatPrice(trade.pnl)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RegimePerformance({ metrics }: { metrics: Record<string, unknown> }) {
  const pnl = objectMetric(metrics.pnl_by_regime);
  const counts = objectMetric(metrics.trade_count_by_regime);
  const winRates = objectMetric(metrics.win_rate_by_regime);
  const labels = Array.from(new Set([...Object.keys(pnl), ...Object.keys(counts), ...Object.keys(winRates)]));
  const coverage = objectMetric(metrics.regime_coverage);
  if (labels.length === 0) {
    return (
      <p className="mt-3 text-sm leading-5 text-zinc-500">
        Regime coverage {metricPercent(coverage.coverage_ratio)}. No completed trades were attributed to regimes.
      </p>
    );
  }
  return (
    <div className="mt-3 space-y-2">
      {labels.map((label) => (
        <div key={label} className="rounded-md border border-zinc-800 bg-[#0d1017] p-3 text-sm">
          <p className="font-medium text-zinc-100">{label}</p>
          <p className="mt-1 text-zinc-400">
            PnL {metricNumber(pnl[label])} / trades {metricRaw(counts[label]) ?? 0} / win{" "}
            {metricPercent(winRates[label])}
          </p>
        </div>
      ))}
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

function essentialParameterKeys(template: StrategyTemplate) {
  const name = template.name.toLowerCase();
  if (name.includes("sma")) return ["fast_window", "slow_window"];
  if (name.includes("rsi")) return ["oversold", "overbought"];
  return Object.keys(template.default_parameters);
}

function optimisationKeysForTemplate(template: StrategyTemplate) {
  const name = template.name.toLowerCase();
  if (name.includes("sma")) return ["fast_window", "slow_window"];
  if (name.includes("rsi")) return ["rsi_period", "oversold", "overbought"];
  return Object.keys(template.default_parameters);
}

function optimisationGridForTemplate(
  template: StrategyTemplate,
  ranges: Record<string, OptimisationRange>,
) {
  const grid: Record<string, StrategyParameterValue[]> = {};
  for (const key of optimisationKeysForTemplate(template)) {
    grid[key] = rangeValues(ranges[key]);
  }
  return grid;
}

function rangeValues(range: OptimisationRange | undefined) {
  if (!range) return [0];
  const step = Math.max(Math.abs(range.step), 1);
  const start = Math.min(range.start, range.end);
  const end = Math.max(range.start, range.end);
  const values: number[] = [];
  for (let value = start; value <= end; value += step) {
    values.push(value);
    if (values.length > 50) break;
  }
  return values;
}

function formatParamLabel(key: string) {
  return key.replaceAll("_", " ");
}

function formatParameters(parameters: Record<string, StrategyParameterValue>) {
  return Object.entries(parameters)
    .map(([key, value]) => `${formatParamLabel(key)}=${value ?? "--"}`)
    .join(", ");
}

function defaultNoteBody() {
  return "## Hypothesis\n\n\n## Observations\n\n\n## Conclusion\n";
}

function metricRaw(value: unknown) {
  return typeof value === "number" ? value : null;
}

function metricNumber(value: unknown) {
  const numberValue = metricRaw(value);
  if (numberValue === null) return "--";
  return numberValue.toFixed(2);
}

function metricPercent(value: unknown) {
  const numberValue = metricRaw(value);
  if (numberValue === null) return "--";
  return formatPercent(numberValue);
}

function objectMetric(value: unknown) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return value as Record<string, unknown>;
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
