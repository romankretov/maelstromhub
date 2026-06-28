import { DatasetsClient } from "@/components/research/research-ui";
import { PageShell } from "@/components/shell/page-shell";

export default function ResearchDatasetsPage() {
  return (
    <PageShell title="Research Datasets" description="Create and review dataset metadata linked to assets and timeframes.">
      <DatasetsClient />
    </PageShell>
  );
}
