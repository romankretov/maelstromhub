package features

import (
	"math"
	"sort"
	"time"

	"maelstrom/backend/internal/models"
)

type Input struct {
	Coin      string
	Interval  string
	Candles   []models.Candle
	Snapshots []models.MarketSnapshot
	SpreadBps float64
}

func Calculate(input Input) models.Feature {
	candles := input.Candles
	snaps := input.Snapshots
	now := time.Now().UTC()
	if len(candles) > 0 {
		now = candles[len(candles)-1].Time
	}
	closes := make([]float64, 0, len(candles))
	volumes := make([]float64, 0, len(candles))
	for _, c := range candles {
		closes = append(closes, c.Close)
		volumes = append(volumes, c.Volume)
	}
	f := models.Feature{
		Time:          now,
		Coin:          input.Coin,
		Interval:      input.Interval,
		SpreadBps:     input.SpreadBps,
		UpdatedAt:     time.Now().UTC(),
		RegimeLabel:   "ignore_choppy",
		HurstEstimate: 0.5,
	}
	f.Return1H = returnN(closes, 1)
	f.Return4H = returnN(closes, 4)
	f.Return24H = returnN(closes, 24)
	f.VolumeVs7DAvg = ratio(last(volumes), avg(tail(volumes, 7*24)))
	f.VolumeZScore = zscore(last(volumes), tail(volumes, 7*24))
	f.RealizedVol = std(returns(tail(closes, 24))) * math.Sqrt(24)
	f.ATR = atr(tail(candles, 24))
	f.ADX = adx(tail(candles, 24))
	f.Autocorr1 = autocorrLag1(returns(tail(closes, 48)))
	f.HurstEstimate = hurst(tail(closes, 96))
	if len(snaps) > 0 {
		ois := mapSlice(snaps, func(s models.MarketSnapshot) float64 { return s.OpenInterest })
		f.OIChange1H = returnN(ois, 1)
		f.OIChange4H = returnN(ois, 4)
		f.OIChange24H = returnN(ois, 24)
		f.FundingZScore = zscore(snaps[len(snaps)-1].Funding, mapSlice(tail(snaps, 7*24), func(s models.MarketSnapshot) float64 { return s.Funding }))
	}
	f.LiquidityScore = clamp(100 - input.SpreadBps*5 + math.Log10(1+avg(tail(volumes, 24)))*8)
	f.OIAnomalyScore = clamp(math.Abs(f.OIChange24H) * 300)
	f.VolumeAnomalyScore = clamp(math.Max(0, f.VolumeZScore) * 25)
	f.MomentumScore = clamp(math.Abs(f.Return24H) * 500)
	f.FundingAnomalyScore = clamp(math.Abs(f.FundingZScore) * 20)
	f.ExecutionQualityScore = clamp(100 - input.SpreadBps*8)
	f.ResearchScore = 0.25*f.LiquidityScore + 0.20*f.OIAnomalyScore + 0.20*f.VolumeAnomalyScore + 0.15*f.MomentumScore + 0.10*f.FundingAnomalyScore + 0.10*f.ExecutionQualityScore
	f.RegimeLabel = classify(f)
	return f
}

func GenerateFlags(f models.Feature) []models.Flag {
	flags := []models.Flag{}
	add := func(kind, severity, msg string) {
		flags = append(flags, models.Flag{Time: f.Time, Coin: f.Coin, FlagType: kind, Severity: severity, Message: msg})
	}
	if f.VolumeVs7DAvg >= 2 {
		add("volume_anomaly", "high", "Volume is more than 2x above 7d average")
	}
	if f.OIChange24H >= 0.18 {
		add("oi_anomaly", "high", "OI up more than 18% in 24h")
	}
	if f.FundingZScore >= 2 {
		add("funding", "medium", "Funding extremely positive")
	}
	if f.FundingZScore < -1 && f.OIChange24H > 0.05 {
		add("squeeze", "medium", "Funding negative while OI rising")
	}
	if f.SpreadBps > 12 {
		add("execution", "high", "Spread too wide")
	}
	if f.Return24H > 0.05 && math.Abs(f.FundingZScore) < 1 {
		add("relative_strength", "medium", "Strong relative strength with neutral funding")
	}
	if f.RealizedVol < 0.02 && f.VolumeZScore > 1 {
		add("volatility", "medium", "Volatility compression with volume rising")
	}
	return flags
}

func NormalizeCrossSection(features []models.Feature) []models.Feature {
	normalize(features, func(f models.Feature) float64 { return f.Return24H }, func(i int, v float64) { features[i].RelativeStrengthRank = v })
	normalize(features, func(f models.Feature) float64 { return f.LiquidityScore }, func(i int, v float64) { features[i].LiquidityScore = v })
	normalize(features, func(f models.Feature) float64 { return f.OIAnomalyScore }, func(i int, v float64) { features[i].OIAnomalyScore = v })
	normalize(features, func(f models.Feature) float64 { return f.VolumeAnomalyScore }, func(i int, v float64) { features[i].VolumeAnomalyScore = v })
	for i := range features {
		f := &features[i]
		f.ResearchScore = 0.25*f.LiquidityScore + 0.20*f.OIAnomalyScore + 0.20*f.VolumeAnomalyScore + 0.15*f.MomentumScore + 0.10*f.FundingAnomalyScore + 0.10*f.ExecutionQualityScore
		f.RegimeLabel = classify(*f)
	}
	return features
}

func classify(f models.Feature) string {
	if f.ExecutionQualityScore < 25 || f.LiquidityScore < 20 {
		return "ignore_low_liquidity"
	}
	if f.RealizedVol < 0.02 && f.VolumeZScore > 0.8 {
		return "volatility_breakout_candidate"
	}
	if math.Abs(f.Return24H) > 0.05 && f.ADX > 20 {
		return "trend_candidate"
	}
	if f.Return4H > 0.03 && f.RelativeStrengthRank > 70 {
		return "momentum_candidate"
	}
	if math.Abs(f.FundingZScore) > 2 || math.Abs(f.Return24H) > 0.12 {
		return "mean_reversion_candidate"
	}
	if f.RealizedVol < 0.015 {
		return "squeeze_candidate"
	}
	return "ignore_choppy"
}

func normalize(features []models.Feature, value func(models.Feature) float64, set func(int, float64)) {
	vals := make([]float64, len(features))
	for i, f := range features {
		vals[i] = value(f)
	}
	minV, maxV := minMax(vals)
	for i, v := range vals {
		if maxV == minV {
			set(i, 50)
		} else {
			set(i, clamp((v-minV)/(maxV-minV)*100))
		}
	}
}

func returnN(values []float64, n int) float64 {
	if len(values) <= n || values[len(values)-1-n] == 0 {
		return 0
	}
	return values[len(values)-1]/values[len(values)-1-n] - 1
}

func returns(values []float64) []float64 {
	out := []float64{}
	for i := 1; i < len(values); i++ {
		if values[i-1] != 0 {
			out = append(out, values[i]/values[i-1]-1)
		}
	}
	return out
}

func atr(candles []models.Candle) float64 {
	if len(candles) == 0 {
		return 0
	}
	sum := 0.0
	for _, c := range candles {
		sum += c.High - c.Low
	}
	return sum / float64(len(candles))
}

func adx(candles []models.Candle) float64 {
	if len(candles) < 2 {
		return 0
	}
	move := math.Abs(candles[len(candles)-1].Close - candles[0].Close)
	rangeSum := 0.0
	for _, c := range candles {
		rangeSum += c.High - c.Low
	}
	if rangeSum == 0 {
		return 0
	}
	return clamp(move / rangeSum * 100)
}

func autocorrLag1(values []float64) float64 {
	if len(values) < 3 {
		return 0
	}
	m := avg(values)
	num, den := 0.0, 0.0
	for i := 1; i < len(values); i++ {
		num += (values[i] - m) * (values[i-1] - m)
	}
	for _, v := range values {
		den += (v - m) * (v - m)
	}
	if den == 0 {
		return 0
	}
	return num / den
}

func hurst(values []float64) float64 {
	if len(values) < 20 {
		return 0.5
	}
	rs := (max(values) - min(values)) / math.Max(std(values), 1e-9)
	return clamp01(math.Log(rs)/math.Log(float64(len(values))) + 0.1)
}

func zscore(value float64, values []float64) float64 {
	s := std(values)
	if s == 0 {
		return 0
	}
	return (value - avg(values)) / s
}

func avg(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}
	sum := 0.0
	for _, v := range values {
		sum += v
	}
	return sum / float64(len(values))
}

func std(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}
	m := avg(values)
	sum := 0.0
	for _, v := range values {
		sum += (v - m) * (v - m)
	}
	return math.Sqrt(sum / float64(len(values)))
}

func ratio(a, b float64) float64 {
	if b == 0 {
		return 0
	}
	return a / b
}

func tail[T any](values []T, n int) []T {
	if len(values) <= n {
		return values
	}
	return values[len(values)-n:]
}

func last(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}
	return values[len(values)-1]
}

func mapSlice[T any](values []T, fn func(T) float64) []float64 {
	out := make([]float64, len(values))
	for i, v := range values {
		out[i] = fn(v)
	}
	return out
}

func minMax(values []float64) (float64, float64) {
	if len(values) == 0 {
		return 0, 0
	}
	sorted := append([]float64(nil), values...)
	sort.Float64s(sorted)
	return sorted[0], sorted[len(sorted)-1]
}

func min(values []float64) float64 {
	m, _ := minMax(values)
	return m
}

func max(values []float64) float64 {
	_, m := minMax(values)
	return m
}

func clamp(v float64) float64 {
	return math.Max(0, math.Min(100, v))
}

func clamp01(v float64) float64 {
	return math.Max(0, math.Min(1, v))
}
