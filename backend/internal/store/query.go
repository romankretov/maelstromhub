package store

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"

	"maelstrom/backend/internal/models"
)

type MarketQuery struct {
	Sort             string
	Direction        string
	MinVolume        float64
	MinResearchScore float64
	Regime           string
	Limit            int
	Offset           int
}

type MarketDetail struct {
	LatestSnapshot             *models.MarketSnapshot `json:"latest_snapshot"`
	LatestFeatures             *models.Feature        `json:"latest_features"`
	RecentFlags                []models.Flag          `json:"recent_flags"`
	RecentCandles              []models.Candle        `json:"recent_candles"`
	FundingHistorySummary      map[string]float64     `json:"funding_history_summary"`
	OrderbookSummary           map[string]float64     `json:"orderbook_summary"`
	TradeSummary               map[string]float64     `json:"trade_summary"`
	SuggestedResearchDirection string                 `json:"suggested_research_direction"`
}

func (s *Store) ListMarkets(ctx context.Context, q MarketQuery) ([]models.MarketRow, error) {
	limit := q.Limit
	if limit <= 0 || limit > 200 {
		limit = 50
	}
	sortKey := map[string]string{
		"coin":           "m.coin",
		"price":          "ms.mid",
		"volume":         "ms.day_ntl_vlm",
		"research_score": "f.research_score",
		"funding":        "ms.funding",
		"adx":            "f.adx",
	}[q.Sort]
	if sortKey == "" {
		sortKey = "f.research_score"
	}
	dir := "DESC"
	if strings.EqualFold(q.Direction, "asc") {
		dir = "ASC"
	}
	args := []any{q.MinVolume, q.MinResearchScore, q.Regime, limit, q.Offset}
	rows, err := s.db.Query(ctx, fmt.Sprintf(`
		WITH latest_snap AS (
			SELECT DISTINCT ON (coin) * FROM market_snapshots ORDER BY coin, time DESC
		), latest_feat AS (
			SELECT DISTINCT ON (coin) * FROM features ORDER BY coin, time DESC
		)
		SELECT m.coin, coalesce(ms.mid, ms.mark_px, 0), coalesce(f.return_24h,0), coalesce(ms.day_ntl_vlm,0), coalesce(f.volume_vs_7d_avg,0),
		       coalesce(ms.open_interest,0), coalesce(f.oi_change_1h,0), coalesce(f.oi_change_4h,0), coalesce(f.oi_change_24h,0),
		       coalesce(ms.funding,0), coalesce(f.funding_zscore,0), coalesce(f.realized_vol,0), coalesce(f.adx,0),
		       coalesce(f.relative_strength_rank,0), coalesce(f.spread_bps,0), coalesce(f.research_score,0), coalesce(f.regime_label,'')
		FROM markets m
		LEFT JOIN latest_snap ms ON ms.coin=m.coin
		LEFT JOIN latest_feat f ON f.coin=m.coin
		WHERE ($1::numeric = 0 OR coalesce(ms.day_ntl_vlm,0) >= $1)
		  AND ($2::numeric = 0 OR coalesce(f.research_score,0) >= $2)
		  AND ($3::text = '' OR coalesce(f.regime_label,'') = $3)
		ORDER BY %s %s NULLS LAST
		LIMIT $4 OFFSET $5`, sortKey, dir), args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []models.MarketRow{}
	for rows.Next() {
		var r models.MarketRow
		if err := rows.Scan(&r.Coin, &r.Price, &r.Return24H, &r.Volume24H, &r.VolumeVs7DAvg, &r.OpenInterest, &r.OIChange1H, &r.OIChange4H, &r.OIChange24H, &r.Funding, &r.FundingZScore, &r.RealizedVol, &r.ADX, &r.RelativeStrengthRank, &r.SpreadBps, &r.ResearchScore, &r.RegimeLabel); err != nil {
			return nil, err
		}
		r.TopFlags, _ = s.ListFlags(ctx, r.Coin, 3)
		out = append(out, r)
	}
	return out, rows.Err()
}

func (s *Store) MarketDetail(ctx context.Context, coin string) (MarketDetail, error) {
	var detail MarketDetail
	snap, _ := s.LatestSnapshot(ctx, coin)
	feat, _ := s.LatestFeature(ctx, coin)
	candles, _ := s.Candles(ctx, coin, "1h", time.Now().Add(-7*24*time.Hour), time.Now())
	flags, _ := s.ListFlags(ctx, coin, 20)
	detail.LatestSnapshot = snap
	detail.LatestFeatures = feat
	detail.RecentCandles = candles
	detail.RecentFlags = flags
	detail.FundingHistorySummary = map[string]float64{}
	detail.OrderbookSummary = map[string]float64{}
	detail.TradeSummary = map[string]float64{}
	if feat != nil {
		detail.SuggestedResearchDirection = SuggestDirection(*feat)
	}
	return detail, nil
}

func (s *Store) LatestSnapshot(ctx context.Context, coin string) (*models.MarketSnapshot, error) {
	var m models.MarketSnapshot
	err := s.db.QueryRow(ctx, `SELECT time, coin, coalesce(mid,0), coalesce(mark_px,0), coalesce(oracle_px,0), coalesce(prev_day_px,0), coalesce(day_ntl_vlm,0), coalesce(open_interest,0), coalesce(funding,0), coalesce(premium,0), raw_ctx FROM market_snapshots WHERE coin=$1 ORDER BY time DESC LIMIT 1`, coin).
		Scan(&m.Time, &m.Coin, &m.Mid, &m.MarkPx, &m.OraclePx, &m.PrevDayPx, &m.DayNtlVlm, &m.OpenInterest, &m.Funding, &m.Premium, &m.RawCtx)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	return &m, err
}

func (s *Store) LatestFeature(ctx context.Context, coin string) (*models.Feature, error) {
	var f models.Feature
	err := s.db.QueryRow(ctx, `SELECT time, coin, interval, coalesce(return_1h,0), coalesce(return_4h,0), coalesce(return_24h,0), coalesce(volume_vs_7d_avg,0), coalesce(volume_zscore,0), coalesce(oi_change_1h,0), coalesce(oi_change_4h,0), coalesce(oi_change_24h,0), coalesce(funding_zscore,0), coalesce(realized_vol,0), coalesce(atr,0), coalesce(adx,0), coalesce(relative_strength_rank,0), coalesce(autocorr_1,0), coalesce(hurst_estimate,0), coalesce(spread_bps,0), coalesce(liquidity_score,0), coalesce(oi_anomaly_score,0), coalesce(volume_anomaly_score,0), coalesce(momentum_score,0), coalesce(funding_anomaly_score,0), coalesce(execution_quality_score,0), coalesce(research_score,0), coalesce(regime_label,''), updated_at FROM features WHERE coin=$1 ORDER BY time DESC LIMIT 1`, coin).
		Scan(&f.Time, &f.Coin, &f.Interval, &f.Return1H, &f.Return4H, &f.Return24H, &f.VolumeVs7DAvg, &f.VolumeZScore, &f.OIChange1H, &f.OIChange4H, &f.OIChange24H, &f.FundingZScore, &f.RealizedVol, &f.ATR, &f.ADX, &f.RelativeStrengthRank, &f.Autocorr1, &f.HurstEstimate, &f.SpreadBps, &f.LiquidityScore, &f.OIAnomalyScore, &f.VolumeAnomalyScore, &f.MomentumScore, &f.FundingAnomalyScore, &f.ExecutionQualityScore, &f.ResearchScore, &f.RegimeLabel, &f.UpdatedAt)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	return &f, err
}

func (s *Store) Candles(ctx context.Context, coin, interval string, from, to time.Time) ([]models.Candle, error) {
	rows, err := s.db.Query(ctx, `SELECT time, coin, interval, open, high, low, close, volume, raw FROM candles WHERE coin=$1 AND interval=$2 AND time >= $3 AND time <= $4 ORDER BY time ASC`, coin, interval, from, to)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []models.Candle{}
	for rows.Next() {
		var c models.Candle
		if err := rows.Scan(&c.Time, &c.Coin, &c.Interval, &c.Open, &c.High, &c.Low, &c.Close, &c.Volume, &c.Raw); err != nil {
			return nil, err
		}
		out = append(out, c)
	}
	return out, rows.Err()
}

func (s *Store) ListFlags(ctx context.Context, coin string, limit int) ([]models.Flag, error) {
	if limit <= 0 {
		limit = 50
	}
	query := `SELECT id, time, coin, flag_type, severity, message, metadata FROM flags`
	args := []any{}
	if coin != "" {
		query += ` WHERE coin=$1`
		args = append(args, coin)
	}
	query += ` ORDER BY time DESC LIMIT `
	args = append(args, limit)
	query += fmt.Sprintf("$%d", len(args))
	rows, err := s.db.Query(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []models.Flag{}
	for rows.Next() {
		var f models.Flag
		if err := rows.Scan(&f.ID, &f.Time, &f.Coin, &f.FlagType, &f.Severity, &f.Message, &f.Metadata); err != nil {
			return nil, err
		}
		out = append(out, f)
	}
	return out, rows.Err()
}

func (s *Store) LatestRuns(ctx context.Context) ([]map[string]any, error) {
	rows, err := s.db.Query(ctx, `SELECT DISTINCT ON (job_name) job_name, started_at, finished_at, status, rows_written, coalesce(error_message,'') FROM ingestion_runs ORDER BY job_name, started_at DESC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []map[string]any{}
	for rows.Next() {
		var job, status, errorMessage string
		var started time.Time
		var finished *time.Time
		var rowsWritten int
		if err := rows.Scan(&job, &started, &finished, &status, &rowsWritten, &errorMessage); err != nil {
			return nil, err
		}
		out = append(out, map[string]any{"job_name": job, "started_at": started, "finished_at": finished, "status": status, "rows_written": rowsWritten, "error_message": errorMessage})
	}
	return out, rows.Err()
}

func (s *Store) ActiveCoins(ctx context.Context) ([]string, error) {
	rows, err := s.db.Query(ctx, `WITH latest AS (
		SELECT DISTINCT ON (coin) coin, coalesce(day_ntl_vlm, 0) AS day_ntl_vlm
		FROM market_snapshots
		ORDER BY coin, time DESC
	)
	SELECT m.coin
	FROM markets m
	LEFT JOIN latest l ON l.coin=m.coin
	WHERE m.is_active
	ORDER BY coalesce(l.day_ntl_vlm, 0) DESC, m.coin`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []string{}
	for rows.Next() {
		var coin string
		if err := rows.Scan(&coin); err != nil {
			return nil, err
		}
		out = append(out, coin)
	}
	return out, rows.Err()
}

func (s *Store) ShortlistCoins(ctx context.Context, limit int) ([]string, error) {
	if limit <= 0 {
		limit = 20
	}
	rows, err := s.db.Query(ctx, `SELECT m.coin FROM markets m LEFT JOIN (SELECT DISTINCT ON (coin) coin, research_score FROM features ORDER BY coin, time DESC) f ON f.coin=m.coin WHERE m.is_active ORDER BY coalesce(f.research_score,0) DESC, m.coin ASC LIMIT $1`, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []string{}
	for rows.Next() {
		var coin string
		if err := rows.Scan(&coin); err != nil {
			return nil, err
		}
		out = append(out, coin)
	}
	return out, rows.Err()
}

func SuggestDirection(f models.Feature) string {
	if f.ExecutionQualityScore < 25 || f.SpreadBps > 15 {
		return "Ignore for now: execution quality poor"
	}
	if f.ADX > 20 && f.OIChange24H > 0.05 && abs(f.FundingZScore) < 1 {
		return "Research trend continuation / breakout"
	}
	if f.FundingZScore > 2 && f.Return24H > 0.05 && f.OIChange24H > 0.05 {
		return "Research crowded long / mean reversion"
	}
	if f.RealizedVol < 0.02 && f.VolumeZScore > 0.8 {
		return "Research volatility breakout"
	}
	if f.FundingZScore < -1 && f.Return24H >= 0 && f.OIChange24H > 0.03 {
		return "Research short squeeze"
	}
	return "Research watchlist candidate; inspect chart structure and liquidity before deeper work"
}

func Raw(v any) json.RawMessage {
	data, _ := json.Marshal(v)
	return data
}

func abs(v float64) float64 {
	if v < 0 {
		return -v
	}
	return v
}
