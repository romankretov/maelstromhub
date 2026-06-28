import { Rocket } from "lucide-react";

import { EmptyState } from "@/components/shell/empty-state";
import { PageShell } from "@/components/shell/page-shell";

export default function DeploymentCenterPage() {
  return (
    <PageShell
      title="Deployment Center"
      description="A future operational checkpoint for approvals, risk limits, and release readiness."
    >
      <EmptyState
        icon={Rocket}
        title="Deployment controls are blocked"
        description="No live trading, key management, or production deployment automation exists. This page is a placeholder for safety-first design."
      />
    </PageShell>
  );
}
