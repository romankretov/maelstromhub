export type Idea = {
  id: string;
  title: string;
  thesis: string;
  created_at: string;
};

export type StrategyStatus =
  | "Draft"
  | "Backtested"
  | "Paper Trading"
  | "Live Small Size"
  | "Live Full Size"
  | "Paused"
  | "Retired";

export type Strategy = {
  id: string;
  name: string;
  status: StrategyStatus;
  source_idea_id: string | null;
  description: string;
  created_at: string;
};

export type AuditEvent = {
  id: string;
  actor: string;
  action: string;
  subject: string;
  created_at: string;
};

export type Asset = {
  id: string;
  symbol: string;
  venue: string;
  description: string | null;
  created_at: string;
};

export type Timeframe = {
  id: string;
  name: string;
  interval: string;
  description: string | null;
  created_at: string;
};

export type Dataset = {
  id: string;
  asset_id: string;
  timeframe_id: string;
  name: string;
  description: string | null;
  latest_candle_timestamp: string | null;
  candle_count: number;
  last_ingestion_status: string | null;
  last_ingestion_error: string | null;
  created_at: string;
};

export type Candle = {
  id: string;
  dataset_id: string;
  opened_at: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  trade_count: number | null;
  created_at: string;
};

export type Feature = {
  id: string;
  dataset_id: string;
  name: string;
  values: Record<string, number>;
  description: string | null;
  created_at: string;
};

export type ExperimentStatus = "Draft" | "Running" | "Completed" | "Failed";

export type Experiment = {
  id: string;
  dataset_id: string;
  feature_id: string | null;
  name: string;
  hypothesis: string;
  notes: string | null;
  metrics: Record<string, number>;
  status: ExperimentStatus;
  created_at: string;
};

export type StrategyParameterValue = string | number | boolean | null;

export type StrategyTemplate = {
  id: string;
  name: string;
  description: string;
  required_features: string[];
  parameters: Record<string, string>;
  default_parameters: Record<string, StrategyParameterValue>;
  created_at: string;
};

export type StrategyVersion = {
  id: string;
  strategy_id: string;
  template_id: string;
  dataset_id: string;
  version_number: number;
  parameters: Record<string, StrategyParameterValue>;
  created_at: string;
};

export type SignalSide = "long" | "short" | "flat";

export type Signal = {
  id: string;
  strategy_version_id: string;
  strategy_id: string;
  dataset_id: string;
  timestamp: string;
  symbol: string;
  side: SignalSide;
  confidence: number;
  reason: string;
  suggested_size: number;
  metadata: Record<string, StrategyParameterValue>;
  created_at: string;
};

export type SignalRunResult = {
  strategy_version_id: string;
  signals_written: number;
  total_signals: number;
};

export type BacktestStatus = "started" | "succeeded" | "failed";
export type BacktestVerdict = "Ready" | "Review" | "Blocked";

export type BacktestRunCreate = {
  starting_balance?: number;
  fee_bps?: number;
  slippage_bps?: number;
};

export type BacktestTrade = {
  id: string;
  backtest_run_id: string;
  timestamp: string;
  symbol: string;
  side: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  pnl: number;
  fees: number;
  reason: string;
};

export type EquityCurveSnapshot = {
  id: string;
  backtest_run_id: string;
  timestamp: string;
  equity: number;
  drawdown: number;
};

export type BacktestRun = {
  id: string;
  strategy_version_id: string;
  dataset_id: string;
  status: BacktestStatus;
  starting_balance: number;
  fee_bps: number;
  slippage_bps: number;
  created_at: string;
  finished_at: string | null;
  metrics: Record<string, number | string>;
};

export type BacktestRunDetail = BacktestRun & {
  trades: BacktestTrade[];
  equity_curve: EquityCurveSnapshot[];
};

export type BacktestEvaluation = {
  verdict: BacktestVerdict;
  risk_adjusted_score: number;
  reasons: string[];
  thresholds: Record<string, number>;
};

export type StrategyPromotionResult = {
  strategy: Strategy;
  promoted: boolean;
  from_status: StrategyStatus;
  to_status: StrategyStatus;
  reasons: string[];
  backtest_run: BacktestRun | null;
  evaluation: BacktestEvaluation | null;
};

export type IdeaCreate = {
  title: string;
  thesis: string;
};

export type StrategyCreate = {
  name: string;
  source_idea_id?: string | null;
  description: string;
};

export type AssetCreate = {
  symbol: string;
  venue: string;
  description?: string | null;
};

export type TimeframeCreate = {
  name: string;
  interval: string;
  description?: string | null;
};

export type DatasetCreate = {
  asset_id: string;
  timeframe_id: string;
  name: string;
  description?: string | null;
};

export type CandleBackfillRequest = {
  start_time?: string | null;
  end_time?: string | null;
};

export type CandleBackfillResult = {
  dataset_id: string;
  inserted: number;
  updated: number;
  total_candles: number;
  latest_candle_timestamp: string | null;
  status: string;
};

export type IngestionJobStatus = "queued" | "running" | "succeeded" | "failed";

export type IngestionJob = {
  id: string;
  dataset_id: string;
  job_type: "candle_backfill" | "feature_compute";
  status: IngestionJobStatus;
  requested_start: string | null;
  requested_end: string | null;
  started_at: string | null;
  finished_at: string | null;
  candles_written: number;
  feature_snapshots_written: number;
  error_message: string | null;
  created_at: string;
};

export type FeatureSnapshot = {
  id: string;
  dataset_id: string;
  timestamp: string;
  feature_name: string;
  numeric_value: number;
  metadata: Record<string, string | number | boolean | null>;
  created_at: string;
};

export type FeatureSummaryItem = {
  feature_name: string;
  snapshot_count: number;
  latest_timestamp: string | null;
  latest_value: number | null;
};

export type FeatureSummary = {
  dataset_id: string;
  total_snapshots: number;
  latest_timestamp: string | null;
  features: FeatureSummaryItem[];
};

export type FeatureCreate = {
  dataset_id: string;
  name: string;
  values?: Record<string, number>;
  description?: string | null;
};

export type ExperimentCreate = {
  dataset_id: string;
  feature_id?: string | null;
  name: string;
  hypothesis: string;
  notes?: string | null;
  metrics?: Record<string, number>;
};

export type StrategyVersionCreate = {
  template_id: string;
  dataset_id: string;
  parameters?: Record<string, StrategyParameterValue>;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function getIdeas(): Promise<Idea[]> {
  const body = await request<{ ideas: Idea[] }>("/ideas");
  return body.ideas;
}

export async function createIdea(payload: IdeaCreate): Promise<Idea> {
  return request<Idea>("/ideas", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getStrategies(): Promise<Strategy[]> {
  const body = await request<{ strategies: Strategy[] }>("/strategies");
  return body.strategies;
}

export async function createStrategy(payload: StrategyCreate): Promise<Strategy> {
  return request<Strategy>("/strategies", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function promoteStrategy(strategyId: string): Promise<StrategyPromotionResult> {
  return request<StrategyPromotionResult>(`/strategies/${strategyId}/promote`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function getStrategyTemplates(): Promise<StrategyTemplate[]> {
  const body = await request<{ strategy_templates: StrategyTemplate[] }>("/strategy-templates");
  return body.strategy_templates;
}

export async function getStrategyVersions(strategyId: string): Promise<StrategyVersion[]> {
  const body = await request<{ strategy_versions: StrategyVersion[] }>(`/strategies/${strategyId}/versions`);
  return body.strategy_versions;
}

export async function createStrategyVersion(
  strategyId: string,
  payload: StrategyVersionCreate,
): Promise<StrategyVersion> {
  return request<StrategyVersion>(`/strategies/${strategyId}/versions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runStrategySignals(versionId: string): Promise<SignalRunResult> {
  return request<SignalRunResult>(`/strategy-versions/${versionId}/run-signals`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function getStrategySignals(versionId: string): Promise<Signal[]> {
  const body = await request<{ signals: Signal[] }>(`/strategy-versions/${versionId}/signals`);
  return body.signals;
}

export async function createBacktest(
  versionId: string,
  payload: BacktestRunCreate,
): Promise<BacktestRunDetail> {
  return request<BacktestRunDetail>(`/strategy-versions/${versionId}/backtests`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getStrategyVersionBacktests(versionId: string): Promise<BacktestRun[]> {
  const body = await request<{ backtests: BacktestRun[] }>(`/strategy-versions/${versionId}/backtests`);
  return body.backtests;
}

export async function getBacktest(backtestId: string): Promise<BacktestRunDetail> {
  return request<BacktestRunDetail>(`/backtests/${backtestId}`);
}

export async function getAuditEvents(): Promise<AuditEvent[]> {
  const body = await request<{ audit_events: AuditEvent[] }>("/audit-events");
  return body.audit_events;
}

export async function getAssets(): Promise<Asset[]> {
  const body = await request<{ assets: Asset[] }>("/assets");
  return body.assets;
}

export async function createAsset(payload: AssetCreate): Promise<Asset> {
  return request<Asset>("/assets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getTimeframes(): Promise<Timeframe[]> {
  const body = await request<{ timeframes: Timeframe[] }>("/timeframes");
  return body.timeframes;
}

export async function createTimeframe(payload: TimeframeCreate): Promise<Timeframe> {
  return request<Timeframe>("/timeframes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getDatasets(): Promise<Dataset[]> {
  const body = await request<{ datasets: Dataset[] }>("/datasets");
  return body.datasets;
}

export async function getDataset(datasetId: string): Promise<Dataset> {
  return request<Dataset>(`/datasets/${datasetId}`);
}

export async function createDataset(payload: DatasetCreate): Promise<Dataset> {
  return request<Dataset>("/datasets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getDatasetCandles(datasetId: string): Promise<Candle[]> {
  const body = await request<{ candles: Candle[] }>(`/datasets/${datasetId}/candles`);
  return body.candles;
}

export async function backfillDatasetCandles(
  datasetId: string,
  payload: CandleBackfillRequest = {},
): Promise<IngestionJob> {
  return request<IngestionJob>(`/datasets/${datasetId}/backfill-candles`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function computeDatasetFeatures(datasetId: string): Promise<IngestionJob> {
  return request<IngestionJob>(`/datasets/${datasetId}/compute-features`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function getDatasetFeatureSnapshots(datasetId: string): Promise<FeatureSnapshot[]> {
  const body = await request<{ feature_snapshots: FeatureSnapshot[] }>(`/datasets/${datasetId}/feature-snapshots`);
  return body.feature_snapshots;
}

export async function getDatasetFeatureSummary(datasetId: string): Promise<FeatureSummary> {
  return request<FeatureSummary>(`/datasets/${datasetId}/feature-summary`);
}

export async function getIngestionJob(jobId: string): Promise<IngestionJob> {
  return request<IngestionJob>(`/ingestion-jobs/${jobId}`);
}

export async function getDatasetIngestionJobs(datasetId: string): Promise<IngestionJob[]> {
  const body = await request<{ ingestion_jobs: IngestionJob[] }>(`/datasets/${datasetId}/ingestion-jobs`);
  return body.ingestion_jobs;
}

export async function getFeatures(): Promise<Feature[]> {
  const body = await request<{ features: Feature[] }>("/features");
  return body.features;
}

export async function createFeature(payload: FeatureCreate): Promise<Feature> {
  return request<Feature>("/features", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getExperiments(): Promise<Experiment[]> {
  const body = await request<{ experiments: Experiment[] }>("/experiments");
  return body.experiments;
}

export async function createExperiment(payload: ExperimentCreate): Promise<Experiment> {
  return request<Experiment>("/experiments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
