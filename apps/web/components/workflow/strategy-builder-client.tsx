"use client";

import { FormEvent, useEffect, useState } from "react";
import { FlaskConical, Plus } from "lucide-react";

import { ErrorState, FeedbackState, LoadingState } from "@/components/shell/feedback";
import { Button } from "@/components/ui/button";
import { createStrategy, getIdeas, getStrategies, type Idea, type Strategy } from "@/lib/api-client";
import { strategyStatuses } from "@/lib/product-shell";

export function StrategyBuilderClient() {
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [sourceIdeaId, setSourceIdeaId] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [loadedIdeas, loadedStrategies] = await Promise.all([getIdeas(), getStrategies()]);
      setIdeas(loadedIdeas);
      setStrategies(loadedStrategies);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load strategy workspace.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const strategy = await createStrategy({
        name,
        description,
        source_idea_id: sourceIdeaId || null,
      });
      setStrategies((current) => [strategy, ...current]);
      setName("");
      setDescription("");
      setSourceIdeaId("");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to create strategy.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
      <form onSubmit={handleSubmit} className="rounded-lg border bg-card p-5">
        <h2 className="text-base font-semibold">Create draft strategy</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Drafts define intent and assumptions only. No signals, backtests, market data, or execution are wired here.
        </p>
        <label className="mt-5 block text-sm font-medium" htmlFor="strategy-name">
          Name
        </label>
        <input
          id="strategy-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="mt-2 h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
          placeholder="Funding Fade Prototype"
          required
        />
        <label className="mt-4 block text-sm font-medium" htmlFor="source-idea">
          Source idea
        </label>
        <select
          id="source-idea"
          value={sourceIdeaId}
          onChange={(event) => setSourceIdeaId(event.target.value)}
          className="mt-2 h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="">Standalone draft</option>
          {ideas.map((idea) => (
            <option key={idea.id} value={idea.id}>
              {idea.title}
            </option>
          ))}
        </select>
        <label className="mt-4 block text-sm font-medium" htmlFor="strategy-description">
          Description
        </label>
        <textarea
          id="strategy-description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          className="mt-2 min-h-32 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-ring"
          placeholder="What should this strategy eventually test?"
          required
        />
        <Button className="mt-5 w-full gap-2" type="submit" disabled={saving}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          {saving ? "Creating" : "Create draft"}
        </Button>
      </form>

      <section className="space-y-4">
        {error ? <ErrorState message={error} /> : null}
        {loading ? <LoadingState label="Loading strategies" /> : null}
        {!loading && strategies.length === 0 ? (
          <FeedbackState
            icon={FlaskConical}
            title="No strategy drafts yet"
            description="Create a draft strategy from an idea or as a standalone research thread. It will start in Draft status."
          />
        ) : null}
        {!loading && strategies.length > 0 ? (
          <div className="grid gap-4">
            {strategies.map((strategy) => {
              const linkedIdea = ideas.find((idea) => idea.id === strategy.source_idea_id);

              return (
                <article key={strategy.id} className="rounded-lg border bg-card p-5">
                  <div className="flex items-start justify-between gap-4">
                    <h2 className="font-semibold">{strategy.name}</h2>
                    <span className="shrink-0 rounded-md border px-2 py-1 text-xs text-muted-foreground">
                      {strategy.status}
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-muted-foreground">{strategy.description}</p>
                  <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span className="rounded-md border px-2 py-1">
                      {linkedIdea ? `Idea: ${linkedIdea.title}` : "Standalone"}
                    </span>
                    <span className="rounded-md border px-2 py-1">
                      {new Date(strategy.created_at).toLocaleString()}
                    </span>
                  </div>
                </article>
              );
            })}
          </div>
        ) : null}
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
      </section>
    </div>
  );
}
