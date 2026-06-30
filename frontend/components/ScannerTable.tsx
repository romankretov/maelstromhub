"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { MarketRow } from "../lib/api";
import { fmt, pct } from "../lib/api";

type SortKey = keyof Pick<MarketRow, "coin" | "research_score" | "volume_24h" | "return_24h" | "open_interest" | "funding" | "adx" | "spread_bps">;

export function ScannerTable({ rows }: { rows: MarketRow[] }) {
  const [sort, setSort] = useState<SortKey>("research_score");
  const [direction, setDirection] = useState<"asc" | "desc">("desc");
  const sorted = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => {
      const av = a[sort];
      const bv = b[sort];
      const result = typeof av === "string" ? av.localeCompare(String(bv)) : Number(av) - Number(bv);
      return direction === "asc" ? result : -result;
    });
    return copy;
  }, [rows, sort, direction]);

  function header(label: string, key: SortKey) {
    return (
      <th
        onClick={() => {
          setDirection(sort === key && direction === "desc" ? "asc" : "desc");
          setSort(key);
        }}
      >
        {label}
      </th>
    );
  }

  return (
    <div className="panel table-wrap">
      <table>
        <thead>
          <tr>
            {header("Coin", "coin")}
            {header("Price", "research_score")}
            {header("24h %", "return_24h")}
            {header("Volume", "volume_24h")}
            <th>Vol / 7d</th>
            {header("OI", "open_interest")}
            <th>OI 24h %</th>
            {header("Funding", "funding")}
            <th>Funding z</th>
            <th>RV</th>
            {header("ADX", "adx")}
            <th>RS Rank</th>
            {header("Spread bps", "spread_bps")}
            {header("Research Score", "research_score")}
            <th>Regime</th>
            <th>Flags</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => (
            <tr key={row.coin} className={row.research_score >= 70 ? "strong" : undefined}>
              <td><Link href={`/markets/${row.coin}`}><strong>{row.coin}</strong></Link></td>
              <td>{fmt(row.price, 4)}</td>
              <td className={row.return_24h >= 0 ? "good" : "bad"}>{pct(row.return_24h)}</td>
              <td>{fmt(row.volume_24h, 0)}</td>
              <td>{fmt(row.volume_vs_7d_avg, 2)}x</td>
              <td>{fmt(row.open_interest, 0)}</td>
              <td>{pct(row.oi_change_24h)}</td>
              <td>{pct(row.funding)}</td>
              <td>{fmt(row.funding_zscore, 2)}</td>
              <td>{fmt(row.realized_vol, 3)}</td>
              <td>{fmt(row.adx, 1)}</td>
              <td>{fmt(row.relative_strength_rank, 0)}</td>
              <td>{fmt(row.spread_bps, 2)}</td>
              <td><strong>{fmt(row.research_score, 1)}</strong></td>
              <td><span className="tag">{row.regime_label || "pending"}</span></td>
              <td>{row.top_flags?.slice(0, 2).map((f) => <span className="tag" key={f.id}>{f.message}</span>)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
