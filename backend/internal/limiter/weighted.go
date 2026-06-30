package limiter

import (
	"context"
	"log/slog"
	"math"
	"math/rand"
	"sync"
	"time"
)

type Config struct {
	CapacityPerMinute int
	EndpointWeights   map[string]int
}

type Metrics struct {
	RequestsByEndpoint map[string]int64   `json:"requests_by_endpoint"`
	FailuresByEndpoint map[string]int64   `json:"failures_by_endpoint"`
	LatencyByEndpoint  map[string]float64 `json:"avg_latency_ms_by_endpoint"`
	Count429           int64              `json:"count_429"`
	CurrentBudget      int                `json:"current_budget"`
	QueueDepth         int                `json:"queue_depth"`
	PausedEndpoints    map[string]string  `json:"paused_endpoints"`
}

type Weighted struct {
	mu           sync.Mutex
	capacity     int
	tokens       float64
	lastRefill   time.Time
	weights      map[string]int
	requests     map[string]int64
	failures     map[string]int64
	latencySumMS map[string]float64
	latencyCount map[string]int64
	pausedUntil  map[string]time.Time
	cooldowns    map[string]time.Duration
	queueDepth   int
	count429     int64
	logger       *slog.Logger
}

func NewWeighted(cfg Config, logger *slog.Logger) *Weighted {
	capacity := cfg.CapacityPerMinute
	if capacity <= 0 {
		capacity = 1200
	}
	return &Weighted{
		capacity:     capacity,
		tokens:       float64(capacity),
		lastRefill:   time.Now(),
		weights:      cfg.EndpointWeights,
		requests:     map[string]int64{},
		failures:     map[string]int64{},
		latencySumMS: map[string]float64{},
		latencyCount: map[string]int64{},
		pausedUntil:  map[string]time.Time{},
		cooldowns:    map[string]time.Duration{},
		logger:       logger,
	}
}

func (l *Weighted) Weight(endpoint string, additional int) int {
	base := l.weights[endpoint]
	if base <= 0 {
		base = 20
	}
	if additional < 0 {
		additional = 0
	}
	return base + additional
}

func (l *Weighted) Wait(ctx context.Context, endpoint string, weight int, critical bool) error {
	if weight <= 0 {
		weight = l.Weight(endpoint, 0)
	}
	if !critical && l.Budget() <= int(math.Ceil(float64(l.capacity)*0.08)) {
		return ErrDeferred
	}
	l.mu.Lock()
	l.queueDepth++
	l.mu.Unlock()
	defer func() {
		l.mu.Lock()
		l.queueDepth--
		l.mu.Unlock()
	}()

	ticker := time.NewTicker(100*time.Millisecond + time.Duration(rand.Intn(80))*time.Millisecond)
	defer ticker.Stop()
	for {
		l.mu.Lock()
		l.refillLocked(time.Now())
		pausedUntil := l.pausedUntil[endpoint]
		if time.Now().Before(pausedUntil) {
			wait := time.Until(pausedUntil)
			l.mu.Unlock()
			if err := sleepContext(ctx, minDuration(wait, time.Second)); err != nil {
				return err
			}
			continue
		}
		if l.tokens >= float64(weight) {
			l.tokens -= float64(weight)
			l.mu.Unlock()
			return nil
		}
		l.mu.Unlock()
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
		}
	}
}

func (l *Weighted) Record(endpoint string, latency time.Duration, err error, statusCode int) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.requests[endpoint]++
	l.latencySumMS[endpoint] += float64(latency.Milliseconds())
	l.latencyCount[endpoint]++
	if err != nil || statusCode >= 400 {
		l.failures[endpoint]++
	}
	if statusCode == 429 {
		l.count429++
		cooldown := l.cooldowns[endpoint]
		if cooldown <= 0 {
			cooldown = 10 * time.Second
		} else {
			cooldown *= 2
			if cooldown > 5*time.Minute {
				cooldown = 5 * time.Minute
			}
		}
		l.cooldowns[endpoint] = cooldown
		l.pausedUntil[endpoint] = time.Now().Add(cooldown)
		l.logger.Warn("hyperliquid_rate_limited", "endpoint", endpoint, "cooldown", cooldown.String())
	}
}

func (l *Weighted) Budget() int {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.refillLocked(time.Now())
	return int(l.tokens)
}

func (l *Weighted) Metrics() Metrics {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.refillLocked(time.Now())
	lat := map[string]float64{}
	for endpoint, sum := range l.latencySumMS {
		count := l.latencyCount[endpoint]
		if count > 0 {
			lat[endpoint] = sum / float64(count)
		}
	}
	paused := map[string]string{}
	now := time.Now()
	for endpoint, until := range l.pausedUntil {
		if now.Before(until) {
			paused[endpoint] = until.Format(time.RFC3339)
		}
	}
	return Metrics{
		RequestsByEndpoint: copyInt64Map(l.requests),
		FailuresByEndpoint: copyInt64Map(l.failures),
		LatencyByEndpoint:  lat,
		Count429:           l.count429,
		CurrentBudget:      int(l.tokens),
		QueueDepth:         l.queueDepth,
		PausedEndpoints:    paused,
	}
}

func (l *Weighted) refillLocked(now time.Time) {
	elapsed := now.Sub(l.lastRefill).Seconds()
	if elapsed <= 0 {
		return
	}
	l.tokens += elapsed * float64(l.capacity) / 60.0
	if l.tokens > float64(l.capacity) {
		l.tokens = float64(l.capacity)
	}
	l.lastRefill = now
}

func copyInt64Map(in map[string]int64) map[string]int64 {
	out := make(map[string]int64, len(in))
	for k, v := range in {
		out[k] = v
	}
	return out
}

func sleepContext(ctx context.Context, d time.Duration) error {
	timer := time.NewTimer(d)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}

func minDuration(a, b time.Duration) time.Duration {
	if a < b {
		return a
	}
	return b
}
