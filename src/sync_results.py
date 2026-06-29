"""P0-3: Robust NetEase → official_results sync using team name matching."""

import json
import urllib.request
from datetime import datetime, timezone

import pandas as pd

from api.team_locale import zh_team_name


def sync_official_results() -> int:
    """Sync NetEase results into official_match_results_2026.parquet.

    Uses zh_team_name() bidirectional matching to resolve the
    match_no mismatch between NetEase API and our fixtures parquet.

    Returns number of new matches synced.
    """
    # Fetch NetEase schedule
    resp = urllib.request.urlopen(
        "https://gw.m.163.com/base/worldCup/qatar/schedule", timeout=15
    )
    data = json.loads(resp.read())
    finished = data["data"]["finishScheduleList"]

    off = pd.read_parquet("data/processed/official_match_results_2026.parquet")
    fixtures = pd.read_parquet("data/processed/fixtures_2026.parquet")

    # Build fixture lookup: (home_zh, away_zh) → match_no
    fx_map = {}
    for _, fx in fixtures.iterrows():
        if pd.isna(fx["home_team"]) or fx["home_team"] == "TBD":
            continue
        key = (zh_team_name(fx["home_team"]), zh_team_name(fx["away_team"]))
        fx_map[key] = int(fx["match_no"])

    updated = 0
    not_found = 0

    for m in finished:
        home_cn = m["home"]
        away_cn = m["away"]
        # Handle NetEase aliases
        ALIASES = {"刚果(金)": "刚果民主共和国"}
        home_cn = ALIASES.get(home_cn, home_cn)
        away_cn = ALIASES.get(away_cn, away_cn)
        mn = fx_map.get((home_cn, away_cn))
        # Try swapped (NetEase might have home/away reversed)
        if mn is None:
            mn = fx_map.get((away_cn, home_cn))

        if mn is None:
            not_found += 1
            # Only log if it's a new match (not already in completed)
            print(f"  [WARN] 未匹配: {home_cn} {m['homeScore']}-{m['awayScore']} {away_cn}")
            continue

        # Find and update the match in official_results
        for idx in off.index:
            if int(off.at[idx, "match_no"]) == mn:
                if pd.isna(off.at[idx, "home_score"]) or not off.at[idx, "completed"]:
                    off.at[idx, "home_score"] = m["homeScore"]
                    off.at[idx, "away_score"] = m["awayScore"]
                    off.at[idx, "completed"] = True
                    off.at[idx, "date_utc"] = datetime.fromtimestamp(
                        m["date"] / 1000, tz=timezone.utc
                    )
                    updated += 1
                    print(
                        f"  [OK] #{mn} {off.at[idx,'home_team']}"
                        f" {m['homeScore']}-{m['awayScore']}"
                        f" {off.at[idx,'away_team']}"
                    )
                break

    if updated:
        off.to_parquet(
            "data/processed/official_match_results_2026.parquet", index=False
        )

    completed_now = len(off[off["completed"] == True])
    print(
        f"\n同步完成: {updated} 新增 | {not_found} 未匹配 | "
        f"累计 {completed_now}/{len(finished)} 已完赛"
    )
    return updated


if __name__ == "__main__":
    sync_official_results()
