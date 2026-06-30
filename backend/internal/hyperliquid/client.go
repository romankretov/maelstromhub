package hyperliquid

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"math/rand"
	"net/http"
	"strings"
	"time"

	"maelstrom/backend/internal/models"
)

type RateLimiter interface {
	Wait(ctx context.Context, endpoint string, weight int, critical bool) error
	Weight(endpoint string, additional int) int
	Record(endpoint string, latency time.Duration, err error, statusCode int)
}

type Config struct {
	BaseURL string
	Timeout time.Duration
}

type Client struct {
	baseURL string
	http    *http.Client
	limiter RateLimiter
	logger  *slog.Logger
}

func NewClient(cfg Config, limiter RateLimiter, logger *slog.Logger) *Client {
	timeout := cfg.Timeout
	if timeout <= 0 {
		timeout = 12 * time.Second
	}
	return &Client{
		baseURL: strings.TrimRight(cfg.BaseURL, "/"),
		http:    &http.Client{Timeout: timeout},
		limiter: limiter,
		logger:  logger,
	}
}

type UniverseItem struct {
	Name        string          `json:"name"`
	SzDecimals  int             `json:"szDecimals"`
	MaxLeverage int             `json:"maxLeverage"`
	Raw         json.RawMessage `json:"-"`
}

type AssetCtx struct {
	DayNtlVlm    models.Decimal  `json:"dayNtlVlm"`
	Funding      models.Decimal  `json:"funding"`
	MarkPx       models.Decimal  `json:"markPx"`
	MidPx        models.Decimal  `json:"midPx"`
	OpenInterest models.Decimal  `json:"openInterest"`
	OraclePx     models.Decimal  `json:"oraclePx"`
	Premium      models.Decimal  `json:"premium"`
	PrevDayPx    models.Decimal  `json:"prevDayPx"`
	Raw          json.RawMessage `json:"-"`
}

type MetaAndAssetCtxs struct {
	Universe []UniverseItem
	Contexts []AssetCtx
}

type CandleSnapshotRequest struct {
	Coin      string `json:"coin"`
	Interval  string `json:"interval"`
	StartTime int64  `json:"startTime"`
	EndTime   int64  `json:"endTime"`
}

type Candle struct {
	Time   int64          `json:"t"`
	CloseT int64          `json:"T"`
	Symbol string         `json:"s"`
	Open   models.Decimal `json:"o"`
	High   models.Decimal `json:"h"`
	Low    models.Decimal `json:"l"`
	Close  models.Decimal `json:"c"`
	Volume models.Decimal `json:"v"`
}

type L2BookRequest struct {
	Coin string `json:"coin"`
}

type L2Book struct {
	Coin   string        `json:"coin"`
	Levels [][]BookLevel `json:"levels"`
	Time   int64         `json:"time"`
}

type BookLevel struct {
	Px models.Decimal `json:"px"`
	Sz models.Decimal `json:"sz"`
	N  int            `json:"n"`
}

type RecentTradesRequest struct {
	Coin string `json:"coin"`
}

type Trade struct {
	Coin string         `json:"coin"`
	Side string         `json:"side"`
	Px   models.Decimal `json:"px"`
	Sz   models.Decimal `json:"sz"`
	Time int64          `json:"time"`
	Hash string         `json:"hash"`
}

type FundingHistoryRequest struct {
	Coin      string `json:"coin"`
	StartTime int64  `json:"startTime"`
	EndTime   int64  `json:"endTime,omitempty"`
}

type FundingRecord struct {
	Coin        string         `json:"coin"`
	FundingRate models.Decimal `json:"fundingRate"`
	Premium     models.Decimal `json:"premium"`
	Time        int64          `json:"time"`
}

func (c *Client) MetaAndAssetCtxs(ctx context.Context) (MetaAndAssetCtxs, error) {
	var raw []json.RawMessage
	if err := c.info(ctx, "metaAndAssetCtxs", map[string]string{"type": "metaAndAssetCtxs"}, &raw, true, 0); err != nil {
		return MetaAndAssetCtxs{}, err
	}
	if len(raw) != 2 {
		return MetaAndAssetCtxs{}, fmt.Errorf("hyperliquid malformed metaAndAssetCtxs response: expected 2 items, got %d", len(raw))
	}
	var meta struct {
		Universe []UniverseItem `json:"universe"`
	}
	if err := json.Unmarshal(raw[0], &meta); err != nil {
		return MetaAndAssetCtxs{}, fmt.Errorf("decode meta: %w", err)
	}
	var ctxs []AssetCtx
	if err := json.Unmarshal(raw[1], &ctxs); err != nil {
		return MetaAndAssetCtxs{}, fmt.Errorf("decode asset contexts: %w", err)
	}
	return MetaAndAssetCtxs{Universe: meta.Universe, Contexts: ctxs}, nil
}

func (c *Client) AllMids(ctx context.Context) (map[string]models.Decimal, error) {
	var mids map[string]models.Decimal
	err := c.info(ctx, "allMids", map[string]string{"type": "allMids"}, &mids, true, 0)
	if mids == nil {
		mids = map[string]models.Decimal{}
	}
	return mids, err
}

func (c *Client) CandleSnapshot(ctx context.Context, req CandleSnapshotRequest) ([]Candle, error) {
	var out []Candle
	body := map[string]any{"type": "candleSnapshot", "req": req}
	err := c.info(ctx, "candleSnapshot", body, &out, true, dynamicWeightFromWindow(req.StartTime, req.EndTime))
	return out, err
}

func (c *Client) L2Book(ctx context.Context, req L2BookRequest, critical bool) (L2Book, error) {
	var out L2Book
	err := c.info(ctx, "l2Book", map[string]any{"type": "l2Book", "coin": req.Coin}, &out, critical, 0)
	return out, err
}

func (c *Client) RecentTrades(ctx context.Context, req RecentTradesRequest, critical bool) ([]Trade, error) {
	var out []Trade
	err := c.info(ctx, "recentTrades", map[string]any{"type": "recentTrades", "coin": req.Coin}, &out, critical, 1)
	return out, err
}

func (c *Client) FundingHistory(ctx context.Context, req FundingHistoryRequest, critical bool) ([]FundingRecord, error) {
	var out []FundingRecord
	body := map[string]any{"type": "fundingHistory", "coin": req.Coin, "startTime": req.StartTime}
	if req.EndTime > 0 {
		body["endTime"] = req.EndTime
	}
	err := c.info(ctx, "fundingHistory", body, &out, critical, dynamicWeightFromWindow(req.StartTime, req.EndTime))
	return out, err
}

func (c *Client) Ping(ctx context.Context) error {
	_, err := c.AllMids(ctx)
	return err
}

func (c *Client) info(ctx context.Context, endpoint string, payload any, out any, critical bool, additionalWeight int) error {
	weight := c.limiter.Weight(endpoint, additionalWeight)
	if err := c.limiter.Wait(ctx, endpoint, weight, critical); err != nil {
		return err
	}
	var lastErr error
	for attempt := 0; attempt < 4; attempt++ {
		start := time.Now()
		status, err := c.doInfo(ctx, payload, out)
		c.limiter.Record(endpoint, time.Since(start), err, status)
		if err == nil {
			c.logger.Debug("hyperliquid_request_ok", "endpoint", endpoint, "status", status, "weight", weight, "latency_ms", time.Since(start).Milliseconds())
			return nil
		}
		lastErr = err
		if status == 429 || status >= 500 || errors.Is(err, context.DeadlineExceeded) {
			delay := time.Duration(150*(1<<attempt))*time.Millisecond + time.Duration(rand.Intn(100))*time.Millisecond
			if sleepErr := sleep(ctx, delay); sleepErr != nil {
				return sleepErr
			}
			continue
		}
		break
	}
	return lastErr
}

func (c *Client) doInfo(ctx context.Context, payload any, out any) (int, error) {
	body, err := json.Marshal(payload)
	if err != nil {
		return 0, err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/info", bytes.NewReader(body))
	if err != nil {
		return 0, err
	}
	req.Header.Set("content-type", "application/json")
	res, err := c.http.Do(req)
	if err != nil {
		return 0, err
	}
	defer res.Body.Close()
	data, readErr := io.ReadAll(io.LimitReader(res.Body, 32<<20))
	if readErr != nil {
		return res.StatusCode, readErr
	}
	if res.StatusCode >= 400 {
		return res.StatusCode, fmt.Errorf("hyperliquid status %d: %s", res.StatusCode, string(data))
	}
	if len(data) == 0 {
		return res.StatusCode, errors.New("hyperliquid empty response")
	}
	if err := json.Unmarshal(data, out); err != nil {
		return res.StatusCode, fmt.Errorf("hyperliquid malformed response: %w", err)
	}
	return res.StatusCode, nil
}

func dynamicWeightFromWindow(start, end int64) int {
	if start <= 0 || end <= start {
		return 0
	}
	days := (end - start) / int64(24*time.Hour/time.Millisecond)
	if days <= 1 {
		return 0
	}
	if days > 30 {
		return 10
	}
	return int(days / 3)
}

func sleep(ctx context.Context, d time.Duration) error {
	timer := time.NewTimer(d)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}
