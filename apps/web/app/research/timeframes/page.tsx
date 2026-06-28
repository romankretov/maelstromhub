import { Timer } from "lucide-react";

import { EmptyState } from "@/components/shell/empty-state";
import { PageShell } from "@/components/shell/page-shell";

export default function ResearchTimeframesPage() {
  return (
    <PageShell title="Research Timeframes" description="Placeholder page for canonical research intervals.">
      <EmptyState
        icon={Timer}
        title="Timeframe CRUD is available in the API"
        description="Use this future page to manage interval metadata before datasets are created."
      />
    </PageShell>
  );
}
