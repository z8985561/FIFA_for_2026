from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from src.firecrawl_preview_pipeline import (
    build_pre_match_context,
    build_search_query,
    extract_context_sections,
    select_search_results,
    select_target_fixtures,
)


def test_build_search_query_contains_match_identity() -> None:
    row = pd.Series(
        {
            "home_team": "Mexico",
            "away_team": "South Africa",
            "date_et": "2026-06-11",
        }
    )

    query = build_search_query(row)

    assert "Mexico vs South Africa" in query
    assert "2026-06-11" in query
    assert "predicted lineup" in query


def test_select_target_fixtures_filters_upcoming_matches() -> None:
    fixtures = pd.DataFrame(
        [
            {"match_no": 1, "date_et": "2026-06-11"},
            {"match_no": 2, "date_et": "2026-06-13"},
            {"match_no": 3, "date_et": "2026-06-20"},
        ]
    )

    selected = select_target_fixtures(
        fixtures,
        as_of_date=pd.Timestamp("2026-06-13").date(),
        days_ahead=3,
    )

    assert selected["match_no"].tolist() == [2]


def test_select_search_results_prefers_relevant_preview_links() -> None:
    search_data = SimpleNamespace(
        web=[
            SimpleNamespace(
                url=(
                    "https://www.sportsmole.co.uk/football/south-korea/world-cup-2026/"
                    "preview/south-korea-vs-czech-republic-prediction-team-news-lineups_598881.html"
                ),
                title="Preview: South Korea vs Czech Republic | World Cup 2026",
                description="Prediction, team news and lineups.",
            ),
            SimpleNamespace(
                url="https://example.com/other-match-preview",
                title="Other match preview",
                description="Unrelated",
            ),
            SimpleNamespace(
                url=(
                    "https://www.sportsmole.co.uk/football/world-cup/"
                    "south-korea-vs-czech-republic_game_248701.html"
                ),
                title="South Korea vs Czech Republic - Match Guide",
                description="Data analysis for the fixture.",
            ),
            SimpleNamespace(
                url="https://onefootball.com/en/news/preview-south-korea-vs-czech-republic-123",
                title="Preview | South Korea vs Czech Republic",
                description="Team news and lineups.",
            ),
        ]
    )

    results = select_search_results(
        search_data,
        home_team="South Korea",
        away_team="Czech Republic",
        allowed_domains=["sportsmole.co.uk"],
        max_sources=2,
    )

    assert len(results) == 2
    assert results[0]["source_name"] == "Sports Mole"
    assert "team-news-lineups" in results[0]["url"]


def test_extract_context_sections_captures_lineups_and_notes() -> None:
    markdown = """
    ## Team News
    South Korea will be without Kim Example through injury, while Lee Sample returns to the squad.
    Head coach Hong Myung-bo said "we are ready for the challenge".

    South Korea possible starting lineup:
    Kim Seung-gyu; Lee Gi-hyuk, Kim Min-jae, Lee Han-beom; Son Heung-min

    Czech Republic possible starting lineup:
    Matej Kovar; Vladimir Coufal, Robin Hranac, Ladislav Krejci; Patrik Schick

    One to watch: Son Heung-min is the star attacker expected to lead the line.
    """

    sections = extract_context_sections(markdown)

    assert "South Korea possible starting lineup" in str(sections["predicted_lineup_text"])
    assert "injury" in str(sections["injury_notes"]).lower()
    assert "Head coach" in str(sections["coach_quotes"])
    assert "One to watch" in str(sections["key_player_notes"])


def test_build_pre_match_context_uses_client_search_and_scrape() -> None:
    fixtures = pd.DataFrame(
        [
            {
                "match_no": 2,
                "stage": "Group Stage",
                "group_name": "Group A",
                "date_et": "2026-06-11",
                "time_et": "22:00",
                "home_team": "South Korea",
                "away_team": "Czech Republic",
            }
        ]
    )

    class FakeClient:
        def search(self, *_args, **_kwargs):
            return SimpleNamespace(
                web=[
                    SimpleNamespace(
                        url=(
                            "https://www.sportsmole.co.uk/football/south-korea/world-cup-2026/"
                            "preview/south-korea-vs-czech-republic-prediction-team-news-lineups_598881.html"
                        ),
                        title="Preview: South Korea vs Czech Republic | World Cup 2026",
                        description="Prediction, team news and lineups.",
                    )
                ]
            )

        def scrape(self, _url, **_kwargs):
            markdown = """
            South Korea possible starting lineup:
            Kim Seung-gyu; Lee Gi-hyuk, Kim Min-jae

            Head coach Hong Myung-bo said "we are ready".
            Son Heung-min is the star player expected to lead the line.
            """
            metadata = SimpleNamespace(
                site_name="Sports Mole",
                title="Preview",
                description="Prediction, team news and lineups.",
                published_time="2026-06-09T14:20:00Z",
            )
            return SimpleNamespace(markdown=markdown, metadata=metadata, warning=None)

    context = build_pre_match_context(fixtures, client=FakeClient())

    assert len(context) == 1
    assert context.loc[0, "source_name"] == "Sports Mole"
    assert context.loc[0, "home_team"] == "South Korea"
    assert "possible starting lineup" in str(context.loc[0, "predicted_lineup_text"]).lower()
