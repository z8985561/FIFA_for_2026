from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from .postgres_queries import (
    qualified_name,
    query_group_difficulty,
    query_group_overview,
    query_group_profiles,
    query_group_strength,
    query_prediction_extremes,
    query_prediction_lookup,
    query_recent_form,
    query_squad_composition,
    query_team_schedule_difficulty,
    query_team_summary,
    query_team_vs_field,
    run_query,
)
from .postgres_views import load_postgres_view_config
from .project_paths import REPORTS_DIR


@dataclass(frozen=True)
class TeamReportData:
    team: str
    team_summary: tuple[list[str], list[tuple[Any, ...]]]
    team_vs_field: tuple[list[str], list[tuple[Any, ...]]]
    squad_composition: tuple[list[str], list[tuple[Any, ...]]]
    schedule_difficulty: tuple[list[str], list[tuple[Any, ...]]]
    recent_form: tuple[list[str], list[tuple[Any, ...]]]
    predictions: tuple[list[str], list[tuple[Any, ...]]]


@dataclass(frozen=True)
class GroupReportData:
    group_name: str
    group_strength: tuple[list[str], list[tuple[Any, ...]]]
    group_profiles: tuple[list[str], list[tuple[Any, ...]]]
    group_difficulty: tuple[list[str], list[tuple[Any, ...]]]
    group_overview: tuple[list[str], list[tuple[Any, ...]]]
    balanced_matches: tuple[list[str], list[tuple[Any, ...]]]
    lopsided_matches: tuple[list[str], list[tuple[Any, ...]]]


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


def render_chart_section(title: str, chart_paths: list[tuple[str, Path]]) -> str:
    if not chart_paths:
        return f"## {title}\n\nNo charts available.\n"
    lines = [f"## {title}\n"]
    for caption, path in chart_paths:
        lines.append(f"### {caption}\n")
        lines.append(f"![{caption}]({path.as_posix()})\n")
    return "\n".join(lines).strip() + "\n"


def default_team_report_path(team: str) -> Path:
    return REPORTS_DIR / f"team_report_{slugify(team)}.md"


def default_group_report_path(group_name: str) -> Path:
    return REPORTS_DIR / f"group_report_{slugify(group_name)}.md"


def default_world_cup_pack_dir() -> Path:
    return REPORTS_DIR / "world_cup_2026_pack"


def default_report_asset_dir(report_path: Path) -> Path:
    return report_path.parent / f"{report_path.stem}_assets"


def write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def current_schema() -> str:
    return load_postgres_view_config().schema


def relative_markdown_path(from_path: Path, to_path: Path) -> Path:
    return Path(os.path.relpath(to_path, start=from_path.parent))


def load_team_report_data(team: str, fixture_limit: int = 8, form_limit: int = 8) -> TeamReportData:
    return TeamReportData(
        team=team,
        team_summary=query_team_summary(team),
        team_vs_field=query_team_vs_field(team),
        squad_composition=query_squad_composition(team),
        schedule_difficulty=query_team_schedule_difficulty(team),
        recent_form=query_recent_form(team, form_limit),
        predictions=query_prediction_lookup(
            team=team,
            stage=None,
            group_name=None,
            limit=fixture_limit,
        ),
    )


def load_group_report_data(
    group_name: str,
    overview_limit: int = 12,
    extremes_limit: int = 6,
) -> GroupReportData:
    group_overview = query_group_overview(group_name)
    overview_columns, overview_rows = group_overview
    if overview_limit < len(overview_rows):
        group_overview = (overview_columns, overview_rows[:overview_limit])

    return GroupReportData(
        group_name=group_name,
        group_strength=query_group_strength(group_name),
        group_profiles=query_group_profiles(group_name),
        group_difficulty=query_group_difficulty(limit=12, group_name=group_name),
        group_overview=group_overview,
        balanced_matches=query_prediction_extremes(
            mode="balanced",
            stage=None,
            group_name=group_name,
            limit=extremes_limit,
        ),
        lopsided_matches=query_prediction_extremes(
            mode="lopsided",
            stage=None,
            group_name=group_name,
            limit=extremes_limit,
        ),
    )


def build_team_report(
    data: TeamReportData,
    chart_files: list[tuple[str, Path]] | None = None,
) -> str:
    team_summary_columns, team_summary_rows = data.team_summary
    team_vs_field_columns, team_vs_field_rows = data.team_vs_field
    squad_composition_columns, squad_composition_rows = data.squad_composition
    schedule_columns, schedule_rows = data.schedule_difficulty
    recent_form_columns, recent_form_rows = data.recent_form
    prediction_columns, prediction_rows = data.predictions
    matches_sampled = recent_form_rows[0][1] if recent_form_rows else 0
    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    sections = [
        f"# Team Research Report: {data.team}\n",
        f"Generated at: {generated_at}\n",
        render_chart_section("Visual Dashboards", chart_files or []),
        render_section(
            "Team Snapshot",
            team_summary_columns,
            team_summary_rows,
            f"No team summary found for {data.team}.",
        ),
        render_section(
            "Team Vs Field",
            team_vs_field_columns,
            team_vs_field_rows,
            f"No team-vs-field comparison found for {data.team}.",
        ),
        render_section(
            "Squad Composition",
            squad_composition_columns,
            squad_composition_rows,
            f"No squad composition found for {data.team}.",
        ),
        render_section(
            "Schedule Difficulty",
            schedule_columns,
            schedule_rows,
            f"No schedule difficulty rows found for {data.team}.",
        ),
        render_section(
            f"Recent Form Last {matches_sampled} Matches",
            recent_form_columns,
            recent_form_rows,
            f"No recent form sample found for {data.team}.",
        ),
        render_section(
            "Known 2026 World Cup Predictions",
            prediction_columns,
            prediction_rows,
            f"No known 2026 fixtures or predictions found for {data.team}.",
        ),
    ]
    return "\n".join(sections).strip() + "\n"


def build_group_report(
    data: GroupReportData,
    chart_files: list[tuple[str, Path]] | None = None,
) -> str:
    group_strength_columns, group_strength_rows = data.group_strength
    group_profiles_columns, group_profiles_rows = data.group_profiles
    group_difficulty_columns, group_difficulty_rows = data.group_difficulty
    group_overview_columns, group_overview_rows = data.group_overview
    balanced_columns, balanced_rows = data.balanced_matches
    lopsided_columns, lopsided_rows = data.lopsided_matches
    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    sections = [
        f"# Group Research Report: {data.group_name}\n",
        f"Generated at: {generated_at}\n",
        render_chart_section("Visual Dashboards", chart_files or []),
        render_section(
            "Group Strength",
            group_strength_columns,
            group_strength_rows,
            f"No group strength data found for {data.group_name}.",
        ),
        render_section(
            "Group Difficulty Context",
            group_difficulty_columns,
            group_difficulty_rows,
            f"No group difficulty context found for {data.group_name}.",
        ),
        render_section(
            "Group Team Profiles",
            group_profiles_columns,
            group_profiles_rows,
            f"No group profile rows found for {data.group_name}.",
        ),
        render_section(
            "Fixture Overview And Baseline Predictions",
            group_overview_columns,
            group_overview_rows,
            f"No fixture overview found for {data.group_name}.",
        ),
        render_section(
            "Most Balanced Matches",
            balanced_columns,
            balanced_rows,
            f"No balanced-match predictions found for {data.group_name}.",
        ),
        render_section(
            "Most Lopsided Matches",
            lopsided_columns,
            lopsided_rows,
            f"No lopsided-match predictions found for {data.group_name}.",
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


def query_group_strength_rollup() -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = current_schema()
    sql = f"""
        WITH group_teams AS (
            SELECT DISTINCT group_name, home_team AS team_name
            FROM {qualified_name(schema, "fixtures_2026")}
            WHERE group_name IS NOT NULL
              AND home_team <> 'TBD'
            UNION
            SELECT DISTINCT group_name, away_team AS team_name
            FROM {qualified_name(schema, "fixtures_2026")}
            WHERE group_name IS NOT NULL
              AND away_team <> 'TBD'
        )
        SELECT
            gt.group_name,
            COUNT(*) AS teams,
            ROUND(AVG(r.latest_elo)::numeric, 2) AS avg_elo,
            ROUND(MAX(r.latest_elo)::numeric, 2) AS max_elo,
            ROUND(MIN(r.latest_elo)::numeric, 2) AS min_elo,
            ROUND((MAX(r.latest_elo) - MIN(r.latest_elo))::numeric, 2) AS elo_spread
        FROM group_teams AS gt
        LEFT JOIN {qualified_name(schema, "ratings")} AS r
            ON gt.team_name = r.team_name
        GROUP BY gt.group_name
        ORDER BY avg_elo DESC, gt.group_name
    """
    return run_query(sql)


def query_prediction_confidence_distribution(
    stage: str | None,
) -> tuple[list[str], list[tuple[Any, ...]]]:
    schema = current_schema()
    clauses: list[str] = []
    params: list[Any] = []

    if stage:
        clauses.append("stage = %s")
        params.append(stage)

    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        WITH prediction_scores AS (
            SELECT
                match_no,
                stage,
                group_name,
                home_team,
                away_team,
                GREATEST(
                    home_win_probability,
                    draw_probability,
                    away_win_probability
                ) AS top_probability,
                (
                    home_win_probability
                    + draw_probability
                    + away_win_probability
                    - GREATEST(
                        home_win_probability,
                        draw_probability,
                        away_win_probability
                    )
                    - LEAST(
                        home_win_probability,
                        draw_probability,
                        away_win_probability
                    )
                ) AS middle_probability
            FROM {qualified_name(schema, "baseline_prediction_summary")}
            {where_clause}
        )
        SELECT
            match_no,
            stage,
            group_name,
            home_team,
            away_team,
            ROUND((top_probability - middle_probability)::numeric, 4) AS confidence_gap
        FROM prediction_scores
        ORDER BY confidence_gap
    """
    return run_query(sql, tuple(params))


def plot_group_strength_chart(
    path: Path,
    columns: list[str],
    rows: list[tuple[Any, ...]],
) -> None:
    if not rows:
        return

    group_idx = columns.index("group_name")
    avg_idx = columns.index("avg_elo")
    spread_idx = columns.index("elo_spread")

    group_names = [str(row[group_idx]) for row in rows]
    avg_elos = [float(row[avg_idx]) for row in rows]
    spreads = [float(row[spread_idx]) for row in rows]

    fig, ax = plt.subplots(figsize=(11, 6.5))
    fig.patch.set_facecolor("#f7f1e3")
    ax.set_facecolor("#fffaf0")
    bars = ax.barh(group_names, avg_elos, color="#2a9d8f", edgecolor="#264653")

    for bar, spread in zip(bars, spreads, strict=True):
        ax.text(
            bar.get_width() + 4,
            bar.get_y() + (bar.get_height() / 2),
            f"spread {spread:.1f}",
            va="center",
            fontsize=9,
            color="#264653",
        )

    ax.invert_yaxis()
    ax.set_title("Group Strength Landscape", fontsize=16, pad=14, color="#1d3557")
    ax.set_xlabel("Average Elo")
    ax.grid(axis="x", linestyle="--", alpha=0.25)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_confidence_distribution_chart(
    path: Path,
    columns: list[str],
    rows: list[tuple[Any, ...]],
) -> None:
    if not rows:
        return

    gap_idx = columns.index("confidence_gap")
    gaps = [float(row[gap_idx]) for row in rows]

    fig, ax = plt.subplots(figsize=(10.5, 6.0))
    fig.patch.set_facecolor("#f5efe6")
    ax.set_facecolor("#fffdf8")
    ax.hist(gaps, bins=10, color="#e76f51", edgecolor="#6d6875", alpha=0.9)
    ax.axvline(sum(gaps) / len(gaps), color="#1d3557", linestyle="--", linewidth=2)
    ax.set_title("Group Stage Prediction Confidence Distribution", fontsize=16, pad=14)
    ax.set_xlabel("Confidence Gap")
    ax.set_ylabel("Matches")
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_team_field_benchmark_chart(
    path: Path,
    team_name: str,
    columns: list[str],
    rows: list[tuple[Any, ...]],
) -> None:
    if not rows:
        return

    row = rows[0]
    latest_idx = columns.index("latest_elo")
    avg_idx = columns.index("avg_field_elo")
    median_idx = columns.index("median_field_elo")
    max_idx = columns.index("max_field_elo")

    labels = [team_name, "Field Avg", "Field Median", "Field Max"]
    values = [
        float(row[latest_idx]),
        float(row[avg_idx]),
        float(row[median_idx]),
        float(row[max_idx]),
    ]
    colors = ["#d62828", "#457b9d", "#2a9d8f", "#6d597a"]

    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    fig.patch.set_facecolor("#f9f4ef")
    ax.set_facecolor("#fffdf8")
    bars = ax.bar(labels, values, color=colors, edgecolor="#264653")
    for bar, value in zip(bars, values, strict=True):
        ax.text(
            bar.get_x() + (bar.get_width() / 2),
            value + 8,
            f"{value:.1f}",
            ha="center",
            fontsize=10,
            color="#1d3557",
        )

    ax.set_title(f"{team_name} Vs Field Benchmarks", fontsize=16, pad=14)
    ax.set_ylabel("Elo")
    ax.grid(axis="y", linestyle="--", alpha=0.2)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_team_prediction_chart(
    path: Path,
    team_name: str,
    columns: list[str],
    rows: list[tuple[Any, ...]],
) -> None:
    if not rows:
        return

    home_team_idx = columns.index("home_team")
    away_team_idx = columns.index("away_team")
    home_prob_idx = columns.index("home_win_probability")
    draw_prob_idx = columns.index("draw_probability")
    away_prob_idx = columns.index("away_win_probability")

    labels: list[str] = []
    home_probs: list[float] = []
    draw_probs: list[float] = []
    away_probs: list[float] = []
    for row in rows:
        home_team = str(row[home_team_idx])
        away_team = str(row[away_team_idx])
        opponent = away_team if home_team == team_name else home_team
        venue_tag = "H" if home_team == team_name else "A"
        labels.append(f"{opponent} ({venue_tag})")
        home_probs.append(float(row[home_prob_idx]))
        draw_probs.append(float(row[draw_prob_idx]))
        away_probs.append(float(row[away_prob_idx]))

    fig, ax = plt.subplots(figsize=(10.2, max(4.8, 1.25 * len(labels))))
    fig.patch.set_facecolor("#f7f3ed")
    ax.set_facecolor("#fffdfa")
    positions = list(range(len(labels)))
    ax.barh(positions, home_probs, color="#2a9d8f", label="Home Win")
    ax.barh(positions, draw_probs, left=home_probs, color="#e9c46a", label="Draw")
    stacked_left = [home + draw for home, draw in zip(home_probs, draw_probs, strict=True)]
    ax.barh(positions, away_probs, left=stacked_left, color="#e76f51", label="Away Win")

    ax.set_yticks(positions, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xlabel("Probability")
    ax.set_title(f"{team_name} 2026 Match Probability Profile", fontsize=16, pad=14)
    ax.legend(loc="lower right")
    ax.grid(axis="x", linestyle="--", alpha=0.2)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_group_team_strength_chart(
    path: Path,
    group_name: str,
    columns: list[str],
    rows: list[tuple[Any, ...]],
) -> None:
    if not rows:
        return

    team_idx = columns.index("team_name")
    elo_idx = columns.index("latest_elo")
    diff_idx = columns.index("elo_vs_group_avg")

    team_names = [str(row[team_idx]) for row in rows]
    latest_elos = [float(row[elo_idx]) for row in rows]
    diffs = [float(row[diff_idx]) for row in rows]

    fig, ax = plt.subplots(figsize=(9.4, 5.8))
    fig.patch.set_facecolor("#f8f5f0")
    ax.set_facecolor("#fffdf8")
    bars = ax.bar(team_names, latest_elos, color="#3a86ff", edgecolor="#1d3557")
    for bar, diff in zip(bars, diffs, strict=True):
        ax.text(
            bar.get_x() + (bar.get_width() / 2),
            bar.get_height() + 8,
            f"{diff:+.1f}",
            ha="center",
            fontsize=10,
            color="#1d3557",
        )

    ax.set_title(f"{group_name} Team Strength Snapshot", fontsize=16, pad=14)
    ax.set_ylabel("Latest Elo")
    ax.grid(axis="y", linestyle="--", alpha=0.2)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_group_fixture_confidence_chart(
    path: Path,
    group_name: str,
    columns: list[str],
    rows: list[tuple[Any, ...]],
) -> None:
    if not rows:
        return

    home_team_idx = columns.index("home_team")
    away_team_idx = columns.index("away_team")
    home_prob_idx = columns.index("home_win_probability")
    draw_prob_idx = columns.index("draw_probability")
    away_prob_idx = columns.index("away_win_probability")

    labels: list[str] = []
    confidence_gaps: list[float] = []
    for row in rows:
        home_prob = float(row[home_prob_idx])
        draw_prob = float(row[draw_prob_idx])
        away_prob = float(row[away_prob_idx])
        sorted_probs = sorted([home_prob, draw_prob, away_prob], reverse=True)
        confidence_gaps.append(sorted_probs[0] - sorted_probs[1])
        labels.append(f"{row[home_team_idx]} vs {row[away_team_idx]}")

    fig, ax = plt.subplots(figsize=(10.5, max(4.8, 1.05 * len(labels))))
    fig.patch.set_facecolor("#f9f6f1")
    ax.set_facecolor("#fffdf9")
    bars = ax.barh(labels, confidence_gaps, color="#ff7f51", edgecolor="#5c677d")
    for bar, gap in zip(bars, confidence_gaps, strict=True):
        ax.text(
            bar.get_width() + 0.01,
            bar.get_y() + (bar.get_height() / 2),
            f"{gap:.3f}",
            va="center",
            fontsize=9,
            color="#1d3557",
        )

    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xlabel("Confidence Gap")
    ax.set_title(f"{group_name} Fixture Confidence Gaps", fontsize=16, pad=14)
    ax.grid(axis="x", linestyle="--", alpha=0.2)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def create_team_chart_files(
    report_path: Path,
    asset_dir: Path,
    data: TeamReportData,
) -> list[tuple[str, Path]]:
    chart_paths: list[tuple[str, Path]] = []

    benchmark_chart = asset_dir / f"{slugify(data.team)}_benchmark.png"
    plot_team_field_benchmark_chart(
        benchmark_chart,
        data.team,
        *data.team_vs_field,
    )
    chart_paths.append(
        (
            "Team Vs Field Benchmark",
            relative_markdown_path(report_path, benchmark_chart),
        )
    )

    prediction_rows = data.predictions[1]
    if prediction_rows:
        prediction_chart = asset_dir / f"{slugify(data.team)}_predictions.png"
        plot_team_prediction_chart(
            prediction_chart,
            data.team,
            *data.predictions,
        )
        chart_paths.append(
            (
                "2026 Match Probability Profile",
                relative_markdown_path(report_path, prediction_chart),
            )
        )

    return chart_paths


def create_group_chart_files(
    report_path: Path,
    asset_dir: Path,
    data: GroupReportData,
) -> list[tuple[str, Path]]:
    chart_paths: list[tuple[str, Path]] = []

    strength_chart = asset_dir / f"{slugify(data.group_name)}_strength.png"
    plot_group_team_strength_chart(
        strength_chart,
        data.group_name,
        *data.group_strength,
    )
    chart_paths.append(
        (
            "Group Team Strength Snapshot",
            relative_markdown_path(report_path, strength_chart),
        )
    )

    overview_rows = data.group_overview[1]
    if overview_rows:
        fixture_chart = asset_dir / f"{slugify(data.group_name)}_confidence_gaps.png"
        plot_group_fixture_confidence_chart(
            fixture_chart,
            data.group_name,
            *data.group_overview,
        )
        chart_paths.append(
            (
                "Fixture Confidence Gaps",
                relative_markdown_path(report_path, fixture_chart),
            )
        )

    return chart_paths


def generate_team_report_file(
    output_path: Path,
    team: str,
    fixture_limit: int,
    form_limit: int,
    asset_dir: Path | None = None,
) -> Path:
    data = load_team_report_data(team, fixture_limit, form_limit)
    chart_files = create_team_chart_files(
        output_path,
        asset_dir or default_report_asset_dir(output_path),
        data,
    )
    write_report(output_path, build_team_report(data, chart_files))
    return output_path


def generate_group_report_file(
    output_path: Path,
    group_name: str,
    overview_limit: int,
    extremes_limit: int,
    asset_dir: Path | None = None,
) -> Path:
    data = load_group_report_data(group_name, overview_limit, extremes_limit)
    chart_files = create_group_chart_files(
        output_path,
        asset_dir or default_report_asset_dir(output_path),
        data,
    )
    write_report(output_path, build_group_report(data, chart_files))
    return output_path


def build_pack_index(
    generated_at: str,
    group_files: list[tuple[str, Path]],
    team_files: list[tuple[str, Path]],
    group_summary: tuple[list[str], list[tuple[Any, ...]]],
    balanced_matches: tuple[list[str], list[tuple[Any, ...]]],
    lopsided_matches: tuple[list[str], list[tuple[Any, ...]]],
    chart_files: list[tuple[str, Path]],
) -> str:
    group_summary_columns, group_summary_rows = group_summary
    balanced_columns, balanced_rows = balanced_matches
    lopsided_columns, lopsided_rows = lopsided_matches

    sections = [
        "# World Cup 2026 Research Pack\n",
        f"Generated at: {generated_at}\n",
        f"Groups included: {len(group_files)}\n",
        f"Teams included: {len(team_files)}\n",
        render_chart_section("Visual Dashboards", chart_files),
        render_section(
            "Group Strength Summary",
            group_summary_columns,
            group_summary_rows,
            "No group strength summary available.",
        ),
        render_section(
            "Most Balanced Group Stage Matches",
            balanced_columns,
            balanced_rows,
            "No balanced group-stage matches available.",
        ),
        render_section(
            "Most Lopsided Group Stage Matches",
            lopsided_columns,
            lopsided_rows,
            "No lopsided group-stage matches available.",
        ),
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
    charts_dir = output_dir / "charts"
    group_charts_dir = charts_dir / "groups"
    team_charts_dir = charts_dir / "teams"
    groups_dir.mkdir(parents=True, exist_ok=True)

    group_files: list[tuple[str, Path]] = []
    for group_name in list_group_names():
        group_path = groups_dir / f"{slugify(group_name)}.md"
        generate_group_report_file(
            group_path,
            group_name=group_name,
            overview_limit=overview_limit,
            extremes_limit=extremes_limit,
            asset_dir=group_charts_dir,
        )
        group_files.append((group_name, Path("groups") / group_path.name))

    team_files: list[tuple[str, Path]] = []
    if include_team_reports:
        teams_dir.mkdir(parents=True, exist_ok=True)
        for team_name in list_world_cup_teams():
            team_path = teams_dir / f"{slugify(team_name)}.md"
            generate_team_report_file(
                team_path,
                team=team_name,
                fixture_limit=fixture_limit,
                form_limit=form_limit,
                asset_dir=team_charts_dir,
            )
            team_files.append((team_name, Path("teams") / team_path.name))

    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    group_summary = query_group_strength_rollup()
    confidence_distribution = query_prediction_confidence_distribution("Group Stage")
    group_chart_path = charts_dir / "group_strength_landscape.png"
    confidence_chart_path = charts_dir / "group_stage_confidence_distribution.png"
    plot_group_strength_chart(group_chart_path, *group_summary)
    plot_confidence_distribution_chart(confidence_chart_path, *confidence_distribution)
    chart_files = [
        ("Group Strength Landscape", Path("charts") / group_chart_path.name),
        (
            "Group Stage Prediction Confidence Distribution",
            Path("charts") / confidence_chart_path.name,
        ),
    ]
    index_path = output_dir / "index.md"
    write_report(
        index_path,
        build_pack_index(
            generated_at,
            group_files,
            team_files,
            group_summary,
            query_prediction_extremes("balanced", "Group Stage", None, 8),
            query_prediction_extremes("lopsided", "Group Stage", None, 8),
            chart_files,
        ),
    )
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
        generate_team_report_file(
            output_path,
            team=args.team,
            fixture_limit=args.fixture_limit,
            form_limit=args.form_limit,
        )
    elif args.command == "group":
        output_path = (
            Path(args.output) if args.output else default_group_report_path(args.group_name)
        )
        generate_group_report_file(
            output_path,
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

    print(f"wrote: {output_path}")


if __name__ == "__main__":
    main()
