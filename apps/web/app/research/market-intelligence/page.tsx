import { MarketIntelligenceClient } from "@/components/research/research-ui";
import { PageShell } from "@/components/shell/page-shell";

export default function MarketIntelligencePage() {
  return (
    <PageShell
      title="Market Intelligence"
      description="Explainable market context generated from deterministic feature snapshots."
    >
      <MarketIntelligenceClient />
    </PageShell>
  );
}
