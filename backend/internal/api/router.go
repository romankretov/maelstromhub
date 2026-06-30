package api

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"strconv"
	"strings"
	"time"

	"maelstrom/backend/internal/config"
	"maelstrom/backend/internal/hyperliquid"
	"maelstrom/backend/internal/ingest"
	"maelstrom/backend/internal/limiter"
	"maelstrom/backend/internal/store"
)

type Dependencies struct {
	Config    config.Config
	Store     *store.Store
	Client    *hyperliquid.Client
	Limiter   *limiter.Weighted
	Scheduler *ingest.Scheduler
	Logger    *slog.Logger
	StartedAt time.Time
}

type Router struct {
	deps Dependencies
	mux  *http.ServeMux
}

func New(deps Dependencies) http.Handler {
	r := &Router{deps: deps, mux: http.NewServeMux()}
	r.routes()
	return cors(logging(r.mux, deps.Logger))
}

func (r *Router) routes() {
	r.mux.HandleFunc("GET /health", r.health)
	r.mux.HandleFunc("GET /api/markets", r.markets)
	r.mux.HandleFunc("GET /api/markets/{coin}", r.marketDetail)
	r.mux.HandleFunc("GET /api/markets/{coin}/candles", r.candles)
	r.mux.HandleFunc("GET /api/flags", r.flags)
	r.mux.HandleFunc("GET /api/ingestion/status", r.ingestionStatus)
	r.mux.HandleFunc("GET /metrics", r.metrics)
}

func (r *Router) health(w http.ResponseWriter, req *http.Request) {
	ctx, cancel := context.WithTimeout(req.Context(), 3*time.Second)
	defer cancel()
	dbStatus := "ok"
	if err := r.deps.Store.PingDB(ctx); err != nil {
		dbStatus = "error"
	}
	redisStatus := "ok"
	if err := r.deps.Store.PingRedis(ctx); err != nil {
		redisStatus = "error"
	}
	hlStatus := "ok"
	if err := r.deps.Client.Ping(ctx); err != nil {
		hlStatus = "stale_or_unavailable"
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"status":       overall(dbStatus, redisStatus),
		"db":           dbStatus,
		"redis":        redisStatus,
		"hyperliquid":  hlStatus,
		"scheduler":    r.deps.Scheduler.Status(),
		"started_at":   r.deps.StartedAt,
		"rate_limiter": r.deps.Limiter.Metrics(),
	})
}

func (r *Router) markets(w http.ResponseWriter, req *http.Request) {
	q := req.URL.Query()
	rows, err := r.deps.Store.ListMarkets(req.Context(), store.MarketQuery{
		Sort:             q.Get("sort"),
		Direction:        q.Get("direction"),
		MinVolume:        floatParam(q.Get("min_volume")),
		MinResearchScore: floatParam(q.Get("min_research_score")),
		Regime:           q.Get("regime"),
		Limit:            intParam(q.Get("limit"), 50),
		Offset:           intParam(q.Get("offset"), 0),
	})
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"markets": rows})
}

func (r *Router) marketDetail(w http.ResponseWriter, req *http.Request) {
	coin := strings.ToUpper(req.PathValue("coin"))
	if coin == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "coin is required"})
		return
	}
	detail, err := r.deps.Store.MarketDetail(req.Context(), coin)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, detail)
}

func (r *Router) candles(w http.ResponseWriter, req *http.Request) {
	q := req.URL.Query()
	interval := q.Get("interval")
	if interval == "" {
		interval = "5m"
	}
	from := time.Now().Add(-7 * 24 * time.Hour)
	to := time.Now()
	if raw := q.Get("from"); raw != "" {
		if parsed, err := time.Parse(time.RFC3339, raw); err == nil {
			from = parsed
		}
	}
	if raw := q.Get("to"); raw != "" {
		if parsed, err := time.Parse(time.RFC3339, raw); err == nil {
			to = parsed
		}
	}
	rows, err := r.deps.Store.Candles(req.Context(), strings.ToUpper(req.PathValue("coin")), interval, from, to)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"candles": rows})
}

func (r *Router) flags(w http.ResponseWriter, req *http.Request) {
	rows, err := r.deps.Store.ListFlags(req.Context(), strings.ToUpper(req.URL.Query().Get("coin")), intParam(req.URL.Query().Get("limit"), 100))
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"flags": rows})
}

func (r *Router) ingestionStatus(w http.ResponseWriter, req *http.Request) {
	runs, err := r.deps.Store.LatestRuns(req.Context())
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"scheduler":      r.deps.Scheduler.Status(),
		"latest_runs":    runs,
		"rate_limiter":   r.deps.Limiter.Metrics(),
		"stale_warnings": []string{},
	})
}

func (r *Router) metrics(w http.ResponseWriter, req *http.Request) {
	writeJSON(w, http.StatusOK, r.deps.Limiter.Metrics())
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("content-type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func writeError(w http.ResponseWriter, err error) {
	writeJSON(w, http.StatusInternalServerError, map[string]string{"error": err.Error()})
}

func floatParam(raw string) float64 {
	v, _ := strconv.ParseFloat(raw, 64)
	return v
}

func intParam(raw string, fallback int) int {
	v, err := strconv.Atoi(raw)
	if err != nil {
		return fallback
	}
	return v
}

func overall(parts ...string) string {
	for _, p := range parts {
		if p != "ok" {
			return "degraded"
		}
	}
	return "ok"
}

func logging(next http.Handler, logger *slog.Logger) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		next.ServeHTTP(w, r)
		logger.Info("http_request", "method", r.Method, "path", r.URL.Path, "latency_ms", time.Since(start).Milliseconds())
	})
}

func cors(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("access-control-allow-origin", "*")
		w.Header().Set("access-control-allow-methods", "GET,POST,OPTIONS")
		w.Header().Set("access-control-allow-headers", "content-type")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}
