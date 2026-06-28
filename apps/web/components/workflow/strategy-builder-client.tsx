"use client";

import { FormEvent, useEffect, useState } from "react";
import { FlaskConical, Layers3, Play, Plus, RefreshCw } from "lucide-react";

import { ErrorState, FeedbackState, LoadingState } from "@/components/shell/feedback";
import { Button } from "@/components/ui/button";
import {
  createStrategy,
  createStrategyVersion,
  getDatasets,
  getIdeas,
  getStrategies,
  getStrategySignals,
  getStrategyTemplates,
  getStrategyVersions,
  runStrategySignals,
  type Dataset,
  type Idea,
  type Signal,
  type Strategy,
  type StrategyParameterValue,
  type StrategyTemplate,
  type StrategyVersion,
} from "@/lib/api-client";
import { strategyStatuses } from "@/lib/product-shell";

export function StrategyBuilderClient() {
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [templates, setTemplates] = useState<StrategyTemplate[]>([]);
  const [versions, setVersions] = useState<StrategyVersion[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [sourceIdeaId, setSourceIdeaId] = useState("");
  const [selectedStrategyId, setSelectedStrategyId] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [parameters, setParameters] = useState<Record<string, StrategyParameterValue>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [creatingVersion, setCreatingVersion] = useState(false);
  const [runningSignals, setRunningSignals] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedTemplate = templates.find((template) => template.id === selectedTemplateId);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [loadedIdeas, loadedStrategies, loadedDatasets, loadedTemplates] = await Promise.all([
        getIdeas(),
        getStrategies(),
        getDatasets(),
        getStrategyTemplates(),
      ]);
      setIdeas(loadedIdeas);
      setStrategies(loadedStrategies);
      setDatasets(loadedDatasets);
      setTemplates(loadedTemplates);
      setSelectedStrategyId((current) => current || loadedStrategies[0]?.id || "");
      setSelectedTemplateId((current) => current || loadedTemplates[0]?.id || "");
      setSelectedDatasetId((current) => current || loadedDatasets[0]?.id || "");
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load strategy workspace.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  useEffect(() => {
    if (!selectedTemplate) {
      return;
    }
    setParameters(selectedTemplate.default_parameters);
  }, [selectedTemplate]);

  useEffect(() => {
    if (!selectedStrategyId) {
      setVersions([]);
      setSelectedVersionId("");
      return;
    }

    async function loadVersions() {
      try {
        const loadedVersions = await getStrategyVersions(selectedStrategyId);
        setVersions(loadedVersions);
        setSelectedVersionId((current) => current || loadedVersions[0]?.id || "");
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load strategy versions.");
      }
    }

    void loadVersions();
  }, [selectedStrategyId]);

  useEffect(() => {
    if (!selectedVersionId) {
      setSignals([]);
      return;
    }

    async function loadSignals() {
      try {
        setSignals(await getStrategySignals(selectedVersionId));
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load signals.");
      }
    }

    void loadSignals();
  }, [selectedVersionId]);

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
      setSelectedStrategyId(strategy.id);
      setName("");
      setDescription("");
      setSourceIdeaId("");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to create strategy.");
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateVersion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedStrategyId || !selectedTemplateId || !selectedDatasetId) {
      setError("Choose a strategy, template, and dataset before creating a version.");
      return;
    }
    setCreatingVersion(true);
    setError(null);
    try {
      const version = await createStrategyVersion(selectedStrategyId, {
        template_id: selectedTemplateId,
        dataset_id: selectedDatasetId,
        parameters,
      });
      setVersions((current) => [version, ...current]);
      setSelectedVersionId(version.id);
      setSignals([]);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to create strategy version.");
    } finally {
      setCreatingVersion(false);
    }
  }

  async function handleRunSignals() {
    if (!selectedVersionId) {
      setError("Create or select a strategy version before generating signals.");
      return;
    }
    setRunningSignals(true);
    setError(null);
    try {
      await runStrategySignals(selectedVersionId);
      await refreshSignals(selectedVersionId);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Unable to generate signals.");
    } finally {
      setRunningSignals(false);
    }
  }

  async function refreshSignals(versionId = selectedVersionId) {
    if (!versionId) {
      return;
    }
    try {
      setSignals(await getStrategySignals(versionId));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load signals.");
    }
  }

  function updateParameter(key: string, value: string) {
    const type = selectedTemplate?.parameters[key];
    setParameters((current) => ({
      ...current,
      [key]: type === "number" ? Number(value) : value,
    }));
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-6 xl:grid-cols-[360px_1fr]">
        <form onSubmit={handleSubmit} className="rounded-lg border bg-card p-5">
          <h2 className="text-base font-semibold">Create draft strategy</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Start with a research intent, then attach a reusable template and dataset to generate signals.
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
          <form onSubmit={handleCreateVersion} className="rounded-lg border bg-card p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-base font-semibold">Choose template - choose dataset - generate signals</h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  Versions bind one strategy draft to one template configuration and one feature-ready dataset.
                </p>
              </div>
              <Layers3 className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
            </div>
            <div className="mt-5 grid gap-4 md:grid-cols-3">
              <label className="block text-sm font-medium" htmlFor="version-strategy">
                Strategy
                <select
                  id="version-strategy"
                  value={selectedStrategyId}
                  onChange={(event) => {
                    setSelectedStrategyId(event.target.value);
                    setSelectedVersionId("");
                  }}
                  className="mt-2 h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
                  required
                >
                  <option value="">Select strategy</option>
                  {strategies.map((strategy) => (
                    <option key={strategy.id} value={strategy.id}>
                      {strategy.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm font-medium" htmlFor="version-template">
                Template
                <select
                  id="version-template"
                  value={selectedTemplateId}
                  onChange={(event) => setSelectedTemplateId(event.target.value)}
                  className="mt-2 h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
                  required
                >
                  <option value="">Select template</option>
                  {templates.map((template) => (
                    <option key={template.id} value={template.id}>
                      {template.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm font-medium" htmlFor="version-dataset">
                Dataset
                <select
                  id="version-dataset"
                  value={selectedDatasetId}
                  onChange={(event) => setSelectedDatasetId(event.target.value)}
                  className="mt-2 h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
                  required
                >
                  <option value="">Select dataset</option>
                  {datasets.map((dataset) => (
                    <option key={dataset.id} value={dataset.id}>
                      {dataset.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {selectedTemplate ? (
              <div className="mt-5 rounded-md border bg-background p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold">{selectedTemplate.name}</h3>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">{selectedTemplate.description}</p>
                  </div>
                  <span className="rounded-md border px-2 py-1 text-xs text-muted-foreground">
                    Requires {selectedTemplate.required_features.join(", ")}
                  </span>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-4">
                  {Object.entries(selectedTemplate.default_parameters).map(([key]) => (
                    <label key={key} className="block text-sm font-medium" htmlFor={`parameter-${key}`}>
                      {key.replaceAll("_", " ")}
                      <input
                        id={`parameter-${key}`}
                        value={String(parameters[key] ?? "")}
                        onChange={(event) => updateParameter(key, event.target.value)}
                        type={selectedTemplate.parameters[key] === "number" ? "number" : "text"}
                        step="any"
                        className="mt-2 h-10 w-full rounded-md border bg-card px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
                      />
                    </label>
                  ))}
                </div>
              </div>
            ) : null}
            <Button className="mt-5 gap-2" type="submit" disabled={creatingVersion}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              {creatingVersion ? "Creating version" : "Create strategy version"}
            </Button>
          </form>

          <section className="rounded-lg border bg-card p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold">Signals</h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  Run the selected version against its dataset feature snapshots.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <select
                  value={selectedVersionId}
                  onChange={(event) => setSelectedVersionId(event.target.value)}
                  className="h-10 rounded-md border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="">Select version</option>
                  {versions.map((version) => (
                    <option key={version.id} value={version.id}>
                      v{version.version_number} - {version.template_id}
                    </option>
                  ))}
                </select>
                <Button variant="outline" className="gap-2" type="button" onClick={() => void refreshSignals()}>
                  <RefreshCw className="h-4 w-4" aria-hidden="true" />
                  Refresh
                </Button>
                <Button className="gap-2" type="button" onClick={handleRunSignals} disabled={runningSignals}>
                  <Play className="h-4 w-4" aria-hidden="true" />
                  {runningSignals ? "Running" : "Run signals"}
                </Button>
              </div>
            </div>
            {versions.length === 0 ? (
              <FeedbackState
                icon={Layers3}
                title="No strategy versions yet"
                description="Create a version from a template and dataset before generating signals."
              />
            ) : null}
            {versions.length > 0 && signals.length === 0 ? (
              <div className="mt-4 rounded-md border border-dashed p-5 text-sm text-muted-foreground">
                No signals for this version yet. Generate signals after the selected dataset has feature snapshots.
              </div>
            ) : null}
            {signals.length > 0 ? (
              <div className="mt-4 overflow-hidden rounded-md border">
                <table className="w-full text-left text-sm">
                  <thead className="bg-muted/50 text-xs text-muted-foreground">
                    <tr>
                      <th className="px-3 py-2 font-medium">Time</th>
                      <th className="px-3 py-2 font-medium">Side</th>
                      <th className="px-3 py-2 font-medium">Confidence</th>
                      <th className="px-3 py-2 font-medium">Size</th>
                      <th className="px-3 py-2 font-medium">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {signals.slice(0, 12).map((signal) => (
                      <tr key={signal.id} className="border-t">
                        <td className="px-3 py-2 text-muted-foreground">
                          {new Date(signal.timestamp).toLocaleString()}
                        </td>
                        <td className="px-3 py-2">
                          <span className="rounded-md border px-2 py-1 text-xs">{signal.side}</span>
                        </td>
                        <td className="px-3 py-2">{signal.confidence.toFixed(2)}</td>
                        <td className="px-3 py-2">{signal.suggested_size.toFixed(2)}</td>
                        <td className="px-3 py-2 text-muted-foreground">{signal.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </section>
        </section>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1fr_360px]">
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
        </section>
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
