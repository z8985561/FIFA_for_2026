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
    "Qatar": "卡塔尔",
    "Switzerland": "瑞士",
    "Brazil": "巴西",
    "Morocco": "摩洛哥",
    "Haiti": "海地",
    "Scotland": "苏格兰",
    "Australia": "澳大利亚",
    "Turkey": "土耳其",
    "Germany": "德国",
    "Curaçao": "库拉索",
    "Ivory Coast": "科特迪瓦",
    "Ecuador": "厄瓜多尔",
    "Netherlands": "荷兰",
    "Japan": "日本",
    "Tunisia": "突尼斯",
    "Sweden": "瑞典",
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
    {
        "match_no": 8,
        "match_date": "2026-06-14",
        "group_name": "Group B",
        "home_team": "Qatar",
        "away_team": "Switzerland",
        "team_name": "Qatar",
        "formation": "4-3-3",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/qatar/world-cup-2026/"
            "predicted-lineups/afif-to-lead-the-charge-how-qatar-could-line-up-"
            "against-switzerland_598998.html"
        ),
        "players": [
            ("GK", "Abunada"),
            ("DF", "Al-Oui"),
            ("DF", "Khoukhi"),
            ("DF", "Pedro Miguel"),
            ("DF", "Ahmed"),
            ("MF", "Laye"),
            ("MF", "Fathi"),
            ("MF", "Gaber"),
            ("FW", "Abdurisag"),
            ("FW", "Afif"),
            ("FW", "Edmilson"),
        ],
    },
    {
        "match_no": 8,
        "match_date": "2026-06-14",
        "group_name": "Group B",
        "home_team": "Qatar",
        "away_team": "Switzerland",
        "team_name": "Switzerland",
        "formation": "4-2-3-1",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/switzerland/world-cup-2026/"
            "predicted-lineups/the-old-guard-how-switzerland-could-line-up-"
            "against-qatar_598999.html"
        ),
        "players": [
            ("GK", "Kobel"),
            ("DF", "Widmer"),
            ("DF", "Akanji"),
            ("DF", "Elvedi"),
            ("DF", "Rodriguez"),
            ("MF", "Xhaka"),
            ("MF", "Freuler"),
            ("MF", "Vargas"),
            ("MF", "Rieder"),
            ("MF", "Ndoye"),
            ("FW", "Amdouni"),
        ],
    },
    {
        "match_no": 13,
        "match_date": "2026-06-14",
        "group_name": "Group C",
        "home_team": "Brazil",
        "away_team": "Morocco",
        "team_name": "Brazil",
        "formation": "4-2-3-1",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/brazil/world-cup-2026/"
            "predicted-lineups/right-back-dilemma-for-ancelotti-predicted-brazil-"
            "lineup-vs-morocco_598949.html"
        ),
        "players": [
            ("GK", "Alisson"),
            ("DF", "Danilo"),
            ("DF", "Marquinhos"),
            ("DF", "Gabriel"),
            ("DF", "Sandro"),
            ("MF", "Casemiro"),
            ("MF", "Guimaraes"),
            ("MF", "Raphinha"),
            ("MF", "Paqueta"),
            ("MF", "Vinicius Jr"),
            ("FW", "Cunha"),
        ],
    },
    {
        "match_no": 13,
        "match_date": "2026-06-14",
        "group_name": "Group C",
        "home_team": "Brazil",
        "away_team": "Morocco",
        "team_name": "Morocco",
        "formation": "4-3-3",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/morocco/world-cup-2026/"
            "predicted-lineups/enforced-changes-after-double-injury-blow-"
            "predicted-morocco-lineup-vs-brazil_598950.html"
        ),
        "players": [
            ("GK", "Bounou"),
            ("DF", "Hakimi"),
            ("DF", "Diop"),
            ("DF", "Riad"),
            ("DF", "Mazraoui"),
            ("MF", "Amrabat"),
            ("MF", "El Aynaoui"),
            ("MF", "Ounahi"),
            ("FW", "Diaz"),
            ("FW", "Saibari"),
            ("FW", "El Khannouss"),
        ],
    },
    {
        "match_no": 14,
        "match_date": "2026-06-14",
        "group_name": "Group C",
        "home_team": "Haiti",
        "away_team": "Scotland",
        "team_name": "Haiti",
        "formation": "4-4-2",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/haiti/world-cup-2026/"
            "predicted-lineups/one-sunderland-one-wolves-predicted-haiti-lineup-"
            "vs-scotland_598954.html"
        ),
        "players": [
            ("GK", "Placide"),
            ("DF", "Arcus"),
            ("DF", "Ade"),
            ("DF", "Delcroix"),
            ("DF", "Experience"),
            ("MF", "Deedson"),
            ("MF", "Jean Jacques"),
            ("MF", "Bellegarde"),
            ("MF", "Providence"),
            ("FW", "Isidor"),
            ("FW", "Nazon"),
        ],
    },
    {
        "match_no": 14,
        "match_date": "2026-06-14",
        "group_name": "Group C",
        "home_team": "Haiti",
        "away_team": "Scotland",
        "team_name": "Scotland",
        "formation": "4-4-2",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/scotland/world-cup-2026/"
            "predicted-lineups/mctominay-decision-gunn-or-gordon-in-goal-"
            "predicted-scotland-lineup-vs-haiti_598955.html"
        ),
        "players": [
            ("GK", "Gunn"),
            ("DF", "Hickey"),
            ("DF", "Hanley"),
            ("DF", "Souttar"),
            ("DF", "Robertson"),
            ("MF", "Doak"),
            ("MF", "McTominay"),
            ("MF", "Ferguson"),
            ("MF", "McGinn"),
            ("FW", "Adams"),
            ("FW", "Shankland"),
        ],
    },
    {
        "match_no": 20,
        "match_date": "2026-06-13",
        "group_name": "Group D",
        "home_team": "Australia",
        "away_team": "Turkey",
        "team_name": "Australia",
        "formation": "5-4-1",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/australia/world-cup-2026/"
            "predicted-lineups/will-toure-leckie-start-how-australia-could-line-up-"
            "against-turkey_599008.html"
        ),
        "players": [
            ("GK", "Ryan"),
            ("DF", "Italiano"),
            ("DF", "Circati"),
            ("DF", "Souttar"),
            ("DF", "Herrington"),
            ("DF", "Bos"),
            ("MF", "Metcalfe"),
            ("MF", "Irvine"),
            ("MF", "O'Neill"),
            ("MF", "Leckie"),
            ("FW", "Toure"),
        ],
    },
    {
        "match_no": 20,
        "match_date": "2026-06-13",
        "group_name": "Group D",
        "home_team": "Australia",
        "away_team": "Turkey",
        "team_name": "Turkey",
        "formation": "4-2-3-1",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/australia/world-cup-2026/"
            "predicted-lineups/will-yildiz-be-involved-how-turkey-could-line-up-"
            "against-australia_599009.html"
        ),
        "players": [
            ("GK", "Cakir"),
            ("DF", "Celik"),
            ("DF", "Demiral"),
            ("DF", "Bardakci"),
            ("DF", "Elmali"),
            ("MF", "Calhanoglu"),
            ("MF", "Yuksek"),
            ("MF", "Guler"),
            ("MF", "Kokcu"),
            ("MF", "Yilmaz"),
            ("FW", "Gul"),
        ],
    },
    {
        "match_no": 25,
        "match_date": "2026-06-15",
        "group_name": "Group E",
        "home_team": "Germany",
        "away_team": "Curaçao",
        "team_name": "Germany",
        "formation": "4-2-3-1",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/germany/world-cup-2026/"
            "predicted-lineups/neuers-return-how-germany-could-line-up-against-"
            "curacao_599049.html"
        ),
        "players": [
            ("GK", "Neuer"),
            ("DF", "Kimmich"),
            ("DF", "Tah"),
            ("DF", "Schlotterbeck"),
            ("DF", "Brown"),
            ("MF", "F Nmecha"),
            ("MF", "Pavlovic"),
            ("MF", "Sane"),
            ("MF", "Musiala"),
            ("MF", "Wirtz"),
            ("FW", "Havertz"),
        ],
    },
    {
        "match_no": 25,
        "match_date": "2026-06-15",
        "group_name": "Group E",
        "home_team": "Germany",
        "away_team": "Curaçao",
        "team_name": "Curaçao",
        "formation": "4-3-3",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/germany/world-cup-2026/"
            "predicted-lineups/bacuna-brothers-to-start-how-curacao-could-line-up-"
            "against-germany_599048.html"
        ),
        "players": [
            ("GK", "Room"),
            ("DF", "Sambo"),
            ("DF", "Obispo"),
            ("DF", "Gaari"),
            ("DF", "Floranus"),
            ("MF", "Comenencia"),
            ("MF", "J Bacuna"),
            ("MF", "L Bacuna"),
            ("FW", "Chong"),
            ("FW", "Gorre"),
            ("FW", "Antonisse"),
        ],
    },
    {
        "match_no": 26,
        "match_date": "2026-06-15",
        "group_name": "Group E",
        "home_team": "Ivory Coast",
        "away_team": "Ecuador",
        "team_name": "Ivory Coast",
        "formation": "4-3-3",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/ivory-coast/world-cup-2026/"
            "predicted-lineups/winger-dilemma-for-fae-predicted-ivory-coast-lineup-"
            "vs-ecuador_599037.html"
        ),
        "players": [
            ("GK", "Y. Fofana"),
            ("DF", "Doue"),
            ("DF", "Agbadou"),
            ("DF", "Kossounou"),
            ("DF", "Konan"),
            ("MF", "Kessie"),
            ("MF", "Sangare"),
            ("MF", "S. Fofana"),
            ("FW", "Diallo"),
            ("FW", "Guessand"),
            ("FW", "Diomande"),
        ],
    },
    {
        "match_no": 26,
        "match_date": "2026-06-15",
        "group_name": "Group E",
        "home_team": "Ivory Coast",
        "away_team": "Ecuador",
        "team_name": "Ecuador",
        "formation": "4-2-3-1",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/ecuador/world-cup-2026/"
            "predicted-lineups/valencia-decision-for-la-tri-predicted-ecuador-"
            "lineup-vs-ivory-coast_599039.html"
        ),
        "players": [
            ("GK", "Galindez"),
            ("DF", "Ordonez"),
            ("DF", "Pacho"),
            ("DF", "Hincapie"),
            ("DF", "Estupinan"),
            ("MF", "Caicedo"),
            ("MF", "Vite"),
            ("MF", "Yeboah"),
            ("MF", "Plata"),
            ("MF", "Angulo"),
            ("FW", "Valencia"),
        ],
    },
    {
        "match_no": 31,
        "match_date": "2026-06-15",
        "group_name": "Group F",
        "home_team": "Netherlands",
        "away_team": "Japan",
        "team_name": "Netherlands",
        "formation": "4-2-3-1",
        "source_name": "Squawka",
        "source_url": (
            "https://www.squawka.com/en/news/netherlands-vs-japan-team-news-"
            "predicted-lineups/"
        ),
        "players": [
            ("GK", "Verbruggen"),
            ("DF", "Dumfries"),
            ("DF", "van Hecke"),
            ("DF", "van Dijk"),
            ("DF", "van de Ven"),
            ("MF", "de Jong"),
            ("MF", "Gravenberch"),
            ("MF", "Summerville"),
            ("MF", "Reijnders"),
            ("MF", "Gakpo"),
            ("FW", "Depay"),
        ],
    },
    {
        "match_no": 31,
        "match_date": "2026-06-15",
        "group_name": "Group F",
        "home_team": "Netherlands",
        "away_team": "Japan",
        "team_name": "Japan",
        "formation": "3-4-2-1",
        "source_name": "Squawka",
        "source_url": (
            "https://www.squawka.com/en/news/netherlands-vs-japan-team-news-"
            "predicted-lineups/"
        ),
        "players": [
            ("GK", "Suzuki"),
            ("DF", "Tomiyasu"),
            ("DF", "Itakura"),
            ("DF", "Watanabe"),
            ("MF", "Doan"),
            ("MF", "Kamada"),
            ("MF", "Tanaka"),
            ("MF", "Nakamura"),
            ("MF", "Kubo"),
            ("MF", "J Ito"),
            ("FW", "Ueda"),
        ],
    },
    {
        "match_no": 32,
        "match_date": "2026-06-15",
        "group_name": "Group F",
        "home_team": "Tunisia",
        "away_team": "Sweden",
        "team_name": "Tunisia",
        "formation": "4-2-3-1",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/tunisia/world-cup-2026/"
            "predicted-lineups/hope-for-hannibal-predicted-tunisia-xi-vs-sweden_"
            "599050.html"
        ),
        "players": [
            ("GK", "Chamakh"),
            ("DF", "Valery"),
            ("DF", "Rekik"),
            ("DF", "Talbi"),
            ("DF", "Ali Abdi"),
            ("MF", "Skhiri"),
            ("MF", "Khedira"),
            ("MF", "Achouri"),
            ("MF", "Hannibal"),
            ("MF", "Gharbi"),
            ("FW", "Chaouat"),
        ],
    },
    {
        "match_no": 32,
        "match_date": "2026-06-15",
        "group_name": "Group F",
        "home_team": "Tunisia",
        "away_team": "Sweden",
        "team_name": "Sweden",
        "formation": "3-4-1-2",
        "source_name": "Sports Mole",
        "source_url": (
            "https://www.sportsmole.co.uk/football/sweden/world-cup-2026/"
            "predicted-lineups/the-sickness-bug-strikes-predicted-sweden-xi-vs-"
            "tunisia_599046.html"
        ),
        "players": [
            ("GK", "Nordfeldt"),
            ("DF", "Hien"),
            ("DF", "Lindelof"),
            ("DF", "Lagerbielke"),
            ("MF", "Bernhardsson"),
            ("MF", "Karlstrom"),
            ("MF", "Ayari"),
            ("MF", "Gudmundsson"),
            ("MF", "Nygren"),
            ("FW", "Gyokeres"),
            ("FW", "Isak"),
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
