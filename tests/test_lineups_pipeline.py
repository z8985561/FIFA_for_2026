from src.lineups_pipeline import build_predicted_lineups


def test_build_predicted_lineups_returns_first_four_match_lineups() -> None:
    lineups = build_predicted_lineups()

    assert len(lineups) == 88
    assert lineups["match_no"].nunique() == 4
    assert lineups["team_name"].nunique() == 8
    assert set(lineups["lineup_status"]) == {"predicted"}
    assert lineups.groupby(["match_no", "team_name"]).size().eq(11).all()


def test_build_predicted_lineups_includes_chinese_team_names() -> None:
    lineups = build_predicted_lineups()
    korea = lineups.loc[lineups["team_name"].eq("South Korea")].iloc[0]

    assert korea["team_name_zh"] == "韩国"
    assert korea["home_team_zh"] == "韩国"
    assert korea["away_team_zh"] == "捷克"
