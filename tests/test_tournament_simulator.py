import pandas as pd

from src.tournament_simulator import (
    ROUND_OF_32_SLOTS,
    resolve_round_of_32_slots,
    run_tournament_simulation,
)


def test_resolve_round_of_32_slots_assigns_unique_third_place_teams() -> None:
    slots = {
        "1A": "A1",
        "2A": "A2",
        "3A": "A3",
        "1B": "B1",
        "2B": "B2",
        "3B": "B3",
        "1C": "C1",
        "2C": "C2",
        "3C": "C3",
        "1D": "D1",
        "2D": "D2",
        "3D": "D3",
        "1E": "E1",
        "2E": "E2",
        "3E": "E3",
        "1F": "F1",
        "2F": "F2",
        "3F": "F3",
        "1G": "G1",
        "2G": "G2",
        "3G": "G3",
        "1H": "H1",
        "2H": "H2",
        "3H": "H3",
        "1I": "I1",
        "2I": "I2",
        "3I": "I3",
        "1J": "J1",
        "2J": "J2",
        "3J": "J3",
        "1K": "K1",
        "2K": "K2",
        "3K": "K3",
        "1L": "L1",
        "2L": "L2",
        "3L": "L3",
    }

    resolved = resolve_round_of_32_slots(slots)
    third_place_teams = [
        team
        for matchup in resolved.values()
        for team in matchup
        if team.endswith("3")
    ]

    assert set(resolved) == set(ROUND_OF_32_SLOTS)
    assert len(third_place_teams) == len(set(third_place_teams))


def test_run_tournament_simulation_returns_stage_probabilities() -> None:
    teams = []
    predictions = []
    match_no = 1
    for group_letter in "ABCDEFGHIJKL":
        group_name = f"Group {group_letter}"
        names = [f"{group_letter}{index}" for index in range(1, 5)]
        for index, team in enumerate(names):
            teams.append(
                {
                    "team_name": team,
                    "group_name": group_name,
                    "latest_elo": 1800.0 - index * 50,
                }
            )
        for home, away in (
            (names[0], names[1]),
            (names[2], names[3]),
            (names[0], names[2]),
            (names[1], names[3]),
            (names[0], names[3]),
            (names[1], names[2]),
        ):
            predictions.append(
                {
                    "match_no": match_no,
                    "home_team": home,
                    "away_team": away,
                    "home_win_probability": 0.55,
                    "draw_probability": 0.25,
                    "away_win_probability": 0.20,
                }
            )
            match_no += 1

    result = run_tournament_simulation(
        pd.DataFrame(predictions),
        pd.DataFrame(teams),
        simulations=20,
        seed=7,
    )

    assert len(result) == 48
    assert result["champion_probability"].between(0.0, 1.0).all()
    assert round(result["champion_probability"].sum(), 6) == 1.0
    assert result["round_of_32_probability"].sum() == 32.0
