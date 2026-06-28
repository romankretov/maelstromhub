# Product Spec v2: Maelstrom UX Reset

## Purpose

Maelstrom should feel like a professional quantitative research terminal, not an admin interface for backend tables.

The backend already has useful primitives: assets, timeframes, datasets, candles, features, market regimes, strategies, signal generation, backtests, promotion gates, and paper trading. The v2 frontend should hide most of those implementation details behind a single research workspace that helps a user move from a fresh database to a first backtest without leaving the page.

Core workflow:

```text
Pick market -> fetch candles -> inspect chart/stats/regime -> configure strategy -> run backtest -> optimise -> paper deploy -> monitor
```

## Product Principles

- One persistent workspace is the centre of the app.
- Hide backend concepts from the primary UX.
- Do not expose Dataset, Feature Snapshot, Timeframe CRUD, or Experiment CRUD to normal users.
- Use user-facing terms: Market, Chart, Stats, Strategy, Backtest, Optimisation, Deploy, Monitor.
- Keep advanced backend objects under `Settings -> Advanced Data Admin`.
- Every screen should answer either "what is happening?", "what should I do next?", or "what changed after this run?"
- A fresh database should not feel empty because backend setup is missing. The app should guide the user to select a market and fetch data.

## Information Architecture

### Primary Product Areas

1. Workspace
   - Main terminal-like research surface.
   - Market selection, candle ingestion, chart, stats, regime, strategy config, backtest, optimisation, and deploy actions.
   - Default landing page.

2. Strategies
   - Strategy library focused on human concepts: strategy name, status, latest backtest, paper deployment, allowed regimes, next action.
   - Does not expose strategy version tables directly.
   - Version details are available as history inside a strategy detail panel.

3. Backtests
   - Historical run comparison and decision support.
   - Shows metrics, verdict, regime performance, assumptions, and promotion readiness.
   - Does not ask users to manually create signals or datasets.

4. Paper Trading
   - Paper accounts, deployments, positions, equity, trades, and blocked-by-regime reasons.
   - Launches from Workspace or Strategy after passing promotion gates.

5. Monitor
   - Operational status, recent audit events, running paper deployments, job health, and data freshness.
   - No live trading controls in v2.

6. Settings
   - Preferences, risk thresholds, supported markets, API configuration.
   - `Advanced Data Admin` for backend object inspection and repair tools.

### Hidden From Primary UX

These remain backend concepts and should not appear as top-level navigation:

- Assets
- Timeframes
- Datasets
- Feature Snapshots
- Experiments
- Ingestion Jobs

If exposed, they belong under:

```text
Settings -> Advanced Data Admin
```

The user-facing replacement vocabulary is:

| Backend concept | Primary UX term |
| --- | --- |
| Asset | Market |
| Timeframe | Interval |
| Dataset | Market Data |
| Candle records | Candles |
| Feature snapshots | Stats |
| Market regime snapshots | Market Regime |
| Strategy version | Strategy Configuration |
| Signal run | Strategy Signals |
| Backtest run | Backtest |
| Paper deployment | Paper Deployment |
| Experiment | Research Note or Optimisation Run |

## Top-Level Navigation

Recommended navigation:

```text
Workspace
Strategies
Backtests
Paper Trading
Monitor
Settings
```

Optional secondary navigation inside Settings:

```text
General
Risk Gates
Data Providers
Advanced Data Admin
Audit Log
```

Remove from normal navigation:

```text
Ideas Lab
Research
Deployment Center
```

These can return later if they have a user-facing workflow. For v2, they add conceptual noise.

## Workspace Layout

The Workspace is a persistent multi-panel surface. It should preserve the selected market, interval, strategy, and latest run state.

### Desktop Layout

```text
+------------------------------------------------------------------------------+
| Header: Market selector | Interval | Data freshness | Primary next action     |
+----------------+---------------------------------------------+---------------+
| Left rail      | Main chart and result surface                | Right panel   |
|                |                                             |               |
| 1. Market      | Chart                                       | Market Regime |
| 2. Data        | Volume / signal overlays                     | Stats         |
| 3. Strategy    | Backtest equity curve / comparison           | Strategy Gate |
| 4. Backtest    |                                             | Next Action   |
| 5. Deploy      |                                             |               |
+----------------+---------------------------------------------+---------------+
```

### Mobile Layout

Use a stacked workflow with persistent context:

```text
Market + interval selector
Current status / next action
Tabs: Chart | Stats | Strategy | Backtest | Deploy
```

### Workspace Panels

1. Market Panel
   - Select market, venue, and interval.
   - Shows data status: missing, stale, current, failed.
   - Primary action: `Fetch Candles` or `Refresh Candles`.

2. Chart Panel
   - Candlestick chart with close/volume fallback if full candles are unavailable.
   - Shows data coverage, latest candle time, and selected interval.
   - Optional overlays: strategy signals, moving averages, regime bands.

3. Stats Panel
   - Human-readable stats, not raw feature snapshot rows.
   - Examples: recent return, volatility, RSI, ATR, trend summary.
   - Links to raw data only in Advanced Data Admin.

4. Market Regime Panel
   - Current regime label, confidence, explanation.
   - Historical regime timeline.
   - Strategy allowed/blocked status.

5. Strategy Panel
   - Select template or existing strategy.
   - Configure parameters.
   - Configure allowed regimes.
   - Save configuration as a strategy version behind the scenes.

6. Backtest Panel
   - Run backtest.
   - Show verdict, score, return, drawdown, trade count, win rate, and regime performance.
   - Compare recent runs side by side.
   - Show promotion readiness and exact blockers.

7. Deploy Panel
   - Create/select paper account.
   - Start paper deployment after gates pass.
   - Step simulation.
   - Show position, equity, trades, and blocked-by-regime reasons.

## Major User Journeys

### Journey 1: Fresh Database to First Backtest

Goal: A new user can reach a first backtest from one page.

1. User opens Workspace.
2. Empty state says: "Choose a market to start research."
3. User selects `BTC` and `1h`.
4. App creates or reuses the backend asset/timeframe/dataset automatically.
5. User clicks `Fetch Candles`.
6. App backfills candles and updates chart/data freshness.
7. App computes stats and market regimes automatically or prompts `Compute Stats`.
8. User selects a strategy template.
9. User edits parameters and allowed regimes.
10. User clicks `Run Backtest`.
11. App generates signals, runs the backtest, and shows verdict plus next action.

Backend objects created implicitly:

```text
Asset -> Dataset -> Feature Snapshots -> Regime Snapshots -> Strategy -> Strategy Version -> Signals -> Backtest Run
```

The user should only see:

```text
Market Data -> Stats -> Market Regime -> Strategy -> Backtest
```

### Journey 2: Compare and Promote

1. User runs several backtests with parameter changes.
2. Backtest Panel shows recent runs side by side.
3. Best run is highlighted by verdict and risk-adjusted score.
4. Promotion gate explains eligibility:
   - Passed: "Ready for paper trading."
   - Blocked: "Max drawdown is worse than threshold", "Not enough trades", or similar.
5. User clicks `Promote to Backtested` if eligible.
6. If blocked, the app shows human-readable reasons and suggested next action.

### Journey 3: Optimise Strategy

1. User clicks `Optimise`.
2. User selects parameter ranges and objective.
3. App runs a set of deterministic backtests.
4. Results are grouped by verdict, return, drawdown, trade count, and regime performance.
5. User promotes or saves the best configuration.

Optimisation in v2 can be simple grid search. It does not need ML or portfolio optimisation.

### Journey 4: Paper Deploy

1. User has a Backtested strategy whose latest verdict is not Dangerous.
2. User selects or creates paper account.
3. User clicks `Start Paper Deployment`.
4. App creates deployment and shows current paper state.
5. User clicks `Step`.
6. App reads next candle/signal, checks market regime, executes or skips, then updates position/equity/trades.
7. If blocked by regime, the UI says why.

### Journey 5: Monitor

1. User opens Monitor.
2. Sees data freshness, running paper deployments, latest backtest verdicts, current market regimes, and audit events.
3. Can pause/stop paper deployments.
4. Cannot live trade.

## Empty States

### Workspace: No Market Selected

Message:

```text
Select a market to start.
Maelstrom will fetch candles, compute stats, identify regime, and prepare a strategy workspace.
```

Primary action:

```text
Choose Market
```

### Market Selected, No Candles

Message:

```text
No candles loaded for BTC 1h.
Fetch historical candles to inspect chart, stats, and strategy behaviour.
```

Primary action:

```text
Fetch Candles
```

### Candles Loaded, No Stats

Message:

```text
Candles are ready. Compute stats to enable regime detection and strategy signals.
```

Primary action:

```text
Compute Stats
```

### Stats Loaded, No Strategy

Message:

```text
Market context is ready. Choose a strategy template or open an existing strategy.
```

Primary action:

```text
Configure Strategy
```

### Backtest Blocked

Message:

```text
Backtest is not ready yet.
```

Reasons should be specific:

```text
- Candles are missing.
- Stats have not been computed.
- Strategy parameters are incomplete.
- Current regime is blocked by the strategy filter.
```

### Timeframes Missing

This should never appear in normal use because intervals are system-defined and seeded automatically. If it happens:

```text
System intervals are unavailable.
Dataset creation is disabled until the API seeds supported intervals.
```

Do not show an empty interval dropdown.

## Visual Design Direction

Maelstrom should feel like a dense, professional research terminal:

- Dark or neutral workbench foundation with high-contrast data surfaces.
- Dense but readable layouts; avoid marketing-style hero pages.
- Persistent context bar for market, interval, data freshness, and current workflow status.
- Cards only for repeated objects or framed tools; avoid cards inside cards.
- Use tables for comparisons, panels for active workspace state, and compact charts for metrics.
- Use icons for actions where standard symbols exist: refresh, run, save, promote, pause, stop.
- Use restrained color semantics:
  - Green: pass, profitable, running.
  - Amber: warning, stale, needs action.
  - Red: blocked, failed, dangerous.
  - Blue or neutral: informational state.
- Make verdicts visually scannable: Safe, Watch, Risky, Dangerous.
- Never require the user to understand backend table names to complete a workflow.

## Existing Backend APIs to Reuse

The v2 workspace can reuse most current APIs through a new orchestration layer.

### Market and Data

- `GET /v1/markets`
- `GET /assets`
- `POST /assets`
- `GET /timeframes`
- `GET /datasets`
- `POST /datasets`
- `GET /datasets/{dataset_id}`
- `POST /datasets/{dataset_id}/backfill-candles`
- `GET /datasets/{dataset_id}/candles`
- `GET /datasets/{dataset_id}/ingestion-jobs`

### Stats and Market Intelligence

- `POST /datasets/{dataset_id}/compute-features`
- `GET /datasets/{dataset_id}/feature-summary`
- `GET /datasets/{dataset_id}/feature-snapshots`
- `POST /datasets/{dataset_id}/compute-regimes`
- `GET /datasets/{dataset_id}/current-regime`
- `GET /datasets/{dataset_id}/regime-snapshots`
- `GET /datasets/{dataset_id}/market-intelligence`

### Strategy and Backtest

- Strategy CRUD and list endpoints.
- Strategy template endpoints.
- Strategy version create/list endpoints.
- Signal generation endpoints.
- Backtest run endpoints.
- Promotion endpoint:
  - `POST /strategies/{strategy_id}/promote`

### Paper Trading

- `POST /paper/accounts`
- `GET /paper/accounts`
- `POST /paper/deployments`
- `GET /paper/deployments`
- `GET /paper/deployments/{deployment_id}`
- `POST /paper/deployments/{deployment_id}/step`

### Operations

- Audit event endpoints.
- Health endpoint.

## New Workspace Orchestration APIs Needed

The frontend should not compose many low-level calls for the core workflow. Add a thin API orchestration layer that maps workspace intent to existing backend objects.

### Workspace State

```text
GET /workspace
```

Returns the current workspace state:

- selected market
- selected interval
- resolved asset id
- resolved dataset id
- data freshness
- candle summary
- feature/stat status
- current regime
- selected strategy
- latest signals
- latest backtests
- promotion readiness
- active paper deployment
- next recommended action

### Select Market

```text
POST /workspace/market
```

Payload:

```json
{
  "symbol": "BTC",
  "venue": "hyperliquid",
  "interval": "1h"
}
```

Responsibilities:

- Resolve or create asset.
- Resolve system timeframe.
- Resolve or create dataset.
- Persist workspace selection.
- Return updated workspace state.

### Fetch Candles

```text
POST /workspace/fetch-candles
```

Responsibilities:

- Ensure dataset exists.
- Queue candle backfill.
- Return job plus updated data state.

### Compute Market Context

```text
POST /workspace/compute-context
```

Responsibilities:

- Queue/perform feature computation.
- Compute regimes when enough feature data exists.
- Return stats, regime, and explanation.

### Configure Strategy

```text
POST /workspace/strategy
```

Responsibilities:

- Resolve or create strategy.
- Create new strategy version behind the scenes.
- Attach dataset.
- Store parameters and allowed regimes.
- Return strategy summary plus validation state.

### Run Backtest

```text
POST /workspace/backtest
```

Responsibilities:

- Ensure candles and stats are ready.
- Generate signals.
- Run backtest.
- Compute verdict and comparison summary.
- Return latest run, recent comparisons, promotion readiness, and next action.

### Optimise

```text
POST /workspace/optimise
```

Responsibilities:

- Accept parameter ranges and objective.
- Run deterministic grid backtests.
- Return ranked configurations and best candidate.

### Promote

```text
POST /workspace/promote
```

Responsibilities:

- Call strategy promotion gate.
- Return success or human-readable blockers.
- Return next action.

### Paper Deploy

```text
POST /workspace/paper-deploy
POST /workspace/paper-step
```

Responsibilities:

- Create/select paper account.
- Start deployment for approved strategy version.
- Step simulation.
- Return position, equity, trades, status, and regime-blocked reasons.

## Implementation Roadmap

### Phase 1: Navigation and Shell Reset

- Make Workspace the default route.
- Replace normal top-level navigation with:
  - Workspace
  - Strategies
  - Backtests
  - Paper Trading
  - Monitor
  - Settings
- Move current Research CRUD pages under `Settings -> Advanced Data Admin`.
- Rename user-facing copy away from backend nouns.

### Phase 2: Workspace Read Model

- Add `GET /workspace`.
- Create a backend service that assembles the current workspace state from existing repositories.
- Add next recommended action logic.
- Add frontend workspace shell with market selector, status bar, chart area, and right-side context panel.

### Phase 3: One-Page Fresh Start Flow

- Add `POST /workspace/market`.
- Add `POST /workspace/fetch-candles`.
- Auto-resolve asset, system timeframe, and dataset.
- Show useful empty states and disabled states.
- Ensure a fresh database can reach candle fetch without visiting admin pages.

### Phase 4: Context and Strategy Flow

- Add `POST /workspace/compute-context`.
- Add `POST /workspace/strategy`.
- Surface stats and regime as human context.
- Add strategy template selection and parameter controls.
- Hide strategy version creation.

### Phase 5: Backtest and Optimisation

- Add `POST /workspace/backtest`.
- Add comparison table and best-run highlight.
- Add `POST /workspace/optimise` for deterministic grid search.
- Integrate promotion readiness into the workspace.

### Phase 6: Paper Deploy and Monitor

- Add workspace paper deployment actions.
- Add Monitor page for paper deployments, audit events, data freshness, and job status.
- Keep live trading absent.

## Acceptance Criteria

- A normal user never needs to create a Timeframe, Dataset, Feature Snapshot, or Experiment.
- From a fresh database, a user can select a market, fetch candles, configure a strategy, and run a first backtest from Workspace.
- The primary navigation no longer looks like backend CRUD.
- Dataset/timeframe/feature/experiment screens are unavailable from normal navigation.
- The workspace clearly displays the next recommended action.
- Backtest results are decision-oriented and explain whether the strategy can move forward.
- Paper deployment remains rehearsal-only. No live trading controls are introduced.

## Non-Goals

- Live trading.
- Private key handling.
- WebSockets.
- Automatic scheduling.
- Machine learning optimisation.
- Portfolio optimisation.
- Replacing the backend data model.
- Removing admin/debug access for backend objects.
