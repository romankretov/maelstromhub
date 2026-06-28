import { Database } from "lucide-react";

import { EmptyState } from "@/components/shell/empty-state";
import { PageShell } from "@/components/shell/page-shell";

export default function ResearchAssetsPage() {
  return (
    <PageShell title="Research Assets" description="Placeholder page for asset metadata used by research datasets.">
      <EmptyState
        icon={Database}
        title="Asset CRUD is available in the API"
        description="The frontend management table is intentionally deferred. No Hyperliquid or market data ingestion is connected."
      />
    </PageShell>
  );
}
