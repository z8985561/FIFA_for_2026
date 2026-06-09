from src.research_report import (
    build_parser,
    default_group_report_path,
    default_team_report_path,
    markdown_table,
    slugify,
)


def test_slugify_normalizes_text() -> None:
    assert slugify("Group C") == "group_c"
    assert slugify("Argentina / Brazil") == "argentina_brazil"


def test_markdown_table_renders_header_and_rows() -> None:
    table = markdown_table(
        ["team_name", "latest_elo"],
        [("Argentina", 1994.95), ("Brazil", 1926.04)],
    )

    assert "| team_name | latest_elo |" in table
    assert "| Argentina | 1994.95 |" in table
    assert "| Brazil | 1926.04 |" in table


def test_default_team_report_path_uses_reports_directory() -> None:
    path = default_team_report_path("Argentina")

    assert path.name == "team_report_argentina.md"


def test_default_group_report_path_uses_reports_directory() -> None:
    path = default_group_report_path("Group C")

    assert path.name == "group_report_group_c.md"


def test_parser_accepts_team_report_command() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["team", "--team", "Argentina", "--fixture-limit", "5", "--form-limit", "6"]
    )

    assert args.command == "team"
    assert args.team == "Argentina"
    assert args.fixture_limit == 5
    assert args.form_limit == 6


def test_parser_accepts_group_report_command() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["group", "--group-name", "Group C", "--overview-limit", "8", "--extremes-limit", "4"]
    )

    assert args.command == "group"
    assert args.group_name == "Group C"
    assert args.overview_limit == 8
    assert args.extremes_limit == 4
