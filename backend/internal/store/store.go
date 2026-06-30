package store

import (
	"context"
	"encoding/json"
	"log/slog"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"

	"maelstrom/backend/internal/models"
)

type Store struct {
	db     *pgxpool.Pool
	redis  *redis.Client
	logger *slog.Logger
}

func New(db *pgxpool.Pool, redis *redis.Client, logger *slog.Logger) *Store {
	return &Store{db: db, redis: redis, logger: logger}
}

func (s *Store) PingDB(ctx context.Context) error {
	return s.db.Ping(ctx)
}

func (s *Store) PingRedis(ctx context.Context) error {
	return s.redis.Ping(ctx).Err()
}

func (s *Store) UpsertMarkets(ctx context.Context, markets []models.Market) (int, error) {
	batch := &pgx.Batch{}
	for _, m := range markets {
		raw := m.RawMeta
		if len(raw) == 0 {
			raw = []byte(`{}`)
		}
		batch.Queue(`INSERT INTO markets (coin, name, sz_decimals, max_leverage, is_active, raw_meta, updated_at)
			VALUES ($1,$2,$3,$4,$5,$6,now())
			ON CONFLICT (coin) DO UPDATE SET name=EXCLUDED.name, sz_decimals=EXCLUDED.sz_decimals, max_leverage=EXCLUDED.max_leverage, is_active=EXCLUDED.is_active, raw_meta=EXCLUDED.raw_meta, updated_at=now()`,
			m.Coin, m.Name, m.SzDecimals, m.MaxLeverage, m.IsActive, raw)
	}
	br := s.db.SendBatch(ctx, batch)
	defer br.Close()
	count := 0
	for range markets {
		if _, err := br.Exec(); err != nil {
			return count, err
		}
		count++
	}
	return count, nil
}

func (s *Store) InsertMarketSnapshots(ctx context.Context, snapshots []models.MarketSnapshot) (int, error) {
	batch := &pgx.Batch{}
	for _, v := range snapshots {
		raw := v.RawCtx
		if len(raw) == 0 {
			raw = []byte(`{}`)
		}
		batch.Queue(`INSERT INTO market_snapshots (time, coin, mid, mark_px, oracle_px, prev_day_px, day_ntl_vlm, open_interest, funding, premium, raw_ctx)
			VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
			ON CONFLICT (coin, time) DO UPDATE SET mid=EXCLUDED.mid, mark_px=EXCLUDED.mark_px, oracle_px=EXCLUDED.oracle_px, prev_day_px=EXCLUDED.prev_day_px, day_ntl_vlm=EXCLUDED.day_ntl_vlm, open_interest=EXCLUDED.open_interest, funding=EXCLUDED.funding, premium=EXCLUDED.premium, raw_ctx=EXCLUDED.raw_ctx`,
			v.Time, v.Coin, v.Mid, v.MarkPx, v.OraclePx, v.PrevDayPx, v.DayNtlVlm, v.OpenInterest, v.Funding, v.Premium, raw)
	}
	br := s.db.SendBatch(ctx, batch)
	defer br.Close()
	count := 0
	for range snapshots {
		if _, err := br.Exec(); err != nil {
			return count, err
		}
		count++
	}
	if len(snapshots) > 0 {
		data, _ := json.Marshal(snapshots)
		_ = s.redis.Set(ctx, "latest:market_snapshots", data, 15*time.Minute).Err()
	}
	return count, nil
}

func (s *Store) UpsertCandles(ctx context.Context, candles []models.Candle) (int, error) {
	batch := &pgx.Batch{}
	for _, c := range candles {
		raw := c.Raw
		if len(raw) == 0 {
			raw = []byte(`{}`)
		}
		batch.Queue(`INSERT INTO candles (time, coin, interval, open, high, low, close, volume, raw)
			VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
			ON CONFLICT (coin, interval, time) DO UPDATE SET open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close, volume=EXCLUDED.volume, raw=EXCLUDED.raw`,
			c.Time, c.Coin, c.Interval, c.Open, c.High, c.Low, c.Close, c.Volume, raw)
	}
	br := s.db.SendBatch(ctx, batch)
	defer br.Close()
	count := 0
	for range candles {
		if _, err := br.Exec(); err != nil {
			return count, err
		}
		count++
	}
	return count, nil
}

func (s *Store) UpsertFeatures(ctx context.Context, features []models.Feature) (int, error) {
	batch := &pgx.Batch{}
	for _, f := range features {
		batch.Queue(`INSERT INTO features (time, coin, interval, return_1h, return_4h, return_24h, volume_vs_7d_avg, volume_zscore, oi_change_1h, oi_change_4h, oi_change_24h, funding_zscore, realized_vol, atr, adx, relative_strength_rank, autocorr_1, hurst_estimate, spread_bps, liquidity_score, oi_anomaly_score, volume_anomaly_score, momentum_score, funding_anomaly_score, execution_quality_score, research_score, regime_label, updated_at)
			VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25,$26,$27,now())
			ON CONFLICT (coin, interval, time) DO UPDATE SET return_1h=EXCLUDED.return_1h, return_4h=EXCLUDED.return_4h, return_24h=EXCLUDED.return_24h, volume_vs_7d_avg=EXCLUDED.volume_vs_7d_avg, volume_zscore=EXCLUDED.volume_zscore, oi_change_1h=EXCLUDED.oi_change_1h, oi_change_4h=EXCLUDED.oi_change_4h, oi_change_24h=EXCLUDED.oi_change_24h, funding_zscore=EXCLUDED.funding_zscore, realized_vol=EXCLUDED.realized_vol, atr=EXCLUDED.atr, adx=EXCLUDED.adx, relative_strength_rank=EXCLUDED.relative_strength_rank, autocorr_1=EXCLUDED.autocorr_1, hurst_estimate=EXCLUDED.hurst_estimate, spread_bps=EXCLUDED.spread_bps, liquidity_score=EXCLUDED.liquidity_score, oi_anomaly_score=EXCLUDED.oi_anomaly_score, volume_anomaly_score=EXCLUDED.volume_anomaly_score, momentum_score=EXCLUDED.momentum_score, funding_anomaly_score=EXCLUDED.funding_anomaly_score, execution_quality_score=EXCLUDED.execution_quality_score, research_score=EXCLUDED.research_score, regime_label=EXCLUDED.regime_label, updated_at=now()`,
			f.Time, f.Coin, f.Interval, f.Return1H, f.Return4H, f.Return24H, f.VolumeVs7DAvg, f.VolumeZScore, f.OIChange1H, f.OIChange4H, f.OIChange24H, f.FundingZScore, f.RealizedVol, f.ATR, f.ADX, f.RelativeStrengthRank, f.Autocorr1, f.HurstEstimate, f.SpreadBps, f.LiquidityScore, f.OIAnomalyScore, f.VolumeAnomalyScore, f.MomentumScore, f.FundingAnomalyScore, f.ExecutionQualityScore, f.ResearchScore, f.RegimeLabel)
	}
	br := s.db.SendBatch(ctx, batch)
	defer br.Close()
	count := 0
	for range features {
		if _, err := br.Exec(); err != nil {
			return count, err
		}
		count++
	}
	return count, nil
}

func (s *Store) InsertFlags(ctx context.Context, flags []models.Flag) (int, error) {
	batch := &pgx.Batch{}
	for _, f := range flags {
		meta := f.Metadata
		if len(meta) == 0 {
			meta = []byte(`{}`)
		}
		batch.Queue(`INSERT INTO flags (time, coin, flag_type, severity, message, metadata) VALUES ($1,$2,$3,$4,$5,$6)`,
			f.Time, f.Coin, f.FlagType, f.Severity, f.Message, meta)
	}
	br := s.db.SendBatch(ctx, batch)
	defer br.Close()
	count := 0
	for range flags {
		if _, err := br.Exec(); err != nil {
			return count, err
		}
		count++
	}
	return count, nil
}

type OrderbookSnapshot struct {
	Time               time.Time
	Coin               string
	BestBid            float64
	BestAsk            float64
	SpreadBps          float64
	BidDepth10Bps      float64
	AskDepth10Bps      float64
	BidDepth50Bps      float64
	AskDepth50Bps      float64
	BidDepth100Bps     float64
	AskDepth100Bps     float64
	BookImbalance50Bps float64
	Raw                json.RawMessage
}

func (s *Store) InsertOrderbookSnapshots(ctx context.Context, rows []OrderbookSnapshot) (int, error) {
	batch := &pgx.Batch{}
	for _, row := range rows {
		raw := row.Raw
		if len(raw) == 0 {
			raw = []byte(`{}`)
		}
		batch.Queue(`INSERT INTO orderbook_snapshots (time, coin, best_bid, best_ask, spread_bps, bid_depth_10bps, ask_depth_10bps, bid_depth_50bps, ask_depth_50bps, bid_depth_100bps, ask_depth_100bps, book_imbalance_50bps, raw)
			VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
			ON CONFLICT (coin, time) DO UPDATE SET best_bid=EXCLUDED.best_bid, best_ask=EXCLUDED.best_ask, spread_bps=EXCLUDED.spread_bps, bid_depth_10bps=EXCLUDED.bid_depth_10bps, ask_depth_10bps=EXCLUDED.ask_depth_10bps, bid_depth_50bps=EXCLUDED.bid_depth_50bps, ask_depth_50bps=EXCLUDED.ask_depth_50bps, bid_depth_100bps=EXCLUDED.bid_depth_100bps, ask_depth_100bps=EXCLUDED.ask_depth_100bps, book_imbalance_50bps=EXCLUDED.book_imbalance_50bps, raw=EXCLUDED.raw`,
			row.Time, row.Coin, row.BestBid, row.BestAsk, row.SpreadBps, row.BidDepth10Bps, row.AskDepth10Bps, row.BidDepth50Bps, row.AskDepth50Bps, row.BidDepth100Bps, row.AskDepth100Bps, row.BookImbalance50Bps, raw)
	}
	br := s.db.SendBatch(ctx, batch)
	defer br.Close()
	count := 0
	for range rows {
		if _, err := br.Exec(); err != nil {
			return count, err
		}
		count++
	}
	return count, nil
}

type RecentTradeSnapshot struct {
	Time               time.Time
	Coin               string
	TradeCount         int
	BuyVolume          float64
	SellVolume         float64
	AggressiveBuyRatio float64
	AvgTradeSize       float64
	LargeTradeCount    int
	Raw                json.RawMessage
}

func (s *Store) InsertRecentTradeSnapshots(ctx context.Context, rows []RecentTradeSnapshot) (int, error) {
	batch := &pgx.Batch{}
	for _, row := range rows {
		raw := row.Raw
		if len(raw) == 0 {
			raw = []byte(`{}`)
		}
		batch.Queue(`INSERT INTO recent_trade_snapshots (time, coin, trade_count, buy_volume, sell_volume, aggressive_buy_ratio, avg_trade_size, large_trade_count, raw)
			VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
			ON CONFLICT (coin, time) DO UPDATE SET trade_count=EXCLUDED.trade_count, buy_volume=EXCLUDED.buy_volume, sell_volume=EXCLUDED.sell_volume, aggressive_buy_ratio=EXCLUDED.aggressive_buy_ratio, avg_trade_size=EXCLUDED.avg_trade_size, large_trade_count=EXCLUDED.large_trade_count, raw=EXCLUDED.raw`,
			row.Time, row.Coin, row.TradeCount, row.BuyVolume, row.SellVolume, row.AggressiveBuyRatio, row.AvgTradeSize, row.LargeTradeCount, raw)
	}
	br := s.db.SendBatch(ctx, batch)
	defer br.Close()
	count := 0
	for range rows {
		if _, err := br.Exec(); err != nil {
			return count, err
		}
		count++
	}
	return count, nil
}

func (s *Store) StartRun(ctx context.Context, job string, metadata any) (string, error) {
	meta, _ := json.Marshal(metadata)
	var id string
	err := s.db.QueryRow(ctx, `INSERT INTO ingestion_runs (job_name, status, metadata) VALUES ($1,'running',$2) RETURNING id`, job, meta).Scan(&id)
	return id, err
}

func (s *Store) FinishRun(ctx context.Context, id string, status string, rows int, errMsg string) error {
	_, err := s.db.Exec(ctx, `UPDATE ingestion_runs SET finished_at=now(), status=$2, rows_written=$3, error_message=$4 WHERE id=$1`, id, status, rows, errMsg)
	return err
}

func (s *Store) TryLock(ctx context.Context, key string, ttl time.Duration) (bool, error) {
	var ok bool
	err := s.db.QueryRow(ctx, `INSERT INTO job_locks (key, locked_until) VALUES ($1, now() + $2::interval)
		ON CONFLICT (key) DO UPDATE SET locked_until=EXCLUDED.locked_until WHERE job_locks.locked_until < now()
		RETURNING true`, key, ttl.String()).Scan(&ok)
	if err == pgx.ErrNoRows {
		return false, nil
	}
	return ok, err
}

func (s *Store) ReleaseLock(ctx context.Context, key string) error {
	_, err := s.db.Exec(ctx, `DELETE FROM job_locks WHERE key=$1`, key)
	return err
}

func (s *Store) DB() *pgxpool.Pool {
	return s.db
}
