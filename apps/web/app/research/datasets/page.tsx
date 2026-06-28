import { Layers } from "lucide-react";

import { EmptyState } from "@/components/shell/empty-state";
import { PageShell } from "@/components/shell/page-shell";

export default function ResearchDatasetsPage() {
  return (
    <PageShell title="Research Datasets" description="Placeholder page for dataset metadata linked to assets and timeframes.">
      <EmptyState
        icon={Layers}
        title="Dataset CRUD is available in the API"
        description="Datasets are metadata records only. Market data ingestion is not implemented."
      />
    </PageShell>
  );
}
