from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .postgres_queries import (
    query_group_overview,
    query_group_strength,
    query_prediction_extremes,
    query_prediction_lookup,
    query_recent_form,
    query_team_summary,
    query_team_vs_field,
)
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


def write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


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
    else:
        raise ValueError(f"Unknown command: {args.command}")

    write_report(output_path, content)
    print(f"wrote: {output_path}")


if __name__ == "__main__":
    main()
