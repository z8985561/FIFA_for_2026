"""Incremental trigger: only run pipeline when new data is available.

Compares max(match_no) from NetEase API vs local official_results.
Returns exit code 0 if pipeline should run, 1 if no new data.
"""

import json
import sys
import urllib.request

import pandas as pd


def check_new_data() -> int:
    """Return 0 if new matches available, 1 if up-to-date, 2 if API error."""
    try:
        resp = urllib.request.urlopen(
            "https://gw.m.163.com/base/worldCup/qatar/schedule", timeout=10
        )
        data = json.loads(resp.read())
    except Exception as e:
        print(f"API_ERROR: {e}", file=sys.stderr)
        return 2

    try:
        finished = data["data"]["finishScheduleList"]
        netease_count = len(finished)
    except KeyError as e:
        print(f"DATA_STRUCTURE_ERROR: {e}", file=sys.stderr)
        return 2

    try:
        off = pd.read_parquet("data/processed/official_match_results_2026.parquet")
        local_count = len(off[off["completed"] == True])
    except Exception as e:
        print(f"LOCAL_READ_ERROR: {e}", file=sys.stderr)
        return 2

    diff = netease_count - local_count
    if diff > 0:
        print(f"NEW_DATA: {diff} new matches (local={local_count}, remote={netease_count})")
        return 0
    else:
        print(f"UP_TO_DATE: local={local_count}, remote={netease_count}")
        return 1


if __name__ == "__main__":
    sys.exit(check_new_data())
