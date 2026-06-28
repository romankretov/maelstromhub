"use client";

import type { FormEvent, ReactNode } from "react";
import { useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  Bot,
  Braces,
  Clock3,
  LineChart,
  ListFilter,
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
import { cn } from "@/lib/utils";

const markets = ["BTC", "ETH", "SOL", "HYPE", "Manual"] as const;
const timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"] as const;
const ranges = ["7d", "30d", "90d", "180d", "1y"] as const;
const tabs = ["Strategy", "Backtests", "Optimisation", "Notes", "Logs"] as const;

const watchlist = [
  { symbol: "BTC", price: "104,280.5", change: "+2.14%", state: "Bull Trend" },
  { symbol: "ETH", price: "3,742.8", change: "+1.02%", state: "Normal Vol" },
  { symbol: "SOL", price: "181.2", change: "-0.44%", state: "Range" },
  { symbol: "HYPE", price: "42.6", change: "+4.85%", state: "High Vol" },
];

const metrics = [
  { label: "Return 30d", value: "+11.8%", tone: "text-emerald-300" },
  { label: "Volatility", value: "Normal", tone: "text-sky-300" },
  { label: "Drawdown", value: "-6.2%", tone: "text-amber-300" },
  { label: "Data", value: "Placeholder", tone: "text-zinc-300" },
];

const candles = [
  { x: 18, open: 95, high: 83, low: 132, close: 106, up: true },
  { x: 40, open: 108, high: 88, low: 139, close: 121, up: true },
  { x: 62, open: 120, high: 94, low: 145, close: 116, up: false },
  { x: 84, open: 114, high: 78, low: 130, close: 91, up: false },
  { x: 106, open: 93, high: 70, low: 122, close: 82, up: false },
  { x: 128, open: 84, high: 63, low: 118, close: 101, up: true },
  { x: 150, open: 103, high: 59, low: 116, close: 74, up: false },
  { x: 172, open: 76, high: 48, low: 105, close: 61, up: false },
  { x: 194, open: 63, high: 40, low: 92, close: 54, up: false },
  { x: 216, open: 56, high: 38, low: 91, close: 78, up: true },
  { x: 238, open: 80, high: 45, low: 104, close: 68, up: false },
  { x: 260, open: 70, high: 42, low: 98, close: 52, up: false },
  { x: 282, open: 54, high: 33, low: 88, close: 46, up: false },
  { x: 304, open: 48, high: 31, low: 84, close: 67, up: true },
  { x: 326, open: 69, high: 36, low: 91, close: 58, up: false },
  { x: 348, open: 60, high: 29, low: 82, close: 41, up: false },
  { x: 370, open: 43, high: 23, low: 71, close: 35, up: false },
  { x: 392, open: 37, high: 18, low: 66, close: 31, up: false },
  { x: 414, open: 33, high: 16, low: 63, close: 51, up: true },
  { x: 436, open: 53, high: 21, low: 69, close: 39, up: false },
  { x: 458, open: 41, high: 19, low: 74, close: 62, up: true },
  { x: 480, open: 64, high: 27, low: 80, close: 36, up: false },
  { x: 502, open: 38, high: 18, low: 70, close: 57, up: true },
  { x: 524, open: 59, high: 24, low: 75, close: 32, up: false },
  { x: 546, open: 34, high: 13, low: 61, close: 23, up: false },
  { x: 568, open: 25, high: 10, low: 55, close: 44, up: true },
];

type Market = (typeof markets)[number];
type Timeframe = (typeof timeframes)[number];
type Range = (typeof ranges)[number];
type Tab = (typeof tabs)[number];

export function WorkspaceShell() {
  const [market, setMarket] = useState<Market>("BTC");
  const [manualMarket, setManualMarket] = useState("");
  const [timeframe, setTimeframe] = useState<Timeframe>("1h");
  const [range, setRange] = useState<Range>("30d");
  const [activeTab, setActiveTab] = useState<Tab>("Strategy");
  const [refreshCount, setRefreshCount] = useState(0);

  const displayMarket = useMemo(() => {
    if (market !== "Manual") return market;
    return manualMarket.trim().toUpperCase() || "CUSTOM";
  }, [manualMarket, market]);

  function handleRefresh(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRefreshCount((current) => current + 1);
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
              onChange={(event) => setMarket(event.target.value as Market)}
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
                onChange={(event) => setManualMarket(event.target.value)}
                placeholder="Enter symbol"
                className="w-full bg-transparent text-sm font-medium uppercase text-zinc-100 outline-none placeholder:text-zinc-600"
              />
            </label>
          ) : null}

          <SegmentedControl
            label="Timeframe"
            value={timeframe}
            options={timeframes}
            onChange={(value) => setTimeframe(value as Timeframe)}
          />
          <SegmentedControl label="Range" value={range} options={ranges} onChange={(value) => setRange(value as Range)} />

          <Button
            type="submit"
            className="ml-auto h-10 gap-2 border border-emerald-500/30 bg-emerald-500/10 text-emerald-200 shadow-none hover:bg-emerald-500/20"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Refresh Data
          </Button>
        </div>
      </form>

      <div className="grid min-h-[calc(100vh-65px)] grid-cols-1 grid-rows-[auto_1fr_auto] xl:grid-cols-[220px_minmax(0,1fr)_320px] xl:grid-rows-[1fr_auto]">
        <aside className="border-b border-zinc-800 bg-[#080a0e] p-3 xl:border-b-0 xl:border-r">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase text-zinc-500">Watchlist</p>
            <ListFilter className="h-4 w-4 text-zinc-500" aria-hidden="true" />
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-1">
            {watchlist.map((item) => (
              <button
                key={item.symbol}
                type="button"
                onClick={() => setMarket(item.symbol as Exclude<Market, "Manual">)}
                className={cn(
                  "rounded-md border p-3 text-left transition-colors",
                  displayMarket === item.symbol
                    ? "border-emerald-400/50 bg-emerald-400/10"
                    : "border-zinc-800 bg-[#0d1017] hover:border-zinc-700",
                )}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium text-zinc-100">{item.symbol}</span>
                  <span className={cn("text-xs", item.change.startsWith("+") ? "text-emerald-300" : "text-red-300")}>
                    {item.change}
                  </span>
                </div>
                <p className="mt-2 text-sm text-zinc-300">{item.price}</p>
                <p className="mt-1 text-xs text-zinc-500">{item.state}</p>
              </button>
            ))}
          </div>

          <div className="mt-4 rounded-md border border-zinc-800 bg-black p-3">
            <p className="text-xs font-medium uppercase text-zinc-500">Pipeline</p>
            <ol className="mt-3 space-y-2 text-xs text-zinc-400">
              {["Market", "Candles", "Stats", "Strategy", "Backtest", "Deploy"].map((step, index) => (
                <li key={step} className="flex items-center gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded border border-zinc-700 text-[10px] text-zinc-300">
                    {index + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          </div>
        </aside>

        <main className="min-w-0 bg-[#050608]">
          <section className="border-b border-zinc-800 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase text-zinc-500">Market / Chart</p>
                <h1 className="mt-1 text-xl font-semibold tracking-normal text-zinc-50">
                  {displayMarket} / USD Perpetual
                </h1>
                <p className="mt-1 text-sm text-zinc-500">
                  Placeholder workspace state - {timeframe} candles over {range}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {metrics.map((metric) => (
                  <div key={metric.label} className="min-w-28 rounded-md border border-zinc-800 bg-[#0d1017] px-3 py-2">
                    <p className="text-[11px] uppercase text-zinc-500">{metric.label}</p>
                    <p className={cn("mt-1 text-sm font-medium", metric.tone)}>{metric.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="p-4">
            <div className="relative min-h-[360px] overflow-hidden rounded-md border border-zinc-800 bg-black md:min-h-[440px]">
              <div className="absolute inset-x-0 top-0 flex items-center justify-between border-b border-zinc-900 bg-[#07090d]/95 px-4 py-3">
                <div className="flex items-center gap-2 text-sm text-zinc-300">
                  <LineChart className="h-4 w-4 text-emerald-300" aria-hidden="true" />
                  Candle view
                </div>
                <div className="flex items-center gap-2 text-xs text-zinc-500">
                  <Clock3 className="h-4 w-4" aria-hidden="true" />
                  Refreshes: {refreshCount}
                </div>
              </div>
              <PlaceholderChart />
            </div>
          </section>
        </main>

        <aside className="border-t border-zinc-800 bg-[#080a0e] p-4 xl:border-l xl:border-t-0">
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-sky-300" aria-hidden="true" />
            <p className="text-sm font-medium">Assistant / Intelligence</p>
          </div>

          <div className="mt-4 space-y-3">
            <IntelligenceBlock
              icon={TrendingUp}
              title="Current Market"
              value="Bull Trend"
              detail="Trend and volatility are placeholder values until workspace orchestration is added."
              tone="emerald"
            />
            <IntelligenceBlock
              icon={ShieldCheck}
              title="Strategy Gate"
              value="Not evaluated"
              detail="Run a backtest from the workspace to see promotion readiness."
              tone="amber"
            />
            <IntelligenceBlock
              icon={Activity}
              title="Next Action"
              value="Refresh Data"
              detail="This ticket uses placeholder data only. Backend orchestration remains intentionally absent."
              tone="sky"
            />
          </div>
        </aside>

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
          <BottomPanel activeTab={activeTab} market={displayMarket} timeframe={timeframe} />
        </section>
      </div>
    </div>
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

function PlaceholderChart() {
  return (
    <svg viewBox="0 0 600 300" className="h-[360px] w-full md:h-[440px]" role="img" aria-label="Placeholder candlestick chart">
      <defs>
        <pattern id="workspace-grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#18181b" strokeWidth="0.8" />
        </pattern>
      </defs>
      <rect width="600" height="300" fill="#020304" />
      <rect width="600" height="300" fill="url(#workspace-grid)" />
      <path d="M18 122 L84 96 L150 83 L216 92 L282 70 L348 58 L414 62 L480 50 L568 36" fill="none" stroke="#10b981" strokeWidth="1.5" opacity="0.5" />
      <path d="M18 146 L84 132 L150 119 L216 128 L282 107 L348 98 L414 102 L480 90 L568 84" fill="none" stroke="#38bdf8" strokeWidth="1.2" opacity="0.45" />
      {candles.map((candle) => (
        <g key={candle.x}>
          <line
            x1={candle.x}
            x2={candle.x}
            y1={candle.high}
            y2={candle.low}
            stroke={candle.up ? "#34d399" : "#fb7185"}
            strokeWidth="1.5"
          />
          <rect
            x={candle.x - 4}
            y={Math.min(candle.open, candle.close)}
            width="8"
            height={Math.max(4, Math.abs(candle.open - candle.close))}
            fill={candle.up ? "#34d399" : "#fb7185"}
            opacity="0.9"
            rx="1"
          />
        </g>
      ))}
      <g opacity="0.45">
        {[120, 150, 182, 210, 238, 265].map((y, index) => (
          <rect key={y} x={18 + index * 92} y={y} width="34" height={280 - y} fill="#71717a" />
        ))}
      </g>
      <text x="20" y="286" fill="#71717a" fontSize="10">
        Placeholder data - backend orchestration not connected
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
  tone: "emerald" | "amber" | "sky";
}) {
  const toneClass = {
    emerald: "text-emerald-300 border-emerald-400/20 bg-emerald-400/5",
    amber: "text-amber-300 border-amber-400/20 bg-amber-400/5",
    sky: "text-sky-300 border-sky-400/20 bg-sky-400/5",
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

function BottomPanel({ activeTab, market, timeframe }: { activeTab: Tab; market: string; timeframe: Timeframe }) {
  if (activeTab === "Strategy") {
    return (
      <PanelGrid>
        <PanelItem icon={Braces} label="Template" value="SMA Crossover" />
        <PanelItem icon={Settings2} label="Parameters" value="Fast 20 / Slow 50" />
        <PanelItem icon={ShieldCheck} label="Allowed Regimes" value="Bull Trend, Range" />
        <PanelItem icon={Play} label="Ready State" value={`Configure ${market} ${timeframe}`} />
      </PanelGrid>
    );
  }

  if (activeTab === "Backtests") {
    return (
      <PanelGrid>
        <PanelItem icon={BarChart3} label="Latest Verdict" value="No run yet" />
        <PanelItem icon={TrendingUp} label="Total Return" value="--" />
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
        <PanelItem icon={Play} label="Action" value="Orchestration pending" />
      </PanelGrid>
    );
  }

  if (activeTab === "Notes") {
    return (
      <div className="p-4">
        <div className="rounded-md border border-zinc-800 bg-black p-4 text-sm leading-6 text-zinc-400">
          Notes will capture research observations for the active workspace. This shell intentionally uses placeholder
          data only.
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="font-mono text-xs leading-6 text-zinc-400">
        <p>[workspace] selected market={market}</p>
        <p>[workspace] selected timeframe={timeframe}</p>
        <p>[workspace] backend orchestration disabled for UX-1</p>
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
