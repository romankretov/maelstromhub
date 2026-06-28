import { FeaturesClient } from "@/components/research/research-ui";
import { PageShell } from "@/components/shell/page-shell";

export default function ResearchFeaturesPage() {
  return (
    <PageShell title="Feature Snapshots" description="Create and review feature snapshots linked to datasets.">
      <FeaturesClient />
    </PageShell>
  );
}
