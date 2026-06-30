package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"maelstrom/backend/internal/api"
	"maelstrom/backend/internal/config"
	"maelstrom/backend/internal/db"
	"maelstrom/backend/internal/hyperliquid"
	"maelstrom/backend/internal/ingest"
	"maelstrom/backend/internal/limiter"
	"maelstrom/backend/internal/store"
)

func main() {
	cfg := config.Load()
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: cfg.LogLevel}))
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	pool, err := db.Open(ctx, cfg.PostgresDSN)
	if err != nil {
		logger.Error("db_open_failed", "error", err)
		os.Exit(1)
	}
	defer pool.Close()
	if err := db.Migrate(ctx, pool, os.Getenv("MIGRATIONS_DIR")); err != nil {
		logger.Error("db_migration_failed", "error", err)
		os.Exit(1)
	}

	cache := db.OpenRedis(cfg.RedisURL)
	defer cache.Close()

	queries := store.New(pool, cache, logger)
	rateLimiter := limiter.NewWeighted(limiter.Config{
		CapacityPerMinute: cfg.RateLimitWeightPerMinute,
		EndpointWeights:   cfg.EndpointWeights,
	}, logger)
	client := hyperliquid.NewClient(hyperliquid.Config{
		BaseURL: cfg.HyperliquidBaseURL,
		Timeout: cfg.HTTPTimeout,
	}, rateLimiter, logger)

	scheduler := ingest.NewScheduler(cfg, client, queries, rateLimiter, logger)
	scheduler.Start(ctx)

	handler := api.New(api.Dependencies{
		Config:    cfg,
		Store:     queries,
		Client:    client,
		Limiter:   rateLimiter,
		Scheduler: scheduler,
		Logger:    logger,
		StartedAt: time.Now().UTC(),
	})
	server := &http.Server{
		Addr:              cfg.HTTPAddr,
		Handler:           handler,
		ReadHeaderTimeout: 5 * time.Second,
	}

	go func() {
		logger.Info("server_started", "addr", cfg.HTTPAddr)
		if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Error("server_failed", "error", err)
			stop()
		}
	}()

	<-ctx.Done()
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	logger.Info("server_stopping")
	_ = server.Shutdown(shutdownCtx)
	scheduler.Stop()
}
