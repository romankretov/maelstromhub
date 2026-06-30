const baseUrl = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export type Flag = {
  id: number;
  time: string;
  coin: string;
  flag_type: string;
  severity: string;
  message: string;
};

export type MarketRow = {
  coin: string;
  price: number;
  return_24h: number;
  volume_24h: number;
  volume_vs_7d_avg: number;
  open_interest: number;
  oi_change_1h: number;
  oi_change_4h: number;
  oi_change_24h: number;
  funding: number;
  funding_zscore: number;
  realized_vol: number;
  adx: number;
  relative_strength_rank: number;
  spread_bps: number;
  research_score: number;
  regime_label: string;
  top_flags: Flag[];
};

export type Candle = {
  time: string;
  coin: string;
  interval: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export async function getMarkets(params: Record<string, string | number | undefined> = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  const res = await fetch(`${baseUrl}/api/markets?${search}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load markets");
  return (await res.json()) as { markets: MarketRow[] };
}

export async function getMarket(coin: string) {
  const res = await fetch(`${baseUrl}/api/markets/${coin}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load market");
  return res.json();
}

export async function getCandles(coin: string, interval = "1h") {
  const res = await fetch(`${baseUrl}/api/markets/${coin}/candles?interval=${interval}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load candles");
  return (await res.json()) as { candles: Candle[] };
}

export async function getHealth() {
  const res = await fetch(`${baseUrl}/api/ingestion/status`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load ingestion status");
  return res.json();
}

export async function getFlags() {
  const res = await fetch(`${baseUrl}/api/flags`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load flags");
  return res.json() as Promise<{ flags: Flag[] }>;
}

export function fmt(v: number, digits = 2) {
  if (!Number.isFinite(v)) return "--";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(v);
}

export function pct(v: number) {
  if (!Number.isFinite(v)) return "--";
  return `${v >= 0 ? "+" : ""}${(v * 100).toFixed(2)}%`;
}
