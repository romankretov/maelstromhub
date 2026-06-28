import { PageShell } from "@/components/shell/page-shell";
import { ResearchOverviewClient } from "@/components/research/research-ui";

export default function ResearchPage() {
  return (
    <PageShell
      title="Research"
      description="A guided workflow for research metadata: Asset -> Dataset -> Features -> Experiment."
    >
      <ResearchOverviewClient />
    </PageShell>
  );
}
