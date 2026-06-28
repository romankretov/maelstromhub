"use client";

import { useEffect, useState } from "react";
import { ArrowRight, CircleDot, History, ShieldCheck } from "lucide-react";

import { ErrorState, FeedbackState, LoadingState } from "@/components/shell/feedback";
import { getAuditEvents, getStrategies, type AuditEvent, type Strategy } from "@/lib/api-client";
import { safetyNotes, workflowSteps } from "@/lib/product-shell";

export function DashboardClient() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDashboard() {
      setLoading(true);
      setError(null);
      try {
        const [loadedStrategies, loadedAuditEvents] = await Promise.all([getStrategies(), getAuditEvents()]);
        setStrategies(loadedStrategies);
        setAuditEvents(loadedAuditEvents.slice(0, 5));
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load dashboard.");
      } finally {
        setLoading(false);
      }
    }

    void loadDashboard();
  }, []);

  return (
    <>
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

      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState label="Loading dashboard" /> : null}

      {!loading ? (
        <section>
          <div className="mb-3 flex items-center justify-between gap-4">
            <h2 className="text-lg font-semibold">Strategies</h2>
            <p className="text-sm text-muted-foreground">Loaded from the API</p>
          </div>
          {strategies.length === 0 ? (
            <FeedbackState
              icon={ShieldCheck}
              title="No strategies yet"
              description="Create a draft strategy in Strategy Builder after capturing an idea or as a standalone research thread."
            />
          ) : (
            <div className="grid gap-4 lg:grid-cols-3">
              {strategies.map((strategy) => (
                <article key={strategy.id} className="rounded-lg border bg-card p-5 shadow-sm">
                  <div className="flex items-start justify-between gap-4">
                    <h3 className="font-semibold">{strategy.name}</h3>
                    <span className="rounded-md border px-2 py-1 text-xs text-muted-foreground">
                      {strategy.status}
                    </span>
                  </div>
                  <p className="mt-4 text-sm leading-6 text-muted-foreground">{strategy.description}</p>
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}

      {!loading ? (
        <section className="grid gap-4 lg:grid-cols-[1fr_360px]">
          <div className="rounded-lg border bg-card p-5">
            <div className="flex items-center gap-2">
              <History className="h-4 w-4 text-primary" aria-hidden="true" />
              <h2 className="text-sm font-semibold">Recent audit events</h2>
            </div>
            {auditEvents.length === 0 ? (
              <p className="mt-4 text-sm text-muted-foreground">No audit events recorded yet.</p>
            ) : (
              <div className="mt-4 divide-y">
                {auditEvents.map((event) => (
                  <div key={event.id} className="py-3 text-sm">
                    <p className="font-medium">{event.action.replaceAll("_", " ")}</p>
                    <p className="mt-1 text-muted-foreground">
                      {event.actor} on {event.subject}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="grid gap-4">
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
          </div>
        </section>
      ) : null}
    </>
  );
}
