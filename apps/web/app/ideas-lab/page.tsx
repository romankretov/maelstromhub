import { Lightbulb } from "lucide-react";

import { EmptyState } from "@/components/shell/empty-state";
import { PageShell } from "@/components/shell/page-shell";

export default function IdeasLabPage() {
  return (
    <PageShell
      title="Ideas Lab"
      description="Capture hypotheses, research notes, and candidate edges before any implementation work begins."
    >
      <EmptyState
        icon={Lightbulb}
        title="No ideas have been promoted yet"
        description="Use this space for structured hypotheses, assumptions, and review notes. Market data ingestion is intentionally not wired in this shell."
      />
    </PageShell>
  );
}
