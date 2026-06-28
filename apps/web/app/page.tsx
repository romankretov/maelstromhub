import { ArrowRight, CircleDot, ShieldCheck } from "lucide-react";

import { PageShell } from "@/components/shell/page-shell";
import { placeholderStrategies, safetyNotes, workflowSteps } from "@/lib/product-shell";

export default function DashboardPage() {
  return (
    <PageShell
      title="Dashboard"
      description="A guided view of the Maelstromhub research lifecycle from idea capture through monitored deployment readiness."
    >
      <section className="grid gap-3 md:grid-cols-6">
        {workflowSteps.map((step, index) => (
          <div key={step} className="rounded-lg border bg-card p-4">
            <div className="flex items-center justify-between gap-3">
              <CircleDot className="h-4 w-4 text-primary" aria-hidden="true" />
              {index < workflowSteps.length - 1 ? (
                <ArrowRight className="hidden h-4 w-4 text-muted-foreground md:block" aria-hidden="true" />
              ) : null}
            </div>
            <p className="mt-4 text-sm font-medium">{step}</p>
          </div>
        ))}
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold">Placeholder strategies</h2>
          <p className="text-sm text-muted-foreground">Static data for product navigation only</p>
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          {placeholderStrategies.map((strategy) => (
            <article key={strategy.name} className="rounded-lg border bg-card p-5 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <h3 className="font-semibold">{strategy.name}</h3>
                <span className="rounded-md border px-2 py-1 text-xs text-muted-foreground">{strategy.status}</span>
              </div>
              <p className="mt-4 text-sm leading-6 text-muted-foreground">{strategy.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {safetyNotes.map((note) => {
          const Icon = note.icon ?? ShieldCheck;

          return (
            <div key={note.label} className="rounded-lg border bg-card p-4">
              <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
              <p className="mt-4 text-sm font-medium">{note.label}</p>
              <p className="mt-1 text-sm text-muted-foreground">{note.value}</p>
            </div>
          );
        })}
      </section>
    </PageShell>
  );
}
