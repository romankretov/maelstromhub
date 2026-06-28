import { PageShell } from "@/components/shell/page-shell";
import { BacktestStudioClient } from "@/components/workflow/backtest-studio-client";

export default function BacktestStudioPage() {
  return (
    <PageShell
      title="Backtest Studio"
      description="Replay generated strategy signals against dataset candles and inspect the first performance readout."
    >
      <BacktestStudioClient />
    </PageShell>
  );
}
