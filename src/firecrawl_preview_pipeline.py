from __future__ import annotations

import argparse
import os
import re
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlparse

import pandas as pd
from firecrawl import Firecrawl

from .lineups_pipeline import TEAM_NAME_ZH
from .postgres_sync import DEFAULT_ENV_PATH, load_env_file
from .project_paths import (
    FIXTURES_PATH,
    PRE_MATCH_CONTEXT_2026_PATH,
    ensure_project_directories,
)
from .team_names import ascii_fold

DEFAULT_INCLUDE_DOMAINS = [
    "sportsmole.co.uk",
    "rotowire.com",
    "fifa.com",
    "reuters.com",
]
DOMAIN_PRIORITY = {
    "sportsmole.co.uk": 100,
    "rotowire.com": 85,
    "fifa.com": 80,
    "reuters.com": 75,
}
SEARCH_RESULT_LIMIT = 6
MAX_SOURCES_PER_MATCH = 2
MARKDOWN_EXCERPT_LIMIT = 1200
SENTENCE_JOIN_LIMIT = 5
MATCH_CONTEXT_COLUMNS = [
    "match_no",
    "stage",
    "group_name",
    "date_et",
    "time_et",
    "home_team",
    "away_team",
    "home_team_zh",
    "away_team_zh",
    "search_query",
    "source_rank",
    "source_quality_score",
    "source_name",
    "source_domain",
    "source_title",
    "source_url",
    "source_description",
    "published_time",
    "predicted_lineup_text",
    "injury_notes",
    "coach_quotes",
    "key_player_notes",
    "content_excerpt",
    "fetch_warning",
    "fetched_at",
]


@dataclass
class PreMatchContextOutputs:
    pre_match_context_path: str
    row_count: int
    match_count: int
    source_count: int


def load_firecrawl_client(env_path: str | os.PathLike[str] = DEFAULT_ENV_PATH) -> Firecrawl:
    path = Path(env_path) if isinstance(env_path, str) else env_path
    file_env = load_env_file(path=path)
    api_key = os.getenv("FIRECRAWL_API_KEY") or file_env.get("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError("Missing FIRECRAWL_API_KEY in environment or .env file.")
    api_url = os.getenv("FIRECRAWL_API_URL") or file_env.get("FIRECRAWL_API_URL")
    return Firecrawl(api_key=api_key, api_url=api_url or "https://api.firecrawl.dev")


def _to_namespace(value: Any) -> Any:
    if isinstance(value, dict):
        return SimpleNamespace(**{key: _to_namespace(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_to_namespace(item) for item in value]
    return value


def build_search_query(match_row: pd.Series) -> str:
    return (
        f"{match_row['home_team']} vs {match_row['away_team']} World Cup 2026 "
        f"{match_row['date_et']} predicted lineup team news injuries key players"
    )


def select_target_fixtures(
    fixtures: pd.DataFrame,
    *,
    as_of_date: date | None = None,
    days_ahead: int | None = 7,
    limit: int | None = None,
    include_past: bool = False,
) -> pd.DataFrame:
    selected = fixtures.copy()
    selected["match_date"] = pd.to_datetime(selected["date_et"]).dt.date
    today = as_of_date or date.today()
    if not include_past:
        selected = selected.loc[selected["match_date"].ge(today)]
    if days_ahead is not None:
        latest = today + timedelta(days=days_ahead)
        selected = selected.loc[selected["match_date"].le(latest)]
    selected = selected.sort_values(["match_date", "match_no"]).drop(columns=["match_date"])
    if limit is not None:
        selected = selected.head(limit)
    return selected.reset_index(drop=True)


def _result_iter(search_data: Any) -> list[Any]:
    if search_data is None:
        return []
    if isinstance(search_data, list):
        return search_data
    web_results = getattr(search_data, "web", None)
    if web_results is not None:
        return list(web_results)
    if isinstance(search_data, dict):
        return list(search_data.get("web") or [])
    return []


def _domain_from_url(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _source_name_from_domain(domain: str) -> str:
    if domain == "sportsmole.co.uk":
        return "Sports Mole"
    if domain == "rotowire.com":
        return "RotoWire"
    if domain == "fifa.com":
        return "FIFA"
    if domain == "reuters.com":
        return "Reuters"
    label = domain.replace(".com", "").replace(".co.uk", "")
    return label.replace("-", " ").title()


def _contains_team_terms(text: str, team_name: str) -> bool:
    normalized_text = ascii_fold(text).lower()
    normalized_team = ascii_fold(team_name).lower()
    aliases = {
        normalized_team,
        normalized_team.replace(" and ", " & "),
    }
    if normalized_team == "united states":
        aliases.update({"usa", "usmnt"})
    if normalized_team == "south korea":
        aliases.update({"korea republic", "korea"})
    if normalized_team == "czech republic":
        aliases.update({"czechia"})
    return any(alias and alias in normalized_text for alias in aliases)


def _result_quality_score(result: Any, home_team: str, away_team: str) -> int:
    title = str(getattr(result, "title", "") or "")
    description = str(getattr(result, "description", "") or "")
    url = str(getattr(result, "url", "") or "")
    haystack = " ".join([title, description, url])
    domain = _domain_from_url(url)
    score = DOMAIN_PRIORITY.get(domain, 40)
    lowered = ascii_fold(haystack).lower()
    if _contains_team_terms(haystack, home_team):
        score += 25
    if _contains_team_terms(haystack, away_team):
        score += 25
    if "predicted lineup" in lowered or "possible lineup" in lowered:
        score += 18
    if "predicted xi" in lowered or "predicted xis" in lowered:
        score += 18
    if "team news" in lowered:
        score += 12
    if "injury, suspension list" in lowered or "injury and suspension list" in lowered:
        score += 14
    if "preview" in lowered:
        score += 8
    if "prediction" in lowered:
        score += 4
    return score


def select_search_results(
    search_data: Any,
    *,
    home_team: str,
    away_team: str,
    allowed_domains: list[str] | None = None,
    max_sources: int = MAX_SOURCES_PER_MATCH,
) -> list[dict[str, Any]]:
    allowed = {_domain_from_url(f"https://{domain}") for domain in (allowed_domains or [])}
    ranked: list[dict[str, Any]] = []
    for raw_result in _result_iter(search_data):
        result = _to_namespace(raw_result)
        url = str(getattr(result, "url", "") or "").strip()
        if not url:
            continue
        haystack = " ".join(
            [
                str(getattr(result, "title", "") or ""),
                str(getattr(result, "description", "") or ""),
                url,
            ]
        )
        if not (
            _contains_team_terms(haystack, home_team) and _contains_team_terms(haystack, away_team)
        ):
            continue
        domain = _domain_from_url(url)
        if allowed and domain not in allowed:
            continue
        ranked.append(
            {
                "url": url,
                "title": str(getattr(result, "title", "") or ""),
                "description": str(getattr(result, "description", "") or ""),
                "domain": domain,
                "source_name": _source_name_from_domain(domain),
                "quality_score": _result_quality_score(result, home_team, away_team),
            }
        )

    ranked.sort(
        key=lambda item: (-int(item["quality_score"]), item["source_name"], item["url"])
    )
    deduped: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for item in ranked:
        if item["url"] in seen_urls:
            continue
        seen_urls.add(item["url"])
        deduped.append(item)
        if len(deduped) >= max_sources:
            break
    return deduped


def _clean_markdown(markdown: str | None) -> str:
    text = (markdown or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_lineup_lines(lines: list[str]) -> str | None:
    pattern = re.compile(
        r"(possible starting lineup|predicted lineup|predicted xi|possible xi)",
        re.IGNORECASE,
    )
    selected: list[str] = []
    for line in lines:
        compact = line.strip()
        if compact.startswith("#") or compact.startswith("!["):
            continue
        if compact and ":" in compact and pattern.search(compact):
            selected.append(compact)
    if not selected:
        return None
    return "\n".join(dict.fromkeys(selected))


def _extract_keyword_lines(lines: list[str], keywords: list[str], *, limit: int) -> str | None:
    selected: list[str] = []
    for line in lines:
        compact = " ".join(line.split()).strip()
        if not compact or compact.startswith("!"):
            continue
        lowered = ascii_fold(compact).lower()
        if any(keyword in lowered for keyword in keywords):
            selected.append(compact)
        if len(selected) >= limit:
            break
    if not selected:
        return None
    return "\n".join(dict.fromkeys(selected))


def _extract_sentences(markdown: str, keywords: list[str], *, limit: int) -> str | None:
    sentences = re.split(r"(?<=[.!?])\s+", markdown.replace("\n", " "))
    selected: list[str] = []
    for sentence in sentences:
        compact = " ".join(sentence.split()).strip()
        if not compact:
            continue
        lowered = ascii_fold(compact).lower()
        if any(keyword in lowered for keyword in keywords):
            selected.append(compact)
        if len(selected) >= limit:
            break
    if not selected:
        return None
    return " ".join(dict.fromkeys(selected))


def extract_context_sections(markdown: str) -> dict[str, str | None]:
    cleaned = _clean_markdown(markdown)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    injury_notes = _extract_keyword_lines(
        lines,
        [
            "injury",
            "suspension",
            "out:",
            "doubtful:",
            "unavailable",
            "returns to the squad",
            "fitness",
        ],
        limit=6,
    ) or _extract_sentences(
        cleaned,
        [
            "injur",
            "suspend",
            "fitness",
            "doubt",
            "ruled out",
            "miss out",
            "absence",
            "available",
            "return to the squad",
        ],
        limit=SENTENCE_JOIN_LIMIT,
    )
    return {
        "predicted_lineup_text": _extract_lineup_lines(lines),
        "injury_notes": injury_notes,
        "coach_quotes": _extract_sentences(
            cleaned,
            [
                '"',
                "manager said",
                "coach said",
                "head coach",
                "boss said",
                "manager admitted",
                "coach admitted",
            ],
            limit=3,
        ),
        "key_player_notes": _extract_sentences(
            cleaned,
            [
                "key player",
                "one to watch",
                "captain",
                "star",
                "talisman",
                "lead the line",
                "returns to the xi",
                "returns to the lineup",
            ],
            limit=4,
        ),
        "content_excerpt": cleaned[:MARKDOWN_EXCERPT_LIMIT] or None,
    }


def _metadata_attr(metadata: Any, field: str) -> Any:
    if metadata is None:
        return None
    if isinstance(metadata, dict):
        return metadata.get(field)
    return getattr(metadata, field, None)


def collect_match_context(
    client: Any,
    match_row: pd.Series,
    *,
    include_domains: list[str] | None = None,
    search_limit: int = SEARCH_RESULT_LIMIT,
    max_sources: int = MAX_SOURCES_PER_MATCH,
) -> list[dict[str, Any]]:
    search_query = build_search_query(match_row)
    search_results = client.search(
        search_query,
        include_domains=include_domains or DEFAULT_INCLUDE_DOMAINS,
        limit=search_limit,
        timeout=15000,
    )
    chosen_sources = select_search_results(
        search_results,
        home_team=str(match_row["home_team"]),
        away_team=str(match_row["away_team"]),
        allowed_domains=include_domains or DEFAULT_INCLUDE_DOMAINS,
        max_sources=max_sources,
    )

    fetched_at = datetime.now(UTC).isoformat()
    rows: list[dict[str, Any]] = []
    for source_rank, source in enumerate(chosen_sources, start=1):
        scraped = client.scrape(
            source["url"],
            formats=["markdown"],
            only_main_content=True,
            timeout=20000,
        )
        metadata = getattr(scraped, "metadata", None)
        sections = extract_context_sections(getattr(scraped, "markdown", "") or "")
        rows.append(
            {
                "match_no": int(match_row["match_no"]),
                "stage": str(match_row["stage"]),
                "group_name": str(match_row["group_name"]),
                "date_et": str(match_row["date_et"]),
                "time_et": str(match_row["time_et"]),
                "home_team": str(match_row["home_team"]),
                "away_team": str(match_row["away_team"]),
                "home_team_zh": TEAM_NAME_ZH.get(str(match_row["home_team"])),
                "away_team_zh": TEAM_NAME_ZH.get(str(match_row["away_team"])),
                "search_query": search_query,
                "source_rank": source_rank,
                "source_quality_score": int(source["quality_score"]),
                "source_name": _metadata_attr(metadata, "site_name") or source["source_name"],
                "source_domain": source["domain"],
                "source_title": _metadata_attr(metadata, "title") or source["title"],
                "source_url": source["url"],
                "source_description": source["description"]
                or _metadata_attr(metadata, "description"),
                "published_time": _metadata_attr(metadata, "published_time")
                or _metadata_attr(metadata, "article:published_time"),
                "predicted_lineup_text": sections["predicted_lineup_text"],
                "injury_notes": sections["injury_notes"],
                "coach_quotes": sections["coach_quotes"],
                "key_player_notes": sections["key_player_notes"],
                "content_excerpt": sections["content_excerpt"],
                "fetch_warning": getattr(scraped, "warning", None),
                "fetched_at": fetched_at,
            }
        )
    return rows


def build_pre_match_context(
    fixtures: pd.DataFrame,
    *,
    client: Any,
    include_domains: list[str] | None = None,
    search_limit: int = SEARCH_RESULT_LIMIT,
    max_sources: int = MAX_SOURCES_PER_MATCH,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, match_row in fixtures.iterrows():
        try:
            rows.extend(
                collect_match_context(
                    client,
                    match_row,
                    include_domains=include_domains,
                    search_limit=search_limit,
                    max_sources=max_sources,
                )
            )
        except Exception as exc:
            rows.append(
                {
                    "match_no": int(match_row["match_no"]),
                    "stage": str(match_row["stage"]),
                    "group_name": str(match_row["group_name"]),
                    "date_et": str(match_row["date_et"]),
                    "time_et": str(match_row["time_et"]),
                    "home_team": str(match_row["home_team"]),
                    "away_team": str(match_row["away_team"]),
                    "home_team_zh": TEAM_NAME_ZH.get(str(match_row["home_team"])),
                    "away_team_zh": TEAM_NAME_ZH.get(str(match_row["away_team"])),
                    "search_query": build_search_query(match_row),
                    "source_rank": None,
                    "source_quality_score": None,
                    "source_name": None,
                    "source_domain": None,
                    "source_title": None,
                    "source_url": None,
                    "source_description": None,
                    "published_time": None,
                    "predicted_lineup_text": None,
                    "injury_notes": None,
                    "coach_quotes": None,
                    "key_player_notes": None,
                    "content_excerpt": None,
                    "fetch_warning": str(exc),
                    "fetched_at": datetime.now(UTC).isoformat(),
                }
            )
    if not rows:
        return pd.DataFrame(columns=MATCH_CONTEXT_COLUMNS)
    return pd.DataFrame(rows)[MATCH_CONTEXT_COLUMNS].sort_values(
        ["match_no", "source_rank", "source_name"],
        na_position="last",
    )


def save_pre_match_context(context_df: pd.DataFrame) -> PreMatchContextOutputs:
    ensure_project_directories()
    context_df.to_parquet(PRE_MATCH_CONTEXT_2026_PATH, index=False)
    return PreMatchContextOutputs(
        pre_match_context_path=str(PRE_MATCH_CONTEXT_2026_PATH),
        row_count=len(context_df),
        match_count=int(context_df["match_no"].nunique()) if not context_df.empty else 0,
        source_count=(
            int(context_df["source_url"].dropna().nunique()) if not context_df.empty else 0
        ),
    )


def prepare_pre_match_context(
    *,
    as_of_date: date | None = None,
    days_ahead: int | None = 7,
    limit: int | None = None,
    include_past: bool = False,
    include_domains: list[str] | None = None,
    search_limit: int = SEARCH_RESULT_LIMIT,
    max_sources: int = MAX_SOURCES_PER_MATCH,
    client: Any | None = None,
) -> PreMatchContextOutputs:
    fixtures = pd.read_parquet(FIXTURES_PATH)
    targets = select_target_fixtures(
        fixtures,
        as_of_date=as_of_date,
        days_ahead=days_ahead,
        limit=limit,
        include_past=include_past,
    )
    firecrawl_client = client or load_firecrawl_client()
    context_df = build_pre_match_context(
        targets,
        client=firecrawl_client,
        include_domains=include_domains,
        search_limit=search_limit,
        max_sources=max_sources,
    )
    outputs = save_pre_match_context(context_df)
    print(
        f"pre_match_context -> {outputs.pre_match_context_path} "
        f"({outputs.row_count} rows / {outputs.match_count} matches / "
        f"{outputs.source_count} sources)"
    )
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect pre-match context via Firecrawl.")
    parser.add_argument("--days-ahead", type=int, default=7)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--include-past", action="store_true")
    parser.add_argument("--search-limit", type=int, default=SEARCH_RESULT_LIMIT)
    parser.add_argument("--max-sources", type=int, default=MAX_SOURCES_PER_MATCH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = prepare_pre_match_context(
        as_of_date=date.today(),
        days_ahead=args.days_ahead,
        limit=args.limit,
        include_past=args.include_past,
        search_limit=args.search_limit,
        max_sources=args.max_sources,
    )
    print(asdict(outputs))


if __name__ == "__main__":
    main()
