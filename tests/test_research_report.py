from src.research_report import (
    build_pack_index,
    build_parser,
    default_group_report_path,
    default_report_asset_dir,
    default_team_report_path,
    default_world_cup_pack_dir,
    markdown_table,
    relative_markdown_path,
    render_chart_section,
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


def test_default_world_cup_pack_dir_uses_reports_directory() -> None:
    path = default_world_cup_pack_dir()

    assert path.name == "world_cup_2026_pack"


def test_default_report_asset_dir_uses_report_stem() -> None:
    path = default_report_asset_dir(default_team_report_path("Argentina"))

    assert path.name == "team_report_argentina_assets"


def test_relative_markdown_path_uses_parent_directory() -> None:
    report_path = default_world_cup_pack_dir() / "groups/group_c.md"
    chart_path = default_world_cup_pack_dir() / "charts/groups/group_c_strength.png"

    assert relative_markdown_path(report_path, chart_path).as_posix() == (
        "../charts/groups/group_c_strength.png"
    )


def test_render_chart_section_embeds_markdown_images() -> None:
    section = render_chart_section(
        "Visual Dashboards",
        [("Strength", default_world_cup_pack_dir() / "charts/group_strength.png")],
    )

    assert "## Visual Dashboards" in section
    assert "![Strength]" in section


def test_build_pack_index_renders_navigation_sections() -> None:
    index = build_pack_index(
        "2026-06-09 15:00:00 +0800",
        [("Group C", default_world_cup_pack_dir() / "groups/group_c.md")],
        [("Argentina", default_world_cup_pack_dir() / "teams/argentina.md")],
        (
            ["group_name", "avg_elo"],
            [("Group C", 1763.50)],
        ),
        (
            ["match_no", "home_team", "away_team"],
            [(14, "Haiti", "Scotland")],
        ),
        (
            ["match_no", "home_team", "away_team"],
            [(16, "Brazil", "Haiti")],
        ),
        [
            (
                "Group Strength Landscape",
                default_world_cup_pack_dir() / "charts/group_strength.png",
            ),
            (
                "Group Stage Prediction Confidence Distribution",
                default_world_cup_pack_dir() / "charts/confidence_distribution.png",
            ),
        ],
    )

    assert "# World Cup 2026 Research Pack" in index
    assert "## Visual Dashboards" in index
    assert "![Group Strength Landscape]" in index
    assert "## Group Strength Summary" in index
    assert "[Group C]" in index
    assert "[Argentina]" in index


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


def test_parser_accepts_world_cup_pack_command() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "world-cup-pack",
            "--include-team-reports",
            "--fixture-limit",
            "5",
            "--form-limit",
            "6",
        ]
    )

    assert args.command == "world-cup-pack"
    assert args.include_team_reports is True
    assert args.fixture_limit == 5
    assert args.form_limit == 6
