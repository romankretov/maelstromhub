"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight, Database, FlaskConical, Gauge, Layers, Microscope, Plus, RefreshCw, Timer } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { ErrorState, FeedbackState, LoadingState } from "@/components/shell/feedback";
import { Button } from "@/components/ui/button";
import {
  createAsset,
  createDataset,
  createExperiment,
  createFeature,
  createTimeframe,
  backfillDatasetCandles,
  computeDatasetFeatures,
  computeDatasetRegimes,
  getAssets,
  getDataset,
  getDatasetCandles,
  getDatasetMarketIntelligence,
  getDatasetFeatureSummary,
  getDatasetIngestionJobs,
  getDatasetRegimeSnapshots,
  getDatasets,
  getExperiments,
  getFeatures,
  getTimeframes,
  type Asset,
  type Candle,
  type Dataset,
  type Experiment,
  type Feature,
  type FeatureSummary,
  type IngestionJob,
  type MarketRegimeSnapshot,
  type Timeframe,
} from "@/lib/api-client";

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function descriptionValue(value: string | null) {
  return value?.trim() ? value : "No description";
}

const SYSTEM_TIMEFRAME_UNAVAILABLE_MESSAGE =
  "System timeframes are unavailable. Dataset creation is disabled until the API seeds supported timeframes.";

export function getSystemTimeframeError(timeframes: Timeframe[], failedToLoad: boolean) {
  if (failedToLoad) return SYSTEM_TIMEFRAME_UNAVAILABLE_MESSAGE;
  if (timeframes.length === 0) return SYSTEM_TIMEFRAME_UNAVAILABLE_MESSAGE;
  return null;
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
    if (datasets.length === 0) return { href: "/research/datasets", label: "Create a dataset", detail: "Choose an asset and supported system timeframe." };
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
    { label: "Market Intelligence", value: datasets.length, href: "/research/market-intelligence", icon: Gauge },
    { label: "Experiments", value: experiments.length, href: "/research/experiments", icon: FlaskConical },
  ];

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-5">
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

export function MarketIntelligenceClient() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [currentRegime, setCurrentRegime] = useState<MarketRegimeSnapshot | null>(null);
  const [regimeSnapshots, setRegimeSnapshots] = useState<MarketRegimeSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadIntelligence = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const loadedDatasets = await getDatasets();
      const datasetId = selectedDatasetId || loadedDatasets[0]?.id || "";
      const [intelligence, snapshots] = datasetId
        ? await Promise.all([getDatasetMarketIntelligence(datasetId), getDatasetRegimeSnapshots(datasetId)])
        : [null, [] as MarketRegimeSnapshot[]];
      setDatasets(loadedDatasets);
      setSelectedDatasetId(datasetId);
      setCurrentRegime(intelligence?.regime ?? null);
      setRegimeSnapshots(snapshots);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load market intelligence.");
    } finally {
      setLoading(false);
    }
  }, [selectedDatasetId]);

  useEffect(() => {
    void loadIntelligence();
  }, [loadIntelligence]);

  const counts = regimeSnapshots.reduce<Record<string, number>>((accumulator, snapshot) => {
    accumulator[snapshot.regime_label] = (accumulator[snapshot.regime_label] ?? 0) + 1;
    return accumulator;
  }, {});

  if (loading) return <LoadingState label="Loading market intelligence" />;
  if (error) return <ErrorState message={error} />;

  return (
    <div className="space-y-6">
      <section className="rounded-lg border bg-card p-5">
        <label className="block text-sm font-medium" htmlFor="market-intelligence-dataset">
          Dataset
          <select
            id="market-intelligence-dataset"
            value={selectedDatasetId}
            onChange={(event) => setSelectedDatasetId(event.target.value)}
            className="mt-2 h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
          >
            {datasets.map((dataset) => (
              <option key={dataset.id} value={dataset.id}>
                {dataset.name}
              </option>
            ))}
          </select>
        </label>
      </section>

      <section className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <section className="rounded-lg border bg-card p-5">
          <h2 className="text-base font-semibold">Current regime</h2>
          {currentRegime ? (
            <>
              <p className="mt-4 text-2xl font-semibold">{currentRegime.regime_label}</p>
              <p className="mt-2 text-sm text-muted-foreground">
                Confidence {(currentRegime.confidence * 100).toFixed(0)}%
              </p>
              <p className="mt-4 text-sm leading-6 text-muted-foreground">{currentRegime.explanation}</p>
            </>
          ) : (
            <p className="mt-3 text-sm text-muted-foreground">No regime snapshot is available.</p>
          )}
        </section>
        <section className="rounded-lg border bg-card p-5">
          <h2 className="text-base font-semibold">Counts</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(counts).map(([label, count]) => (
              <div key={label} className="rounded-md border bg-background p-3">
                <p className="text-sm font-medium">{label}</p>
                <p className="mt-1 text-2xl font-semibold">{count}</p>
              </div>
            ))}
          </div>
        </section>
      </section>

      <section className="rounded-lg border bg-card p-5">
        <h2 className="text-base font-semibold">Historical regime timeline</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b text-xs text-muted-foreground">
              <tr>
                <th className="py-2 pr-4 font-medium">Time</th>
                <th className="py-2 pr-4 font-medium">Label</th>
                <th className="py-2 pr-4 font-medium">Trend</th>
                <th className="py-2 pr-4 font-medium">Volatility</th>
                <th className="py-2 font-medium">Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {regimeSnapshots.map((snapshot) => (
                <tr key={snapshot.id}>
                  <td className="py-3 pr-4 text-muted-foreground">{formatDate(snapshot.timestamp)}</td>
                  <td className="py-3 pr-4 font-medium">{snapshot.regime_label}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{snapshot.trend_regime}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{snapshot.volatility_regime}</td>
                  <td className="py-3 text-muted-foreground">{snapshot.risk_regime}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
          <FormTitle title="Create internal timeframe" description="Admin-only override for supported exchange intervals." />
          <TextInput label="Name" value={name} onChange={setName} placeholder="One hour" required />
          <TextInput label="Interval" value={interval} onChange={setInterval} placeholder="1h" required />
          <TextArea label="Description" value={description} onChange={setDescription} placeholder="Optional notes" />
          <SubmitButton saving={saving} label="Create internal timeframe" />
        </form>
      }
      content={
        <ListSection loading={loading} error={error} emptyIcon={Timer} emptyTitle="No timeframes available" emptyDescription="System timeframes are normally seeded automatically by the API.">
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
  const [timeframesFailedToLoad, setTimeframesFailedToLoad] = useState(false);

  useEffect(() => {
    async function loadDatasets() {
      setLoading(true);
      setError(null);
      setTimeframesFailedToLoad(false);
      try {
        const [loadedAssets, loadedDatasets] = await Promise.all([getAssets(), getDatasets()]);
        let loadedTimeframes: Timeframe[] = [];
        try {
          loadedTimeframes = await getTimeframes();
        } catch {
          setTimeframesFailedToLoad(true);
        }
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

  const timeframeSystemError = loading || error ? null : getSystemTimeframeError(timeframes, timeframesFailedToLoad);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (timeframeSystemError) {
      setError(timeframeSystemError);
      return;
    }
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
          <FormTitle title="Create dataset" description="Link an asset to a supported system timeframe. This stores metadata only." />
          <SelectInput label="Asset" value={assetId} onChange={setAssetId} options={assets.map((asset) => ({ value: asset.id, label: `${asset.symbol} / ${asset.venue}` }))} required />
          {timeframeSystemError ? (
            <div className="mt-4 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
              {timeframeSystemError}
            </div>
          ) : (
            <SelectInput label="System timeframe" value={timeframeId} onChange={setTimeframeId} options={timeframes.map((timeframe) => ({ value: timeframe.id, label: `${timeframe.name} (${timeframe.interval})` }))} required />
          )}
          <TextInput label="Name" value={name} onChange={setName} placeholder="BTC 1h research dataset" required />
          <TextArea label="Description" value={description} onChange={setDescription} placeholder="Dataset scope and assumptions" />
          <SubmitButton saving={saving} label="Create dataset" disabled={!assetId || !timeframeId || Boolean(timeframeSystemError)} />
        </form>
      }
      content={
        <ListSection loading={loading} error={error} emptyIcon={Layers} emptyTitle="No datasets yet" emptyDescription="Create an asset, then define a dataset with a supported system timeframe.">
          {datasets.map((dataset) => (
            <RecordCard key={dataset.id} title={dataset.name} badge="Dataset" description={descriptionValue(dataset.description)} createdAt={dataset.created_at} meta={datasetMeta(dataset, assets, timeframes)} href={`/research/datasets/${dataset.id}`} />
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

export function DatasetDetailClient({ datasetId }: { datasetId: string }) {
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [jobs, setJobs] = useState<IngestionJob[]>([]);
  const [featureSummary, setFeatureSummary] = useState<FeatureSummary | null>(null);
  const [regimeSnapshots, setRegimeSnapshots] = useState<MarketRegimeSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [backfilling, setBackfilling] = useState(false);
  const [computingFeatures, setComputingFeatures] = useState(false);
  const [computingRegimes, setComputingRegimes] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadDataset = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [loadedDataset, loadedCandles, loadedJobs, loadedFeatureSummary, loadedRegimes] = await Promise.all([
        getDataset(datasetId),
        getDatasetCandles(datasetId),
        getDatasetIngestionJobs(datasetId),
        getDatasetFeatureSummary(datasetId),
        getDatasetRegimeSnapshots(datasetId),
      ]);
      setDataset(loadedDataset);
      setCandles(loadedCandles);
      setJobs(loadedJobs);
      setFeatureSummary(loadedFeatureSummary);
      setRegimeSnapshots(loadedRegimes);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load dataset.");
    } finally {
      setLoading(false);
    }
  }, [datasetId]);

  useEffect(() => {
    void loadDataset();
  }, [loadDataset]);

  async function handleBackfill() {
    setBackfilling(true);
    setError(null);
    setNotice(null);
    try {
      const job = await backfillDatasetCandles(datasetId);
      const [loadedDataset, loadedCandles, loadedJobs] = await Promise.all([
        getDataset(datasetId),
        getDatasetCandles(datasetId),
        getDatasetIngestionJobs(datasetId),
      ]);
      setDataset(loadedDataset);
      setCandles(loadedCandles);
      setJobs(loadedJobs);
      setNotice(`Backfill job queued: ${job.id}.`);
    } catch (backfillError) {
      setError(backfillError instanceof Error ? backfillError.message : "Unable to backfill candles.");
    } finally {
      setBackfilling(false);
    }
  }

  async function handleComputeFeatures() {
    setComputingFeatures(true);
    setError(null);
    setNotice(null);
    try {
      const job = await computeDatasetFeatures(datasetId);
      const loadedJobs = await getDatasetIngestionJobs(datasetId);
      setJobs(loadedJobs);
      setNotice(`Feature compute job queued: ${job.id}.`);
    } catch (computeError) {
      setError(computeError instanceof Error ? computeError.message : "Unable to queue feature computation.");
    } finally {
      setComputingFeatures(false);
    }
  }

  async function handleComputeRegimes() {
    setComputingRegimes(true);
    setError(null);
    setNotice(null);
    try {
      const result = await computeDatasetRegimes(datasetId);
      setRegimeSnapshots(await getDatasetRegimeSnapshots(datasetId));
      setNotice(`Regime snapshots computed: ${result.snapshots_written}.`);
    } catch (computeError) {
      setError(computeError instanceof Error ? computeError.message : "Unable to compute regimes.");
    } finally {
      setComputingRegimes(false);
    }
  }

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await loadDataset();
    } finally {
      setRefreshing(false);
    }
  }

  if (loading) return <LoadingState label="Loading dataset" />;
  if (error && !dataset) return <ErrorState message={error} />;
  if (!dataset) {
    return (
      <FeedbackState
        icon={Layers}
        title="Dataset not found"
        description="The dataset could not be loaded from the API."
      />
    );
  }

  return (
    <div className="space-y-6">
      {error ? <ErrorState message={error} /> : null}
      {notice ? <section className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">{notice}</section> : null}

      <section className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Candles" value={dataset.candle_count.toString()} />
        <MetricCard label="Features" value={(featureSummary?.total_snapshots ?? 0).toString()} />
        <MetricCard label="Latest feature" value={featureSummary?.latest_timestamp ? formatDate(featureSummary.latest_timestamp) : "none"} />
        <MetricCard label="Regime" value={regimeSnapshots[0]?.regime_label ?? "none"} />
      </section>

      <section className="rounded-lg border bg-card p-5">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div>
            <h2 className="text-lg font-semibold">{dataset.name}</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              {descriptionValue(dataset.description)}
            </p>
            <p className="mt-3 text-xs text-muted-foreground">Created {formatDate(dataset.created_at)}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleRefresh} disabled={refreshing}>
              <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
              {refreshing ? "Refreshing" : "Refresh"}
            </Button>
            <Button onClick={handleBackfill} disabled={backfilling}>
              {backfilling ? "Queueing" : "Backfill data"}
            </Button>
            <Button onClick={handleComputeFeatures} disabled={computingFeatures || candles.length === 0}>
              {computingFeatures ? "Queueing" : "Compute features"}
            </Button>
            <Button onClick={handleComputeRegimes} disabled={computingRegimes || (featureSummary?.total_snapshots ?? 0) === 0}>
              <Gauge className="mr-2 h-4 w-4" aria-hidden="true" />
              {computingRegimes ? "Computing" : "Compute Regimes"}
            </Button>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <section className="rounded-lg border bg-card p-5">
          <h2 className="text-base font-semibold">Current Regime</h2>
          {regimeSnapshots[0] ? (
            <>
              <p className="mt-4 text-2xl font-semibold">{regimeSnapshots[0].regime_label}</p>
              <p className="mt-2 text-sm text-muted-foreground">
                Confidence {(regimeSnapshots[0].confidence * 100).toFixed(0)}%
              </p>
              <p className="mt-4 text-sm leading-6 text-muted-foreground">{regimeSnapshots[0].explanation}</p>
            </>
          ) : (
            <p className="mt-3 text-sm text-muted-foreground">No regime snapshots computed yet.</p>
          )}
        </section>

        <section className="rounded-lg border bg-card p-5">
          <div className="mb-4 flex items-center justify-between gap-4">
            <h2 className="text-base font-semibold">Regime history</h2>
            <p className="text-sm text-muted-foreground">{regimeSnapshots.length} snapshots</p>
          </div>
          {regimeSnapshots.length === 0 ? (
            <p className="text-sm text-muted-foreground">Compute regimes after feature snapshots exist.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b text-xs text-muted-foreground">
                  <tr>
                    <th className="py-2 pr-4 font-medium">Time</th>
                    <th className="py-2 pr-4 font-medium">Regime</th>
                    <th className="py-2 pr-4 font-medium">Confidence</th>
                    <th className="py-2 font-medium">Explanation</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {regimeSnapshots.slice(0, 12).map((snapshot) => (
                    <tr key={snapshot.id}>
                      <td className="py-3 pr-4 text-muted-foreground">{formatDate(snapshot.timestamp)}</td>
                      <td className="py-3 pr-4 font-medium">{snapshot.regime_label}</td>
                      <td className="py-3 pr-4 text-muted-foreground">
                        {(snapshot.confidence * 100).toFixed(0)}%
                      </td>
                      <td className="py-3 text-muted-foreground">{snapshot.explanation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </section>

      <section className="rounded-lg border bg-card p-5">
        <div className="mb-4 flex items-center justify-between gap-4">
          <h2 className="text-base font-semibold">Ingestion jobs</h2>
          <p className="text-sm text-muted-foreground">{jobs.length} jobs</p>
        </div>
        {jobs.length === 0 ? (
          <p className="text-sm text-muted-foreground">No ingestion jobs have been queued for this dataset.</p>
        ) : (
          <div className="divide-y">
            {jobs.map((job) => (
              <div key={job.id} className="py-3 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <p className="font-medium">{job.id}</p>
                  <span className="rounded-md border px-2 py-1 text-xs text-muted-foreground">
                    {job.job_type} / {job.status}
                  </span>
                </div>
                <p className="mt-1 text-muted-foreground">
                  {job.candles_written} candles, {job.feature_snapshots_written} feature snapshots
                  {job.finished_at ? `, finished ${formatDate(job.finished_at)}` : ""}
                </p>
                {job.error_message ? <p className="mt-1 text-red-700">{job.error_message}</p> : null}
              </div>
            ))}
          </div>
        )}
      </section>

      {candles.length === 0 ? (
        <FeedbackState
          icon={Layers}
          title="No candles in this dataset"
          description="Run a candle backfill to fetch historical Hyperliquid candles for this dataset's asset and timeframe."
        />
      ) : (
        <section className="rounded-lg border bg-card p-5">
          <div className="mb-4 flex items-center justify-between gap-4">
            <h2 className="text-base font-semibold">Close price</h2>
            <p className="text-sm text-muted-foreground">{candles.length} candles</p>
          </div>
          <CandleChart candles={candles} />
          <div className="mt-4 grid gap-2 text-xs text-muted-foreground md:grid-cols-2">
            <span>First: {formatDate(candles[0].opened_at)}</span>
            <span>Last: {formatDate(candles[candles.length - 1].opened_at)}</span>
          </div>
        </section>
      )}

      <section className="rounded-lg border bg-card p-5">
        <div className="mb-4 flex items-center justify-between gap-4">
          <h2 className="text-base font-semibold">Feature summary</h2>
          <p className="text-sm text-muted-foreground">{featureSummary?.total_snapshots ?? 0} snapshots</p>
        </div>
        {!featureSummary || featureSummary.features.length === 0 ? (
          <p className="text-sm text-muted-foreground">No generated feature snapshots yet. Backfill candles first, then compute features.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b text-xs text-muted-foreground">
                <tr>
                  <th className="py-2 pr-4 font-medium">Feature</th>
                  <th className="py-2 pr-4 font-medium">Snapshots</th>
                  <th className="py-2 pr-4 font-medium">Latest value</th>
                  <th className="py-2 font-medium">Latest timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {featureSummary.features.map((feature) => (
                  <tr key={feature.feature_name}>
                    <td className="py-3 pr-4 font-medium">{feature.feature_name}</td>
                    <td className="py-3 pr-4 text-muted-foreground">{feature.snapshot_count}</td>
                    <td className="py-3 pr-4 text-muted-foreground">
                      {feature.latest_value === null ? "n/a" : feature.latest_value.toFixed(6)}
                    </td>
                    <td className="py-3 text-muted-foreground">
                      {feature.latest_timestamp ? formatDate(feature.latest_timestamp) : "n/a"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
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

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-2 truncate text-sm font-semibold">{value}</p>
    </div>
  );
}

function RecordCard({ title, badge, description, createdAt, meta, href }: { title: string; badge: string; description: string; createdAt: string; meta?: string; href?: string }) {
  const titleNode = href ? (
    <Link href={href} className="hover:text-primary">
      {title}
    </Link>
  ) : (
    title
  );

  return (
    <article className="rounded-lg border bg-card p-5">
      <div className="flex items-start justify-between gap-4">
        <h2 className="font-semibold">{titleNode}</h2>
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

function CandleChart({ candles }: { candles: Candle[] }) {
  const width = 720;
  const height = 240;
  const padding = 16;
  const closes = candles.map((candle) => candle.close);
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const range = max - min || 1;
  const points = candles.map((candle, index) => {
    const x = padding + (index / Math.max(candles.length - 1, 1)) * (width - padding * 2);
    const y = height - padding - ((candle.close - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  });

  return (
    <div className="overflow-hidden rounded-lg border bg-background">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-64 w-full" role="img" aria-label="Dataset candle close price chart">
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="hsl(var(--border))" />
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="hsl(var(--border))" />
        <polyline fill="none" stroke="hsl(var(--primary))" strokeWidth="2" points={points.join(" ")} />
      </svg>
    </div>
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
