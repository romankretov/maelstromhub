import { getMarkets } from "../lib/api";
import { ScannerTable } from "../components/ScannerTable";

export default async function MarketScannerPage({
  searchParams
}: {
  searchParams: { regime?: string; min_volume?: string; min_research_score?: string };
}) {
  const data = await getMarkets({
    sort: "research_score",
    direction: "desc",
    min_volume: searchParams.min_volume,
    min_research_score: searchParams.min_research_score ?? 20,
    regime: searchParams.regime,
    limit: 100
  }).catch(() => ({ markets: [] }));
  return (
    <div className="grid">
      <div className="toolbar">
        <div>
          <h1>Market Scanner</h1>
          <p className="muted">Top Hyperliquid perps ranked by explainable research score.</p>
        </div>
        <form>
          <select name="regime" defaultValue={searchParams.regime ?? ""}>
            <option value="">All regimes</option>
            <option value="trend_candidate">trend_candidate</option>
            <option value="momentum_candidate">momentum_candidate</option>
            <option value="mean_reversion_candidate">mean_reversion_candidate</option>
            <option value="squeeze_candidate">squeeze_candidate</option>
            <option value="volatility_breakout_candidate">volatility_breakout_candidate</option>
            <option value="ignore_low_liquidity">ignore_low_liquidity</option>
            <option value="ignore_choppy">ignore_choppy</option>
          </select>
          <input name="min_volume" placeholder="Min volume" defaultValue={searchParams.min_volume ?? ""} />
          <input name="min_research_score" placeholder="Min score" defaultValue={searchParams.min_research_score ?? "20"} />
          <button>Apply</button>
        </form>
      </div>
      <ScannerTable rows={data.markets} />
    </div>
  );
}
