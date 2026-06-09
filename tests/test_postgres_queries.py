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
