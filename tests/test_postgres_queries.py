from src.postgres_queries import build_parser, qualified_name


def test_qualified_name_quotes_schema_and_relation() -> None:
    assert qualified_name("research", "matches") == '"research"."matches"'


def test_parser_accepts_top_rated_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["top-rated", "--limit", "5"])

    assert args.command == "top-rated"
    assert args.limit == 5


def test_parser_accepts_team_history_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["team-history", "--team", "Argentina", "--limit", "3"])

    assert args.command == "team-history"
    assert args.team == "Argentina"
    assert args.limit == 3


def test_parser_accepts_prediction_query_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["prediction-query", "--team", "Brazil", "--limit", "2"])

    assert args.command == "prediction-query"
    assert args.team == "Brazil"
    assert args.limit == 2


def test_parser_accepts_enhanced_prediction_query_command() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["enhanced-prediction-query", "--group-name", "Group C", "--limit", "4"]
    )

    assert args.command == "enhanced-prediction-query"
    assert args.group_name == "Group C"
    assert args.limit == 4


def test_parser_accepts_scoreline_query_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["scoreline-query", "--match-no", "1", "--limit", "10"])

    assert args.command == "scoreline-query"
    assert args.match_no == 1
    assert args.limit == 10


def test_parser_accepts_group_overview_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["group-overview", "--group-name", "Group C", "--output", "out.csv"])

    assert args.command == "group-overview"
    assert args.group_name == "Group C"
    assert args.output == "out.csv"


def test_parser_accepts_recent_form_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["recent-form", "--team", "Brazil", "--limit", "8"])

    assert args.command == "recent-form"
    assert args.team == "Brazil"
    assert args.limit == 8


def test_parser_accepts_team_vs_field_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["team-vs-field", "--team", "Argentina"])

    assert args.command == "team-vs-field"
    assert args.team == "Argentina"


def test_parser_accepts_group_strength_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["group-strength", "--group-name", "Group C"])

    assert args.command == "group-strength"
    assert args.group_name == "Group C"


def test_parser_accepts_prediction_extremes_command() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "prediction-extremes",
            "--mode",
            "lopsided",
            "--stage",
            "Group Stage",
            "--limit",
            "5",
        ]
    )

    assert args.command == "prediction-extremes"
    assert args.mode == "lopsided"
    assert args.stage == "Group Stage"
    assert args.limit == 5


def test_parser_accepts_world_cup_teams_command() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["world-cup-teams", "--group-name", "Group C", "--confederation", "CAF", "--limit", "5"]
    )

    assert args.command == "world-cup-teams"
    assert args.group_name == "Group C"
    assert args.confederation == "CAF"
    assert args.limit == 5


def test_parser_accepts_squad_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["squad", "--team", "Argentina", "--position", "FW"])

    assert args.command == "squad"
    assert args.team == "Argentina"
    assert args.position == "FW"


def test_parser_accepts_squad_summary_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["squad-summary", "--team", "Argentina"])

    assert args.command == "squad-summary"
    assert args.team == "Argentina"


def test_parser_accepts_group_profiles_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["group-profiles", "--group-name", "Group C", "--output", "out.csv"])

    assert args.command == "group-profiles"
    assert args.group_name == "Group C"
    assert args.output == "out.csv"


def test_parser_accepts_squad_composition_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["squad-composition", "--team", "Argentina"])

    assert args.command == "squad-composition"
    assert args.team == "Argentina"


def test_parser_accepts_team_schedule_difficulty_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["team-schedule-difficulty", "--team", "Argentina"])

    assert args.command == "team-schedule-difficulty"
    assert args.team == "Argentina"


def test_parser_accepts_group_difficulty_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["group-difficulty", "--limit", "6"])

    assert args.command == "group-difficulty"
    assert args.limit == 6


def test_parser_accepts_match_features_command() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["match-features", "--team", "Argentina", "--group-name", "Group J", "--limit", "3"]
    )

    assert args.command == "match-features"
    assert args.team == "Argentina"
    assert args.group_name == "Group J"
    assert args.limit == 3
