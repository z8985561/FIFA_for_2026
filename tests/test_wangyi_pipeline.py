import pandas as pd

from src.wangyi_pipeline import validate_wangyi_outputs


def test_validate_wangyi_outputs_accepts_complete_team_sets() -> None:
    coaches = pd.DataFrame(
        {
            "team_id": [1, 2],
            "team_name": ["Mexico", "South Korea"],
            "manager_name_zh": ["阿吉雷", "洪明甫"],
            "manager_name_en": ["Javier Aguirre", "Myung-bo Hong"],
            "manager_id": [11, 22],
        }
    )
    squads = pd.DataFrame(
        {
            "team_id": [1] * 26 + [2] * 26,
            "team_name": ["Mexico"] * 26 + ["South Korea"] * 26,
            "position": ["GK"] * 52,
            "player_id": list(range(52)),
            "name_zh": [f"球员{i}" for i in range(52)],
            "name_en": [f"Player {i}" for i in range(52)],
            "shirt_no": [str(i) for i in range(52)],
            "age": [25] * 52,
            "goals": [0] * 52,
            "assists": [0] * 52,
            "yellow_cards": [0] * 52,
            "red_cards": [0] * 52,
            "is_suspended": [False] * 52,
        }
    )

    warnings = validate_wangyi_outputs(
        coaches,
        squads,
        expected_teams={"Mexico", "South Korea"},
    )

    assert warnings == []


def test_validate_wangyi_outputs_warns_on_abnormal_squad_size() -> None:
    coaches = pd.DataFrame(
        {
            "team_id": [1],
            "team_name": ["Jordan"],
            "manager_name_zh": ["教练"],
            "manager_name_en": ["Coach"],
            "manager_id": [11],
        }
    )
    squads = pd.DataFrame(
        {
            "team_id": [1] * 25,
            "team_name": ["Jordan"] * 25,
            "position": ["GK"] * 25,
            "player_id": list(range(25)),
            "name_zh": [f"球员{i}" for i in range(25)],
            "name_en": [f"Player {i}" for i in range(25)],
            "shirt_no": [str(i) for i in range(25)],
            "age": [25] * 25,
            "goals": [0] * 25,
            "assists": [0] * 25,
            "yellow_cards": [0] * 25,
            "red_cards": [0] * 25,
            "is_suspended": [False] * 25,
        }
    )

    warnings = validate_wangyi_outputs(
        coaches,
        squads,
        expected_teams={"Jordan"},
    )

    assert warnings == ["Abnormal squad sizes: Jordan=25"]
