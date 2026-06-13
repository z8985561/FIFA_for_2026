from src.team_names import ascii_fold, normalize_team_name


def test_normalize_team_name_handles_common_aliases() -> None:
    assert normalize_team_name("USA") == "United States"
    assert normalize_team_name("Czechia") == "Czech Republic"
    assert normalize_team_name("Curacao") == "Curaçao"
    assert normalize_team_name("Türkiye") == "Turkey"
    assert normalize_team_name("韩国") == "South Korea"
    assert normalize_team_name("科特迪瓦") == "Ivory Coast"
    assert normalize_team_name("民主刚果") == "DR Congo"


def test_ascii_fold_removes_diacritics() -> None:
    assert ascii_fold("Curaçao") == "Curacao"
