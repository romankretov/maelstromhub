"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { ArrowRight, Database, FlaskConical, Layers, Microscope, Plus, Timer } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { ErrorState, FeedbackState, LoadingState } from "@/components/shell/feedback";
import { Button } from "@/components/ui/button";
import {
  createAsset,
  createDataset,
  createExperiment,
  createFeature,
  createTimeframe,
  getAssets,
  getDatasets,
  getExperiments,
  getFeatures,
  getTimeframes,
  type Asset,
  type Dataset,
  type Experiment,
  type Feature,
  type Timeframe,
} from "@/lib/api-client";

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function descriptionValue(value: string | null) {
  return value?.trim() ? value : "No description";
}

export function ResearchOverviewClient() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [features, setFeatures] = useState<Feature[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadResearch() {
      setLoading(true);
      setError(null);
      try {
        const [loadedAssets, loadedDatasets, loadedFeatures, loadedExperiments] = await Promise.all([
          getAssets(),
          getDatasets(),
          getFeatures(),
          getExperiments(),
        ]);
        setAssets(loadedAssets);
        setDatasets(loadedDatasets);
        setFeatures(loadedFeatures);
        setExperiments(loadedExperiments);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load research workspace.");
      } finally {
        setLoading(false);
      }
    }

    void loadResearch();
  }, []);

  const nextAction = useMemo(() => {
    if (assets.length === 0) return { href: "/research/assets", label: "Create an asset", detail: "Start with a symbol and venue." };
    if (datasets.length === 0) return { href: "/research/datasets", label: "Create a dataset", detail: "Link an asset to a timeframe." };
    if (features.length === 0) return { href: "/research/features", label: "Create a feature snapshot", detail: "Attach research values to a dataset." };
    if (experiments.length === 0) return { href: "/research/experiments", label: "Create an experiment", detail: "Record the first research attempt." };
    return { href: "/research/experiments", label: "Review experiments", detail: "Continue refining research attempts." };
  }, [assets.length, datasets.length, experiments.length, features.length]);

  if (loading) return <LoadingState label="Loading research overview" />;
  if (error) return <ErrorState message={error} />;

  const stats = [
    { label: "Assets", value: assets.length, href: "/research/assets", icon: Database },
    { label: "Datasets", value: datasets.length, href: "/research/datasets", icon: Layers },
    { label: "Features", value: features.length, href: "/research/features", icon: Microscope },
    { label: "Experiments", value: experiments.length, href: "/research/experiments", icon: FlaskConical },
  ];

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-4">
        {stats.map((stat) => (
          <Link key={stat.label} href={stat.href} className="rounded-lg border bg-card p-5 transition-colors hover:bg-muted">
            <stat.icon className="h-5 w-5 text-primary" aria-hidden="true" />
            <p className="mt-4 text-2xl font-semibold">{stat.value}</p>
            <p className="mt-1 text-sm text-muted-foreground">{stat.label}</p>
          </Link>
        ))}
      </section>

      <Link href={nextAction.href} className="flex items-center justify-between gap-4 rounded-lg border bg-card p-5 transition-colors hover:bg-muted">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Next best action</p>
          <h2 className="mt-2 text-lg font-semibold">{nextAction.label}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{nextAction.detail}</p>
        </div>
        <ArrowRight className="h-5 w-5 text-primary" aria-hidden="true" />
      </Link>

      <section className="grid gap-3 md:grid-cols-4">
        {["Asset", "Dataset", "Features", "Experiment"].map((step, index) => (
          <div key={step} className="rounded-lg border bg-card p-4">
            <p className="text-xs text-muted-foreground">Step {index + 1}</p>
            <p className="mt-2 text-sm font-medium">{step}</p>
          </div>
        ))}
      </section>
    </div>
  );
}

export function AssetsClient() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [symbol, setSymbol] = useState("");
  const [venue, setVenue] = useState("hyperliquid");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadAssets() {
      setLoading(true);
      setError(null);
      try {
        setAssets(await getAssets());
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load assets.");
      } finally {
        setLoading(false);
      }
    }

    void loadAssets();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const asset = await createAsset({ symbol, venue, description: description || null });
      setAssets((current) => [asset, ...current]);
      setSymbol("");
      setVenue("hyperliquid");
      setDescription("");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to create asset.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <ResearchFormLayout
      form={
        <form onSubmit={handleSubmit} className="rounded-lg border bg-card p-5">
          <FormTitle title="Create asset" description="Start research with a venue and symbol. No market data is connected." />
          <TextInput label="Symbol" value={symbol} onChange={setSymbol} placeholder="BTC" required />
          <TextInput label="Venue" value={venue} onChange={setVenue} placeholder="hyperliquid" required />
          <TextArea label="Description" value={description} onChange={setDescription} placeholder="Research metadata only" />
          <SubmitButton saving={saving} label="Create asset" />
        </form>
      }
      content={
        <ListSection loading={loading} error={error} emptyIcon={Database} emptyTitle="No assets yet" emptyDescription="Create the first asset before datasets can be defined.">
          {assets.map((asset) => (
            <RecordCard key={asset.id} title={`${asset.symbol} / ${asset.venue}`} badge="Asset" description={descriptionValue(asset.description)} createdAt={asset.created_at} />
          ))}
        </ListSection>
      }
    />
  );
}

export function TimeframesClient() {
  const [timeframes, setTimeframes] = useState<Timeframe[]>([]);
  const [name, setName] = useState("");
  const [interval, setInterval] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadTimeframes() {
      setLoading(true);
      setError(null);
      try {
        setTimeframes(await getTimeframes());
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load timeframes.");
      } finally {
        setLoading(false);
      }
    }

    void loadTimeframes();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const timeframe = await createTimeframe({ name, interval, description: description || null });
      setTimeframes((current) => [timeframe, ...current]);
      setName("");
      setInterval("");
      setDescription("");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to create timeframe.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <ResearchFormLayout
      form={
        <form onSubmit={handleSubmit} className="rounded-lg border bg-card p-5">
          <FormTitle title="Create timeframe" description="Define a canonical interval for dataset metadata." />
          <TextInput label="Name" value={name} onChange={setName} placeholder="One hour" required />
          <TextInput label="Interval" value={interval} onChange={setInterval} placeholder="1h" required />
          <TextArea label="Description" value={description} onChange={setDescription} placeholder="Optional notes" />
          <SubmitButton saving={saving} label="Create timeframe" />
        </form>
      }
      content={
        <ListSection loading={loading} error={error} emptyIcon={Timer} emptyTitle="No timeframes yet" emptyDescription="Create a timeframe before building datasets.">
          {timeframes.map((timeframe) => (
            <RecordCard key={timeframe.id} title={timeframe.name} badge={timeframe.interval} description={descriptionValue(timeframe.description)} createdAt={timeframe.created_at} />
          ))}
        </ListSection>
      }
    />
  );
}

export function DatasetsClient() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [timeframes, setTimeframes] = useState<Timeframe[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [assetId, setAssetId] = useState("");
  const [timeframeId, setTimeframeId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDatasets() {
      setLoading(true);
      setError(null);
      try {
        const [loadedAssets, loadedTimeframes, loadedDatasets] = await Promise.all([getAssets(), getTimeframes(), getDatasets()]);
        setAssets(loadedAssets);
        setTimeframes(loadedTimeframes);
        setDatasets(loadedDatasets);
        setAssetId(loadedAssets[0]?.id ?? "");
        setTimeframeId(loadedTimeframes[0]?.id ?? "");
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load datasets.");
      } finally {
        setLoading(false);
      }
    }

    void loadDatasets();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const dataset = await createDataset({ asset_id: assetId, timeframe_id: timeframeId, name, description: description || null });
      setDatasets((current) => [dataset, ...current]);
      setName("");
      setDescription("");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to create dataset.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <ResearchFormLayout
      form={
        <form onSubmit={handleSubmit} className="rounded-lg border bg-card p-5">
          <FormTitle title="Create dataset" description="Link an asset and timeframe. This stores metadata only." />
          <SelectInput label="Asset" value={assetId} onChange={setAssetId} options={assets.map((asset) => ({ value: asset.id, label: `${asset.symbol} / ${asset.venue}` }))} required />
          <SelectInput label="Timeframe" value={timeframeId} onChange={setTimeframeId} options={timeframes.map((timeframe) => ({ value: timeframe.id, label: `${timeframe.name} (${timeframe.interval})` }))} required />
          <TextInput label="Name" value={name} onChange={setName} placeholder="BTC 1h research dataset" required />
          <TextArea label="Description" value={description} onChange={setDescription} placeholder="Dataset scope and assumptions" />
          <SubmitButton saving={saving} label="Create dataset" disabled={!assetId || !timeframeId} />
        </form>
      }
      content={
        <ListSection loading={loading} error={error} emptyIcon={Layers} emptyTitle="No datasets yet" emptyDescription="Create assets and timeframes first, then define a dataset.">
          {datasets.map((dataset) => (
            <RecordCard key={dataset.id} title={dataset.name} badge="Dataset" description={descriptionValue(dataset.description)} createdAt={dataset.created_at} meta={datasetMeta(dataset, assets, timeframes)} />
          ))}
        </ListSection>
      }
    />
  );
}

export function FeaturesClient() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [features, setFeatures] = useState<Feature[]>([]);
  const [datasetId, setDatasetId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadFeatures() {
      setLoading(true);
      setError(null);
      try {
        const [loadedDatasets, loadedFeatures] = await Promise.all([getDatasets(), getFeatures()]);
        setDatasets(loadedDatasets);
        setFeatures(loadedFeatures);
        setDatasetId(loadedDatasets[0]?.id ?? "");
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load features.");
      } finally {
        setLoading(false);
      }
    }

    void loadFeatures();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const feature = await createFeature({ dataset_id: datasetId, name, description: description || null, values: {} });
      setFeatures((current) => [feature, ...current]);
      setName("");
      setDescription("");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to create feature.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <ResearchFormLayout
      form={
        <form onSubmit={handleSubmit} className="rounded-lg border bg-card p-5">
          <FormTitle title="Create feature snapshot" description="Attach a named feature snapshot to a dataset. Feature pipelines are not implemented." />
          <SelectInput label="Dataset" value={datasetId} onChange={setDatasetId} options={datasets.map((dataset) => ({ value: dataset.id, label: dataset.name }))} required />
          <TextInput label="Name" value={name} onChange={setName} placeholder="Volatility snapshot" required />
          <TextArea label="Description" value={description} onChange={setDescription} placeholder="Feature notes and assumptions" />
          <SubmitButton saving={saving} label="Create feature" disabled={!datasetId} />
        </form>
      }
      content={
        <ListSection loading={loading} error={error} emptyIcon={Microscope} emptyTitle="No feature snapshots yet" emptyDescription="Create a dataset first, then add a feature snapshot.">
          {features.map((feature) => (
            <RecordCard key={feature.id} title={feature.name} badge="Feature" description={descriptionValue(feature.description)} createdAt={feature.created_at} meta={datasetName(feature.dataset_id, datasets)} />
          ))}
        </ListSection>
      }
    />
  );
}

export function ExperimentsClient() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [features, setFeatures] = useState<Feature[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [datasetId, setDatasetId] = useState("");
  const [featureId, setFeatureId] = useState("");
  const [name, setName] = useState("");
  const [hypothesis, setHypothesis] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadExperiments() {
      setLoading(true);
      setError(null);
      try {
        const [loadedDatasets, loadedFeatures, loadedExperiments] = await Promise.all([getDatasets(), getFeatures(), getExperiments()]);
        setDatasets(loadedDatasets);
        setFeatures(loadedFeatures);
        setExperiments(loadedExperiments);
        setDatasetId(loadedDatasets[0]?.id ?? "");
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load experiments.");
      } finally {
        setLoading(false);
      }
    }

    void loadExperiments();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const experiment = await createExperiment({
        dataset_id: datasetId,
        feature_id: featureId || null,
        name,
        hypothesis,
        notes: notes || null,
        metrics: {},
      });
      setExperiments((current) => [experiment, ...current]);
      setFeatureId("");
      setName("");
      setHypothesis("");
      setNotes("");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to create experiment.");
    } finally {
      setSaving(false);
    }
  }

  const featureOptions = features.filter((feature) => !datasetId || feature.dataset_id === datasetId);

  return (
    <ResearchFormLayout
      form={
        <form onSubmit={handleSubmit} className="rounded-lg border bg-card p-5">
          <FormTitle title="Create experiment" description="Record a research attempt. Strategy versions and backtests are not connected yet." />
          <SelectInput label="Dataset" value={datasetId} onChange={setDatasetId} options={datasets.map((dataset) => ({ value: dataset.id, label: dataset.name }))} required />
          <SelectInput label="Feature snapshot" value={featureId} onChange={setFeatureId} options={featureOptions.map((feature) => ({ value: feature.id, label: feature.name }))} placeholder="No feature linked" />
          <TextInput label="Name" value={name} onChange={setName} placeholder="Funding volatility study" required />
          <TextArea label="Hypothesis" value={hypothesis} onChange={setHypothesis} placeholder="What are you trying to learn?" required />
          <TextArea label="Notes" value={notes} onChange={setNotes} placeholder="Optional research notes" />
          <SubmitButton saving={saving} label="Create experiment" disabled={!datasetId} />
        </form>
      }
      content={
        <ListSection loading={loading} error={error} emptyIcon={FlaskConical} emptyTitle="No experiments yet" emptyDescription="Create a dataset, optionally add features, then record an experiment.">
          {experiments.map((experiment) => (
            <RecordCard key={experiment.id} title={experiment.name} badge={experiment.status} description={experiment.hypothesis} createdAt={experiment.created_at} meta={datasetName(experiment.dataset_id, datasets)} />
          ))}
        </ListSection>
      }
    />
  );
}

function ResearchFormLayout({ form, content }: { form: ReactNode; content: ReactNode }) {
  return <div className="grid gap-6 lg:grid-cols-[380px_1fr]">{form}<section className="space-y-4">{content}</section></div>;
}

function FormTitle({ title, description }: { title: string; description: string }) {
  return (
    <>
      <h2 className="text-base font-semibold">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
    </>
  );
}

function TextInput({ label, value, onChange, placeholder, required }: { label: string; value: string; onChange: (value: string) => void; placeholder: string; required?: boolean }) {
  return (
    <>
      <label className="mt-5 block text-sm font-medium">{label}</label>
      <input value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring" placeholder={placeholder} required={required} />
    </>
  );
}

function TextArea({ label, value, onChange, placeholder, required }: { label: string; value: string; onChange: (value: string) => void; placeholder: string; required?: boolean }) {
  return (
    <>
      <label className="mt-5 block text-sm font-medium">{label}</label>
      <textarea value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 min-h-28 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-ring" placeholder={placeholder} required={required} />
    </>
  );
}

function SelectInput({ label, value, onChange, options, placeholder = "Select an option", required }: { label: string; value: string; onChange: (value: string) => void; options: Array<{ value: string; label: string }>; placeholder?: string; required?: boolean }) {
  return (
    <>
      <label className="mt-5 block text-sm font-medium">{label}</label>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring" required={required}>
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
    </>
  );
}

function SubmitButton({ saving, label, disabled }: { saving: boolean; label: string; disabled?: boolean }) {
  return (
    <Button className="mt-5 w-full gap-2" type="submit" disabled={saving || disabled}>
      <Plus className="h-4 w-4" aria-hidden="true" />
      {saving ? "Creating" : label}
    </Button>
  );
}

function ListSection({
  loading,
  error,
  emptyIcon,
  emptyTitle,
  emptyDescription,
  children,
}: {
  loading: boolean;
  error: string | null;
  emptyIcon: LucideIcon;
  emptyTitle: string;
  emptyDescription: string;
  children: ReactNode;
}) {
  const items = Array.isArray(children) ? children.filter(Boolean) : children ? [children] : [];

  if (error) return <ErrorState message={error} />;
  if (loading) return <LoadingState label="Loading research records" />;
  if (items.length === 0) return <FeedbackState icon={emptyIcon} title={emptyTitle} description={emptyDescription} />;
  return <div className="grid gap-4">{children}</div>;
}

function RecordCard({ title, badge, description, createdAt, meta }: { title: string; badge: string; description: string; createdAt: string; meta?: string }) {
  return (
    <article className="rounded-lg border bg-card p-5">
      <div className="flex items-start justify-between gap-4">
        <h2 className="font-semibold">{title}</h2>
        <span className="shrink-0 rounded-md border px-2 py-1 text-xs text-muted-foreground">{badge}</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">{description}</p>
      <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted-foreground">
        {meta ? <span className="rounded-md border px-2 py-1">{meta}</span> : null}
        <span className="rounded-md border px-2 py-1">{formatDate(createdAt)}</span>
      </div>
    </article>
  );
}

function datasetName(datasetId: string, datasets: Dataset[]) {
  return datasets.find((dataset) => dataset.id === datasetId)?.name ?? "Unknown dataset";
}

function datasetMeta(dataset: Dataset, assets: Asset[], timeframes: Timeframe[]) {
  const asset = assets.find((item) => item.id === dataset.asset_id);
  const timeframe = timeframes.find((item) => item.id === dataset.timeframe_id);
  return `${asset?.symbol ?? "Unknown asset"} / ${timeframe?.interval ?? "Unknown timeframe"}`;
}
