import Link from "next/link";
import { Database, Settings } from "lucide-react";

import { EmptyState } from "@/components/shell/empty-state";
import { PageShell } from "@/components/shell/page-shell";

export default function SettingsPage() {
  return (
    <PageShell
      title="Settings"
      description="Workspace preferences, integrations, operator controls, and advanced data administration."
    >
      <div className="grid gap-4 md:grid-cols-2">
        <EmptyState
          icon={Settings}
          title="No settings are configurable yet"
          description="Private keys, trading permissions, and production controls are intentionally absent from this scaffold."
        />
        <Link
          href="/settings/advanced-data-admin"
          className="rounded-lg border bg-card p-6 transition-colors hover:bg-muted"
        >
          <Database className="h-5 w-5 text-primary" aria-hidden="true" />
          <h2 className="mt-4 text-lg font-semibold">Advanced Data Admin</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Inspect legacy research and data objects that are hidden from the primary workspace flow.
          </p>
        </Link>
      </div>
    </PageShell>
  );
}
