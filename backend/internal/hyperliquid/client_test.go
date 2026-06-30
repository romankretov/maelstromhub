package hyperliquid

import (
	"bytes"
	"context"
	"io"
	"log/slog"
	"net/http"
	"testing"

	"maelstrom/backend/internal/limiter"
)

func TestMetaAndAssetCtxsParsesTypedResponse(t *testing.T) {
	client := NewClient(Config{BaseURL: "http://hyperliquid.test"}, limiter.NewWeighted(limiter.Config{CapacityPerMinute: 1000}, slog.Default()), slog.Default())
	client.http.Transport = roundTripFunc(func(r *http.Request) (*http.Response, error) {
		return response(200, `[{"universe":[{"name":"BTC","szDecimals":5,"maxLeverage":50}]},[{"markPx":"100","midPx":"100.1","oraclePx":"99.9","prevDayPx":"95","dayNtlVlm":"123","openInterest":"456","funding":"0.0001","premium":"0.02"}]]`), nil
	})
	resp, err := client.MetaAndAssetCtxs(context.Background())
	if err != nil {
		t.Fatalf("meta: %v", err)
	}
	if len(resp.Universe) != 1 || resp.Universe[0].Name != "BTC" {
		t.Fatalf("unexpected universe: %+v", resp.Universe)
	}
	if len(resp.Contexts) != 1 || float64(resp.Contexts[0].MarkPx) != 100 {
		t.Fatalf("unexpected ctx: %+v", resp.Contexts)
	}
}

func TestMalformedResponseReturnsError(t *testing.T) {
	client := NewClient(Config{BaseURL: "http://hyperliquid.test"}, limiter.NewWeighted(limiter.Config{CapacityPerMinute: 1000}, slog.Default()), slog.Default())
	client.http.Transport = roundTripFunc(func(r *http.Request) (*http.Response, error) {
		return response(200, `{"bad":`), nil
	})
	if _, err := client.AllMids(context.Background()); err == nil {
		t.Fatalf("expected malformed response error")
	}
}

type roundTripFunc func(*http.Request) (*http.Response, error)

func (f roundTripFunc) RoundTrip(req *http.Request) (*http.Response, error) {
	return f(req)
}

func response(status int, body string) *http.Response {
	return &http.Response{
		StatusCode: status,
		Body:       io.NopCloser(bytes.NewBufferString(body)),
		Header:     http.Header{"content-type": []string{"application/json"}},
	}
}
