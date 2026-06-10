from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from .project_paths import PREDICTED_LINEUPS_PATH, ensure_project_directories

LINEUP_STATUS_PREDICTED = "predicted"

TEAM_NAME_ZH = {
    "Mexico": "墨西哥",
    "South Africa": "南非",
    "South Korea": "韩国",
    "Czech Republic": "捷克",
    "Canada": "加拿大",
    "Bosnia and Herzegovina": "波黑",
    "United States": "美国",
    "Paraguay": "巴拉圭",
}

PREDICTED_LINEUP_SEEDS = [
    {
        "match_no": 1,
        "match_date": "2026-06-11",
        "group_name": "Group A",
        "home_team": "Mexico",
        "away_team": "South Africa",
        "team_name": "Mexico",
        "formation": "4-3-3",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/mexico/world-cup-2026/"
            "preview/mexico-vs-south-africa-prediction-team-news-lineups_598869.html"
        ),
        "players": [
            ("GK", "Guillermo Ochoa"),
            ("DF", "Jorge Sanchez"),
            ("DF", "Cesar Montes"),
            ("DF", "Edson Alvarez"),
            ("DF", "Jesus Gallardo"),
            ("MF", "Erick Gutierrez"),
            ("MF", "Alvaro Fidalgo"),
            ("MF", "Orbelin Pineda"),
            ("FW", "Roberto Alvarado"),
            ("FW", "Raul Jimenez"),
            ("FW", "Julian Quinones"),
        ],
    },
    {
        "match_no": 1,
        "match_date": "2026-06-11",
        "group_name": "Group A",
        "home_team": "Mexico",
        "away_team": "South Africa",
        "team_name": "South Africa",
        "formation": "4-2-3-1",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/mexico/world-cup-2026/"
            "preview/mexico-vs-south-africa-prediction-team-news-lineups_598869.html"
        ),
        "players": [
            ("GK", "Ronwen Williams"),
            ("DF", "Khuliso Mudau"),
            ("DF", "Mbekezeli Mbokazi"),
            ("DF", "Ime Okon"),
            ("DF", "Aubrey Modiba"),
            ("MF", "Thalente Mbatha"),
            ("MF", "Yaya Sithole"),
            ("MF", "Teboho Mokoena"),
            ("FW", "Oswin Appollis"),
            ("FW", "Lyle Foster"),
            ("FW", "Relebohile Mofokeng"),
        ],
    },
    {
        "match_no": 2,
        "match_date": "2026-06-11",
        "group_name": "Group A",
        "home_team": "South Korea",
        "away_team": "Czech Republic",
        "team_name": "South Korea",
        "formation": "4-2-3-1",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/south-korea/world-cup-2026/"
            "preview/south-korea-vs-czech-republic-prediction-team-news-lineups_598881.html"
        ),
        "players": [
            ("GK", "Kim Seung-gyu"),
            ("DF", "Lee Gi-hyuk"),
            ("DF", "Kim Min-jae"),
            ("DF", "Lee Han-beom"),
            ("MF", "Seol Young-woo"),
            ("MF", "Hwang In-beom"),
            ("MF", "Paik Seung-ho"),
            ("MF", "Lee Tae-seok"),
            ("FW", "Hwang Hee-chan"),
            ("FW", "Lee Jae-sung"),
            ("FW", "Son Heung-min"),
        ],
    },
    {
        "match_no": 2,
        "match_date": "2026-06-11",
        "group_name": "Group A",
        "home_team": "South Korea",
        "away_team": "Czech Republic",
        "team_name": "Czech Republic",
        "formation": "3-4-3",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/south-korea/world-cup-2026/"
            "preview/south-korea-vs-czech-republic-prediction-team-news-lineups_598881.html"
        ),
        "players": [
            ("GK", "Matej Kovar"),
            ("DF", "Stepan Chaloupek"),
            ("DF", "Robin Hranac"),
            ("DF", "Ladislav Krejci"),
            ("MF", "Vladimir Coufal"),
            ("MF", "Lukas Cerv"),
            ("MF", "Tomas Soucek"),
            ("MF", "David Jurasek"),
            ("FW", "Lukas Provod"),
            ("FW", "Pavel Sulc"),
            ("FW", "Patrik Schick"),
        ],
    },
    {
        "match_no": 7,
        "match_date": "2026-06-12",
        "group_name": "Group B",
        "home_team": "Canada",
        "away_team": "Bosnia and Herzegovina",
        "team_name": "Canada",
        "formation": "3-4-2-1",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/canada/world-cup-2026/"
            "predicted-lineups/davies-status-in-question-predicted-canada-lineup-vs-"
            "bosnia-herzegovina_598906.html"
        ),
        "players": [
            ("GK", "Maxime Crepeau"),
            ("DF", "Alistair Johnston"),
            ("DF", "Luc de Fougerolles"),
            ("DF", "Derek Cornelius"),
            ("MF", "Richie Laryea"),
            ("MF", "Tajon Buchanan"),
            ("MF", "Stephen Eustaquio"),
            ("MF", "Ismael Kone"),
            ("MF", "Liam Millar"),
            ("FW", "Jonathan David"),
            ("FW", "Cyle Larin"),
        ],
    },
    {
        "match_no": 7,
        "match_date": "2026-06-12",
        "group_name": "Group B",
        "home_team": "Canada",
        "away_team": "Bosnia and Herzegovina",
        "team_name": "Bosnia and Herzegovina",
        "formation": "4-3-3",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/canada/world-cup-2026/"
            "predicted-lineups/davies-status-in-question-predicted-canada-lineup-vs-"
            "bosnia-herzegovina_598906.html"
        ),
        "players": [
            ("GK", "Nikola Vasilj"),
            ("DF", "Dzenis Burnic"),
            ("DF", "Armin Gigovic"),
            ("DF", "Tarik Muharemovic"),
            ("DF", "Amar Memic"),
            ("MF", "Eldar Celik"),
            ("MF", "Ivan Basic"),
            ("MF", "Esmir Bajraktarevic"),
            ("FW", "Madjid Mahmic"),
            ("FW", "Ermedin Demirovic"),
            ("FW", "Esmir Bazdar"),
        ],
    },
    {
        "match_no": 19,
        "match_date": "2026-06-12",
        "group_name": "Group D",
        "home_team": "United States",
        "away_team": "Paraguay",
        "team_name": "United States",
        "formation": "4-3-3",
        "source_name": "RotoWire",
        "source_url": (
            "https://www.rotowire.com/soccer/article/2026-world-cup-group-d-preview-"
            "united-states-paraguay-australia-turkiye-tactics-lineups-set-pieces-"
            "odds-110622"
        ),
        "players": [
            ("GK", "Matt Freese"),
            ("DF", "Chris Richards"),
            ("DF", "Auston Trusty"),
            ("DF", "Mark McKenzie"),
            ("MF", "Tim Weah"),
            ("MF", "Weston McKennie"),
            ("MF", "Tyler Adams"),
            ("MF", "Antonee Robinson"),
            ("FW", "Malik Tillman"),
            ("FW", "Folarin Balogun"),
            ("FW", "Christian Pulisic"),
        ],
    },
    {
        "match_no": 19,
        "match_date": "2026-06-12",
        "group_name": "Group D",
        "home_team": "United States",
        "away_team": "Paraguay",
        "team_name": "Paraguay",
        "formation": "4-2-3-1",
        "source_name": "RotoWire",
        "source_url": (
            "https://www.rotowire.com/soccer/article/2026-world-cup-group-d-preview-"
            "united-states-paraguay-australia-turkiye-tactics-lineups-set-pieces-"
            "odds-110622"
        ),
        "players": [
            ("GK", "Gatito Fernandez"),
            ("DF", "Juan Caceres"),
            ("DF", "Omar Alderete"),
            ("DF", "Gustavo Gomez"),
            ("DF", "Junior Alonso"),
            ("MF", "Damian Bobadilla"),
            ("MF", "Andres Cubas"),
            ("MF", "Julio Enciso"),
            ("MF", "Diego Gomez"),
            ("MF", "Miguel Almiron"),
            ("FW", "Antonio Sanabria"),
        ],
    },
]


@dataclass(frozen=True)
class LineupOutputs:
    predicted_lineups_path: str
    lineup_rows: int
    match_count: int
    team_count: int


def build_predicted_lineups() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for seed in PREDICTED_LINEUP_SEEDS:
        for lineup_order, (position_group, player_name) in enumerate(seed["players"], start=1):
            rows.append(
                {
                    "match_no": seed["match_no"],
                    "match_date": pd.to_datetime(seed["match_date"]).date(),
                    "group_name": seed["group_name"],
                    "home_team": seed["home_team"],
                    "away_team": seed["away_team"],
                    "home_team_zh": TEAM_NAME_ZH[str(seed["home_team"])],
                    "away_team_zh": TEAM_NAME_ZH[str(seed["away_team"])],
                    "team_name": seed["team_name"],
                    "team_name_zh": TEAM_NAME_ZH[str(seed["team_name"])],
                    "lineup_status": LINEUP_STATUS_PREDICTED,
                    "formation": seed["formation"],
                    "lineup_order": lineup_order,
                    "position_group": position_group,
                    "player_name": player_name,
                    "source_name": seed["source_name"],
                    "source_url": seed["source_url"],
                }
            )
    return pd.DataFrame(rows).sort_values(["match_no", "team_name", "lineup_order"])


def prepare_predicted_lineups() -> LineupOutputs:
    ensure_project_directories()
    lineups = build_predicted_lineups()
    lineups.to_parquet(PREDICTED_LINEUPS_PATH, index=False)
    return LineupOutputs(
        predicted_lineups_path=str(PREDICTED_LINEUPS_PATH),
        lineup_rows=len(lineups),
        match_count=int(lineups["match_no"].nunique()),
        team_count=int(lineups["team_name"].nunique()),
    )


def main() -> None:
    outputs = prepare_predicted_lineups()
    for key, value in asdict(outputs).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
