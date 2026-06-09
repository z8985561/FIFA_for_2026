from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
FEATURE_DATA_DIR = DATA_DIR / "features"
REPORTS_DIR = ROOT_DIR / "reports"

RAW_HISTORY_PATH = RAW_DATA_DIR / "international_results.csv"
FIXTURES_2026_PATH = ROOT_DIR / "world_cup_2026_schedule_beijing.csv"

MATCHES_PATH = PROCESSED_DATA_DIR / "matches.parquet"
TEAMS_PATH = PROCESSED_DATA_DIR / "teams.parquet"
RATINGS_PATH = PROCESSED_DATA_DIR / "ratings.parquet"
FIXTURES_PATH = PROCESSED_DATA_DIR / "fixtures_2026.parquet"
DATABASE_PATH = PROCESSED_DATA_DIR / "fifa_research.duckdb"

BASELINE_METRICS_PATH = REPORTS_DIR / "baseline_metrics.json"
BASELINE_PREDICTIONS_PATH = REPORTS_DIR / "world_cup_2026_baseline_predictions.csv"


def ensure_project_directories() -> None:
    for path in (RAW_DATA_DIR, PROCESSED_DATA_DIR, FEATURE_DATA_DIR, REPORTS_DIR):
        path.mkdir(parents=True, exist_ok=True)
