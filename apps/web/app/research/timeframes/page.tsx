import { TimeframesClient } from "@/components/research/research-ui";
import { PageShell } from "@/components/shell/page-shell";

export default function ResearchTimeframesPage() {
  return (
    <PageShell title="Research Timeframes" description="Create and review canonical intervals for research datasets.">
      <TimeframesClient />
    </PageShell>
  );
}
