import { ExperimentsClient } from "@/components/research/research-ui";
import { PageShell } from "@/components/shell/page-shell";

export default function ResearchExperimentsPage() {
  return (
    <PageShell title="Research Experiments" description="Create and review research attempts linked to datasets and feature snapshots.">
      <ExperimentsClient />
    </PageShell>
  );
}
