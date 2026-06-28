import { PageShell } from "@/components/shell/page-shell";
import { IdeasLabClient } from "@/components/workflow/ideas-lab-client";

export default function IdeasLabPage() {
  return (
    <PageShell
      title="Ideas Lab"
      description="Capture hypotheses, research notes, and candidate edges before any implementation work begins."
    >
      <IdeasLabClient />
    </PageShell>
  );
}
