# Hyperliquid Integration Notes

Official Hyperliquid docs are the source of truth:

- Info endpoint: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint
- Rate limits: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits

The client uses `POST /info` with request bodies including:

- `{"type":"metaAndAssetCtxs"}`
- `{"type":"allMids"}`
- `{"type":"candleSnapshot","req":{...}}`
- `{"type":"l2Book","coin":"BTC"}`
- `{"type":"recentTrades","coin":"BTC"}`
- `{"type":"fundingHistory","coin":"BTC","startTime":...}`

Weights are configurable through `ENDPOINT_WEIGHTS`; do not hardcode official limits in code.
