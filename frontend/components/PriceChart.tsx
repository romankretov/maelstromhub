"use client";

import ReactECharts from "echarts-for-react";
import type { Candle } from "../lib/api";

export function PriceChart({ candles }: { candles: Candle[] }) {
  const option = {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    grid: [{ left: 50, right: 20, top: 20, height: 220 }, { left: 50, right: 20, top: 270, height: 70 }],
    xAxis: [
      { type: "category", data: candles.map((c) => c.time), axisLabel: { color: "#9ca3af" } },
      { type: "category", data: candles.map((c) => c.time), gridIndex: 1, axisLabel: { show: false } }
    ],
    yAxis: [
      { scale: true, axisLabel: { color: "#9ca3af" }, splitLine: { lineStyle: { color: "#1f2937" } } },
      { gridIndex: 1, axisLabel: { color: "#9ca3af" }, splitLine: { show: false } }
    ],
    series: [
      {
        type: "candlestick",
        data: candles.map((c) => [c.open, c.close, c.low, c.high]),
        itemStyle: { color: "#34d399", color0: "#fb7185", borderColor: "#34d399", borderColor0: "#fb7185" }
      },
      {
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: candles.map((c) => c.volume),
        itemStyle: { color: "#374151" }
      }
    ]
  };
  return <ReactECharts option={option} style={{ height: 370 }} />;
}
