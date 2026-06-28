import { AssetsClient } from "@/components/research/research-ui";
import { PageShell } from "@/components/shell/page-shell";

export default function ResearchAssetsPage() {
  return (
    <PageShell title="Research Assets" description="Create and review asset metadata used by research datasets.">
      <AssetsClient />
    </PageShell>
  );
}
