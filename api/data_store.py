from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.project_paths import (
    ENHANCED_PREDICTIONS_PATH,
    FIXTURES_PATH,
    MATCH_FEATURE_STORE_2026_PATH,
    SCORELINE_ANALYSIS_PATH,
    SCORELINE_VALUE_BETS_PATH,
    TOURNAMENT_SIMULATION_PATH,
)

from .schemas import (
    GroupAdvanceRow,
    MatchDetail,
    MatchSummary,
    MetadataResponse,
    ScheduleMatch,
    ScorelineRow,
    SimulatorCombination,
    SimulatorRequest,
    SimulatorResponse,
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


def _as_str(row: pd.Series, column: str) -> str | None:
    if column not in row:
        return None
    value = _clean(row[column])
    return None if value is None else str(value)


def _as_bool(row: pd.Series, column: str) -> bool:
    if column not in row:
        return False
    value = _clean(row[column])
    return bool(value) if value is not None else False


@dataclass
class DashboardDataStore:
    fixtures: pd.DataFrame
    enhanced: pd.DataFrame
    scorelines: pd.DataFrame
    value_bets: pd.DataFrame
    groups: pd.DataFrame
    tournament: pd.DataFrame
    match_features: pd.DataFrame

    @classmethod
    def load(cls) -> DashboardDataStore:
        return cls(
            fixtures=_read_table(FIXTURES_PATH),
            enhanced=_read_table(ENHANCED_PREDICTIONS_PATH),
            scorelines=_read_table(SCORELINE_ANALYSIS_PATH),
            value_bets=_read_table(SCORELINE_VALUE_BETS_PATH),
            groups=_read_table(GROUP_ADVANCE_PATH),
            tournament=_read_table(TOURNAMENT_SIMULATION_PATH),
            match_features=_read_table(MATCH_FEATURE_STORE_2026_PATH),
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
        return [self._schedule_match(row) for _, row in rows.iterrows()]

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

    def list_group_advance(self, *, group_name: str | None = None) -> list[GroupAdvanceRow]:
        rows = self.groups.copy()
        if rows.empty:
            return []
        if group_name:
            rows = rows[rows["group_name"].eq(group_name)]
        rows["team_name_zh"] = rows["team_name"].map(zh_team_name)
        rows = rows.sort_values(
            ["group_name", "group_advance_probability"],
            ascending=[True, False],
        )
        return [
            GroupAdvanceRow(
                group_name=str(row.group_name),
                team_name=str(row.team_name),
                team_name_zh=str(row.team_name_zh),
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
        return rows.merge(top_scorelines, on="match_no", how="left")

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
        )

    def _schedule_match(self, row: pd.Series) -> ScheduleMatch:
        home_team = _as_str(row, "home_team") or "TBD"
        away_team = _as_str(row, "away_team") or "TBD"
        return ScheduleMatch(
            match_no=int(row.match_no),
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
