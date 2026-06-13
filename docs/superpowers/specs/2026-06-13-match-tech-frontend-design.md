# 比赛技术统计展示 — 前端设计文档

> 日期: 2026-06-13

## 目标

将网易技战术 API 数据（控球率、射门、角球、红黄牌等）通过 API 暴露，在前端 MatchAnalysisPage 以雷达图形式展示主客两队对比。

## 背景

`src/wangyi_tech_pipeline.py` 已完成，产出 `wangyi_match_tech_2026.parquet`。数据通过 `mid`（网易比赛 ID）标识，需映射到内部 `match_no`。

## 数据流

```
wangyi_match_tech_2026.parquet
    ↓ (mid → match_no 映射)
api/data_store.py: _match_tech(match_no)
    ↓
GET /api/matches/{match_no}  →  MatchDetail.match_tech
    ↓
MatchAnalysisPage  →  MatchTechRadar 组件
```

## mid → match_no 映射

通过网易 schedule API（`https://gw.m.163.com/base/worldCup/qatar/schedule`）的 `finishScheduleList` 和 `scheduleList`，将 `mid` 与已有 fixtures 数据中的主客队名进行匹配，建立映射表。

## API 变更

### 新增 Pydantic schema

```python
class MatchTechStats(BaseModel):
    home_possession: int = 0
    away_possession: int = 0
    home_shots: int = 0
    away_shots: int = 0
    home_shots_on_target: int = 0
    away_shots_on_target: int = 0
    home_corners: int = 0
    away_corners: int = 0
    home_yellow_cards: int = 0
    away_yellow_cards: int = 0
    home_red_cards: int = 0
    away_red_cards: int = 0
```

### MatchDetail 新增字段

```python
class MatchDetail(BaseModel):
    # ... existing ...
    match_tech: MatchTechStats | None = None
```

### data_store 新增方法

`_match_tech(match_no)` — 从 `wangyi_match_tech_2026.parquet` 读取，通过 mid 映射查找。

## 前端变更

### TypeScript 类型

```typescript
export interface MatchTechStats {
  home_possession: number
  away_possession: number
  home_shots: number
  away_shots: number
  home_shots_on_target: number
  away_shots_on_target: number
  home_corners: number
  away_corners: number
  home_yellow_cards: number
  away_yellow_cards: number
  home_red_cards: number
  away_red_cards: number
}
```

`MatchDetail` 新增 `match_tech?: MatchTechStats | null`

### MatchTechRadar 组件（新建）

ECharts 雷达图，六边形：控球率、射门、射正、角球、黄牌、红牌。主队红色、客队绿色。

### MatchAnalysisPage

在球队状态卡片下方插入 `<MatchTechRadar>`。

## 涉及文件

| 文件 | 变更 |
|------|------|
| `api/schemas.py` | 新增 `MatchTechStats`，`MatchDetail` 加字段 |
| `api/data_store.py` | 新增 `_match_tech()`，加载 parquet |
| `web/src/types/api.ts` | 新增 `MatchTechStats`，`MatchDetail` 加字段 |
| `web/src/components/match/MatchTechRadar.vue` | 新建 |
| `web/src/pages/MatchAnalysisPage.vue` | 插入雷达图 |
| `tests/test_dashboard_api.py` | 新增测试 |

## YAGNI

- 不做球员事件时间线（之后再做）
- 不做赛季累计统计展示
- 不做教练信息展示（已有 TeamContextCard）
