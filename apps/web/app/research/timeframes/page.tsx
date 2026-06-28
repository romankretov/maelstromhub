import { TimeframesClient } from "@/components/research/research-ui";
import { PageShell } from "@/components/shell/page-shell";

export default function ResearchTimeframesPage() {
  return (
    <PageShell title="Internal Timeframes" description="Admin-only view of system-supported dataset intervals. Normal dataset creation uses these automatically.">
      <TimeframesClient />
    </PageShell>
  );
}
