package ingest

import (
	"context"
	"log/slog"
	"sync"
	"time"

	"maelstrom/backend/internal/config"
	"maelstrom/backend/internal/features"
	"maelstrom/backend/internal/hyperliquid"
	"maelstrom/backend/internal/limiter"
	"maelstrom/backend/internal/models"
	"maelstrom/backend/internal/store"
)

type Scheduler struct {
	cfg     config.Config
	client  *hyperliquid.Client
	store   *store.Store
	limiter *limiter.Weighted
	logger  *slog.Logger
	wg      sync.WaitGroup
	cancel  context.CancelFunc
	started time.Time
}

func NewScheduler(cfg config.Config, client *hyperliquid.Client, store *store.Store, limiter *limiter.Weighted, logger *slog.Logger) *Scheduler {
	return &Scheduler{cfg: cfg, client: client, store: store, limiter: limiter, logger: logger, started: time.Now().UTC()}
}

func (s *Scheduler) Start(parent context.Context) {
	if !s.cfg.SchedulerEnabled {
		return
	}
	ctx, cancel := context.WithCancel(parent)
	s.cancel = cancel
	s.loop(ctx, "tier1_meta", s.cfg.Tier1MetaInterval, s.ingestMeta)
	s.loop(ctx, "tier1_mids", s.cfg.Tier1MidsInterval, s.ingestMids)
	s.loop(ctx, "candles", 2*time.Minute, s.ingestCandles)
	s.loop(ctx, "features", 3*time.Minute, s.computeFeatures)
	s.loop(ctx, "l2book", s.cfg.L2BookInterval, s.ingestL2Books)
	s.loop(ctx, "recent_trades", s.cfg.RecentTradesInterval, s.ingestRecentTrades)
}

func (s *Scheduler) Stop() {
	if s.cancel != nil {
		s.cancel()
	}
	s.wg.Wait()
}

func (s *Scheduler) Status() map[string]any {
	return map[string]any{"enabled": s.cfg.SchedulerEnabled, "started_at": s.started, "shortlist_size": s.cfg.ShortlistSize}
}

func (s *Scheduler) loop(ctx context.Context, name string, interval time.Duration, fn func(context.Context) (int, error)) {
	s.wg.Add(1)
	go func() {
		defer s.wg.Done()
		ticker := time.NewTicker(interval)
		defer ticker.Stop()
		for {
			rows, err := s.run(ctx, name, fn)
			if err != nil {
				s.logger.Warn("ingestion_job_failed", "job", name, "rows", rows, "error", err)
			}
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
			}
		}
	}()
}

func (s *Scheduler) run(ctx context.Context, name string, fn func(context.Context) (int, error)) (int, error) {
	ok, err := s.store.TryLock(ctx, name, 10*time.Minute)
	if err != nil || !ok {
		return 0, err
	}
	defer func() {
		if err := s.store.ReleaseLock(context.Background(), name); err != nil {
			s.logger.Warn("job_lock_release_failed", "job", name, "error", err)
		}
	}()
	id, err := s.store.StartRun(ctx, name, nil)
	if err != nil {
		return 0, err
	}
	rows, runErr := fn(ctx)
	status := "succeeded"
	errMsg := ""
	if runErr != nil {
		status = "failed"
		errMsg = runErr.Error()
	}
	_ = s.store.FinishRun(ctx, id, status, rows, errMsg)
	return rows, runErr
}

func (s *Scheduler) ingestMeta(ctx context.Context) (int, error) {
	resp, err := s.client.MetaAndAssetCtxs(ctx)
	if err != nil {
		return 0, err
	}
	now := time.Now().UTC()
	markets := make([]models.Market, 0, len(resp.Universe))
	snaps := make([]models.MarketSnapshot, 0, len(resp.Contexts))
	for i, u := range resp.Universe {
		markets = append(markets, models.Market{Coin: u.Name, Name: u.Name, SzDecimals: u.SzDecimals, MaxLeverage: u.MaxLeverage, IsActive: true, RawMeta: store.Raw(u)})
		if i < len(resp.Contexts) {
			c := resp.Contexts[i]
			snaps = append(snaps, models.MarketSnapshot{
				Time: now, Coin: u.Name, Mid: float64(c.MidPx), MarkPx: float64(c.MarkPx), OraclePx: float64(c.OraclePx),
				PrevDayPx: float64(c.PrevDayPx), DayNtlVlm: float64(c.DayNtlVlm), OpenInterest: float64(c.OpenInterest),
				Funding: float64(c.Funding), Premium: float64(c.Premium), RawCtx: store.Raw(c),
			})
		}
	}
	count, err := s.store.UpsertMarkets(ctx, markets)
	if err != nil {
		return count, err
	}
	written, err := s.store.InsertMarketSnapshots(ctx, snaps)
	return count + written, err
}

func (s *Scheduler) ingestMids(ctx context.Context) (int, error) {
	mids, err := s.client.AllMids(ctx)
	if err != nil {
		return 0, err
	}
	now := time.Now().UTC()
	snaps := make([]models.MarketSnapshot, 0, len(mids))
	for coin, mid := range mids {
		snaps = append(snaps, models.MarketSnapshot{Time: now, Coin: coin, Mid: float64(mid)})
	}
	return s.store.InsertMarketSnapshots(ctx, snaps)
}

func (s *Scheduler) ingestCandles(ctx context.Context) (int, error) {
	coins, err := s.store.ActiveCoins(ctx)
	if err != nil || len(coins) == 0 {
		return 0, err
	}
	total := 0
	end := time.Now().UTC()
	start := end.Add(-time.Duration(s.cfg.CandleBackfillDays) * 24 * time.Hour)
	for _, coin := range coins {
		for _, interval := range s.cfg.CandleIntervals {
			candles, err := s.client.CandleSnapshot(ctx, hyperliquid.CandleSnapshotRequest{Coin: coin, Interval: interval, StartTime: start.UnixMilli(), EndTime: end.UnixMilli()})
			if err != nil {
				s.logger.Warn("candle_fetch_failed", "coin", coin, "interval", interval, "error", err)
				continue
			}
			rows := make([]models.Candle, 0, len(candles))
			for _, c := range candles {
				rows = append(rows, models.Candle{Time: time.UnixMilli(c.Time).UTC(), Coin: coin, Interval: interval, Open: float64(c.Open), High: float64(c.High), Low: float64(c.Low), Close: float64(c.Close), Volume: float64(c.Volume), Raw: store.Raw(c)})
			}
			n, err := s.store.UpsertCandles(ctx, rows)
			total += n
			if err != nil {
				return total, err
			}
		}
	}
	return total, nil
}

func (s *Scheduler) computeFeatures(ctx context.Context) (int, error) {
	coins, err := s.store.ActiveCoins(ctx)
	if err != nil {
		return 0, err
	}
	out := []models.Feature{}
	flags := []models.Flag{}
	for _, coin := range coins {
		candles, _ := s.store.Candles(ctx, coin, "1h", time.Now().Add(-8*24*time.Hour), time.Now())
		if len(candles) < 2 {
			continue
		}
		f := features.Calculate(features.Input{Coin: coin, Interval: "1h", Candles: candles, SpreadBps: 2})
		out = append(out, f)
	}
	out = features.NormalizeCrossSection(out)
	for _, f := range out {
		flags = append(flags, features.GenerateFlags(f)...)
	}
	n, err := s.store.UpsertFeatures(ctx, out)
	if err != nil {
		return n, err
	}
	_, _ = s.store.InsertFlags(ctx, flags)
	return n, nil
}

func (s *Scheduler) ingestL2Books(ctx context.Context) (int, error) {
	coins, err := s.store.ShortlistCoins(ctx, s.cfg.ShortlistSize)
	if err != nil {
		return 0, err
	}
	rows := []store.OrderbookSnapshot{}
	for _, coin := range coins {
		book, err := s.client.L2Book(ctx, hyperliquid.L2BookRequest{Coin: coin}, false)
		if err != nil {
			s.logger.Warn("l2book_fetch_deferred_or_failed", "coin", coin, "error", err)
			continue
		}
		rows = append(rows, orderbookSnapshot(coin, book))
	}
	return s.store.InsertOrderbookSnapshots(ctx, rows)
}

func (s *Scheduler) ingestRecentTrades(ctx context.Context) (int, error) {
	coins, err := s.store.ShortlistCoins(ctx, s.cfg.ShortlistSize)
	if err != nil {
		return 0, err
	}
	rows := []store.RecentTradeSnapshot{}
	for _, coin := range coins {
		trades, err := s.client.RecentTrades(ctx, hyperliquid.RecentTradesRequest{Coin: coin}, false)
		if err != nil {
			s.logger.Warn("recent_trades_fetch_deferred_or_failed", "coin", coin, "error", err)
			continue
		}
		rows = append(rows, tradeSnapshot(coin, trades))
	}
	return s.store.InsertRecentTradeSnapshots(ctx, rows)
}

func orderbookSnapshot(coin string, book hyperliquid.L2Book) store.OrderbookSnapshot {
	now := time.Now().UTC()
	if book.Time > 0 {
		now = time.UnixMilli(book.Time).UTC()
	}
	bids, asks := []hyperliquid.BookLevel{}, []hyperliquid.BookLevel{}
	if len(book.Levels) > 0 {
		bids = book.Levels[0]
	}
	if len(book.Levels) > 1 {
		asks = book.Levels[1]
	}
	bestBid, bestAsk := 0.0, 0.0
	if len(bids) > 0 {
		bestBid = float64(bids[0].Px)
	}
	if len(asks) > 0 {
		bestAsk = float64(asks[0].Px)
	}
	mid := (bestBid + bestAsk) / 2
	spread := 0.0
	if mid > 0 {
		spread = (bestAsk - bestBid) / mid * 10000
	}
	bid50, ask50 := depthWithin(bids, mid, 50, true), depthWithin(asks, mid, 50, false)
	imbalance := 0.0
	if bid50+ask50 > 0 {
		imbalance = (bid50 - ask50) / (bid50 + ask50)
	}
	return store.OrderbookSnapshot{
		Time: now, Coin: coin, BestBid: bestBid, BestAsk: bestAsk, SpreadBps: spread,
		BidDepth10Bps: depthWithin(bids, mid, 10, true), AskDepth10Bps: depthWithin(asks, mid, 10, false),
		BidDepth50Bps: bid50, AskDepth50Bps: ask50,
		BidDepth100Bps: depthWithin(bids, mid, 100, true), AskDepth100Bps: depthWithin(asks, mid, 100, false),
		BookImbalance50Bps: imbalance, Raw: store.Raw(book),
	}
}

func depthWithin(levels []hyperliquid.BookLevel, mid float64, bps float64, bid bool) float64 {
	if mid <= 0 {
		return 0
	}
	total := 0.0
	for _, level := range levels {
		px := float64(level.Px)
		distance := (px - mid) / mid * 10000
		if bid {
			distance = -distance
		}
		if distance >= 0 && distance <= bps {
			total += px * float64(level.Sz)
		}
	}
	return total
}

func tradeSnapshot(coin string, trades []hyperliquid.Trade) store.RecentTradeSnapshot {
	now := time.Now().UTC()
	buy, sell, totalSize := 0.0, 0.0, 0.0
	large := 0
	for _, trade := range trades {
		if trade.Time > 0 {
			now = time.UnixMilli(trade.Time).UTC()
		}
		size := float64(trade.Sz)
		totalSize += size
		if trade.Side == "B" || trade.Side == "buy" {
			buy += size
		} else {
			sell += size
		}
		if size > 10000 {
			large++
		}
	}
	avg := 0.0
	if len(trades) > 0 {
		avg = totalSize / float64(len(trades))
	}
	ratio := 0.0
	if buy+sell > 0 {
		ratio = buy / (buy + sell)
	}
	return store.RecentTradeSnapshot{Time: now, Coin: coin, TradeCount: len(trades), BuyVolume: buy, SellVolume: sell, AggressiveBuyRatio: ratio, AvgTradeSize: avg, LargeTradeCount: large, Raw: store.Raw(trades)}
}
