import { FlaskConical } from "lucide-react";

import { EmptyState } from "@/components/shell/empty-state";
import { PageShell } from "@/components/shell/page-shell";
import { strategyStatuses } from "@/lib/product-shell";

export default function StrategyBuilderPage() {
  return (
    <PageShell
      title="Strategy Builder"
      description="Turn validated ideas into explicit strategy definitions, assumptions, and lifecycle status."
    >
      <EmptyState
        icon={FlaskConical}
        title="No strategy definitions yet"
        description="Strategy authoring is a placeholder. The lifecycle is defined, but no execution, signal generation, or order logic exists."
      />
      <section className="rounded-lg border bg-card p-5">
        <h2 className="text-sm font-semibold">Lifecycle statuses</h2>
        <div className="mt-4 flex flex-wrap gap-2">
          {strategyStatuses.map((status) => (
            <span key={status} className="rounded-md border px-3 py-1 text-sm text-muted-foreground">
              {status}
            </span>
          ))}
        </div>
      </section>
    </PageShell>
  );
}
