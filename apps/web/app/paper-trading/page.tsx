import { PageShell } from "@/components/shell/page-shell";
import { PaperTradingClient } from "@/components/workflow/paper-trading-client";

export default function PaperTradingPage() {
  return (
    <PageShell
      title="Paper Deploy"
      description="Rehearse Backtested strategies with manual simulated execution before any live trading path exists."
    >
      <PaperTradingClient />
    </PageShell>
  );
}
