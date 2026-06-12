from __future__ import annotations

import pandas as pd

from src.official_results_pipeline import build_official_results_frame


def test_build_official_results_frame_normalizes_names_and_completion() -> None:
    payload = {
        "Results": [
            {
                "IdMatch": "400021443",
                "IdSeason": "285023",
                "IdStage": "289273",
                "IdGroup": "289275",
                "MatchNumber": 2,
                "StageName": [{"Locale": "en-GB", "Description": "First Stage"}],
                "GroupName": [{"Locale": "en-GB", "Description": "Group A"}],
                "Date": "2026-06-12T02:00:00Z",
                "LocalDate": "2026-06-11T20:00:00Z",
                "Home": {
                    "TeamName": [{"Locale": "en-GB", "Description": "Korea Republic"}],
                },
                "Away": {
                    "TeamName": [{"Locale": "en-GB", "Description": "Czechia"}],
                },
                "HomeTeamScore": 2,
                "AwayTeamScore": 1,
                "HomeTeamPenaltyScore": None,
                "AwayTeamPenaltyScore": None,
                "Winner": "43822",
                "MatchStatus": 0,
                "ResultType": 0,
                "OfficialityStatus": 0,
                "Attendance": "45678",
                "LastPeriodUpdate": "2026-06-12T03:58:00Z",
                "MatchReportUrl": "https://www.fifa.com/example",
                "Stadium": {
                    "Name": [{"Locale": "en-GB", "Description": "Estadio Akron"}],
                    "CityName": [{"Locale": "en-GB", "Description": "Guadalajara"}],
                    "CountryName": [{"Locale": "en-GB", "Description": "Mexico"}],
                },
            },
            {
                "IdMatch": "400021444",
                "IdSeason": "285023",
                "MatchNumber": 3,
                "StageName": [{"Locale": "en-GB", "Description": "First Stage"}],
                "GroupName": [{"Locale": "en-GB", "Description": "Group B"}],
                "Date": "2026-06-12T19:00:00Z",
                "Home": {
                    "TeamName": [{"Locale": "en-GB", "Description": "Canada"}],
                },
                "Away": {
                    "TeamName": [
                        {
                            "Locale": "en-GB",
                            "Description": "Bosnia and Herzegovina",
                        }
                    ],
                },
                "HomeTeamScore": None,
                "AwayTeamScore": None,
                "MatchStatus": 1,
            },
        ]
    }

    frame = build_official_results_frame(payload)

    assert len(frame) == 2
    first = frame.iloc[0]
    assert first["match_no"] == 2
    assert first["home_team"] == "South Korea"
    assert first["away_team"] == "Czech Republic"
    assert first["home_score"] == 2
    assert first["away_score"] == 1
    assert bool(first["completed"]) is True
    assert first["attendance"] == 45678
    assert isinstance(first["date_utc"], pd.Timestamp)

    second = frame.iloc[1]
    assert second["match_no"] == 3
    assert bool(second["completed"]) is False
    assert pd.isna(second["home_score"])
    assert pd.isna(second["away_score"])
