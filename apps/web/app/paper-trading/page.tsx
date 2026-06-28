import { Activity } from "lucide-react";

import { EmptyState } from "@/components/shell/empty-state";
import { PageShell } from "@/components/shell/page-shell";

export default function PaperTradingPage() {
  return (
    <PageShell
      title="Paper Trading"
      description="Track future simulated execution only after a strategy has passed research and backtesting checks."
    >
      <EmptyState
        icon={Activity}
        title="No paper trading sessions"
        description="Paper trading is represented as a lifecycle stage only. Simulated fills, balances, and PnL are not implemented yet."
      />
    </PageShell>
  );
}
