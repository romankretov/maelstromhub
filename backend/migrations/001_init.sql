CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS markets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  coin text NOT NULL UNIQUE,
  name text NOT NULL,
  sz_decimals integer NOT NULL DEFAULT 0,
  max_leverage integer NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  raw_meta jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS market_snapshots (
  time timestamptz NOT NULL,
  coin text NOT NULL,
  mid numeric,
  mark_px numeric,
  oracle_px numeric,
  prev_day_px numeric,
  day_ntl_vlm numeric,
  open_interest numeric,
  funding numeric,
  premium numeric,
  raw_ctx jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (coin, time)
);
CREATE INDEX IF NOT EXISTS market_snapshots_time_idx ON market_snapshots (time DESC);

CREATE TABLE IF NOT EXISTS candles (
  time timestamptz NOT NULL,
  coin text NOT NULL,
  interval text NOT NULL,
  open numeric NOT NULL,
  high numeric NOT NULL,
  low numeric NOT NULL,
  close numeric NOT NULL,
  volume numeric NOT NULL,
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (coin, interval, time)
);
CREATE INDEX IF NOT EXISTS candles_coin_interval_time_idx ON candles (coin, interval, time DESC);

CREATE TABLE IF NOT EXISTS orderbook_snapshots (
  time timestamptz NOT NULL,
  coin text NOT NULL,
  best_bid numeric,
  best_ask numeric,
  spread_bps numeric,
  bid_depth_10bps numeric,
  ask_depth_10bps numeric,
  bid_depth_50bps numeric,
  ask_depth_50bps numeric,
  bid_depth_100bps numeric,
  ask_depth_100bps numeric,
  book_imbalance_50bps numeric,
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (coin, time)
);
CREATE INDEX IF NOT EXISTS orderbook_snapshots_time_idx ON orderbook_snapshots (time DESC);

CREATE TABLE IF NOT EXISTS recent_trade_snapshots (
  time timestamptz NOT NULL,
  coin text NOT NULL,
  trade_count integer NOT NULL DEFAULT 0,
  buy_volume numeric NOT NULL DEFAULT 0,
  sell_volume numeric NOT NULL DEFAULT 0,
  aggressive_buy_ratio numeric,
  avg_trade_size numeric,
  large_trade_count integer NOT NULL DEFAULT 0,
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (coin, time)
);
CREATE INDEX IF NOT EXISTS recent_trade_snapshots_time_idx ON recent_trade_snapshots (time DESC);

CREATE TABLE IF NOT EXISTS features (
  time timestamptz NOT NULL,
  coin text NOT NULL,
  interval text NOT NULL,
  return_1h numeric,
  return_4h numeric,
  return_24h numeric,
  volume_vs_7d_avg numeric,
  volume_zscore numeric,
  oi_change_1h numeric,
  oi_change_4h numeric,
  oi_change_24h numeric,
  funding_zscore numeric,
  realized_vol numeric,
  atr numeric,
  adx numeric,
  relative_strength_rank numeric,
  autocorr_1 numeric,
  hurst_estimate numeric,
  spread_bps numeric,
  liquidity_score numeric,
  oi_anomaly_score numeric,
  volume_anomaly_score numeric,
  momentum_score numeric,
  funding_anomaly_score numeric,
  execution_quality_score numeric,
  research_score numeric,
  regime_label text,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (coin, interval, time)
);
CREATE INDEX IF NOT EXISTS features_score_idx ON features (research_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS features_time_idx ON features (time DESC);

CREATE TABLE IF NOT EXISTS flags (
  id bigserial PRIMARY KEY,
  time timestamptz NOT NULL,
  coin text NOT NULL,
  flag_type text NOT NULL,
  severity text NOT NULL,
  message text NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS flags_coin_time_idx ON flags (coin, time DESC);
CREATE INDEX IF NOT EXISTS flags_time_idx ON flags (time DESC);

CREATE TABLE IF NOT EXISTS ingestion_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_name text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  status text NOT NULL,
  rows_written integer NOT NULL DEFAULT 0,
  error_message text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ingestion_runs_job_time_idx ON ingestion_runs (job_name, started_at DESC);

CREATE TABLE IF NOT EXISTS job_locks (
  key text PRIMARY KEY,
  locked_until timestamptz NOT NULL
);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
    PERFORM create_hypertable('market_snapshots', 'time', if_not_exists => TRUE);
    PERFORM create_hypertable('candles', 'time', if_not_exists => TRUE);
    PERFORM create_hypertable('orderbook_snapshots', 'time', if_not_exists => TRUE);
    PERFORM create_hypertable('recent_trade_snapshots', 'time', if_not_exists => TRUE);
    PERFORM create_hypertable('features', 'time', if_not_exists => TRUE);
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'Timescale hypertable creation skipped: %', SQLERRM;
END $$;
