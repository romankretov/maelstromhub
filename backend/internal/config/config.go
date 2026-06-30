package config

import (
	"log/slog"
	"os"
	"strconv"
	"strings"
	"time"
)

type Config struct {
	HTTPAddr                 string
	HyperliquidBaseURL       string
	PostgresDSN              string
	RedisURL                 string
	RateLimitWeightPerMinute int
	EndpointWeights          map[string]int
	Tier1MetaInterval        time.Duration
	Tier1MidsInterval        time.Duration
	CandleIntervals          []string
	CandleBackfillDays       int
	ShortlistSize            int
	L2BookInterval           time.Duration
	RecentTradesInterval     time.Duration
	SchedulerEnabled         bool
	HTTPTimeout              time.Duration
	LogLevel                 slog.Level
}

func Load() Config {
	return Config{
		HTTPAddr:                 env("HTTP_ADDR", ":8080"),
		HyperliquidBaseURL:       env("HYPERLIQUID_BASE_URL", "https://api.hyperliquid.xyz"),
		PostgresDSN:              env("POSTGRES_DSN", "postgres://maelstrom:maelstrom@postgres:5432/maelstrom?sslmode=disable"),
		RedisURL:                 env("REDIS_URL", "redis://redis:6379/0"),
		RateLimitWeightPerMinute: envInt("RATE_LIMIT_WEIGHT_PER_MINUTE", 1200),
		EndpointWeights:          parseWeights(env("ENDPOINT_WEIGHTS", "metaAndAssetCtxs=20,allMids=2,candleSnapshot=20,l2Book=2,recentTrades=20,fundingHistory=20")),
		Tier1MetaInterval:        time.Duration(envInt("TIER1_META_INTERVAL_SECONDS", 45)) * time.Second,
		Tier1MidsInterval:        time.Duration(envInt("TIER1_MIDS_INTERVAL_SECONDS", 20)) * time.Second,
		CandleIntervals:          split(env("CANDLE_INTERVALS", "1m,5m,15m,1h")),
		CandleBackfillDays:       envInt("CANDLE_BACKFILL_DAYS", 14),
		ShortlistSize:            envInt("SHORTLIST_SIZE", 20),
		L2BookInterval:           time.Duration(envInt("L2BOOK_INTERVAL_SECONDS", 60)) * time.Second,
		RecentTradesInterval:     time.Duration(envInt("RECENT_TRADES_INTERVAL_SECONDS", 60)) * time.Second,
		SchedulerEnabled:         envBool("SCHEDULER_ENABLED", true),
		HTTPTimeout:              time.Duration(envInt("HTTP_TIMEOUT_SECONDS", 12)) * time.Second,
		LogLevel:                 parseLevel(env("LOG_LEVEL", "info")),
	}
}

func env(key, fallback string) string {
	if value := strings.TrimSpace(os.Getenv(key)); value != "" {
		return value
	}
	return fallback
}

func envInt(key string, fallback int) int {
	value, err := strconv.Atoi(env(key, ""))
	if err != nil {
		return fallback
	}
	return value
}

func envBool(key string, fallback bool) bool {
	value := strings.ToLower(env(key, ""))
	if value == "" {
		return fallback
	}
	return value == "1" || value == "true" || value == "yes"
}

func split(value string) []string {
	parts := strings.Split(value, ",")
	out := make([]string, 0, len(parts))
	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part != "" {
			out = append(out, part)
		}
	}
	return out
}

func parseWeights(value string) map[string]int {
	weights := map[string]int{}
	for _, pair := range split(value) {
		key, raw, ok := strings.Cut(pair, "=")
		if !ok {
			continue
		}
		weight, err := strconv.Atoi(strings.TrimSpace(raw))
		if err == nil && weight > 0 {
			weights[strings.TrimSpace(key)] = weight
		}
	}
	return weights
}

func parseLevel(value string) slog.Level {
	switch strings.ToLower(value) {
	case "debug":
		return slog.LevelDebug
	case "warn":
		return slog.LevelWarn
	case "error":
		return slog.LevelError
	default:
		return slog.LevelInfo
	}
}
