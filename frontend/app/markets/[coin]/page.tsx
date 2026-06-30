import { getCandles, getMarket, fmt, pct } from "../../../lib/api";
import { PriceChart } from "../../../components/PriceChart";

export default async function CoinDetailPage({ params }: { params: { coin: string } }) {
  const coin = params.coin.toUpperCase();
  const [detail, candleData] = await Promise.all([
    getMarket(coin).catch(() => null),
    getCandles(coin, "1h").catch(() => ({ candles: [] }))
  ]);
  const f = detail?.latest_features;
  const s = detail?.latest_snapshot;
  return (
    <div className="grid">
      <div className="toolbar">
        <div>
          <h1>{coin}</h1>
          <p className="muted">{detail?.suggested_research_direction ?? "Waiting for enough market data."}</p>
        </div>
        <div>
          <span className="tag">Score {fmt(f?.research_score ?? 0, 1)}</span>
          <span className="tag">{f?.regime_label ?? "pending"}</span>
        </div>
      </div>

      <section className="panel" style={{ padding: 16 }}>
        <PriceChart candles={candleData.candles} />
      </section>

      <section className="metric-grid">
        <div className="metric"><div className="muted">Price</div><strong>{fmt(s?.mid ?? s?.mark_px ?? 0, 4)}</strong></div>
        <div className="metric"><div className="muted">24h Return</div><strong>{pct(f?.return_24h ?? 0)}</strong></div>
        <div className="metric"><div className="muted">Open Interest 24h</div><strong>{pct(f?.oi_change_24h ?? 0)}</strong></div>
        <div className="metric"><div className="muted">Funding z</div><strong>{fmt(f?.funding_zscore ?? 0, 2)}</strong></div>
        <div className="metric"><div className="muted">Realized Vol</div><strong>{fmt(f?.realized_vol ?? 0, 3)}</strong></div>
        <div className="metric"><div className="muted">ADX</div><strong>{fmt(f?.adx ?? 0, 1)}</strong></div>
        <div className="metric"><div className="muted">Spread bps</div><strong>{fmt(f?.spread_bps ?? 0, 2)}</strong></div>
        <div className="metric"><div className="muted">Liquidity</div><strong>{fmt(f?.liquidity_score ?? 0, 1)}</strong></div>
      </section>

      <section className="panel" style={{ padding: 16 }}>
        <h2>Latest Flags</h2>
        {detail?.recent_flags?.length ? detail.recent_flags.map((flag: any) => <span className="tag" key={flag.id}>{flag.message}</span>) : <p className="muted">No flags yet.</p>}
      </section>

      <section className="panel" style={{ padding: 16 }}>
        <h2>Orderbook / Execution</h2>
        <p className="muted">Execution quality is estimated from spread and liquidity data. L2 enrichment is rate-budget aware and may be stale during cooldowns.</p>
      </section>
    </div>
  );
}
