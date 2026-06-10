from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
FEATURE_DATA_DIR = DATA_DIR / "features"
REPORTS_DIR = ROOT_DIR / "reports"
RAW_IDENTITY_DIR = RAW_DATA_DIR / "identity"
RAW_ODDS_DIR = RAW_DATA_DIR / "odds"
RAW_HISTORICAL_ODDS_DIR = RAW_ODDS_DIR / "historical"

RAW_HISTORY_PATH = RAW_DATA_DIR / "international_results.csv"
FIXTURES_2026_PATH = ROOT_DIR / "world_cup_2026_schedule_beijing.csv"
RAW_FIFA_RANKINGS_PATH = RAW_IDENTITY_DIR / "fifa_rankings_april_2026.html"
RAW_WORLD_CUP_SQUADS_PATH = RAW_IDENTITY_DIR / "world_cup_2026_squads.html"

MATCHES_PATH = PROCESSED_DATA_DIR / "matches.parquet"
TEAMS_PATH = PROCESSED_DATA_DIR / "teams.parquet"
RATINGS_PATH = PROCESSED_DATA_DIR / "ratings.parquet"
FIXTURES_PATH = PROCESSED_DATA_DIR / "fixtures_2026.parquet"
FIFA_RANKINGS_PATH = PROCESSED_DATA_DIR / "fifa_rankings_2026.parquet"
SQUADS_2026_PATH = PROCESSED_DATA_DIR / "squads_2026.parquet"
WORLD_CUP_TEAMS_2026_PATH = PROCESSED_DATA_DIR / "world_cup_teams_2026.parquet"
TEAM_GOAL_FORM_FEATURES_PATH = PROCESSED_DATA_DIR / "team_goal_form_features.parquet"
MARKET_ODDS_SNAPSHOTS_PATH = PROCESSED_DATA_DIR / "market_odds_snapshots.parquet"
HISTORICAL_MARKET_ODDS_SNAPSHOTS_PATH = (
    PROCESSED_DATA_DIR / "historical_market_odds_snapshots.parquet"
)
MATCH_FEATURE_STORE_2026_PATH = FEATURE_DATA_DIR / "match_feature_store_2026.parquet"
HISTORICAL_MATCH_FEATURE_STORE_PATH = FEATURE_DATA_DIR / "historical_match_feature_store.parquet"
MATCH_ODDS_FEATURES_PATH = FEATURE_DATA_DIR / "match_odds_features.parquet"
HISTORICAL_MATCH_ODDS_FEATURES_PATH = FEATURE_DATA_DIR / "historical_match_odds_features.parquet"
DATABASE_PATH = PROCESSED_DATA_DIR / "fifa_research.duckdb"

BASELINE_METRICS_PATH = REPORTS_DIR / "baseline_metrics.json"
BASELINE_PREDICTIONS_PATH = REPORTS_DIR / "world_cup_2026_baseline_predictions.csv"
ENHANCED_METRICS_PATH = REPORTS_DIR / "enhanced_model_metrics.json"
ENHANCED_PREDICTIONS_PATH = REPORTS_DIR / "world_cup_2026_enhanced_predictions.csv"
TOURNAMENT_SIMULATION_PATH = REPORTS_DIR / "world_cup_2026_tournament_simulation.csv"
SCORELINE_METRICS_PATH = REPORTS_DIR / "scoreline_model_metrics.json"
SCORELINE_ANALYSIS_PATH = REPORTS_DIR / "world_cup_2026_scoreline_analysis.csv"
WORLD_CUP_BACKTEST_METRICS_PATH = REPORTS_DIR / "world_cup_backtest_metrics.csv"
WORLD_CUP_BACKTEST_PREDICTIONS_PATH = REPORTS_DIR / "world_cup_backtest_predictions.csv"
WORLD_CUP_BACKTEST_CALIBRATION_PATH = REPORTS_DIR / "world_cup_backtest_calibration.csv"
WORLD_CUP_BACKTEST_CONFEDERATION_PATH = (
    REPORTS_DIR / "world_cup_backtest_confederation_diagnostics.csv"
)
WORLD_CUP_BACKTEST_LOW_SCORE_PATH = REPORTS_DIR / "world_cup_backtest_low_score_diagnostics.csv"
WORLD_CUP_BACKTEST_UPSET_PATH = REPORTS_DIR / "world_cup_backtest_upset_diagnostics.csv"


def ensure_project_directories() -> None:
    for path in (
        RAW_DATA_DIR,
        RAW_IDENTITY_DIR,
        RAW_ODDS_DIR,
        RAW_HISTORICAL_ODDS_DIR,
        PROCESSED_DATA_DIR,
        FEATURE_DATA_DIR,
        REPORTS_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
