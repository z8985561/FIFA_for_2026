import pandas as pd

from src.world_cup_identity import (
    build_world_cup_teams_master,
    clean_player_name,
    extract_rankings_from_lines,
    parse_birth_age,
    team_id_from_name,
)


def test_extract_rankings_from_lines_parses_world_cup_aliases() -> None:
    lines = [
        "1. France",
        "16. USA",
        "22. Trkiye",
        "41. Czechia",
        "46. Congo DR",
        "82. Curaao",
    ]

    rankings = extract_rankings_from_lines(lines)

    assert rankings == [
        (1, "France"),
        (16, "United States"),
        (22, "Turkey"),
        (41, "Czech Republic"),
        (46, "DR Congo"),
        (82, "Curaçao"),
    ]


def test_parse_birth_age_extracts_date_and_age() -> None:
    birth_date, age = parse_birth_age("May 17, 2000 (aged 26)")

    assert str(birth_date) == "2000-05-17"
    assert age == 26


def test_clean_player_name_detects_captain_flag() -> None:
    player_name, captain = clean_player_name("Ronwen Williams (captain)")

    assert player_name == "Ronwen Williams"
    assert captain is True


def test_team_id_from_name_uses_ascii_safe_slug() -> None:
    assert team_id_from_name("Curaçao") == "curacao"


def test_build_world_cup_teams_master_combines_identity_layers() -> None:
    fixtures = pd.DataFrame(
        {
            "group_name": ["Group C", "Group C"],
            "home_team": ["Brazil", "Haiti"],
            "away_team": ["Morocco", "Scotland"],
        }
    )
    rankings = pd.DataFrame(
        {
            "fifa_rank": [6, 8, 43, 83],
            "team_name": ["Brazil", "Morocco", "Scotland", "Haiti"],
            "ranking_source": ["ESPN"] * 4,
            "ranking_date": [pd.Timestamp("2026-04-01").date()] * 4,
            "points": [None] * 4,
        }
    )
    ratings = pd.DataFrame(
        {
            "team_name": ["Brazil", "Morocco", "Scotland", "Haiti"],
            "latest_match_date": [pd.Timestamp("2026-06-06").date()] * 4,
            "latest_elo": [1926.04, 1837.26, 1690.63, 1600.07],
            "matches_played": [1059, 617, 851, 510],
        }
    )
    historical_teams = pd.DataFrame(
        {
            "team_name": ["Brazil", "Morocco", "Scotland", "Haiti"],
            "first_match_date": [pd.Timestamp("1914-09-20").date()] * 4,
            "last_match_date": [pd.Timestamp("2026-06-06").date()] * 4,
            "total_matches": [1059, 617, 851, 510],
        }
    )
    squads = pd.DataFrame(
        {
            "team_id": ["brazil", "morocco", "scotland", "haiti"],
            "team_name": ["Brazil", "Morocco", "Scotland", "Haiti"],
            "player_name": ["A", "B", "C", "D"],
            "age": [28, 27, 29, 26],
            "caps": [40, 35, 20, 15],
        }
    )

    teams_master = build_world_cup_teams_master(
        fixtures=fixtures,
        rankings=rankings,
        ratings=ratings,
        historical_teams=historical_teams,
        squads=squads,
    )

    assert len(teams_master) == 4
    assert set(teams_master["confederation"]) == {"CAF", "CONCACAF", "CONMEBOL", "UEFA"}
    assert teams_master.loc[teams_master["team_name"] == "Brazil", "fifa_rank"].item() == 6
