import { MonitorCog } from "lucide-react";

import { EmptyState } from "@/components/shell/empty-state";
import { PageShell } from "@/components/shell/page-shell";

export default function MonitorPage() {
  return (
    <PageShell
      title="Monitor"
      description="A future operations surface for strategy state, health checks, audit events, and incident review."
    >
      <EmptyState
        icon={MonitorCog}
        title="No monitored systems"
        description="Monitoring is limited to the product shell. Metrics, traces, alerts, and live strategy telemetry are not connected."
      />
    </PageShell>
  );
}
