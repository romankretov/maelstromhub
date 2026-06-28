import { Settings } from "lucide-react";

import { EmptyState } from "@/components/shell/empty-state";
import { PageShell } from "@/components/shell/page-shell";

export default function SettingsPage() {
  return (
    <PageShell
      title="Settings"
      description="A future home for workspace preferences, integrations, and operator controls."
    >
      <EmptyState
        icon={Settings}
        title="No settings are configurable yet"
        description="Private keys, trading permissions, and production controls are intentionally absent from this scaffold."
      />
    </PageShell>
  );
}
