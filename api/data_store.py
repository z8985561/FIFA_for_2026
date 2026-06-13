from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.match_review_pipeline import build_match_review_features
from src.project_paths import (
    ENHANCED_PREDICTIONS_PATH,
    FIXTURES_PATH,
    MATCH_FEATURE_STORE_2026_PATH,
    MATCH_REVIEW_FEATURES_PATH,
    OFFICIAL_MATCH_RESULTS_2026_PATH,
    SCORELINE_ANALYSIS_PATH,
    SCORELINE_VALUE_BETS_PATH,
    TOURNAMENT_SIMULATION_PATH,
    WANGYI_COACHES_2026_PATH,
    WANGYI_SQUAD_STATS_2026_PATH,
)

from .schemas import (
    DataQualityRow,
    GroupAdvanceRow,
    MatchDetail,
    MatchReviewRow,
    MatchSummary,
    MetadataResponse,
    ScheduleMatch,
    ScorelineRow,
    SimulatorCombination,
    SimulatorRequest,
    SimulatorResponse,
    TeamContext,
)
from .team_locale import zh_team_name

GROUP_ADVANCE_PATH = Path("reports/world_cup_2026_group_advance_probabilities.csv")


def _read_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, np.floating | float) and not np.isfinite(value):
        return None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def _as_float(row: pd.Series, column: str) -> float | None:
    if column not in row:
        return None
    value = _clean(row[column])
    return None if value is None else float(value)


def _as_float_raw(value: Any) -> float | None:
    value = _clean(value)
    return None if value is None else float(value)


def _as_str(row: pd.Series, column: str) -> str | None:
    if column not in row:
        return None
    value = _clean(row[column])
    return None if value is None else str(value)


def _as_int(row: pd.Series, column: str) -> int | None:
    if column not in row:
        return None
    value = _clean(row[column])
    return None if value is None else int(value)


def _as_bool(row: pd.Series, column: str) -> bool:
    if column not in row:
        return False
    value = _clean(row[column])
    return bool(value) if value is not None else False


def _as_int_dict(values: dict[str, Any], key: str) -> int | None:
    value = _clean(values.get(key))
    return None if value is None else int(value)


def _text_dict(values: dict[str, Any], key: str) -> str | None:
    value = _clean(values.get(key))
    return None if value is None else str(value)


@dataclass
class DashboardDataStore:
    fixtures: pd.DataFrame
    enhanced: pd.DataFrame
    scorelines: pd.DataFrame
    value_bets: pd.DataFrame
    groups: pd.DataFrame
    tournament: pd.DataFrame
    match_features: pd.DataFrame
    official_results: pd.DataFrame
    match_reviews: pd.DataFrame
    wangyi_coaches: pd.DataFrame
    wangyi_squad_stats: pd.DataFrame

    @classmethod
    def load(cls) -> DashboardDataStore:
        match_reviews = _read_table(MATCH_REVIEW_FEATURES_PATH)
        if match_reviews.empty:
            match_reviews = build_match_review_features()
        return cls(
            fixtures=_read_table(FIXTURES_PATH),
            enhanced=_read_table(ENHANCED_PREDICTIONS_PATH),
            scorelines=_read_table(SCORELINE_ANALYSIS_PATH),
            value_bets=_read_table(SCORELINE_VALUE_BETS_PATH),
            groups=_read_table(GROUP_ADVANCE_PATH),
            tournament=_read_table(TOURNAMENT_SIMULATION_PATH),
            match_features=_read_table(MATCH_FEATURE_STORE_2026_PATH),
            official_results=_read_table(OFFICIAL_MATCH_RESULTS_2026_PATH),
            match_reviews=match_reviews,
            wangyi_coaches=_read_table(WANGYI_COACHES_2026_PATH),
            wangyi_squad_stats=_read_table(WANGYI_SQUAD_STATS_2026_PATH),
        )

    def row_counts(self) -> dict[str, int]:
        return {
            "fixtures": len(self.fixtures),
            "enhanced_predictions": len(self.enhanced),
            "scorelines": len(self.scorelines),
            "value_bets": len(self.value_bets),
            "group_advance": len(self.groups),
            "tournament_simulation": len(self.tournament),
            "match_features": len(self.match_features),
            "official_results": len(self.official_results),
            "match_reviews": len(self.match_reviews),
            "wangyi_coaches": len(self.wangyi_coaches),
            "wangyi_squad_stats": len(self.wangyi_squad_stats),
        }

    def metadata(self) -> MetadataResponse:
        latest_score_odds = self._latest_text(self.value_bets, "latest_fetched_at")
        latest_market = self._latest_text(self.enhanced, "latest_fetched_at")
        latest_match = self._latest_text(self.enhanced, "date_et")
        return MetadataResponse(
            model_version="dashboard-mvp-0.1",
            data_scope="2026 World Cup local model outputs and ingested odds snapshots",
            row_counts=self.row_counts(),
            latest_score_odds_fetched_at=latest_score_odds,
            latest_market_fetched_at=latest_market,
            latest_match_date_et=latest_match,
            compliance_note=(
                "仅用于概率研究和虚拟模拟，不提供真实下单、支付或账户功能。"
            ),
        )

    def list_matches(
        self,
        *,
        limit: int | None = None,
        group_name: str | None = None,
    ) -> list[MatchSummary]:
        rows = self._match_rows()
        if group_name:
            rows = rows[rows["group_name"].eq(group_name)]
        rows = rows.sort_values(["date_et", "match_no"], na_position="last")
        if limit is not None:
            rows = rows.head(limit)
        return [self._match_summary(row) for _, row in rows.iterrows()]

    def list_schedule(
        self,
        *,
        stage: str | None = None,
        group_name: str | None = None,
    ) -> list[ScheduleMatch]:
        rows = self.fixtures.copy()
        if rows.empty:
            return []
        if stage:
            rows = rows[rows["stage"].eq(stage)]
        if group_name:
            rows = rows[rows["group_name"].eq(group_name)]
        rows = rows.sort_values(["date_et", "time_et", "match_no"], na_position="last")
        result_lookup = self._official_results_by_match()
        prediction_lookup = self._prediction_by_match()
        top_scoreline_lookup = self._top_scoreline_by_match()
        return [
            self._schedule_match(
                row,
                result_lookup=result_lookup,
                prediction_lookup=prediction_lookup,
                top_scoreline_lookup=top_scoreline_lookup,
            )
            for _, row in rows.iterrows()
        ]

    def list_data_quality(self) -> list[DataQualityRow]:
        if self.fixtures.empty:
            return []

        prediction_match_nos = set(self.enhanced["match_no"].astype(int).tolist())
        scoreline_match_nos = set(self.scorelines["match_no"].astype(int).tolist())
        odds_rows = self._scoreline_value_rows()
        score_odds_match_nos = (
            set(
                odds_rows.loc[odds_rows["has_score_odds"].fillna(False), "match_no"]
                .astype(int)
                .tolist()
            )
            if not odds_rows.empty and "has_score_odds" in odds_rows.columns
            else set()
        )
        market_odds_match_nos = (
            set(
                self.enhanced.loc[self.enhanced["has_market_odds"].fillna(False), "match_no"]
                .astype(int)
                .tolist()
            )
            if not self.enhanced.empty and "has_market_odds" in self.enhanced.columns
            else set()
        )
        lineup_match_nos = self._lineup_adjusted_match_nos()
        score_snapshot_by_match = self._latest_by_match(odds_rows, "latest_fetched_at")
        market_snapshot_by_match = self._latest_by_match(self.enhanced, "latest_fetched_at")

        rows = self.fixtures.sort_values(["date_et", "time_et", "match_no"], na_position="last")
        return [
            self._data_quality_row(
                row=row,
                prediction_match_nos=prediction_match_nos,
                scoreline_match_nos=scoreline_match_nos,
                score_odds_match_nos=score_odds_match_nos,
                market_odds_match_nos=market_odds_match_nos,
                lineup_match_nos=lineup_match_nos,
                score_snapshot_by_match=score_snapshot_by_match,
                market_snapshot_by_match=market_snapshot_by_match,
            )
            for _, row in rows.iterrows()
        ]

    def get_match(self, match_no: int) -> MatchDetail:
        rows = self._match_rows()
        match_rows = rows[rows["match_no"].eq(match_no)]
        if match_rows.empty:
            raise KeyError(f"Match {match_no} not found")
        match = self._match_summary(match_rows.iloc[0])

        score_rows = self.scorelines[self.scorelines["match_no"].eq(match_no)]
        score_row = score_rows.iloc[0] if not score_rows.empty else pd.Series(dtype=object)
        enhanced_rows = self.enhanced[self.enhanced["match_no"].eq(match_no)]
        enhanced_row = enhanced_rows.iloc[0] if not enhanced_rows.empty else pd.Series(dtype=object)

        expected_goals = {
            "home_raw": _as_float(score_row, "raw_home_expected_goals"),
            "away_raw": _as_float(score_row, "raw_away_expected_goals"),
            "home_final": _as_float(score_row, "home_expected_goals"),
            "away_final": _as_float(score_row, "away_expected_goals"),
        }
        outcome_probabilities = {
            "home_win": _as_float(score_row, "score_home_win_probability"),
            "draw": _as_float(score_row, "score_draw_probability"),
            "away_win": _as_float(score_row, "score_away_win_probability"),
            "over_2_5": _as_float(score_row, "over_2_5_probability"),
            "under_2_5": _as_float(score_row, "under_2_5_probability"),
            "both_teams_score": _as_float(score_row, "both_teams_score_probability"),
        }
        market_probabilities = {
            "home_win": _as_float(enhanced_row, "consensus_home_win_probability"),
            "draw": _as_float(enhanced_row, "consensus_draw_probability"),
            "away_win": _as_float(enhanced_row, "consensus_away_win_probability"),
        }
        return MatchDetail(
            match=match,
            expected_goals=expected_goals,
            outcome_probabilities=outcome_probabilities,
            market_probabilities=market_probabilities,
            home_team_context=self._team_context(match.home_team),
            away_team_context=self._team_context(match.away_team),
            factor_breakdown=self._factor_breakdown(score_row, enhanced_row),
        )

    def list_scorelines(
        self,
        *,
        match_no: int | None = None,
        limit: int = 10,
        signal: str | None = None,
        sort_by: str = "rank",
    ) -> list[ScorelineRow]:
        rows = self._scoreline_value_rows()
        if match_no is not None:
            rows = rows[rows["match_no"].eq(match_no)]
        if signal is not None:
            rows = rows[rows["value_signal"].eq(signal)]
        if sort_by == "edge":
            rows = rows.sort_values(["market_edge", "model_probability"], ascending=[False, False])
        elif sort_by == "probability":
            rows = rows.sort_values(["model_probability", "market_edge"], ascending=[False, False])
        else:
            rows = rows.sort_values(["match_no", "scoreline_rank"], na_position="last")
        rows = rows.head(limit)
        return [self._scoreline_row(row) for _, row in rows.iterrows()]

    def list_match_reviews(
        self,
        *,
        limit: int | None = None,
        review_bucket: str | None = None,
    ) -> list[MatchReviewRow]:
        rows = self.match_reviews.copy()
        if rows.empty:
            return []
        if review_bucket:
            rows = rows[rows["review_bucket"].eq(review_bucket)]
        rows = rows.sort_values(["match_no"], ascending=[False])
        if limit is not None:
            rows = rows.head(limit)
        return [self._match_review_row(row) for _, row in rows.iterrows()]

    def list_group_advance(self, *, group_name: str | None = None) -> list[GroupAdvanceRow]:
        rows = self.groups.copy()
        if rows.empty:
            return []
        standings = self._group_live_standings()
        if standings.empty:
            standings = self._empty_group_live_standings(rows)
        rows = rows.merge(
            standings,
            on=["group_name", "team_name"],
            how="left",
        )
        if group_name:
            rows = rows[rows["group_name"].eq(group_name)]
        rows["team_name_zh"] = rows["team_name"].map(zh_team_name)
        rows = rows.sort_values(
            ["group_name", "standing_rank", "group_advance_probability"],
            ascending=[True, True, False],
        )
        return [
            GroupAdvanceRow(
                group_name=str(row.group_name),
                team_name=str(row.team_name),
                team_name_zh=str(row.team_name_zh),
                standing_rank=int(_clean(row.standing_rank) or 0),
                played=int(_clean(row.played) or 0),
                wins=int(_clean(row.wins) or 0),
                draws=int(_clean(row.draws) or 0),
                losses=int(_clean(row.losses) or 0),
                goals_for=int(_clean(row.goals_for) or 0),
                goals_against=int(_clean(row.goals_against) or 0),
                goal_difference=int(_clean(row.goal_difference) or 0),
                points=int(_clean(row.points) or 0),
                group_winner_probability=float(row.group_winner_probability),
                group_runner_up_probability=float(row.group_runner_up_probability),
                top2_probability=float(row.top2_probability),
                third_place_advance_probability=float(row.third_place_advance_probability),
                group_advance_probability=float(row.group_advance_probability),
                not_advance_probability=float(row.not_advance_probability),
            )
            for _, row in rows.iterrows()
        ]

    def settle_simulator(self, request: SimulatorRequest) -> SimulatorResponse:
        rows = self._scoreline_value_rows()
        lookup = {
            (int(row.match_no), str(row.scoreline)): row
            for _, row in rows.iterrows()
        }
        combo_size = _bet_type_size(request.bet_type)
        candidates = list(combinations(request.selections, combo_size))
        valid_candidates = [
            combo
            for combo in candidates
            if len({selection.match_no for selection in combo}) == len(combo)
        ]

        combinations_out: list[SimulatorCombination] = []
        for combo in valid_candidates:
            probability = 1.0
            decimal_odds = 1.0
            missing_odds = False
            for selection in combo:
                row = lookup.get((selection.match_no, selection.scoreline))
                if row is None:
                    probability = 0.0
                    missing_odds = True
                    decimal_odds = np.nan
                    continue
                probability *= float(row.model_probability)
                odds = _clean(row.best_decimal_odds)
                if odds is None:
                    missing_odds = True
                    decimal_odds = np.nan
                elif np.isfinite(decimal_odds):
                    decimal_odds *= float(odds)
            theoretical = (
                None
                if missing_odds or not np.isfinite(decimal_odds)
                else decimal_odds * request.stake_per_combination
            )
            expected = None if theoretical is None else probability * theoretical
            combinations_out.append(
                SimulatorCombination(
                    selections=list(combo),
                    hit_probability=probability,
                    decimal_odds=(
                        None if missing_odds or not np.isfinite(decimal_odds) else decimal_odds
                    ),
                    theoretical_payout=theoretical,
                    expected_payout=expected,
                    missing_odds=missing_odds,
                )
            )

        total_stake = len(combinations_out) * request.stake_per_combination
        expected_payouts = [combo.expected_payout or 0.0 for combo in combinations_out]
        theoretical_payouts = [
            combo.theoretical_payout
            for combo in combinations_out
            if combo.theoretical_payout is not None
        ]
        estimated_hit_probability = 1.0
        for combo in combinations_out:
            estimated_hit_probability *= 1.0 - combo.hit_probability
        estimated_hit_probability = 1.0 - estimated_hit_probability
        max_payout = max(theoretical_payouts) if theoretical_payouts else None
        min_payout = min(theoretical_payouts) if theoretical_payouts else None
        payout_spread_ratio = None if max_payout is None else max_payout / max(total_stake, 1e-12)
        risk_score, risk_rating, risk_reasons = _risk_rating(
            hit_probability=estimated_hit_probability,
            payout_spread_ratio=payout_spread_ratio,
            combinations=combinations_out,
            total_stake=total_stake,
            budget=request.budget,
        )
        return SimulatorResponse(
            budget=request.budget,
            stake_per_combination=request.stake_per_combination,
            bet_type=request.bet_type,
            combination_count=len(combinations_out),
            total_stake=total_stake,
            min_theoretical_payout=min_payout,
            max_theoretical_payout=max_payout,
            total_expected_payout=sum(expected_payouts),
            expected_net_return=sum(expected_payouts) - total_stake,
            estimated_hit_probability=estimated_hit_probability,
            payout_spread_ratio=payout_spread_ratio,
            risk_score=risk_score,
            risk_rating=risk_rating,
            risk_reasons=risk_reasons,
            combinations=combinations_out,
        )

    def _match_rows(self) -> pd.DataFrame:
        if self.enhanced.empty:
            return pd.DataFrame()
        rows = self.enhanced.copy()
        fixture_columns = [
            "match_no",
            "time_et",
            "date_bj",
            "time_bj",
            "venue_city",
        ]
        if not self.fixtures.empty:
            rows = rows.merge(
                self.fixtures[
                    [column for column in fixture_columns if column in self.fixtures.columns]
                ],
                on="match_no",
                how="left",
            )
        top_scorelines = (
            self.scorelines[self.scorelines["scoreline_rank"].eq(1)][
                ["match_no", "scoreline", "scoreline_probability"]
            ]
            .rename(
                columns={
                    "scoreline": "top_scoreline",
                    "scoreline_probability": "top_scoreline_probability",
                }
            )
            if not self.scorelines.empty
            else pd.DataFrame(columns=["match_no", "top_scoreline", "top_scoreline_probability"])
        )
        rows = rows.merge(top_scorelines, on="match_no", how="left")
        if not self.official_results.empty:
            official_columns = [
                "match_no",
                "home_score",
                "away_score",
                "completed",
                "source_name",
            ]
            official_rows = self.official_results[
                [column for column in official_columns if column in self.official_results.columns]
            ].rename(
                columns={
                    "home_score": "actual_home_score",
                    "away_score": "actual_away_score",
                    "source_name": "result_source_name",
                }
            )
            rows = rows.merge(official_rows, on="match_no", how="left")
        return rows

    def _match_summary(self, row: pd.Series) -> MatchSummary:
        home_team = str(row.home_team)
        away_team = str(row.away_team)
        return MatchSummary(
            match_no=int(row.match_no),
            stage=_as_str(row, "stage"),
            group_name=_as_str(row, "group_name"),
            date_et=_as_str(row, "date_et"),
            time_et=_as_str(row, "time_et"),
            date_bj=_as_str(row, "date_bj"),
            time_bj=_as_str(row, "time_bj"),
            home_team=home_team,
            away_team=away_team,
            home_team_zh=zh_team_name(home_team) or home_team,
            away_team_zh=zh_team_name(away_team) or away_team,
            venue_city=_as_str(row, "venue_city"),
            home_win_probability=_as_float(row, "blended_home_win_probability")
            or _as_float(row, "home_win_probability"),
            draw_probability=_as_float(row, "blended_draw_probability")
            or _as_float(row, "draw_probability"),
            away_win_probability=_as_float(row, "blended_away_win_probability")
            or _as_float(row, "away_win_probability"),
            predicted_outcome=_as_str(row, "blended_predicted_outcome")
            or _as_str(row, "predicted_outcome"),
            has_market_odds=_as_bool(row, "has_market_odds"),
            latest_fetched_at=_as_str(row, "latest_fetched_at"),
            top_scoreline=_as_str(row, "top_scoreline"),
            top_scoreline_probability=_as_float(row, "top_scoreline_probability"),
            actual_home_score=_as_int(row, "actual_home_score"),
            actual_away_score=_as_int(row, "actual_away_score"),
            completed=_as_bool(row, "completed"),
            result_source_name=_as_str(row, "result_source_name"),
        )

    def _match_review_row(self, row: pd.Series) -> MatchReviewRow:
        home_team = _as_str(row, "home_team") or "TBD"
        away_team = _as_str(row, "away_team") or "TBD"
        return MatchReviewRow(
            match_no=int(row.match_no),
            stage=_as_str(row, "stage"),
            group_name=_as_str(row, "group_name"),
            home_team=home_team,
            away_team=away_team,
            home_team_zh=_as_str(row, "home_team_zh") or zh_team_name(home_team) or home_team,
            away_team_zh=_as_str(row, "away_team_zh") or zh_team_name(away_team) or away_team,
            predicted_outcome=_as_str(row, "predicted_outcome"),
            actual_outcome=_as_str(row, "actual_outcome"),
            top_scoreline=_as_str(row, "top_scoreline"),
            actual_scoreline=_as_str(row, "actual_scoreline"),
            expected_home_goals=_as_float(row, "expected_home_goals"),
            expected_away_goals=_as_float(row, "expected_away_goals"),
            expected_total_goals=_as_float(row, "expected_total_goals"),
            actual_total_goals=_as_int(row, "actual_total_goals"),
            outcome_hit=_as_bool(row, "outcome_hit"),
            scoreline_hit=_as_bool(row, "scoreline_hit"),
            total_goals_error=_as_float(row, "total_goals_error"),
            actual_outcome_probability=_as_float(row, "actual_outcome_probability"),
            predicted_home_win_probability=_as_float(row, "predicted_home_win_probability"),
            predicted_draw_probability=_as_float(row, "predicted_draw_probability"),
            predicted_away_win_probability=_as_float(row, "predicted_away_win_probability"),
            review_bucket=_as_str(row, "review_bucket") or "unknown",
            result_source_name=_as_str(row, "result_source_name"),
        )

    def _prediction_by_match(self) -> dict[int, dict[str, Any]]:
        if self.enhanced.empty:
            return {}
        out: dict[int, dict[str, Any]] = {}
        cols = [
            "match_no",
            "predicted_outcome",
            "home_win_probability",
            "draw_probability",
            "away_win_probability",
        ]
        available = [c for c in cols if c in self.enhanced.columns]
        for _, row in self.enhanced[available].iterrows():
            mn = int(row["match_no"])
            out[mn] = {c: row.get(c) for c in available if c != "match_no"}
        return out

    def _top_scoreline_by_match(self) -> dict[int, dict[str, Any]]:
        if self.scorelines.empty:
            return {}
        rank_col = "scoreline_rank" if "scoreline_rank" in self.scorelines.columns else None
        prob_col = (
            "scoreline_probability"
            if "scoreline_probability" in self.scorelines.columns
            else None
        )
        if not rank_col or not prob_col:
            return {}
        top = self.scorelines[self.scorelines[rank_col] == 1][["match_no", "scoreline", prob_col]]
        return {
            int(r["match_no"]): {"scoreline": r["scoreline"], "probability": r[prob_col]}
            for _, r in top.iterrows()
        }

    def _schedule_match(
        self,
        row: pd.Series,
        *,
        result_lookup: dict[int, dict[str, Any]],
        prediction_lookup: dict[int, dict[str, Any]] | None = None,
        top_scoreline_lookup: dict[int, dict[str, Any]] | None = None,
    ) -> ScheduleMatch:
        home_team = _as_str(row, "home_team") or "TBD"
        away_team = _as_str(row, "away_team") or "TBD"
        mn = int(row.match_no)
        result = result_lookup.get(mn, {})
        pred = (prediction_lookup or {}).get(mn, {})
        top_sl = (top_scoreline_lookup or {}).get(mn, {})
        return ScheduleMatch(
            match_no=mn,
            stage=_as_str(row, "stage") or "Unknown",
            group_name=_as_str(row, "group_name"),
            date_et=_as_str(row, "date_et"),
            time_et=_as_str(row, "time_et"),
            date_bj=_as_str(row, "date_bj"),
            time_bj=_as_str(row, "time_bj"),
            home_team=home_team,
            away_team=away_team,
            home_team_zh=zh_team_name(home_team) or "待定",
            away_team_zh=zh_team_name(away_team) or "待定",
            venue=_as_str(row, "venue"),
            city=_as_str(row, "city"),
            venue_city=_as_str(row, "venue_city"),
            neutral=_as_bool(row, "neutral"),
            actual_home_score=_as_int_dict(result, "home_score"),
            actual_away_score=_as_int_dict(result, "away_score"),
            completed=bool(result.get("completed", False)),
            result_source_name=_text_dict(result, "source_name"),
            predicted_outcome=pred.get("predicted_outcome") or None,
            home_win_probability=_as_float_raw(pred.get("home_win_probability")),
            draw_probability=_as_float_raw(pred.get("draw_probability")),
            away_win_probability=_as_float_raw(pred.get("away_win_probability")),
            top_scoreline=top_sl.get("scoreline") or None,
            top_scoreline_probability=_as_float_raw(top_sl.get("probability")),
        )

    def _data_quality_row(
        self,
        *,
        row: pd.Series,
        prediction_match_nos: set[int],
        scoreline_match_nos: set[int],
        score_odds_match_nos: set[int],
        market_odds_match_nos: set[int],
        lineup_match_nos: set[int],
        score_snapshot_by_match: dict[int, str],
        market_snapshot_by_match: dict[int, str],
    ) -> DataQualityRow:
        match_no = int(row.match_no)
        home_team = _as_str(row, "home_team") or "TBD"
        away_team = _as_str(row, "away_team") or "TBD"
        latest_score_odds = score_snapshot_by_match.get(match_no)
        latest_market = market_snapshot_by_match.get(match_no)
        checks = {
            "has_fixture": True,
            "has_prediction": match_no in prediction_match_nos,
            "has_scoreline_model": match_no in scoreline_match_nos,
            "has_score_odds": match_no in score_odds_match_nos,
            "has_market_odds": match_no in market_odds_match_nos,
            "has_lineup_adjustment": match_no in lineup_match_nos,
            "has_snapshot_time": bool(latest_score_odds or latest_market),
        }
        score = self._completeness_score(checks)
        return DataQualityRow(
            match_no=match_no,
            stage=_as_str(row, "stage") or "Unknown",
            group_name=_as_str(row, "group_name"),
            home_team=home_team,
            away_team=away_team,
            home_team_zh=zh_team_name(home_team) or "待定",
            away_team_zh=zh_team_name(away_team) or "待定",
            has_fixture=checks["has_fixture"],
            has_prediction=checks["has_prediction"],
            has_scoreline_model=checks["has_scoreline_model"],
            has_score_odds=checks["has_score_odds"],
            has_market_odds=checks["has_market_odds"],
            has_lineup_adjustment=checks["has_lineup_adjustment"],
            latest_score_odds_fetched_at=latest_score_odds,
            latest_market_fetched_at=latest_market,
            completeness_score=score,
            completeness_level=self._completeness_level(score),
            missing_items=self._missing_items(checks),
        )

    def _scoreline_value_rows(self) -> pd.DataFrame:
        if self.value_bets.empty:
            if self.scorelines.empty:
                return pd.DataFrame()
            rows = self.scorelines.copy()
            rows["model_probability"] = rows["scoreline_probability"]
            rows["model_fair_odds"] = 1.0 / rows["model_probability"].clip(lower=1e-12)
            rows["has_score_odds"] = False
            rows["value_signal"] = "missing_odds"
            return rows
        return self.value_bets.copy()

    def _lineup_adjusted_match_nos(self) -> set[int]:
        if self.scorelines.empty:
            return set()
        rows = self.scorelines.copy()
        has_status = (
            rows.get("home_lineup_status", pd.Series(index=rows.index, dtype=object)).notna()
            & rows.get("away_lineup_status", pd.Series(index=rows.index, dtype=object)).notna()
        )
        has_adjustment = (
            rows.get("home_lineup_log_adjustment", pd.Series(index=rows.index, dtype=float))
            .fillna(0)
            .ne(0)
            | rows.get("away_lineup_log_adjustment", pd.Series(index=rows.index, dtype=float))
            .fillna(0)
            .ne(0)
        )
        return set(rows.loc[has_status | has_adjustment, "match_no"].astype(int).tolist())

    def _official_results_by_match(self) -> dict[int, dict[str, Any]]:
        if self.official_results.empty or "match_no" not in self.official_results.columns:
            return {}
        rows = self.official_results.dropna(subset=["match_no"]).copy()
        rows = rows.sort_values(["match_no", "fetched_at"], na_position="last")
        latest = rows.groupby("match_no", as_index=False, sort=False).tail(1)
        return {
            int(row.match_no): row.to_dict()
            for _, row in latest.iterrows()
        }

    def _group_live_standings(self) -> pd.DataFrame:
        if self.fixtures.empty:
            return pd.DataFrame()

        fixtures = self.fixtures.copy()
        fixtures = fixtures.loc[fixtures["stage"].eq("Group Stage")].copy()
        if fixtures.empty:
            return pd.DataFrame()

        team_rows = []
        for fixture in fixtures.itertuples(index=False):
            team_rows.append(
                {
                    "group_name": str(fixture.group_name),
                    "team_name": str(fixture.home_team),
                }
            )
            team_rows.append(
                {
                    "group_name": str(fixture.group_name),
                    "team_name": str(fixture.away_team),
                }
            )
        standings = pd.DataFrame(team_rows).drop_duplicates().reset_index(drop=True)
        for column in [
            "played",
            "wins",
            "draws",
            "losses",
            "goals_for",
            "goals_against",
            "goal_difference",
            "points",
        ]:
            standings[column] = 0

        if self.official_results.empty:
            standings["standing_rank"] = standings.groupby("group_name").cumcount() + 1
            return standings

        completed = self.official_results.copy()
        completed = completed.loc[completed.get("completed", False).fillna(False)].copy()
        if completed.empty:
            standings["standing_rank"] = standings.groupby("group_name").cumcount() + 1
            return standings

        results = fixtures.merge(
            completed[
                [
                    "match_no",
                    "home_team",
                    "away_team",
                    "home_score",
                    "away_score",
                    "completed",
                ]
            ],
            on="match_no",
            how="inner",
            suffixes=("_fixture", "_result"),
        )
        if results.empty:
            standings["standing_rank"] = standings.groupby("group_name").cumcount() + 1
            return standings

        for row in results.itertuples(index=False):
            home_team = str(row.home_team_fixture)
            away_team = str(row.away_team_fixture)
            home_score = int(row.home_score)
            away_score = int(row.away_score)
            group_name = str(row.group_name)
            self._apply_group_match_result(
                standings,
                group_name=group_name,
                home_team=home_team,
                away_team=away_team,
                home_score=home_score,
                away_score=away_score,
            )

        standings["goal_difference"] = standings["goals_for"] - standings["goals_against"]
        standings = standings.sort_values(
            [
                "group_name",
                "points",
                "goal_difference",
                "goals_for",
                "team_name",
            ],
            ascending=[True, False, False, False, True],
        ).reset_index(drop=True)
        standings["standing_rank"] = standings.groupby("group_name").cumcount() + 1
        return standings

    @staticmethod
    def _apply_group_match_result(
        standings: pd.DataFrame,
        *,
        group_name: str,
        home_team: str,
        away_team: str,
        home_score: int,
        away_score: int,
    ) -> None:
        home_mask = standings["group_name"].eq(group_name) & standings["team_name"].eq(home_team)
        away_mask = standings["group_name"].eq(group_name) & standings["team_name"].eq(away_team)

        standings.loc[home_mask, "played"] += 1
        standings.loc[away_mask, "played"] += 1
        standings.loc[home_mask, "goals_for"] += home_score
        standings.loc[home_mask, "goals_against"] += away_score
        standings.loc[away_mask, "goals_for"] += away_score
        standings.loc[away_mask, "goals_against"] += home_score

        if home_score > away_score:
            standings.loc[home_mask, "wins"] += 1
            standings.loc[home_mask, "points"] += 3
            standings.loc[away_mask, "losses"] += 1
        elif home_score < away_score:
            standings.loc[away_mask, "wins"] += 1
            standings.loc[away_mask, "points"] += 3
            standings.loc[home_mask, "losses"] += 1
        else:
            standings.loc[home_mask, "draws"] += 1
            standings.loc[away_mask, "draws"] += 1
            standings.loc[home_mask, "points"] += 1
            standings.loc[away_mask, "points"] += 1

    @staticmethod
    def _empty_group_live_standings(group_rows: pd.DataFrame) -> pd.DataFrame:
        standings = group_rows[["group_name", "team_name"]].drop_duplicates().copy()
        standings = standings.sort_values(["group_name", "team_name"]).reset_index(drop=True)
        for column in [
            "played",
            "wins",
            "draws",
            "losses",
            "goals_for",
            "goals_against",
            "goal_difference",
            "points",
        ]:
            standings[column] = 0
        standings["standing_rank"] = standings.groupby("group_name").cumcount() + 1
        return standings

    @staticmethod
    def _latest_by_match(rows: pd.DataFrame, column: str) -> dict[int, str]:
        if rows.empty or column not in rows.columns or "match_no" not in rows.columns:
            return {}
        clean_rows = rows[["match_no", column]].dropna()
        if clean_rows.empty:
            return {}
        clean_rows = clean_rows.copy()
        clean_rows[column] = pd.to_datetime(clean_rows[column], errors="coerce", utc=True)
        clean_rows = clean_rows.dropna(subset=[column])
        if clean_rows.empty:
            return {}
        latest = clean_rows.groupby("match_no")[column].max()
        return {int(match_no): value.isoformat() for match_no, value in latest.items()}

    @staticmethod
    def _completeness_score(checks: dict[str, bool]) -> int:
        weights = {
            "has_fixture": 10,
            "has_prediction": 20,
            "has_scoreline_model": 20,
            "has_score_odds": 20,
            "has_market_odds": 15,
            "has_lineup_adjustment": 10,
            "has_snapshot_time": 5,
        }
        return sum(weight for key, weight in weights.items() if checks.get(key, False))

    @staticmethod
    def _completeness_level(score: int) -> str:
        if score >= 80:
            return "High"
        if score >= 50:
            return "Medium"
        return "Low"

    @staticmethod
    def _missing_items(checks: dict[str, bool]) -> list[str]:
        missing_map = {
            "has_prediction": "missing_prediction",
            "has_scoreline_model": "missing_scoreline_model",
            "has_score_odds": "missing_score_odds",
            "has_market_odds": "missing_market_odds",
            "has_lineup_adjustment": "missing_lineup_adjustment",
            "has_snapshot_time": "missing_snapshot_time",
        }
        return [missing_item for key, missing_item in missing_map.items() if not checks[key]]

    @staticmethod
    def _latest_text(rows: pd.DataFrame, column: str) -> str | None:
        if rows.empty or column not in rows.columns:
            return None
        values = rows[column].dropna()
        if values.empty:
            return None
        try:
            parsed = pd.to_datetime(values, errors="coerce", utc=True).dropna()
        except (TypeError, ValueError):
            parsed = pd.Series(dtype="datetime64[ns, UTC]")
        if not parsed.empty:
            return parsed.max().isoformat()
        return str(values.max())

    def _scoreline_row(self, row: pd.Series) -> ScorelineRow:
        probability = (
            _as_float(row, "model_probability")
            or _as_float(row, "scoreline_probability")
            or 0.0
        )
        rank = _as_float(row, "scoreline_rank")
        bookmaker_count = _as_float(row, "bookmaker_count")
        return ScorelineRow(
            match_no=int(row.match_no),
            stage=_as_str(row, "stage"),
            group_name=_as_str(row, "group_name"),
            date_et=_as_str(row, "date_et"),
            home_team=_as_str(row, "home_team"),
            away_team=_as_str(row, "away_team"),
            home_team_zh=zh_team_name(_as_str(row, "home_team")),
            away_team_zh=zh_team_name(_as_str(row, "away_team")),
            scoreline_rank=None if rank is None else int(row.scoreline_rank),
            scoreline=str(row.scoreline),
            model_probability=probability,
            model_fair_odds=_as_float(row, "model_fair_odds"),
            best_decimal_odds=_as_float(row, "best_decimal_odds"),
            average_decimal_odds=_as_float(row, "average_decimal_odds"),
            market_edge=_as_float(row, "market_edge"),
            kelly_fraction=_as_float(row, "kelly_fraction"),
            has_score_odds=_as_bool(row, "has_score_odds"),
            value_signal=_as_str(row, "value_signal") or "missing_odds",
            bookmaker_count=None if bookmaker_count is None else int(row.bookmaker_count),
            source_names=_as_str(row, "source_names"),
            source_urls=_as_str(row, "source_urls"),
            source_match_ids=_as_str(row, "source_match_ids"),
            latest_fetched_at=_as_str(row, "latest_fetched_at"),
        )

    def _team_context(self, team_name: str) -> TeamContext | None:
        coach_rows = (
            self.wangyi_coaches.loc[self.wangyi_coaches["team_name"].eq(team_name)]
            if not self.wangyi_coaches.empty
            else pd.DataFrame()
        )
        squad_rows = (
            self.wangyi_squad_stats.loc[self.wangyi_squad_stats["team_name"].eq(team_name)]
            if not self.wangyi_squad_stats.empty
            else pd.DataFrame()
        )
        if coach_rows.empty and squad_rows.empty:
            return None

        coach_row = coach_rows.iloc[0] if not coach_rows.empty else pd.Series(dtype=object)
        suspended_rows = (
            squad_rows.loc[squad_rows["is_suspended"].fillna(False)].copy()
            if not squad_rows.empty and "is_suspended" in squad_rows.columns
            else pd.DataFrame()
        )
        suspended_players_zh = (
            sorted(
                {
                    str(value)
                    for value in suspended_rows.get("name_zh", pd.Series(dtype=object)).dropna()
                    if str(value).strip()
                }
            )
            if not suspended_rows.empty
            else []
        )
        suspended_players_en = (
            sorted(
                {
                    str(value)
                    for value in suspended_rows.get("name_en", pd.Series(dtype=object)).dropna()
                    if str(value).strip()
                }
            )
            if not suspended_rows.empty
            else []
        )
        return TeamContext(
            team_name=team_name,
            team_name_zh=zh_team_name(team_name) or team_name,
            coach_name_zh=_as_str(coach_row, "manager_name_zh"),
            coach_name_en=_as_str(coach_row, "manager_name_en"),
            suspended_count=len(suspended_rows),
            suspended_players_zh=suspended_players_zh,
            suspended_players_en=suspended_players_en,
            squad_size=None if squad_rows.empty else int(len(squad_rows)),
        )

    def _factor_breakdown(
        self,
        score_row: pd.Series,
        enhanced_row: pd.Series,
    ) -> list[dict[str, float | str | bool | None]]:
        return [
            {
                "factor": "Elo 与基础攻防",
                "home_delta_goals": 0.0,
                "away_delta_goals": 0.0,
                "description": "由历史强度、攻防参数和中立场条件形成基础期望进球。",
            },
            {
                "factor": "预计首发阵容",
                "home_delta_goals": _as_float(score_row, "home_lineup_log_adjustment"),
                "away_delta_goals": _as_float(score_row, "away_lineup_log_adjustment"),
                "description": "根据预测首发对进攻和防守的影响做温和修正。",
            },
            {
                "factor": "停赛球员修正",
                "home_delta_goals": _as_float(score_row, "home_suspension_log_adjustment"),
                "away_delta_goals": _as_float(score_row, "away_suspension_log_adjustment"),
                "applied": (
                    (_as_int(score_row, "home_suspended_count") or 0) > 0
                    or (_as_int(score_row, "away_suspended_count") or 0) > 0
                ),
                "description": "根据网易阵容数据中的停赛球员，对双方进攻和防守能力做额外修正。",
            },
            {
                "factor": "小组首战节奏",
                "home_delta_goals": _as_float(score_row, "home_group_opener_log_adjustment"),
                "away_delta_goals": _as_float(score_row, "away_group_opener_log_adjustment"),
                "applied": _as_bool(score_row, "group_opener_mismatch_adjustment_applied"),
                "description": "小组首战若强弱差明显，适度提高热门方主动进攻节奏。",
            },
            {
                "factor": "市场赔率约束",
                "home_delta_goals": None,
                "away_delta_goals": None,
                "applied": _as_bool(score_row, "has_market_outcome_constraint"),
                "description": "使用体彩/国际赔率隐含概率对胜平负边际做校准。",
            },
            {
                "factor": "跨大洲盲区保护",
                "home_delta_goals": None,
                "away_delta_goals": None,
                "applied": not _as_bool(enhanced_row, "same_confederation"),
                "description": "跨大洲对阵降低模型过度自信，给冷门留出尾部概率。",
            },
        ]


def _bet_type_size(bet_type: str) -> int:
    normalized = bet_type.lower().replace("串", "x").replace("单关", "single")
    if normalized in {"single", "1x1", "1"}:
        return 1
    if normalized in {"2x1", "2"}:
        return 2
    if normalized in {"4x1", "4"}:
        return 4
    raise ValueError(f"Unsupported bet_type: {bet_type}")


def _risk_rating(
    *,
    hit_probability: float,
    payout_spread_ratio: float | None,
    combinations: list[SimulatorCombination],
    total_stake: float,
    budget: float,
) -> tuple[int, str, list[str]]:
    ratio = payout_spread_ratio or 0.0
    high_odds_count = sum(1 for combo in combinations if (combo.decimal_odds or 0.0) >= 100.0)
    score = 20
    reasons: list[str] = []
    if hit_probability < 0.002:
        score += 50
        reasons.append("总命中概率低于0.2%")
    elif hit_probability < 0.01:
        score += 35
        reasons.append("总命中概率低于1%")
    elif hit_probability < 0.05:
        score += 20
        reasons.append("总命中概率低于5%")
    if ratio >= 1000:
        score += 35
        reasons.append("最大返奖超过总投入1000倍")
    elif ratio >= 100:
        score += 25
        reasons.append("最大返奖超过总投入100倍")
    elif ratio >= 20:
        score += 10
        reasons.append("最大返奖超过总投入20倍")
    if high_odds_count:
        score += min(20, high_odds_count * 5)
        reasons.append("组合包含多个高赔率精确比分")
    if total_stake > budget:
        score += 20
        reasons.append("模拟总投入超过预算")
    score = max(0, min(score, 100))
    if score >= 80:
        rating = "Extreme"
    elif score >= 60:
        rating = "High"
    elif score >= 35:
        rating = "Medium"
    else:
        rating = "Low"
    if not reasons:
        reasons.append("命中概率和返奖跨度处于相对温和区间")
    return score, rating, reasons
