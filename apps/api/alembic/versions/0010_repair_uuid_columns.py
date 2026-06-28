"""repair uuid columns

Revision ID: 0010_repair_uuid_columns
Revises: 0009_add_market_intelligence
Create Date: 2026-06-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0010_repair_uuid_columns"
down_revision: str | None = "0009_add_market_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SMA_CROSSOVER_TEMPLATE_ID = "3af69744-0317-49ec-8850-b8494d40a1be"
RSI_MEAN_REVERSION_TEMPLATE_ID = "fc33a083-aabc-4e37-bd46-eb31ac5d5a3c"

FOREIGN_KEYS = [
    ("strategies", "strategies_source_idea_id_fkey", "source_idea_id", "ideas", "id", "SET NULL"),
    ("datasets", "datasets_asset_id_fkey", "asset_id", "assets", "id", "CASCADE"),
    ("datasets", "datasets_timeframe_id_fkey", "timeframe_id", "timeframes", "id", "RESTRICT"),
    ("candles", "candles_dataset_id_fkey", "dataset_id", "datasets", "id", "CASCADE"),
    ("ingestion_jobs", "ingestion_jobs_dataset_id_fkey", "dataset_id", "datasets", "id", "CASCADE"),
    ("feature_snapshots", "feature_snapshots_dataset_id_fkey", "dataset_id", "datasets", "id", "CASCADE"),
    ("market_regime_snapshots", "market_regime_snapshots_dataset_id_fkey", "dataset_id", "datasets", "id", "CASCADE"),
    ("strategy_versions", "strategy_versions_strategy_id_fkey", "strategy_id", "strategies", "id", "CASCADE"),
    ("strategy_versions", "strategy_versions_template_id_fkey", "template_id", "strategy_templates", "id", "RESTRICT"),
    ("strategy_versions", "strategy_versions_dataset_id_fkey", "dataset_id", "datasets", "id", "CASCADE"),
    ("signals", "signals_strategy_version_id_fkey", "strategy_version_id", "strategy_versions", "id", "CASCADE"),
    ("signals", "signals_strategy_id_fkey", "strategy_id", "strategies", "id", "CASCADE"),
    ("signals", "signals_dataset_id_fkey", "dataset_id", "datasets", "id", "CASCADE"),
    ("backtest_runs", "backtest_runs_strategy_version_id_fkey", "strategy_version_id", "strategy_versions", "id", "CASCADE"),
    ("backtest_runs", "backtest_runs_dataset_id_fkey", "dataset_id", "datasets", "id", "CASCADE"),
    ("backtest_trades", "backtest_trades_backtest_run_id_fkey", "backtest_run_id", "backtest_runs", "id", "CASCADE"),
    (
        "equity_curve_snapshots",
        "equity_curve_snapshots_backtest_run_id_fkey",
        "backtest_run_id",
        "backtest_runs",
        "id",
        "CASCADE",
    ),
    ("paper_deployments", "paper_deployments_strategy_id_fkey", "strategy_id", "strategies", "id", "CASCADE"),
    (
        "paper_deployments",
        "paper_deployments_strategy_version_id_fkey",
        "strategy_version_id",
        "strategy_versions",
        "id",
        "CASCADE",
    ),
    ("paper_deployments", "paper_deployments_dataset_id_fkey", "dataset_id", "datasets", "id", "CASCADE"),
    (
        "paper_deployments",
        "paper_deployments_paper_account_id_fkey",
        "paper_account_id",
        "paper_accounts",
        "id",
        "CASCADE",
    ),
    ("paper_trades", "paper_trades_deployment_id_fkey", "deployment_id", "paper_deployments", "id", "CASCADE"),
    ("paper_positions", "paper_positions_deployment_id_fkey", "deployment_id", "paper_deployments", "id", "CASCADE"),
    ("features", "features_dataset_id_fkey", "dataset_id", "datasets", "id", "CASCADE"),
    ("experiments", "experiments_dataset_id_fkey", "dataset_id", "datasets", "id", "CASCADE"),
    ("experiments", "experiments_feature_id_fkey", "feature_id", "features", "id", "SET NULL"),
]

UUID_COLUMNS = [
    ("ideas", "id"),
    ("strategies", "id"),
    ("strategies", "source_idea_id"),
    ("audit_events", "id"),
    ("assets", "id"),
    ("timeframes", "id"),
    ("datasets", "id"),
    ("datasets", "asset_id"),
    ("datasets", "timeframe_id"),
    ("candles", "id"),
    ("candles", "dataset_id"),
    ("ingestion_jobs", "id"),
    ("ingestion_jobs", "dataset_id"),
    ("feature_snapshots", "id"),
    ("feature_snapshots", "dataset_id"),
    ("market_regime_snapshots", "id"),
    ("market_regime_snapshots", "dataset_id"),
    ("strategy_templates", "id"),
    ("strategy_versions", "id"),
    ("strategy_versions", "strategy_id"),
    ("strategy_versions", "template_id"),
    ("strategy_versions", "dataset_id"),
    ("signals", "id"),
    ("signals", "strategy_version_id"),
    ("signals", "strategy_id"),
    ("signals", "dataset_id"),
    ("backtest_runs", "id"),
    ("backtest_runs", "strategy_version_id"),
    ("backtest_runs", "dataset_id"),
    ("backtest_trades", "id"),
    ("backtest_trades", "backtest_run_id"),
    ("equity_curve_snapshots", "id"),
    ("equity_curve_snapshots", "backtest_run_id"),
    ("paper_accounts", "id"),
    ("paper_deployments", "id"),
    ("paper_deployments", "strategy_id"),
    ("paper_deployments", "strategy_version_id"),
    ("paper_deployments", "dataset_id"),
    ("paper_deployments", "paper_account_id"),
    ("paper_trades", "id"),
    ("paper_trades", "deployment_id"),
    ("paper_positions", "id"),
    ("paper_positions", "deployment_id"),
    ("features", "id"),
    ("features", "dataset_id"),
    ("experiments", "id"),
    ("experiments", "dataset_id"),
    ("experiments", "feature_id"),
]


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    for table, constraint, *_ in FOREIGN_KEYS:
        op.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT IF EXISTS "{constraint}"')

    for table, column in UUID_COLUMNS:
        using_expression = f'right("{column}"::text, 36)::uuid'
        if (table, column) in {
            ("strategy_templates", "id"),
            ("strategy_versions", "template_id"),
        }:
            using_expression = (
                f'CASE "{column}"::text '
                f"WHEN 'sma_crossover' THEN '{SMA_CROSSOVER_TEMPLATE_ID}'::uuid "
                f"WHEN 'rsi_mean_reversion' THEN '{RSI_MEAN_REVERSION_TEMPLATE_ID}'::uuid "
                f'ELSE right("{column}"::text, 36)::uuid END'
            )
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = '{table}'
                      AND column_name = '{column}'
                      AND data_type <> 'uuid'
                ) THEN
                    ALTER TABLE "{table}"
                    ALTER COLUMN "{column}" TYPE uuid
                    USING {using_expression};
                END IF;
            END $$;
            """
        )

    for table, constraint, column, remote_table, remote_column, ondelete in FOREIGN_KEYS:
        op.create_foreign_key(
            constraint,
            table,
            remote_table,
            [column],
            [remote_column],
            ondelete=ondelete,
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    for table, constraint, *_ in FOREIGN_KEYS:
        op.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT IF EXISTS "{constraint}"')
    for table, column in reversed(UUID_COLUMNS):
        op.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" TYPE varchar(36) USING "{column}"::text')
    for table, constraint, column, remote_table, remote_column, ondelete in FOREIGN_KEYS:
        op.create_foreign_key(
            constraint,
            table,
            remote_table,
            [column],
            [remote_column],
            ondelete=ondelete,
        )
