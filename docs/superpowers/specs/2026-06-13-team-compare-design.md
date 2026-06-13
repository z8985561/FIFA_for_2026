# 实力对比模块 — 前端设计文档

> 日期: 2026-06-13
> 状态: 待开发

## 目标

在 MatchAnalysisPage 中嵌入实力对比模块，自动展示当前比赛主客两队的综合实力对比。

## 数据来源

| 指标 | 数据源 | 覆盖 |
|------|--------|------|
| Elo 评分 | `ratings.parquet` (latest_elo) | 48 队 |
| FIFA 排名 | `match_feature_store_2026.parquet` | 48 队 |
| 阵容人数 / 平均年龄 / 总出场 | `match_feature_store_2026.parquet` | 48 队 |
| 出线概率 | `group_advance_probabilities.csv` | 48 队 |
| 赛季场均数据 | `wangyi_match_tech` (season stats) | 仅已赛队 |

## API

新增 `GET /api/teams/compare?team_a=<name>&team_b=<name>`

返回两队对比数据，包含上述所有指标。数据结构见 `api/schemas.py` 新增的 `TeamCompareResponse`。

## 前端

### 新组件: TeamCompare.vue

**Props:** `teamA: string, teamB: string`（英文队名）

- 上方：ECharts 六维雷达图（Elo / FIFA排名 / 阵容人数 / 平均年龄 / 总出场 / 出线概率）
- 下方：4 张补充卡片（场均进球 / 场均失球 / 场均射门 / 场均犯规+牌）

### MatchAnalysisPage 插入位置

在 `MatchTechRadar` 之后、`预测 vs 实际` 之前。

## 涉及文件

| 文件 | 变更 |
|------|------|
| `api/schemas.py` | 新增 TeamCompareResponse, TeamCompareItem |
| `api/main.py` | 新增 GET /api/teams/compare |
| `api/data_store.py` | 新增 compare_teams() |
| `web/src/types/api.ts` | 新增类型 |
| `web/src/components/match/TeamCompare.vue` | 新建 |
| `web/src/pages/MatchAnalysisPage.vue` | 插入组件 |
| `tests/test_dashboard_api.py` | 新增测试 |
