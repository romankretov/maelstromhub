import { PageShell } from "@/components/shell/page-shell";
import { DashboardClient } from "@/components/workflow/dashboard-client";

export default function DashboardPage() {
  return (
    <PageShell
      title="Dashboard"
      description="A guided view of the Maelstromhub research lifecycle from idea capture through monitored deployment readiness."
    >
      <DashboardClient />
    </PageShell>
  );
}
