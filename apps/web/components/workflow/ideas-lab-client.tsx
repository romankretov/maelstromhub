"use client";

import { FormEvent, useEffect, useState } from "react";
import { Lightbulb, Plus } from "lucide-react";

import { FeedbackState, ErrorState, LoadingState } from "@/components/shell/feedback";
import { Button } from "@/components/ui/button";
import { createIdea, getIdeas, type Idea } from "@/lib/api-client";

export function IdeasLabClient() {
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [title, setTitle] = useState("");
  const [thesis, setThesis] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadIdeas() {
    setLoading(true);
    setError(null);
    try {
      setIdeas(await getIdeas());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load ideas.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadIdeas();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const idea = await createIdea({ title, thesis });
      setIdeas((current) => [idea, ...current]);
      setTitle("");
      setThesis("");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to create idea.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
      <form onSubmit={handleSubmit} className="rounded-lg border bg-card p-5">
        <h2 className="text-base font-semibold">Create idea</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Capture the thesis before strategy rules, backtests, or trading workflows exist.
        </p>
        <label className="mt-5 block text-sm font-medium" htmlFor="idea-title">
          Title
        </label>
        <input
          id="idea-title"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          className="mt-2 h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
          placeholder="Funding rate mean reversion"
          required
        />
        <label className="mt-4 block text-sm font-medium" htmlFor="idea-thesis">
          Thesis
        </label>
        <textarea
          id="idea-thesis"
          value={thesis}
          onChange={(event) => setThesis(event.target.value)}
          className="mt-2 min-h-32 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-ring"
          placeholder="What behavior should be researched, and why might it persist?"
          required
        />
        <Button className="mt-5 w-full gap-2" type="submit" disabled={saving}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          {saving ? "Creating" : "Create idea"}
        </Button>
      </form>

      <section className="space-y-4">
        {error ? <ErrorState message={error} /> : null}
        {loading ? <LoadingState label="Loading ideas" /> : null}
        {!loading && ideas.length === 0 ? (
          <FeedbackState
            icon={Lightbulb}
            title="No ideas yet"
            description="Create the first idea to start the workflow. Strategy drafts can be linked to ideas later in Strategy Builder."
          />
        ) : null}
        {!loading && ideas.length > 0 ? (
          <div className="grid gap-4">
            {ideas.map((idea) => (
              <article key={idea.id} className="rounded-lg border bg-card p-5">
                <div className="flex items-start justify-between gap-4">
                  <h2 className="font-semibold">{idea.title}</h2>
                  <span className="shrink-0 rounded-md border px-2 py-1 text-xs text-muted-foreground">
                    Idea
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">{idea.thesis}</p>
                <p className="mt-4 text-xs text-muted-foreground">{new Date(idea.created_at).toLocaleString()}</p>
              </article>
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}
