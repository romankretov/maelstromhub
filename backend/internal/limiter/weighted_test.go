package limiter

import (
	"context"
	"log/slog"
	"testing"
	"time"
)

func TestWeightedLimiterDefersNonCriticalWhenBudgetLow(t *testing.T) {
	l := NewWeighted(Config{CapacityPerMinute: 10, EndpointWeights: map[string]int{"x": 9}}, slog.Default())
	if err := l.Wait(context.Background(), "x", 9, true); err != nil {
		t.Fatalf("critical wait: %v", err)
	}
	err := l.Wait(context.Background(), "x", 1, false)
	if err != ErrDeferred {
		t.Fatalf("expected deferred, got %v", err)
	}
}

func TestWeightedLimiterPausesEndpointAfter429(t *testing.T) {
	l := NewWeighted(Config{CapacityPerMinute: 100}, slog.Default())
	l.Record("recentTrades", time.Millisecond, nil, 429)
	metrics := l.Metrics()
	if metrics.Count429 != 1 {
		t.Fatalf("expected 429 count")
	}
	if _, ok := metrics.PausedEndpoints["recentTrades"]; !ok {
		t.Fatalf("expected endpoint pause")
	}
}
