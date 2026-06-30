package models

import (
	"encoding/json"
	"strconv"
	"time"
)

type Decimal float64

func (d *Decimal) UnmarshalJSON(data []byte) error {
	var s string
	if err := json.Unmarshal(data, &s); err == nil {
		if s == "" {
			*d = 0
			return nil
		}
		v, parseErr := strconv.ParseFloat(s, 64)
		if parseErr != nil {
			*d = 0
			return nil
		}
		*d = Decimal(v)
		return nil
	}
	var f float64
	if err := json.Unmarshal(data, &f); err != nil {
		*d = 0
		return nil
	}
	*d = Decimal(f)
	return nil
}

type Market struct {
	Coin        string          `json:"coin"`
	Name        string          `json:"name"`
	SzDecimals  int             `json:"sz_decimals"`
	MaxLeverage int             `json:"max_leverage"`
	IsActive    bool            `json:"is_active"`
	RawMeta     json.RawMessage `json:"raw_meta,omitempty"`
}

type MarketSnapshot struct {
	Time         time.Time       `json:"time"`
	Coin         string          `json:"coin"`
	Mid          float64         `json:"mid"`
	MarkPx       float64         `json:"mark_px"`
	OraclePx     float64         `json:"oracle_px"`
	PrevDayPx    float64         `json:"prev_day_px"`
	DayNtlVlm    float64         `json:"day_ntl_vlm"`
	OpenInterest float64         `json:"open_interest"`
	Funding      float64         `json:"funding"`
	Premium      float64         `json:"premium"`
	RawCtx       json.RawMessage `json:"raw_ctx,omitempty"`
}

type Candle struct {
	Time     time.Time       `json:"time"`
	Coin     string          `json:"coin"`
	Interval string          `json:"interval"`
	Open     float64         `json:"open"`
	High     float64         `json:"high"`
	Low      float64         `json:"low"`
	Close    float64         `json:"close"`
	Volume   float64         `json:"volume"`
	Raw      json.RawMessage `json:"raw,omitempty"`
}

type Feature struct {
	Time                  time.Time `json:"time"`
	Coin                  string    `json:"coin"`
	Interval              string    `json:"interval"`
	Return1H              float64   `json:"return_1h"`
	Return4H              float64   `json:"return_4h"`
	Return24H             float64   `json:"return_24h"`
	VolumeVs7DAvg         float64   `json:"volume_vs_7d_avg"`
	VolumeZScore          float64   `json:"volume_zscore"`
	OIChange1H            float64   `json:"oi_change_1h"`
	OIChange4H            float64   `json:"oi_change_4h"`
	OIChange24H           float64   `json:"oi_change_24h"`
	FundingZScore         float64   `json:"funding_zscore"`
	RealizedVol           float64   `json:"realized_vol"`
	ATR                   float64   `json:"atr"`
	ADX                   float64   `json:"adx"`
	RelativeStrengthRank  float64   `json:"relative_strength_rank"`
	Autocorr1             float64   `json:"autocorr_1"`
	HurstEstimate         float64   `json:"hurst_estimate"`
	SpreadBps             float64   `json:"spread_bps"`
	LiquidityScore        float64   `json:"liquidity_score"`
	OIAnomalyScore        float64   `json:"oi_anomaly_score"`
	VolumeAnomalyScore    float64   `json:"volume_anomaly_score"`
	MomentumScore         float64   `json:"momentum_score"`
	FundingAnomalyScore   float64   `json:"funding_anomaly_score"`
	ExecutionQualityScore float64   `json:"execution_quality_score"`
	ResearchScore         float64   `json:"research_score"`
	RegimeLabel           string    `json:"regime_label"`
	UpdatedAt             time.Time `json:"updated_at"`
}

type Flag struct {
	ID       int64           `json:"id"`
	Time     time.Time       `json:"time"`
	Coin     string          `json:"coin"`
	FlagType string          `json:"flag_type"`
	Severity string          `json:"severity"`
	Message  string          `json:"message"`
	Metadata json.RawMessage `json:"metadata,omitempty"`
}

type MarketRow struct {
	Coin                 string  `json:"coin"`
	Price                float64 `json:"price"`
	Return24H            float64 `json:"return_24h"`
	Volume24H            float64 `json:"volume_24h"`
	VolumeVs7DAvg        float64 `json:"volume_vs_7d_avg"`
	OpenInterest         float64 `json:"open_interest"`
	OIChange1H           float64 `json:"oi_change_1h"`
	OIChange4H           float64 `json:"oi_change_4h"`
	OIChange24H          float64 `json:"oi_change_24h"`
	Funding              float64 `json:"funding"`
	FundingZScore        float64 `json:"funding_zscore"`
	RealizedVol          float64 `json:"realized_vol"`
	ADX                  float64 `json:"adx"`
	RelativeStrengthRank float64 `json:"relative_strength_rank"`
	SpreadBps            float64 `json:"spread_bps"`
	ResearchScore        float64 `json:"research_score"`
	RegimeLabel          string  `json:"regime_label"`
	TopFlags             []Flag  `json:"top_flags"`
}
