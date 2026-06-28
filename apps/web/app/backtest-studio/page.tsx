import { TestTubeDiagonal } from "lucide-react";

import { EmptyState } from "@/components/shell/empty-state";
import { PageShell } from "@/components/shell/page-shell";

export default function BacktestStudioPage() {
  return (
    <PageShell
      title="Backtest Studio"
      description="Prepare a future workspace for deterministic strategy evaluation and comparable research outputs."
    >
      <EmptyState
        icon={TestTubeDiagonal}
        title="Backtesting is not implemented"
        description="This page reserves the workflow step for future backtest runners, assumptions, and result comparison without pretending results exist today."
      />
    </PageShell>
  );
}
