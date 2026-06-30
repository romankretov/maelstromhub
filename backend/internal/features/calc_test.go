package features

import (
	"testing"
	"time"

	"maelstrom/backend/internal/models"
)

func TestCalculateProducesResearchScoreAndRegime(t *testing.T) {
	candles := make([]models.Candle, 48)
	start := time.Now().Add(-48 * time.Hour)
	for i := range candles {
		price := 100 + float64(i)
		candles[i] = models.Candle{Time: start.Add(time.Duration(i) * time.Hour), Coin: "BTC", Interval: "1h", Open: price - 1, High: price + 2, Low: price - 2, Close: price, Volume: 1000 + float64(i*20)}
	}
	f := Calculate(Input{Coin: "BTC", Interval: "1h", Candles: candles, SpreadBps: 1})
	if f.ResearchScore <= 0 {
		t.Fatalf("expected score, got %+v", f)
	}
	if f.RegimeLabel == "" {
		t.Fatalf("expected regime")
	}
}

func TestGenerateFlags(t *testing.T) {
	flags := GenerateFlags(models.Feature{Time: time.Now(), Coin: "BTC", VolumeVs7DAvg: 2.5, OIChange24H: 0.2, SpreadBps: 20})
	if len(flags) < 3 {
		t.Fatalf("expected multiple flags, got %d", len(flags))
	}
}
