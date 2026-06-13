# 赛前情报展示 + 赛后深度复盘 — 前端设计文档

> 日期: 2026-06-13
> 分支: feat/confed-bias-protection

## 目标

将后端已返回但前端未消费的数据（Firecrawl 赛前情报、Wangyi 球队上下文、matchReviews 复盘数据）接入 Vue 3 仪表盘前端。

## 背景

后端 `GET /api/matches/{match_no}` 已在近期提交中新增了 `preview_sources`、`home_team_context`、`away_team_context` 三个字段，`outcome_probabilities` 额外包含 `over_2_5`、`under_2_5`、`both_teams_score`。前端 TypeScript 类型定义和页面均未消费这些数据。

后端 `GET /api/reviews/matches` 返回已完赛比赛的详细复盘数据（预期进球、误差、review_bucket 分类），前端 `api.ts` 已定义 `matchReviews()` 但从未调用。

## 架构决策

- 新建组件放到对应目录：`web/src/components/match/`（比赛相关）和 `web/src/components/home/`（首页相关）
- 遵循现有代码风格：`<script setup lang="ts">` + scoped CSS
- 使用 Element Plus 组件（ElCard、ElTag、ElCollapse 等）
- 数据流：页面调用 API → `useAsyncState` → 传递给子组件 props
- 不引入新的 npm 依赖

## 方向 A：MatchAnalysisPage 赛前情报展示

### A.1 TypeScript 类型补全

**文件：** `web/src/types/api.ts`

新增接口：

```typescript
export interface TeamContext {
  team_name: string
  team_name_zh: string
  coach_name_zh?: string | null
  coach_name_en?: string | null
  suspended_count: number
  suspended_players_zh: string[]
  suspended_players_en: string[]
  squad_size?: number | null
}

export interface MatchPreviewSource {
  match_no: number
  team_name: string
  team_name_zh: string
  source_name?: string | null
  source_domain?: string | null
  source_title?: string | null
  source_url?: string | null
  published_time?: string | null
  predicted_lineup_text?: string | null
  injury_notes?: string | null
  coach_quotes?: string | null
  key_player_notes?: string | null
}
```

`MatchDetail` 增加字段：

```typescript
export interface MatchDetail {
  // ... existing fields ...
  home_team_context?: TeamContext | null
  away_team_context?: TeamContext | null
  preview_sources: MatchPreviewSource[]
}
```

### A.2 赛前情报卡片 (PreMatchContextCard)

**文件：** `web/src/components/match/PreMatchContextCard.vue`（新建）

**Props:**
- `sources: MatchPreviewSource[]`

**展示内容:**
- 无数据时：不渲染（返回空）
- 有数据时：ElCard，标题"赛前情报"，副标题显示来源数量
- 每个来源一个 ElCollapse 项：
  - 标题：来源名称 + 链接图标 + 发布时间
  - 折叠内容：预测首发文本、伤病信息、教练引语、关键球员
- 伤病信息中的 "Out:" 关键词用红色标签标注

### A.3 球队上下文卡片 (TeamContextCard)

**文件：** `web/src/components/match/TeamContextCard.vue`（新建）

**Props:**
- `context: TeamContext | null | undefined`
- `side: 'home' | 'away'`

**展示内容:**
- 无数据时：显示"暂无数据"
- 标题：球队名（中文）
- 教练名（中文优先，英文兜底）
- 阵容人数
- 停赛球员列表（ElTag，type="danger"）
- 无停赛时显示"无停赛球员"

### A.4 MatchAnalysisPage 变更

**文件：** `web/src/pages/MatchAnalysisPage.vue`

- 概率卡片从 3 项扩展到最多 6 项（已赛时显示 over/under 2.5 + BTTS）
- 在概率卡片下方插入 `PreMatchContextCard`
- 在情报卡片下方插入两个并排的 `TeamContextCard`（主/客）
- 引入新组件和类型

## 方向 B：HomePage 赛后深度复盘

### B.1 深度复盘卡片 (MatchReviewInsight)

**文件：** `web/src/components/home/MatchReviewInsight.vue`（新建）

**Props:**
- `reviews: MatchReviewRow[]`

**展示内容:**
- 标题"赛后深度复盘"
- 每场比赛一张卡片，展示：
  - 主队 vs 客队（中文名）+ 实际比分
  - 三列指标：模型预期总进球 | 实际总进球 | 误差
  - 方向命中/偏离 + 比分命中/偏离（图标 + 文字）
  - 实际结果模型置信度（百分比 + 解释）
  - review_bucket 标签

### B.2 HomePage 变更

**文件：** `web/src/pages/HomePage.vue`

- 新增 `matchReviews` 的 `useAsyncState`
- 在"最新赛果复盘"区块下面插入 `MatchReviewInsight`
- 引入新组件和类型

## 组件 Props 接口总览

```
PreMatchContextCard
  sources: MatchPreviewSource[]

TeamContextCard
  context: TeamContext | null | undefined
  side: 'home' | 'away'

MatchReviewInsight
  reviews: MatchReviewRow[]
```

## 数据流

```
MatchAnalysisPage
  ├─ dashboardApi.matchDetail(matchNo)  →  detail.data
  │   ├─ .preview_sources              →  PreMatchContextCard
  │   ├─ .home_team_context            →  TeamContextCard (side="home")
  │   ├─ .away_team_context            →  TeamContextCard (side="away")
  │   └─ .outcome_probabilities        →  扩展 StatCard 网格

HomePage
  ├─ dashboardApi.matchReviews(8)     →  matchReviews.data → MatchReviewInsight
  └─ 现有数据不变
```

## 不做的事 (YAGNI)

- 不新建独立页面
- 不引入新的 npm 依赖
- 不改动后端代码
- 不在 MatchAnalysisPage 展示 matchReviews（复盘数据放首页即可）
- 不替换现有 RecentResultsReview 组件
