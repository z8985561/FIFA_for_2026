from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date
from io import StringIO

import duckdb
import pandas as pd
import requests
from lxml import html

from .data_pipeline import load_world_cup_fixtures
from .project_paths import (
    DATABASE_PATH,
    FIFA_RANKINGS_PATH,
    RATINGS_PATH,
    RAW_FIFA_RANKINGS_PATH,
    RAW_WORLD_CUP_SQUADS_PATH,
    SQUADS_2026_PATH,
    TEAMS_PATH,
    WORLD_CUP_TEAMS_2026_PATH,
    ensure_project_directories,
)
from .schema import apply_schema
from .team_names import ascii_fold, normalize_team_name

ESPN_RANKINGS_URL = "https://www.espn.com/soccer/story/_/id/46664763/fifa-mens-top-50-world-rankings"
WIKIPEDIA_SQUADS_URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads"
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}
RANKING_LINE_PATTERN = re.compile(r"^(\d+)\.\s+(.+?)$")
PLAYER_AGE_PATTERN = re.compile(r"^(?P<date>.+?)\s+\(aged\s+(?P<age>\d+)\)$")

CONFEDERATION_BY_TEAM = {
    "Algeria": "CAF",
    "Argentina": "CONMEBOL",
    "Australia": "AFC",
    "Austria": "UEFA",
    "Belgium": "UEFA",
    "Bosnia and Herzegovina": "UEFA",
    "Brazil": "CONMEBOL",
    "Canada": "CONCACAF",
    "Cape Verde": "CAF",
    "Colombia": "CONMEBOL",
    "Croatia": "UEFA",
    "Cura\u00e7ao": "CONCACAF",
    "Czech Republic": "UEFA",
    "DR Congo": "CAF",
    "Ecuador": "CONMEBOL",
    "Egypt": "CAF",
    "England": "UEFA",
    "France": "UEFA",
    "Germany": "UEFA",
    "Ghana": "CAF",
    "Haiti": "CONCACAF",
    "Iran": "AFC",
    "Iraq": "AFC",
    "Ivory Coast": "CAF",
    "Japan": "AFC",
    "Jordan": "AFC",
    "Mexico": "CONCACAF",
    "Morocco": "CAF",
    "Netherlands": "UEFA",
    "New Zealand": "OFC",
    "Norway": "UEFA",
    "Panama": "CONCACAF",
    "Paraguay": "CONMEBOL",
    "Portugal": "UEFA",
    "Qatar": "AFC",
    "Saudi Arabia": "AFC",
    "Scotland": "UEFA",
    "Senegal": "CAF",
    "South Africa": "CAF",
    "South Korea": "AFC",
    "Spain": "UEFA",
    "Sweden": "UEFA",
    "Switzerland": "UEFA",
    "Tunisia": "CAF",
    "Turkey": "UEFA",
    "United States": "CONCACAF",
    "Uruguay": "CONMEBOL",
    "Uzbekistan": "AFC",
}


@dataclass(frozen=True)
class IdentityOutputs:
    rankings_path: str
    squads_path: str
    teams_path: str
    database_path: str


def team_id_from_name(team_name: str) -> str:
    normalized = ascii_fold(normalize_team_name(team_name)).lower()
    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")


def download_rankings_page() -> str:
    response = requests.get(ESPN_RANKINGS_URL, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()
    RAW_FIFA_RANKINGS_PATH.write_text(response.text, encoding="utf-8")
    return response.text


def download_squads_page() -> str:
    response = requests.get(WIKIPEDIA_SQUADS_URL, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()
    RAW_WORLD_CUP_SQUADS_PATH.write_text(response.text, encoding="utf-8")
    return response.text


def load_rankings_page() -> str:
    if RAW_FIFA_RANKINGS_PATH.exists():
        return RAW_FIFA_RANKINGS_PATH.read_text(encoding="utf-8")
    return download_rankings_page()


def load_squads_page() -> str:
    if RAW_WORLD_CUP_SQUADS_PATH.exists():
        return RAW_WORLD_CUP_SQUADS_PATH.read_text(encoding="utf-8")
    return download_squads_page()


def extract_rankings_from_lines(lines: list[str]) -> list[tuple[int, str]]:
    rankings: list[tuple[int, str]] = []
    for line in lines:
        matched = RANKING_LINE_PATTERN.match(line)
        if not matched:
            continue
        fifa_rank = int(matched.group(1))
        team_name = normalize_team_name(matched.group(2))
        rankings.append((fifa_rank, team_name))
    return rankings


def parse_rankings_snapshot(html_text: str) -> pd.DataFrame:
    document = html.fromstring(html_text)
    paragraph_lines = []
    for paragraph in document.xpath("//p"):
        line = " ".join(part.strip() for part in paragraph.xpath(".//text()") if part.strip())
        if line:
            paragraph_lines.append(line)

    extracted = extract_rankings_from_lines(paragraph_lines)
    rankings = pd.DataFrame(extracted, columns=["fifa_rank", "team_name"]).drop_duplicates(
        subset=["team_name"]
    )
    issue_date = document.xpath("//meta[@name='DC.date.issued']/@content")
    ranking_date = pd.to_datetime(issue_date[0]).date() if issue_date else date(2026, 4, 1)
    rankings["ranking_source"] = "ESPN FIFA Men's Top 50 World Rankings"
    rankings["ranking_date"] = ranking_date
    rankings["points"] = pd.Series([None] * len(rankings), dtype="float64")
    return rankings.sort_values("fifa_rank").reset_index(drop=True)


def parse_birth_age(value: str) -> tuple[date | None, int | None]:
    cleaned = " ".join(str(value).split())
    matched = PLAYER_AGE_PATTERN.match(cleaned)
    if not matched:
        return None, None
    birth_date = pd.to_datetime(matched.group("date")).date()
    return birth_date, int(matched.group("age"))


def clean_player_name(value: str) -> tuple[str, bool]:
    cleaned = " ".join(str(value).split())
    captain = "(captain)" in cleaned.lower()
    cleaned = re.sub(r"\s*\(captain\)\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip(), captain


def parse_squads_snapshot(html_text: str) -> pd.DataFrame:
    document = html.fromstring(html_text)
    nodes = document.xpath("//h2|//h3|//table[contains(@class, 'wikitable')]")
    squad_rows: list[dict[str, object]] = []
    current_group: str | None = None
    current_team: str | None = None
    team_table_count = 0

    for node in nodes:
        if node.tag == "h2":
            headline = " ".join(part.strip() for part in node.xpath(".//text()") if part.strip())
            if headline.startswith("Group "):
                current_group = headline
            continue
        if node.tag == "h3":
            current_team = normalize_team_name(
                " ".join(part.strip() for part in node.xpath(".//text()") if part.strip())
            )
            continue
        if current_group is None or current_team is None or team_table_count >= 48:
            continue

        team_table_count += 1
        squad_table = pd.read_html(StringIO(html.tostring(node, encoding="unicode")))[0]
        squad_table.columns = [str(column) for column in squad_table.columns]
        for row in squad_table.to_dict(orient="records"):
            player_name, captain = clean_player_name(row["Player"])
            birth_date, age = parse_birth_age(str(row["Date of birth (age)"]))
            squad_rows.append(
                {
                    "team_id": team_id_from_name(current_team),
                    "team_name": current_team,
                    "group_name": current_group,
                    "shirt_number": int(row["No."]),
                    "position": str(row["Pos."]).strip(),
                    "player_name": player_name,
                    "captain": captain,
                    "date_of_birth": birth_date,
                    "age": age,
                    "caps": int(row["Caps"]),
                    "goals": int(row["Goals"]),
                    "club": " ".join(str(row["Club"]).split()),
                    "source_url": WIKIPEDIA_SQUADS_URL,
                }
            )

    return pd.DataFrame(squad_rows).sort_values(
        ["group_name", "team_name", "shirt_number"]
    ).reset_index(drop=True)


def load_or_build_base_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    if RATINGS_PATH.exists() and TEAMS_PATH.exists():
        return pd.read_parquet(RATINGS_PATH), pd.read_parquet(TEAMS_PATH)
    from .data_pipeline import prepare_research_data

    prepare_research_data()
    return pd.read_parquet(RATINGS_PATH), pd.read_parquet(TEAMS_PATH)


def build_world_cup_teams_master(
    fixtures: pd.DataFrame,
    rankings: pd.DataFrame,
    ratings: pd.DataFrame,
    historical_teams: pd.DataFrame,
    squads: pd.DataFrame,
) -> pd.DataFrame:
    qualified = (
        pd.concat(
            [
                fixtures[["group_name", "home_team"]].rename(columns={"home_team": "team_name"}),
                fixtures[["group_name", "away_team"]].rename(columns={"away_team": "team_name"}),
            ],
            ignore_index=True,
        )
        .loc[lambda frame: frame["group_name"].notna() & frame["team_name"].ne("TBD")]
        .drop_duplicates()
        .assign(
            team_name=lambda frame: frame["team_name"].map(normalize_team_name),
            team_id=lambda frame: frame["team_name"].map(team_id_from_name),
            confederation=lambda frame: frame["team_name"].map(CONFEDERATION_BY_TEAM),
        )
    )

    squad_summary = squads.groupby(["team_id", "team_name"], as_index=False).agg(
        squad_size=("player_name", "count"),
        squad_average_age=("age", "mean"),
        squad_total_caps=("caps", "sum"),
    )

    merged = (
        qualified.merge(rankings, on="team_name", how="left")
        .merge(ratings, on="team_name", how="left")
        .merge(historical_teams, on="team_name", how="left")
        .merge(squad_summary, on=["team_id", "team_name"], how="left")
    )
    merged["squad_average_age"] = merged["squad_average_age"].round(2)
    return merged.sort_values(["group_name", "team_name"]).reset_index(drop=True)


def write_identity_tables(
    rankings: pd.DataFrame,
    squads: pd.DataFrame,
    teams_master: pd.DataFrame,
) -> None:
    connection = duckdb.connect(str(DATABASE_PATH))
    try:
        apply_schema(
            connection,
            table_names=("fifa_rankings_2026", "squads_2026", "world_cup_teams_2026"),
        )
        connection.register("rankings_frame", rankings)
        connection.register("squads_frame", squads)
        connection.register("teams_master_frame", teams_master)
        connection.execute(
            """
            INSERT INTO fifa_rankings_2026
            SELECT fifa_rank, team_name, ranking_source, ranking_date, points
            FROM rankings_frame
            """
        )
        connection.execute(
            """
            INSERT INTO squads_2026
            SELECT
                team_id,
                team_name,
                group_name,
                shirt_number,
                position,
                player_name,
                captain,
                date_of_birth,
                age,
                caps,
                goals,
                club,
                source_url
            FROM squads_frame
            """
        )
        connection.execute(
            """
            INSERT INTO world_cup_teams_2026
            SELECT
                team_id,
                team_name,
                group_name,
                confederation,
                fifa_rank,
                ranking_source,
                ranking_date,
                latest_elo,
                latest_match_date,
                matches_played,
                first_match_date,
                last_match_date,
                total_matches,
                squad_size,
                squad_average_age,
                squad_total_caps
            FROM teams_master_frame
            """
        )
    finally:
        connection.close()


def prepare_world_cup_identity_data() -> IdentityOutputs:
    ensure_project_directories()

    rankings = parse_rankings_snapshot(load_rankings_page())
    squads = parse_squads_snapshot(load_squads_page())
    fixtures = load_world_cup_fixtures()
    ratings, historical_teams = load_or_build_base_tables()
    teams_master = build_world_cup_teams_master(
        fixtures=fixtures,
        rankings=rankings,
        ratings=ratings,
        historical_teams=historical_teams,
        squads=squads,
    )

    rankings.to_parquet(FIFA_RANKINGS_PATH, index=False)
    squads.to_parquet(SQUADS_2026_PATH, index=False)
    teams_master.to_parquet(WORLD_CUP_TEAMS_2026_PATH, index=False)
    write_identity_tables(rankings, squads, teams_master)

    return IdentityOutputs(
        rankings_path=str(FIFA_RANKINGS_PATH),
        squads_path=str(SQUADS_2026_PATH),
        teams_path=str(WORLD_CUP_TEAMS_2026_PATH),
        database_path=str(DATABASE_PATH),
    )


def main() -> None:
    outputs = prepare_world_cup_identity_data()
    for key, value in asdict(outputs).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
