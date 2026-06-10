from __future__ import annotations

import argparse
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd
import requests

from .lineups_pipeline import TEAM_NAME_ZH
from .project_paths import (
    FIXTURES_PATH,
    SCORE_ODDS_COLLECTION_STATUS_PATH,
    SCORE_ODDS_FEATURES_PATH,
    SCORE_ODDS_SNAPSHOTS_PATH,
    ensure_project_directories,
)

SPORTSGAMBLER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

SPORTTERY_HEADERS = {
    "User-Agent": SPORTSGAMBLER_HEADERS["User-Agent"],
    "Referer": "https://www.sporttery.cn/jc/zqdz/index.html",
}

SPORTTERY_FIXED_BONUS_API = (
    "https://webapi.sporttery.cn/gateway/uniform/football/getFixedBonusV1.qry"
)
SPORTTERY_MATCH_LIST_API = (
    "https://webapi.sporttery.cn/gateway/uniform/football/getMatchListV1.qry"
)
SPORTTERY_CLIENT_CODE = "3001"
SPORTTERY_SOURCE_NAME = "中国体育彩票"
SPORTTERY_BOOKMAKER_KEY = "sporttery"
SPORTTERY_BOOKMAKER_TITLE = "中国体育彩票"
SPORTTERY_WORLD_CUP_LEAGUE_KEYWORD = "世界杯"
SPORTTERY_KNOWN_MATCH_IDS = {
    1: "2040162",
    2: "2040163",
    7: "2040164",
    19: "2040165",
}

SPORTTERY_TEAM_NAME_TO_FIXTURE_TEAM = {
    "阿尔及利": "Algeria",
    "阿尔及利亚": "Algeria",
    "阿根廷": "Argentina",
    "奥地利": "Austria",
    "澳大利亚": "Australia",
    "巴拉圭": "Paraguay",
    "巴拿马": "Panama",
    "巴西": "Brazil",
    "比利时": "Belgium",
    "波黑": "Bosnia and Herzegovina",
    "佛得角": "Cape Verde",
    "刚果(金)": "DR Congo",
    "刚果金": "DR Congo",
    "哥伦比亚": "Colombia",
    "德国": "Germany",
    "厄瓜多尔": "Ecuador",
    "法国": "France",
    "加纳": "Ghana",
    "加拿大": "Canada",
    "捷克": "Czech Republic",
    "克罗地亚": "Croatia",
    "卡塔尔": "Qatar",
    "科特迪瓦": "Ivory Coast",
    "库拉索": "Curaçao",
    "摩洛哥": "Morocco",
    "墨西哥": "Mexico",
    "南非": "South Africa",
    "挪威": "Norway",
    "葡萄牙": "Portugal",
    "日本": "Japan",
    "瑞典": "Sweden",
    "瑞士": "Switzerland",
    "沙特": "Saudi Arabia",
    "沙特阿拉伯": "Saudi Arabia",
    "塞内加尔": "Senegal",
    "苏格兰": "Scotland",
    "土耳其": "Turkey",
    "突尼斯": "Tunisia",
    "乌拉圭": "Uruguay",
    "乌兹别克": "Uzbekistan",
    "乌兹别克斯坦": "Uzbekistan",
    "西班牙": "Spain",
    "新西兰": "New Zealand",
    "伊拉克": "Iraq",
    "伊朗": "Iran",
    "英格兰": "England",
    "约旦": "Jordan",
    "海地": "Haiti",
    "韩国": "South Korea",
    "荷兰": "Netherlands",
    "美国": "United States",
    "埃及": "Egypt",
}
SPORTTERY_FIXTURE_TEAM_TO_ZH = {
    english_name: chinese_name
    for chinese_name, english_name in SPORTTERY_TEAM_NAME_TO_FIXTURE_TEAM.items()
}

SPORTSGAMBLER_KNOWN_URLS = {
    1: (
        "https://www.sportsgambler.com/betting-tips/football/"
        "mexico-vs-south-africa-prediction-lineups-odds-2026-06-11/"
    ),
    2: (
        "https://www.sportsgambler.com/betting-tips/football/"
        "south-korea-vs-czech-republic-prediction-lineups-odds-2026-06-12/"
    ),
}

SPORTSGAMBLER_TEAM_SLUGS = {
    "Bosnia and Herzegovina": ("bosnia-and-herzegovina", "bosnia-herzegovina"),
    "Czech Republic": ("czech-republic",),
    "Mexico": ("mexico",),
    "South Africa": ("south-africa",),
    "South Korea": ("south-korea",),
    "Canada": ("canada",),
    "United States": ("usa", "united-states"),
    "Paraguay": ("paraguay",),
}

SPORTTERY_SCORELINE_CODES = {
    "s01s00": "1-0",
    "s02s00": "2-0",
    "s02s01": "2-1",
    "s03s00": "3-0",
    "s03s01": "3-1",
    "s03s02": "3-2",
    "s04s00": "4-0",
    "s04s01": "4-1",
    "s04s02": "4-2",
    "s05s00": "5-0",
    "s05s01": "5-1",
    "s05s02": "5-2",
    "s-1sh": "胜其他",
    "s00s00": "0-0",
    "s01s01": "1-1",
    "s02s02": "2-2",
    "s03s03": "3-3",
    "s-1sd": "平其他",
    "s00s01": "0-1",
    "s00s02": "0-2",
    "s01s02": "1-2",
    "s00s03": "0-3",
    "s01s03": "1-3",
    "s02s03": "2-3",
    "s00s04": "0-4",
    "s01s04": "1-4",
    "s02s04": "2-4",
    "s00s05": "0-5",
    "s01s05": "1-5",
    "s02s05": "2-5",
    "s-1sa": "负其他",
}

DEFAULT_MATCH_LIMIT = 72
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30
SPORTTERY_MATCH_ID_PATTERN = re.compile(r"[?&]mid=(\d+)")
SCORE_ODDS_PATTERN = re.compile(
    r'<span class="mabeto-btn-no">\s*([^<]+?)\s*</span>\s*'
    r'<span class="mabeto-btn-odd">\s*([^<]+?)\s*</span>',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ScoreOddsPipelineOutputs:
    score_odds_snapshots_path: str
    score_odds_features_path: str
    collection_status_path: str
    snapshot_rows: int
    feature_rows: int
    status_rows: int
    collected_matches: int


def american_to_decimal(american_odds: str | int | float) -> float:
    value = str(american_odds).strip().replace("\u2212", "-")
    if not value:
        raise ValueError("american_odds cannot be empty")
    number = float(value.replace("+", ""))
    if number > 0:
        return 1.0 + number / 100.0
    if number < 0:
        return 1.0 + 100.0 / abs(number)
    raise ValueError("american_odds cannot be zero")


def score_odds_implied_probability(decimal_odds: float) -> float:
    if decimal_odds <= 1.0:
        raise ValueError("decimal_odds must be greater than 1.0")
    return 1.0 / decimal_odds


def fixture_team_zh(team_name: str) -> str:
    return TEAM_NAME_ZH.get(team_name, SPORTTERY_FIXTURE_TEAM_TO_ZH.get(team_name, team_name))


def sporttery_match_id_for_fixture(row: pd.Series) -> str | None:
    existing_match_id = row.get("source_match_id")
    if pd.notna(existing_match_id) and str(existing_match_id).strip():
        return str(existing_match_id).strip()
    return SPORTTERY_KNOWN_MATCH_IDS.get(int(row["match_no"]))


def sporttery_source_url(match_id: str) -> str:
    return f"https://www.sporttery.cn/jc/zqdz/index.html?showType=3&mid={match_id}"


def extract_sporttery_match_id_from_url(source_url: object) -> str | None:
    if source_url is None or pd.isna(source_url):
        return None
    match = SPORTTERY_MATCH_ID_PATTERN.search(str(source_url))
    return match.group(1) if match else None


def reverse_scoreline(scoreline: str) -> str:
    if scoreline == "胜其他":
        return "负其他"
    if scoreline == "负其他":
        return "胜其他"
    if scoreline == "平其他":
        return scoreline
    parts = scoreline.split("-")
    if len(parts) == 2 and all(part.isdigit() for part in parts):
        return f"{parts[1]}-{parts[0]}"
    return scoreline


def fetch_sporttery_match_list(
    *,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    response = requests.get(
        SPORTTERY_MATCH_LIST_API,
        params={"clientCode": SPORTTERY_CLIENT_CODE},
        headers={**SPORTTERY_HEADERS, "Referer": "https://www.lottery.gov.cn/jc/index.html"},
        timeout=timeout_seconds,
    )
    if response.status_code != 200:
        raise ValueError(f"{SPORTTERY_MATCH_LIST_API} returned HTTP {response.status_code}")
    payload = response.json()
    if str(payload.get("errorCode")) != "0":
        raise ValueError(str(payload.get("errorMessage", "sporttery match list request failed")))
    return payload


def iter_sporttery_match_list_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    match_info_list = payload.get("value", {}).get("matchInfoList", [])
    if not isinstance(match_info_list, list):
        return rows
    for day in match_info_list:
        if not isinstance(day, dict):
            continue
        sub_matches = day.get("subMatchList", [])
        if isinstance(sub_matches, list):
            rows.extend(row for row in sub_matches if isinstance(row, dict))
    return rows


def is_sporttery_world_cup_match(row: dict[str, Any]) -> bool:
    league_values = (
        str(row.get("leagueAbbName", "")),
        str(row.get("leagueAllName", "")),
    )
    return any(SPORTTERY_WORLD_CUP_LEAGUE_KEYWORD in value for value in league_values)


def normalize_sporttery_team_name(name: object) -> str | None:
    if name is None:
        return None
    normalized = str(name).strip()
    return SPORTTERY_TEAM_NAME_TO_FIXTURE_TEAM.get(normalized)


def build_sporttery_match_id_map(
    fixtures: pd.DataFrame,
    sporttery_rows: list[dict[str, Any]],
) -> dict[int, str]:
    metadata = build_sporttery_match_metadata_map(fixtures, sporttery_rows)
    return {
        match_no: str(values["source_match_id"])
        for match_no, values in metadata.items()
    }


def build_sporttery_match_metadata_map(
    fixtures: pd.DataFrame,
    sporttery_rows: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    fixture_lookup: dict[tuple[str, str], int] = {}
    for fixture in fixtures.itertuples(index=False):
        fixture_lookup[(str(fixture.home_team), str(fixture.away_team))] = int(fixture.match_no)

    match_metadata: dict[int, dict[str, Any]] = {}
    for row in sporttery_rows:
        if not is_sporttery_world_cup_match(row):
            continue
        home_team = normalize_sporttery_team_name(
            row.get("homeTeamAllName") or row.get("homeTeamAbbName")
        )
        away_team = normalize_sporttery_team_name(
            row.get("awayTeamAllName") or row.get("awayTeamAbbName")
        )
        match_id = row.get("matchId")
        if home_team is None or away_team is None or match_id in (None, ""):
            continue
        match_no = fixture_lookup.get((home_team, away_team))
        source_home_away_reversed = False
        if match_no is None:
            match_no = fixture_lookup.get((away_team, home_team))
            source_home_away_reversed = match_no is not None
        if match_no is not None:
            match_metadata[match_no] = {
                "source_match_id": str(match_id),
                "source_home_away_reversed": source_home_away_reversed,
            }
    return match_metadata


def discover_sporttery_match_ids(
    fixtures: pd.DataFrame,
    *,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> dict[int, str]:
    payload = fetch_sporttery_match_list(timeout_seconds=timeout_seconds)
    return build_sporttery_match_id_map(fixtures, iter_sporttery_match_list_rows(payload))


def discover_sporttery_match_metadata(
    fixtures: pd.DataFrame,
    *,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> dict[int, dict[str, Any]]:
    payload = fetch_sporttery_match_list(timeout_seconds=timeout_seconds)
    return build_sporttery_match_metadata_map(fixtures, iter_sporttery_match_list_rows(payload))


def add_sporttery_match_ids_to_fixtures(
    fixtures: pd.DataFrame,
    sporttery_match_ids: dict[int, str] | dict[int, dict[str, Any]],
) -> pd.DataFrame:
    enriched = fixtures.copy()
    known_ids: dict[int, str] = {**SPORTTERY_KNOWN_MATCH_IDS}
    reversed_flags: dict[int, bool] = {}
    for match_no, value in sporttery_match_ids.items():
        if isinstance(value, dict):
            known_ids[int(match_no)] = str(value["source_match_id"])
            reversed_flags[int(match_no)] = bool(value.get("source_home_away_reversed", False))
        else:
            known_ids[int(match_no)] = str(value)
    enriched["source_match_id"] = enriched["match_no"].map(
        lambda match_no: known_ids.get(int(match_no))
    )
    enriched["source_home_away_reversed"] = enriched["match_no"].map(
        lambda match_no: reversed_flags.get(int(match_no), False)
    )
    return enriched


def fetch_sporttery_fixed_bonus(
    match_id: str,
    *,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    response = requests.get(
        SPORTTERY_FIXED_BONUS_API,
        params={"clientCode": SPORTTERY_CLIENT_CODE, "matchId": match_id},
        headers={**SPORTTERY_HEADERS, "Referer": sporttery_source_url(match_id)},
        timeout=timeout_seconds,
    )
    if response.status_code != 200:
        raise ValueError(f"{SPORTTERY_FIXED_BONUS_API} returned HTTP {response.status_code}")
    payload = response.json()
    if str(payload.get("errorCode")) != "0":
        raise ValueError(str(payload.get("errorMessage", "sporttery fixed bonus request failed")))
    return payload


def latest_sporttery_crs_row(payload: dict[str, Any]) -> dict[str, Any] | None:
    crs_rows = payload.get("value", {}).get("oddsHistory", {}).get("crsList", [])
    if not isinstance(crs_rows, list) or not crs_rows:
        return None
    valid_rows = [row for row in crs_rows if isinstance(row, dict)]
    if not valid_rows:
        return None
    return sorted(
        valid_rows,
        key=lambda row: f"{row.get('updateDate', '')} {row.get('updateTime', '')}",
    )[-1]


def extract_sporttery_correct_score_odds(
    payload: dict[str, Any],
) -> list[tuple[str, str, float]]:
    latest_row = latest_sporttery_crs_row(payload)
    if latest_row is None:
        return []

    rows: list[tuple[str, str, float]] = []
    for code, scoreline in SPORTTERY_SCORELINE_CODES.items():
        raw_odds = latest_row.get(code)
        if raw_odds in (None, ""):
            continue
        decimal_odds = float(raw_odds)
        if decimal_odds <= 1.0:
            continue
        rows.append((scoreline, str(raw_odds), decimal_odds))
    return rows


def sportsgambler_candidate_urls(row: pd.Series) -> list[str]:
    if int(row["match_no"]) in SPORTSGAMBLER_KNOWN_URLS:
        return [SPORTSGAMBLER_KNOWN_URLS[int(row["match_no"])]]

    home_slugs = SPORTSGAMBLER_TEAM_SLUGS.get(str(row["home_team"]), ())
    away_slugs = SPORTSGAMBLER_TEAM_SLUGS.get(str(row["away_team"]), ())
    match_date = pd.to_datetime(row["date_et"]).date().isoformat()
    urls: list[str] = []
    for home_slug in home_slugs:
        for away_slug in away_slugs:
            urls.append(
                "https://www.sportsgambler.com/betting-tips/football/"
                f"{home_slug}-vs-{away_slug}-prediction-lineups-odds-{match_date}/"
            )
    return urls


def fetch_url(url: str, *, timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS) -> str:
    response = requests.get(
        url,
        headers=SPORTSGAMBLER_HEADERS,
        timeout=timeout_seconds,
        allow_redirects=False,
    )
    if response.status_code != 200:
        raise ValueError(f"{url} returned HTTP {response.status_code}")
    return response.text


def extract_sportsgambler_correct_score_odds(html: str) -> list[tuple[str, str, float]]:
    block_start = html.find("Latest Correct Score Odds")
    if block_start < 0:
        block_start = html.find('class="correct-score-odds"')
    if block_start < 0:
        return []
    block = html[block_start : block_start + 20_000]

    rows: list[tuple[str, str, float]] = []
    seen: set[str] = set()
    for scoreline, american_odds in SCORE_ODDS_PATTERN.findall(block):
        normalized_scoreline = " ".join(scoreline.strip().split())
        normalized_american_odds = american_odds.strip().replace("\u2212", "-")
        if normalized_scoreline in seen:
            continue
        seen.add(normalized_scoreline)
        rows.append(
            (
                normalized_scoreline,
                normalized_american_odds,
                american_to_decimal(normalized_american_odds),
            )
        )
    return rows


def append_score_odds_rows(
    snapshot_rows: list[dict[str, Any]],
    *,
    fixture: Any,
    extracted: list[tuple[str, str, float]],
    bookmaker_key: str,
    bookmaker_title: str,
    source_name: str,
    source_url: str | None,
    source_match_id: str | None,
    fetched_at: datetime,
) -> None:
    home_team = str(fixture.home_team)
    away_team = str(fixture.away_team)
    for scoreline, display_odds, decimal_odds in extracted:
        snapshot_rows.append(
            {
                "match_no": int(fixture.match_no),
                "stage": str(fixture.stage),
                "group_name": fixture.group_name,
                "date_et": pd.to_datetime(fixture.date_et).date(),
                "home_team": home_team,
                "away_team": away_team,
                "home_team_zh": fixture_team_zh(home_team),
                "away_team_zh": fixture_team_zh(away_team),
                "scoreline": scoreline,
                "bookmaker_key": bookmaker_key,
                "bookmaker_title": bookmaker_title,
                "american_odds": display_odds,
                "decimal_odds": decimal_odds,
                "raw_implied_probability": score_odds_implied_probability(decimal_odds),
                "source_name": source_name,
                "source_url": source_url,
                "source_match_id": source_match_id,
                "fetched_at": fetched_at,
            }
        )


def build_score_odds_snapshots(
    fixtures: pd.DataFrame,
    *,
    match_limit: int = DEFAULT_MATCH_LIMIT,
    fetched_at: datetime | None = None,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    existing_sporttery_match_ids: set[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    fetched_at = fetched_at or datetime.now(UTC)
    fixture_rows = fixtures.sort_values(["date_et", "match_no"]).head(match_limit)
    existing_sporttery_match_ids = existing_sporttery_match_ids or set()
    snapshot_rows: list[dict[str, Any]] = []
    status_rows: list[dict[str, Any]] = []

    for fixture in fixture_rows.itertuples(index=False):
        fixture_series = pd.Series(fixture._asdict())
        home_team = str(fixture.home_team)
        away_team = str(fixture.away_team)
        source_home_away_reversed = bool(
            fixture_series.get("source_home_away_reversed", False)
        )

        sporttery_match_id = sporttery_match_id_for_fixture(fixture_series)
        if sporttery_match_id is not None:
            source_url = sporttery_source_url(sporttery_match_id)
            if sporttery_match_id in existing_sporttery_match_ids:
                extracted = []
                sporttery_status = "skipped_existing"
                sporttery_error = "source_match_id already collected"
            else:
                try:
                    payload = fetch_sporttery_fixed_bonus(
                        sporttery_match_id,
                        timeout_seconds=timeout_seconds,
                    )
                    extracted = extract_sporttery_correct_score_odds(payload)
                    if source_home_away_reversed:
                        extracted = [
                            (reverse_scoreline(scoreline), display_odds, decimal_odds)
                            for scoreline, display_odds, decimal_odds in extracted
                        ]
                    append_score_odds_rows(
                        snapshot_rows,
                        fixture=fixture,
                        extracted=extracted,
                        bookmaker_key=SPORTTERY_BOOKMAKER_KEY,
                        bookmaker_title=SPORTTERY_BOOKMAKER_TITLE,
                        source_name=SPORTTERY_SOURCE_NAME,
                        source_url=source_url,
                        source_match_id=sporttery_match_id,
                        fetched_at=fetched_at,
                    )
                    sporttery_status = "collected" if extracted else "missing"
                    sporttery_error = None if extracted else "correct score odds not found"
                except Exception as exc:
                    extracted = []
                    sporttery_status = "missing"
                    sporttery_error = str(exc)

            status_rows.append(
                {
                    "match_no": int(fixture.match_no),
                    "date_et": pd.to_datetime(fixture.date_et).date(),
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_team_zh": fixture_team_zh(home_team),
                    "away_team_zh": fixture_team_zh(away_team),
                    "source_name": SPORTTERY_SOURCE_NAME,
                    "source_url": source_url,
                    "source_match_id": sporttery_match_id,
                    "attempted_urls": (
                        f"{SPORTTERY_FIXED_BONUS_API}?clientCode={SPORTTERY_CLIENT_CODE}"
                        f"&matchId={sporttery_match_id}"
                    ),
                    "status": sporttery_status,
                    "scoreline_count": len(extracted),
                    "error_message": sporttery_error,
                    "fetched_at": fetched_at,
                }
            )

        attempted_urls = sportsgambler_candidate_urls(fixture_series)
        source_url = None
        extracted = []
        error_message = None

        for candidate_url in attempted_urls:
            try:
                html = fetch_url(candidate_url, timeout_seconds=timeout_seconds)
                extracted = extract_sportsgambler_correct_score_odds(html)
                if extracted:
                    source_url = candidate_url
                    break
                error_message = "correct score odds block not found"
            except Exception as exc:
                error_message = str(exc)

        append_score_odds_rows(
            snapshot_rows,
            fixture=fixture,
            extracted=extracted,
            bookmaker_key="sportsgambler_consensus",
            bookmaker_title="SportsGambler listed odds",
            source_name="SportsGambler",
            source_url=source_url,
            source_match_id=None,
            fetched_at=fetched_at,
        )
        status_rows.append(
            {
                "match_no": int(fixture.match_no),
                "date_et": pd.to_datetime(fixture.date_et).date(),
                "home_team": home_team,
                "away_team": away_team,
                "home_team_zh": fixture_team_zh(home_team),
                "away_team_zh": fixture_team_zh(away_team),
                "source_name": "SportsGambler",
                "source_url": source_url,
                "source_match_id": None,
                "attempted_urls": "|".join(attempted_urls),
                "status": "collected" if extracted else "missing",
                "scoreline_count": len(extracted),
                "error_message": None if extracted else error_message,
                "fetched_at": fetched_at,
            }
        )

    snapshots = pd.DataFrame(snapshot_rows)
    status = pd.DataFrame(status_rows)
    if not snapshots.empty:
        snapshots = snapshots.sort_values(["match_no", "scoreline", "bookmaker_key"]).reset_index(
            drop=True
        )
    return snapshots, status


def build_score_odds_features(score_odds_snapshots: pd.DataFrame) -> pd.DataFrame:
    if score_odds_snapshots.empty:
        return pd.DataFrame()
    score_odds_snapshots = normalize_score_odds_snapshots(score_odds_snapshots)

    features = (
        score_odds_snapshots.groupby(
            [
                "match_no",
                "stage",
                "group_name",
                "date_et",
                "home_team",
                "away_team",
                "home_team_zh",
                "away_team_zh",
                "scoreline",
            ],
            as_index=False,
        )
        .agg(
            best_decimal_odds=("decimal_odds", "max"),
            average_decimal_odds=("decimal_odds", "mean"),
            raw_market_implied_probability=("raw_implied_probability", "mean"),
            bookmaker_count=("bookmaker_key", "nunique"),
            latest_fetched_at=("fetched_at", "max"),
            source_names=("source_name", lambda values: "|".join(sorted(set(map(str, values))))),
            source_urls=("source_url", lambda values: "|".join(sorted(set(map(str, values))))),
            source_match_ids=(
                "source_match_id",
                lambda values: "|".join(
                    sorted({str(value) for value in values if pd.notna(value)})
                ),
            ),
        )
        .sort_values(["match_no", "scoreline"])
        .reset_index(drop=True)
    )
    implied_sum = features.groupby("match_no")["raw_market_implied_probability"].transform("sum")
    features["listed_score_market_overround_proxy"] = implied_sum - 1.0
    features["listed_score_fair_probability"] = (
        features["raw_market_implied_probability"] / implied_sum
    )
    return features


def normalize_score_odds_snapshots(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    normalized = frame.copy()
    if "source_match_id" not in normalized.columns:
        normalized["source_match_id"] = normalized["source_url"].map(
            extract_sporttery_match_id_from_url
        )
    if "source_match_id" in normalized.columns:
        normalized["source_match_id"] = normalized["source_match_id"].astype("string")
    return normalized


def normalize_score_odds_status(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    normalized = frame.copy()
    if "source_match_id" not in normalized.columns:
        normalized["source_match_id"] = normalized["source_url"].map(
            extract_sporttery_match_id_from_url
        )
    if "source_match_id" in normalized.columns:
        normalized["source_match_id"] = normalized["source_match_id"].astype("string")
    return normalized


def merge_score_odds_snapshots(
    previous_snapshots: pd.DataFrame,
    new_snapshots: pd.DataFrame,
) -> pd.DataFrame:
    previous_snapshots = normalize_score_odds_snapshots(previous_snapshots)
    new_snapshots = normalize_score_odds_snapshots(new_snapshots)
    if previous_snapshots.empty:
        return new_snapshots
    if new_snapshots.empty:
        return previous_snapshots

    combined = pd.concat([previous_snapshots, new_snapshots], ignore_index=True)
    dedupe_columns = [
        "match_no",
        "scoreline",
        "bookmaker_key",
        "source_match_id",
        "source_url",
    ]
    combined = combined.drop_duplicates(subset=dedupe_columns, keep="last")
    return combined.sort_values(["match_no", "scoreline", "bookmaker_key"]).reset_index(drop=True)


def merge_score_odds_status(
    previous_status: pd.DataFrame,
    new_status: pd.DataFrame,
) -> pd.DataFrame:
    previous_status = normalize_score_odds_status(previous_status)
    new_status = normalize_score_odds_status(new_status)
    if previous_status.empty:
        return new_status
    if new_status.empty:
        return previous_status

    combined = pd.concat([previous_status, new_status], ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["match_no", "source_name", "source_match_id"],
        keep="last",
    )
    return combined.sort_values(["match_no", "source_name"]).reset_index(drop=True)


def prepare_score_odds_features(
    *,
    fixtures_path=FIXTURES_PATH,
    match_limit: int = DEFAULT_MATCH_LIMIT,
    discover_sporttery: bool = True,
    skip_existing_sporttery: bool = False,
    score_odds_snapshots_path=SCORE_ODDS_SNAPSHOTS_PATH,
    score_odds_features_path=SCORE_ODDS_FEATURES_PATH,
    collection_status_path=SCORE_ODDS_COLLECTION_STATUS_PATH,
) -> ScoreOddsPipelineOutputs:
    ensure_project_directories()
    fixtures = pd.read_parquet(fixtures_path)
    if discover_sporttery:
        try:
            sporttery_match_ids = discover_sporttery_match_metadata(fixtures)
        except Exception:
            sporttery_match_ids = {}
        fixtures = add_sporttery_match_ids_to_fixtures(fixtures, sporttery_match_ids)

    previous_snapshots = pd.DataFrame()
    previous_status = pd.DataFrame()
    existing_sporttery_match_ids: set[str] = set()
    if skip_existing_sporttery and score_odds_snapshots_path.exists():
        previous_snapshots = normalize_score_odds_snapshots(
            pd.read_parquet(score_odds_snapshots_path)
        )
        if collection_status_path.exists():
            previous_status = normalize_score_odds_status(pd.read_parquet(collection_status_path))
        if "source_match_id" in previous_snapshots.columns:
            existing_sporttery_match_ids = set(
                previous_snapshots.loc[
                    previous_snapshots["source_name"].eq(SPORTTERY_SOURCE_NAME),
                    "source_match_id",
                ]
                .dropna()
                .astype(str)
            )

    snapshots, status = build_score_odds_snapshots(
        fixtures,
        match_limit=match_limit,
        existing_sporttery_match_ids=existing_sporttery_match_ids,
    )
    if skip_existing_sporttery:
        snapshots = merge_score_odds_snapshots(previous_snapshots, snapshots)
        status = merge_score_odds_status(previous_status, status)
    features = build_score_odds_features(snapshots)

    snapshots.to_parquet(score_odds_snapshots_path, index=False)
    features.to_parquet(score_odds_features_path, index=False)
    status.to_parquet(collection_status_path, index=False)

    return ScoreOddsPipelineOutputs(
        score_odds_snapshots_path=str(score_odds_snapshots_path),
        score_odds_features_path=str(score_odds_features_path),
        collection_status_path=str(collection_status_path),
        snapshot_rows=len(snapshots),
        feature_rows=len(features),
        status_rows=len(status),
        collected_matches=(
            int(status.loc[status["status"].eq("collected"), "match_no"].nunique())
            if not status.empty
            else 0
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect correct-score market odds.")
    parser.add_argument("--limit", type=int, default=DEFAULT_MATCH_LIMIT)
    parser.add_argument(
        "--skip-existing-sporttery",
        action="store_true",
        help="Skip Sporttery mids already present in the local score-odds snapshot file.",
    )
    parser.add_argument(
        "--no-discover-sporttery",
        action="store_true",
        help="Disable Sporttery match-list discovery and use the built-in mid mapping only.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    outputs = prepare_score_odds_features(
        match_limit=args.limit,
        discover_sporttery=not args.no_discover_sporttery,
        skip_existing_sporttery=args.skip_existing_sporttery,
    )
    for key, value in asdict(outputs).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
