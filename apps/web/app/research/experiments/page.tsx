import { FlaskConical } from "lucide-react";

import { EmptyState } from "@/components/shell/empty-state";
import { PageShell } from "@/components/shell/page-shell";

export default function ResearchExperimentsPage() {
  return (
    <PageShell title="Research Experiments" description="Placeholder page for research attempts linked to datasets and feature snapshots.">
      <EmptyState
        icon={FlaskConical}
        title="Experiment CRUD is available in the API"
        description="Experiments capture research attempts. Strategy versions and backtests are intentionally not connected yet."
      />
    </PageShell>
  );
}
