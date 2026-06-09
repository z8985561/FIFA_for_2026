from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from .elo import EloConfig, expected_home_score
from .enhanced_model import prepare_enhanced_outputs
from .project_paths import (
    ENHANCED_PREDICTIONS_PATH,
    TOURNAMENT_SIMULATION_PATH,
    WORLD_CUP_TEAMS_2026_PATH,
    ensure_project_directories,
)

GROUPS = tuple(f"Group {letter}" for letter in "ABCDEFGHIJKL")

ROUND_OF_32_SLOTS: dict[int, tuple[str, str]] = {
    73: ("2A", "2B"),
    74: ("1E", "3ABCDF"),
    75: ("1F", "2C"),
    76: ("1C", "2F"),
    77: ("1I", "3CDFGH"),
    78: ("2E", "2I"),
    79: ("1A", "3CEFHI"),
    80: ("1L", "3EHIJK"),
    81: ("1D", "3BEFIJ"),
    82: ("1G", "3AEHIJ"),
    83: ("2K", "2L"),
    84: ("1H", "2J"),
    85: ("1B", "3EFGIJ"),
    86: ("1J", "2H"),
    87: ("1K", "3DEIJL"),
    88: ("2D", "2G"),
}

KNOCKOUT_BRACKET: dict[int, tuple[str, str]] = {
    89: ("W74", "W77"),
    90: ("W73", "W75"),
    91: ("W76", "W78"),
    92: ("W79", "W80"),
    93: ("W83", "W84"),
    94: ("W81", "W82"),
    95: ("W86", "W88"),
    96: ("W85", "W87"),
    97: ("W89", "W90"),
    98: ("W93", "W94"),
    99: ("W91", "W92"),
    100: ("W95", "W96"),
    101: ("W97", "W98"),
    102: ("W99", "W100"),
    104: ("W101", "W102"),
}


@dataclass
class TeamStanding:
    team_name: str
    group_name: str
    points: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    elo: float = 1500.0
    random_tiebreaker: float = 0.0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against


@dataclass(frozen=True)
class SimulationOutputs:
    output_path: str
    simulations: int
    seed: int
    rows: int


def group_letter(group_name: str) -> str:
    return group_name.removeprefix("Group ").strip()


def ensure_simulation_inputs() -> None:
    if not ENHANCED_PREDICTIONS_PATH.exists():
        prepare_enhanced_outputs()


def outcome_goals(outcome: str, rng: np.random.Generator) -> tuple[int, int]:
    if outcome == "draw":
        goals = int(rng.choice([0, 1, 2], p=[0.25, 0.55, 0.20]))
        return goals, goals

    margin = int(rng.choice([1, 2, 3], p=[0.70, 0.22, 0.08]))
    loser_goals = int(rng.choice([0, 1, 2], p=[0.55, 0.35, 0.10]))
    winner_goals = loser_goals + margin
    if outcome == "home_win":
        return winner_goals, loser_goals
    return loser_goals, winner_goals


def add_match_result(
    standings: dict[str, TeamStanding],
    home_team: str,
    away_team: str,
    home_goals: int,
    away_goals: int,
) -> None:
    home = standings[home_team]
    away = standings[away_team]
    home.goals_for += home_goals
    home.goals_against += away_goals
    away.goals_for += away_goals
    away.goals_against += home_goals

    if home_goals > away_goals:
        home.points += 3
        home.wins += 1
        away.losses += 1
    elif home_goals < away_goals:
        away.points += 3
        away.wins += 1
        home.losses += 1
    else:
        home.points += 1
        away.points += 1
        home.draws += 1
        away.draws += 1


def rank_group(standings: list[TeamStanding]) -> list[TeamStanding]:
    return sorted(
        standings,
        key=lambda item: (
            item.points,
            item.goal_difference,
            item.goals_for,
            item.wins,
            item.elo,
            item.random_tiebreaker,
        ),
        reverse=True,
    )


def rank_third_place_teams(teams: list[TeamStanding]) -> list[TeamStanding]:
    return sorted(
        teams,
        key=lambda item: (
            item.points,
            item.goal_difference,
            item.goals_for,
            item.wins,
            item.elo,
            item.random_tiebreaker,
        ),
        reverse=True,
    )


def simulate_group_stage(
    predictions: pd.DataFrame,
    team_profiles: pd.DataFrame,
    rng: np.random.Generator,
) -> tuple[dict[str, TeamStanding], dict[str, str]]:
    group_map = team_profiles.set_index("team_name")["group_name"].to_dict()
    standings = {
        row.team_name: TeamStanding(
            team_name=row.team_name,
            group_name=row.group_name,
            elo=float(row.latest_elo),
            random_tiebreaker=float(rng.random()),
        )
        for row in team_profiles.itertuples(index=False)
    }

    for row in predictions.sort_values("match_no").itertuples(index=False):
        probabilities = np.array(
            [
                row.home_win_probability,
                row.draw_probability,
                row.away_win_probability,
            ],
            dtype=float,
        )
        probabilities = probabilities / probabilities.sum()
        outcome = str(rng.choice(["home_win", "draw", "away_win"], p=probabilities))
        home_goals, away_goals = outcome_goals(outcome, rng)
        add_match_result(standings, row.home_team, row.away_team, home_goals, away_goals)

    slots: dict[str, str] = {}
    third_place: list[TeamStanding] = []
    for group_name in GROUPS:
        group_teams = [
            team for team in standings.values() if group_map[team.team_name] == group_name
        ]
        ranked = rank_group(group_teams)
        letter = group_letter(group_name)
        slots[f"1{letter}"] = ranked[0].team_name
        slots[f"2{letter}"] = ranked[1].team_name
        third_place.append(ranked[2])

    best_thirds = rank_third_place_teams(third_place)[:8]
    for third in best_thirds:
        slots[f"3{group_letter(third.group_name)}"] = third.team_name

    return standings, slots


def resolve_third_place_slot(
    slot: str,
    group_slots: dict[str, str],
    used_thirds: set[str],
) -> str:
    eligible_letters = slot.removeprefix("3")
    available = [
        (letter, group_slots[f"3{letter}"])
        for letter in eligible_letters
        if f"3{letter}" in group_slots and group_slots[f"3{letter}"] not in used_thirds
    ]
    if not available:
        remaining = [
            (key.removeprefix("3"), value)
            for key, value in group_slots.items()
            if key.startswith("3") and value not in used_thirds
        ]
        if not remaining:
            raise ValueError(f"No third-place team available for slot {slot}")
        available = remaining

    # The official slot labels constrain eligible groups. Until the full FIFA third-place
    # allocation table is encoded, use alphabetical order for a deterministic assignment.
    selected_team = sorted(available, key=lambda item: item[0])[0][1]
    used_thirds.add(selected_team)
    return selected_team


def assign_third_place_slots(
    group_slots: dict[str, str],
) -> dict[tuple[int, int], str]:
    third_entries = [
        (match_no, side_index, slot)
        for match_no, matchup in ROUND_OF_32_SLOTS.items()
        for side_index, slot in enumerate(matchup)
        if slot.startswith("3")
    ]
    third_team_by_group = {
        key.removeprefix("3"): value
        for key, value in group_slots.items()
        if key.startswith("3")
    }

    def candidates(slot: str, used: set[str]) -> list[str]:
        eligible_letters = slot.removeprefix("3")
        return [
            third_team_by_group[letter]
            for letter in eligible_letters
            if letter in third_team_by_group and third_team_by_group[letter] not in used
        ]

    def search(
        remaining: list[tuple[int, int, str]],
        assigned: dict[tuple[int, int], str],
        used: set[str],
    ) -> dict[tuple[int, int], str] | None:
        if not remaining:
            return assigned

        remaining = sorted(remaining, key=lambda entry: len(candidates(entry[2], used)))
        match_no, side_index, slot = remaining[0]
        for team in candidates(slot, used):
            result = search(
                remaining[1:],
                {**assigned, (match_no, side_index): team},
                used | {team},
            )
            if result is not None:
                return result
        return None

    assignment = search(third_entries, {}, set())
    if assignment is not None:
        return assignment

    used: set[str] = set()
    fallback_assignment: dict[tuple[int, int], str] = {}
    for match_no, side_index, slot in third_entries:
        fallback_assignment[(match_no, side_index)] = resolve_third_place_slot(
            slot,
            group_slots,
            used,
        )
    return fallback_assignment


def resolve_round_of_32_slots(group_slots: dict[str, str]) -> dict[int, tuple[str, str]]:
    third_assignment = assign_third_place_slots(group_slots)
    resolved: dict[int, tuple[str, str]] = {}
    for match_no, (home_slot, away_slot) in ROUND_OF_32_SLOTS.items():
        home_team = (
            third_assignment[(match_no, 0)]
            if home_slot.startswith("3")
            else group_slots[home_slot]
        )
        away_team = (
            third_assignment[(match_no, 1)]
            if away_slot.startswith("3")
            else group_slots[away_slot]
        )
        resolved[match_no] = (home_team, away_team)
    return resolved


def knockout_win_probability(team_a: str, team_b: str, elo_map: dict[str, float]) -> float:
    config = EloConfig()
    return expected_home_score(
        float(elo_map.get(team_a, config.initial_rating)),
        float(elo_map.get(team_b, config.initial_rating)),
        neutral=True,
        config=config,
    )


def simulate_knockout_match(
    team_a: str,
    team_b: str,
    elo_map: dict[str, float],
    rng: np.random.Generator,
) -> str:
    probability_a = knockout_win_probability(team_a, team_b, elo_map)
    return team_a if float(rng.random()) < probability_a else team_b


def simulate_knockout_stage(
    group_slots: dict[str, str],
    elo_map: dict[str, float],
    rng: np.random.Generator,
) -> dict[str, set[str] | str]:
    match_winners: dict[int, str] = {}
    round_of_32 = resolve_round_of_32_slots(group_slots)
    round_of_32_teams = {team for matchup in round_of_32.values() for team in matchup}

    for match_no, (team_a, team_b) in round_of_32.items():
        match_winners[match_no] = simulate_knockout_match(team_a, team_b, elo_map, rng)

    stage_teams: dict[str, set[str] | str] = {
        "round_of_32": round_of_32_teams,
        "round_of_16": {match_winners[match_no] for match_no in range(73, 89)},
    }

    for match_no in range(89, 105):
        if match_no == 103:
            continue
        team_a_ref, team_b_ref = KNOCKOUT_BRACKET[match_no]
        team_a = match_winners[int(team_a_ref.removeprefix("W"))]
        team_b = match_winners[int(team_b_ref.removeprefix("W"))]
        match_winners[match_no] = simulate_knockout_match(team_a, team_b, elo_map, rng)

        if match_no == 96:
            stage_teams["quarter_final"] = {match_winners[number] for number in range(89, 97)}
        elif match_no == 100:
            stage_teams["semi_final"] = {match_winners[number] for number in range(97, 101)}
        elif match_no == 102:
            stage_teams["final"] = {match_winners[101], match_winners[102]}
        elif match_no == 104:
            stage_teams["champion"] = match_winners[104]

    return stage_teams


def empty_counts(team_names: list[str]) -> dict[str, dict[str, int]]:
    stages = [
        "group_winner",
        "group_runner_up",
        "third_place_advance",
        "round_of_32",
        "round_of_16",
        "quarter_final",
        "semi_final",
        "final",
        "champion",
    ]
    return {team: {stage: 0 for stage in stages} for team in team_names}


def run_tournament_simulation(
    predictions: pd.DataFrame,
    team_profiles: pd.DataFrame,
    *,
    simulations: int,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    team_names = sorted(team_profiles["team_name"].tolist())
    team_groups = team_profiles.set_index("team_name")["group_name"].to_dict()
    elo_map = team_profiles.set_index("team_name")["latest_elo"].to_dict()
    counts = empty_counts(team_names)

    for _ in range(simulations):
        _standings, group_slots = simulate_group_stage(predictions, team_profiles, rng)

        for letter in "ABCDEFGHIJKL":
            counts[group_slots[f"1{letter}"]]["group_winner"] += 1
            counts[group_slots[f"2{letter}"]]["group_runner_up"] += 1
            third_team = group_slots.get(f"3{letter}")
            if third_team:
                counts[third_team]["third_place_advance"] += 1

        knockout = simulate_knockout_stage(group_slots, elo_map, rng)
        for stage in (
            "round_of_32",
            "round_of_16",
            "quarter_final",
            "semi_final",
            "final",
        ):
            for team in knockout[stage]:
                counts[team][stage] += 1
        champion = str(knockout["champion"])
        counts[champion]["champion"] += 1

    rows: list[dict[str, Any]] = []
    for team in team_names:
        row = {
            "team_name": team,
            "group_name": team_groups[team],
            "simulations": simulations,
        }
        for stage, count in counts[team].items():
            row[f"{stage}_probability"] = count / simulations
        rows.append(row)

    return pd.DataFrame(rows).sort_values(
        ["champion_probability", "final_probability", "semi_final_probability"],
        ascending=[False, False, False],
    )


def prepare_tournament_simulation(
    *,
    simulations: int = 10000,
    seed: int = 20260609,
    output_path: str | None = None,
) -> SimulationOutputs:
    ensure_project_directories()
    ensure_simulation_inputs()

    predictions = pd.read_csv(ENHANCED_PREDICTIONS_PATH)
    team_profiles = pd.read_parquet(WORLD_CUP_TEAMS_2026_PATH)
    result = run_tournament_simulation(
        predictions,
        team_profiles,
        simulations=simulations,
        seed=seed,
    )

    path = (
        TOURNAMENT_SIMULATION_PATH
        if output_path is None
        else TOURNAMENT_SIMULATION_PATH.parent / output_path
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(path, index=False, encoding="utf-8-sig")
    return SimulationOutputs(
        output_path=str(path),
        simulations=simulations,
        seed=seed,
        rows=len(result),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulate the 2026 World Cup tournament path.")
    parser.add_argument("--simulations", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260609)
    parser.add_argument("--output")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    outputs = prepare_tournament_simulation(
        simulations=args.simulations,
        seed=args.seed,
        output_path=args.output,
    )
    for key, value in asdict(outputs).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
