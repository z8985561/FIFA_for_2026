from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .postgres_queries import (
    qualified_name,
    query_group_overview,
    query_group_strength,
    query_prediction_extremes,
    query_prediction_lookup,
    query_recent_form,
    query_team_summary,
    query_team_vs_field,
    run_query,
)
from .postgres_views import load_postgres_view_config
from .project_paths import REPORTS_DIR


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized or "report"


def markdown_table(columns: list[str], rows: list[tuple[Any, ...]]) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| " + " | ".join("" if cell is None else str(cell) for cell in row) + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def render_section(
    title: str,
    columns: list[str],
    rows: list[tuple[Any, ...]],
    empty_message: str,
) -> str:
    if not rows:
        return f"## {title}\n\n{empty_message}\n"
    return f"## {title}\n\n{markdown_table(columns, rows)}\n"


def default_team_report_path(team: str) -> Path:
    return REPORTS_DIR / f"team_report_{slugify(team)}.md"


def default_group_report_path(group_name: str) -> Path:
    return REPORTS_DIR / f"group_report_{slugify(group_name)}.md"


def default_world_cup_pack_dir() -> Path:
    return REPORTS_DIR / "world_cup_2026_pack"


def write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def current_schema() -> str:
    return load_postgres_view_config().schema


def build_team_report(team: str, fixture_limit: int = 8, form_limit: int = 8) -> str:
    team_summary_columns, team_summary_rows = query_team_summary(team)
    team_vs_field_columns, team_vs_field_rows = query_team_vs_field(team)
    recent_form_columns, recent_form_rows = query_recent_form(team, form_limit)
    prediction_columns, prediction_rows = query_prediction_lookup(
        team=team,
        stage=None,
        group_name=None,
        limit=fixture_limit,
    )

    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    sections = [
        f"# Team Research Report: {team}\n",
        f"Generated at: {generated_at}\n",
        render_section(
            "Team Snapshot",
            team_summary_columns,
            team_summary_rows,
            f"No team summary found for {team}.",
        ),
        render_section(
            "Team Vs Field",
            team_vs_field_columns,
            team_vs_field_rows,
            f"No team-vs-field comparison found for {team}.",
        ),
        render_section(
            f"Recent Form Last {form_limit} Matches",
            recent_form_columns,
            recent_form_rows,
            f"No recent form sample found for {team}.",
        ),
        render_section(
            "Known 2026 World Cup Predictions",
            prediction_columns,
            prediction_rows,
            f"No known 2026 fixtures or predictions found for {team}.",
        ),
    ]
    return "\n".join(sections).strip() + "\n"


def build_group_report(group_name: str, overview_limit: int = 12, extremes_limit: int = 6) -> str:
    group_strength_columns, group_strength_rows = query_group_strength(group_name)
    group_overview_columns, group_overview_rows = query_group_overview(group_name)
    balanced_columns, balanced_rows = query_prediction_extremes(
        mode="balanced",
        stage=None,
        group_name=group_name,
        limit=extremes_limit,
    )
    lopsided_columns, lopsided_rows = query_prediction_extremes(
        mode="lopsided",
        stage=None,
        group_name=group_name,
        limit=extremes_limit,
    )

    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    if overview_limit < len(group_overview_rows):
        group_overview_rows = group_overview_rows[:overview_limit]

    sections = [
        f"# Group Research Report: {group_name}\n",
        f"Generated at: {generated_at}\n",
        render_section(
            "Group Strength",
            group_strength_columns,
            group_strength_rows,
            f"No group strength data found for {group_name}.",
        ),
        render_section(
            "Fixture Overview And Baseline Predictions",
            group_overview_columns,
            group_overview_rows,
            f"No fixture overview found for {group_name}.",
        ),
        render_section(
            "Most Balanced Matches",
            balanced_columns,
            balanced_rows,
            f"No balanced-match predictions found for {group_name}.",
        ),
        render_section(
            "Most Lopsided Matches",
            lopsided_columns,
            lopsided_rows,
            f"No lopsided-match predictions found for {group_name}.",
        ),
    ]
    return "\n".join(sections).strip() + "\n"


def list_group_names() -> list[str]:
    schema = current_schema()
    sql = f"""
        SELECT DISTINCT group_name
        FROM {qualified_name(schema, "fixtures_2026")}
        WHERE group_name IS NOT NULL
        ORDER BY group_name
    """
    _, rows = run_query(sql)
    return [str(row[0]) for row in rows]


def list_world_cup_teams() -> list[str]:
    schema = current_schema()
    sql = f"""
        SELECT team_name
        FROM (
            SELECT home_team AS team_name
            FROM {qualified_name(schema, "fixtures_2026")}
            WHERE home_team <> 'TBD'
            UNION
            SELECT away_team AS team_name
            FROM {qualified_name(schema, "fixtures_2026")}
            WHERE away_team <> 'TBD'
        ) AS world_cup_teams
        ORDER BY team_name
    """
    _, rows = run_query(sql)
    return [str(row[0]) for row in rows]


def build_pack_index(
    generated_at: str,
    group_files: list[tuple[str, Path]],
    team_files: list[tuple[str, Path]],
) -> str:
    sections = [
        "# World Cup 2026 Research Pack\n",
        f"Generated at: {generated_at}\n",
        f"Groups included: {len(group_files)}\n",
        f"Teams included: {len(team_files)}\n",
        "## Group Reports\n",
    ]

    if group_files:
        sections.extend(f"- [{group_name}]({path.as_posix()})" for group_name, path in group_files)
    else:
        sections.append("No group reports generated.")

    sections.append("\n## Team Reports\n")
    if team_files:
        sections.extend(f"- [{team_name}]({path.as_posix()})" for team_name, path in team_files)
    else:
        sections.append("No team reports generated.")

    return "\n".join(sections).strip() + "\n"


def generate_world_cup_pack(
    output_dir: Path,
    include_team_reports: bool,
    fixture_limit: int,
    form_limit: int,
    overview_limit: int,
    extremes_limit: int,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    groups_dir = output_dir / "groups"
    teams_dir = output_dir / "teams"
    groups_dir.mkdir(parents=True, exist_ok=True)

    group_files: list[tuple[str, Path]] = []
    for group_name in list_group_names():
        group_path = groups_dir / f"{slugify(group_name)}.md"
        write_report(
            group_path,
            build_group_report(
                group_name=group_name,
                overview_limit=overview_limit,
                extremes_limit=extremes_limit,
            ),
        )
        group_files.append((group_name, Path("groups") / group_path.name))

    team_files: list[tuple[str, Path]] = []
    if include_team_reports:
        teams_dir.mkdir(parents=True, exist_ok=True)
        for team_name in list_world_cup_teams():
            team_path = teams_dir / f"{slugify(team_name)}.md"
            write_report(
                team_path,
                build_team_report(
                    team=team_name,
                    fixture_limit=fixture_limit,
                    form_limit=form_limit,
                ),
            )
            team_files.append((team_name, Path("teams") / team_path.name))

    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    index_path = output_dir / "index.md"
    write_report(index_path, build_pack_index(generated_at, group_files, team_files))
    return index_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Markdown research reports.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    team_parser = subparsers.add_parser("team", help="Generate a team research report.")
    team_parser.add_argument("--team", required=True)
    team_parser.add_argument("--fixture-limit", type=int, default=8)
    team_parser.add_argument("--form-limit", type=int, default=8)
    team_parser.add_argument("--output")

    group_parser = subparsers.add_parser("group", help="Generate a group research report.")
    group_parser.add_argument("--group-name", required=True)
    group_parser.add_argument("--overview-limit", type=int, default=12)
    group_parser.add_argument("--extremes-limit", type=int, default=6)
    group_parser.add_argument("--output")

    pack_parser = subparsers.add_parser(
        "world-cup-pack",
        help="Generate a batch World Cup research pack.",
    )
    pack_parser.add_argument("--output-dir")
    pack_parser.add_argument("--include-team-reports", action="store_true")
    pack_parser.add_argument("--fixture-limit", type=int, default=8)
    pack_parser.add_argument("--form-limit", type=int, default=8)
    pack_parser.add_argument("--overview-limit", type=int, default=12)
    pack_parser.add_argument("--extremes-limit", type=int, default=6)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "team":
        output_path = Path(args.output) if args.output else default_team_report_path(args.team)
        content = build_team_report(
            team=args.team,
            fixture_limit=args.fixture_limit,
            form_limit=args.form_limit,
        )
    elif args.command == "group":
        output_path = (
            Path(args.output) if args.output else default_group_report_path(args.group_name)
        )
        content = build_group_report(
            group_name=args.group_name,
            overview_limit=args.overview_limit,
            extremes_limit=args.extremes_limit,
        )
    elif args.command == "world-cup-pack":
        output_dir = Path(args.output_dir) if args.output_dir else default_world_cup_pack_dir()
        index_path = generate_world_cup_pack(
            output_dir=output_dir,
            include_team_reports=args.include_team_reports,
            fixture_limit=args.fixture_limit,
            form_limit=args.form_limit,
            overview_limit=args.overview_limit,
            extremes_limit=args.extremes_limit,
        )
        print(f"wrote: {index_path}")
        return
    else:
        raise ValueError(f"Unknown command: {args.command}")

    write_report(output_path, content)
    print(f"wrote: {output_path}")


if __name__ == "__main__":
    main()
