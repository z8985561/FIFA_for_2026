# 赛前情报展示 + 赛后深度复盘 — 实现计划

> **给执行者：** 使用 superpowers-executing-plans 来逐任务实现此计划。步骤使用 checkbox (`- [ ]`) 语法跟踪。

**目标：** 将后端已返回的 Firecrawl 赛前情报、Wangyi 球队上下文、matchReviews 复盘数据接入 Vue 3 前端看板。

**架构：** 纯前端改动 — 补 TypeScript 类型，新建 3 个展示组件（PreMatchContextCard、TeamContextCard、MatchReviewInsight），修改 2 个页面（MatchAnalysisPage、HomePage）。后端和测试不变。

**技术栈：** Vue 3 Composition API (`<script setup lang="ts">`) + Element Plus + TypeScript + scoped CSS

---

### 任务 1: 补全 TypeScript 类型定义

**文件：**
- 修改: `web/src/types/api.ts`

- [ ] **步骤 1: 添加 TeamContext 和 MatchPreviewSource 接口，扩展 MatchDetail**

在文件末尾 `}` 之前（最后一个接口之后），新增：

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

修改 `MatchDetail` 接口，在 `factor_breakdown` 之后、闭合 `}` 之前添加：

```typescript
  home_team_context?: TeamContext | null
  away_team_context?: TeamContext | null
  preview_sources: MatchPreviewSource[]
```

完整 `MatchDetail` 变为：

```typescript
export interface MatchDetail {
  match: MatchSummary
  expected_goals: Record<string, number | null>
  outcome_probabilities: Record<string, number | null>
  market_probabilities: Record<string, number | null>
  home_team_context?: TeamContext | null
  away_team_context?: TeamContext | null
  preview_sources: MatchPreviewSource[]
  factor_breakdown: FactorBreakdown[]
}
```

- [ ] **步骤 2: 验证 — 运行 TypeScript 类型检查**

```powershell
cd web; npx vue-tsc --noEmit 2>&1
```

预期: 无新增类型错误（可能有预先存在的 warning）

- [ ] **步骤 3: 提交**

```bash
git add web/src/types/api.ts
git commit -m "feat: add TeamContext and MatchPreviewSource types, extend MatchDetail"
```

---

### 任务 2: 创建 PreMatchContextCard 组件

**文件：**
- 创建: `web/src/components/match/PreMatchContextCard.vue`

- [ ] **步骤 1: 编写组件**

```vue
<script setup lang="ts">
import type { MatchPreviewSource } from '@/types/api'

const props = defineProps<{
  sources: MatchPreviewSource[]
}>()

function openUrl(url?: string | null) {
  if (url) window.open(url, '_blank', 'noopener')
}

function hasContent(source: MatchPreviewSource): boolean {
  return !!(
    source.predicted_lineup_text ||
    source.injury_notes ||
    source.coach_quotes ||
    source.key_player_notes
  )
}
</script>

<template>
  <section v-if="props.sources.length" class="section-card">
    <div class="section-title">
      <h2>赛前情报</h2>
      <span>{{ props.sources.length }} 个来源</span>
    </div>

    <ElCollapse accordion>
      <ElCollapseItem
        v-for="(source, i) in props.sources"
        :key="i"
      >
        <template #title>
          <div class="source-header">
            <span class="source-name">{{ source.source_name || '未知来源' }}</span>
            <span v-if="source.published_time" class="source-time">{{ source.published_time }}</span>
            <ElTag
              v-if="source.source_url"
              size="small"
              type="info"
              class="source-link-tag"
              @click.stop="openUrl(source.source_url)"
            >
              查看原文
            </ElTag>
          </div>
        </template>

        <div v-if="hasContent(source)" class="source-body">
          <div v-if="source.predicted_lineup_text" class="source-block">
            <h4>预测首发</h4>
            <pre>{{ source.predicted_lineup_text }}</pre>
          </div>
          <div v-if="source.injury_notes" class="source-block">
            <h4>伤病 / 停赛</h4>
            <pre>{{ source.injury_notes }}</pre>
          </div>
          <div v-if="source.coach_quotes" class="source-block">
            <h4>教练发言</h4>
            <pre>{{ source.coach_quotes }}</pre>
          </div>
          <div v-if="source.key_player_notes" class="source-block">
            <h4>关键球员</h4>
            <pre>{{ source.key_player_notes }}</pre>
          </div>
        </div>
        <div v-else class="source-body muted">暂无详细内容</div>
      </ElCollapseItem>
    </ElCollapse>
  </section>
</template>

<style scoped>
.source-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.source-name {
  font-weight: 700;
}

.source-time {
  color: var(--color-muted);
  font-size: 13px;
}

.source-link-tag {
  cursor: pointer;
}

.source-body {
  display: grid;
  gap: 18px;
  padding: 8px 0;
}

.source-block h4 {
  margin: 0 0 6px;
  font-size: 14px;
  color: var(--color-accent);
}

.source-block pre {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--color-ink);
}

.muted {
  color: var(--color-muted);
  font-size: 13px;
}
</style>
```

- [ ] **步骤 2: 提交**

```bash
git add web/src/components/match/PreMatchContextCard.vue
git commit -m "feat: add PreMatchContextCard component for Firecrawl news display"
```

---

### 任务 3: 创建 TeamContextCard 组件

**文件：**
- 创建: `web/src/components/match/TeamContextCard.vue`

- [ ] **步骤 1: 编写组件**

```vue
<script setup lang="ts">
import type { TeamContext } from '@/types/api'

const props = defineProps<{
  context: TeamContext | null | undefined
  side: 'home' | 'away'
}>()
</script>

<template>
  <div class="team-context-card">
    <div class="tc-head">
      <ElTag :type="props.side === 'home' ? 'primary' : 'warning'" size="small">
        {{ props.side === 'home' ? '主队' : '客队' }}
      </ElTag>
      <strong>{{ props.context?.team_name_zh || '暂无数据' }}</strong>
    </div>

    <template v-if="props.context">
      <div class="tc-row">
        <span>教练</span>
        <strong>{{ props.context.coach_name_zh || props.context.coach_name_en || '暂无' }}</strong>
      </div>
      <div class="tc-row">
        <span>阵容人数</span>
        <strong>{{ props.context.squad_size ?? '暂无' }}</strong>
      </div>
      <div class="tc-row">
        <span>停赛球员</span>
        <div v-if="props.context.suspended_count > 0" class="tc-tags">
          <ElTag
            v-for="(name, i) in props.context.suspended_players_zh"
            :key="i"
            type="danger"
            size="small"
          >
            {{ name }}
          </ElTag>
        </div>
        <span v-else class="muted">无停赛球员</span>
      </div>
    </template>
    <div v-else class="tc-row muted">暂无球队数据</div>
  </div>
</template>

<style scoped>
.team-context-card {
  display: grid;
  gap: 12px;
  padding: 18px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.72);
}

.tc-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tc-head strong {
  font-size: 18px;
}

.tc-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.tc-row span {
  color: var(--color-muted);
  font-size: 13px;
}

.tc-row strong {
  font-size: 15px;
}

.tc-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.muted {
  color: var(--color-muted);
  font-size: 13px;
}
</style>
```

- [ ] **步骤 2: 提交**

```bash
git add web/src/components/match/TeamContextCard.vue
git commit -m "feat: add TeamContextCard component for Wangyi team data display"
```

---

### 任务 4: 更新 MatchAnalysisPage

**文件：**
- 修改: `web/src/pages/MatchAnalysisPage.vue`

- [ ] **步骤 1: 添加新组件的 import**

在 `<script setup>` 顶部的 import 区域，`FactorWaterfall` import 之后添加：

```typescript
import PreMatchContextCard from '@/components/match/PreMatchContextCard.vue'
import TeamContextCard from '@/components/match/TeamContextCard.vue'
```

在 type import 中，`MatchDetail` 之后添加 `TeamContext`（虽然通过 MatchDetail 间接使用，但为了明确导入）：

实际上不需要单独 import TeamContext 类型——通过 `detail.data.value?.home_team_context` 会自动推导。只需更新组件 import。

- [ ] **步骤 2: 扩展概率 StatCard 网格**

在模板中，将现有的 3 个 StatCard（主胜/平局/客胜）的 `<div class="stat-grid">` 区块，替换为包含 6 项概率的版本：

```html
    <div v-if="detail.data.value" class="stat-grid stat-grid-6">
      <StatCard label="主胜概率" :value="percent(detail.data.value.outcome_probabilities.home_win)" />
      <StatCard label="平局概率" :value="percent(detail.data.value.outcome_probabilities.draw)" />
      <StatCard label="客胜概率" :value="percent(detail.data.value.outcome_probabilities.away_win)" />
      <StatCard label="大 2.5" :value="percent(detail.data.value.outcome_probabilities.over_2_5)" />
      <StatCard label="小 2.5" :value="percent(detail.data.value.outcome_probabilities.under_2_5)" />
      <StatCard label="双方进球" :value="percent(detail.data.value.outcome_probabilities.both_teams_score)" />
    </div>
```

- [ ] **步骤 3: 插入新卡片到模板**

在概率 stat-grid 之后、"预测 vs 实际" section 之前，插入：

```html
    <PreMatchContextCard :sources="detail.data.value?.preview_sources ?? []" />

    <section v-if="detail.data.value" class="section-card">
      <div class="section-title">
        <h2>球队状态</h2>
        <span>来自网易及赛前情报</span>
      </div>
      <div class="team-context-grid">
        <TeamContextCard
          :context="detail.data.value.home_team_context"
          side="home"
        />
        <TeamContextCard
          :context="detail.data.value.away_team_context"
          side="away"
        />
      </div>
    </section>
```

- [ ] **步骤 4: 添加新 grid 的 CSS**

在 `<style scoped>` 中，现有的 `.stat-grid` 之后添加：

```css
.stat-grid-6 {
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.team-context-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

@media (max-width: 900px) {
  .stat-grid-6 {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .team-context-grid {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **步骤 5: 提交**

```bash
git add web/src/pages/MatchAnalysisPage.vue
git commit -m "feat: add pre-match context and team context cards to MatchAnalysisPage"
```

---

### 任务 5: 创建 MatchReviewInsight 组件

**文件：**
- 创建: `web/src/components/home/MatchReviewInsight.vue`

- [ ] **步骤 1: 编写组件**

```vue
<script setup lang="ts">
import type { MatchReviewRow } from '@/types/api'

const props = defineProps<{
  reviews: MatchReviewRow[]
}>()

function bucketLabel(bucket: string): string {
  const map: Record<string, string> = {
    exact_hit: '精确命中',
    outcome_hit_only: '方向命中',
    upset_miss: '冷门偏差',
    outcome_miss: '方向偏离',
    scoreline_hit: '比分命中',
    outcome_hit_scoreline_miss: '方向对/比分错',
  }
  return map[bucket] || bucket
}

function bucketType(bucket: string): 'success' | 'danger' | 'warning' | 'info' {
  if (bucket === 'exact_hit' || bucket === 'scoreline_hit') return 'success'
  if (bucket === 'upset_miss' || bucket === 'outcome_miss') return 'danger'
  if (bucket === 'outcome_hit_only' || bucket === 'outcome_hit_scoreline_miss') return 'warning'
  return 'info'
}
</script>

<template>
  <section v-if="props.reviews.length" class="section-card">
    <div class="section-title">
      <h2>赛后深度复盘</h2>
      <span>预期 vs 实际进球分析</span>
    </div>

    <div class="review-insight-grid">
      <article
        v-for="review in props.reviews"
        :key="review.match_no"
        class="insight-card"
      >
        <div class="insight-head">
          <div>
            <span class="insight-kicker">
              第 {{ review.match_no }} 场 · {{ review.group_name }}
            </span>
            <h3>{{ review.home_team_zh }} vs {{ review.away_team_zh }}</h3>
          </div>
          <ElTag :type="bucketType(review.review_bucket)" size="small">
            {{ bucketLabel(review.review_bucket) }}
          </ElTag>
        </div>

        <div class="insight-score">
          <strong>{{ review.actual_scoreline || review.home_team + ' ' + review.away_team }}</strong>
        </div>

        <div class="insight-metrics">
          <div class="metric">
            <span>模型预期总进球</span>
            <strong>{{ review.expected_total_goals?.toFixed(2) ?? '暂无' }}</strong>
          </div>
          <div class="metric">
            <span>实际总进球</span>
            <strong>{{ review.actual_total_goals ?? '暂无' }}</strong>
          </div>
          <div class="metric">
            <span>误差</span>
            <strong :class="{
              'text-green': review.total_goals_error != null && Math.abs(review.total_goals_error) < 0.5,
              'text-red': review.total_goals_error != null && Math.abs(review.total_goals_error) >= 1.5,
            }">
              {{ review.total_goals_error != null
                ? (review.total_goals_error >= 0 ? '+' : '') + review.total_goals_error.toFixed(2)
                : '暂无' }}
            </strong>
          </div>
        </div>

        <div class="insight-footer">
          <span>
            {{ review.outcome_hit ? '✓ 方向命中' : '✗ 方向偏离' }}
          </span>
          <span>
            {{ review.scoreline_hit ? '✓ 比分命中' : '✗ 比分偏离' }}
          </span>
          <span v-if="review.actual_outcome_probability != null">
            真实结果置信度 {{ (review.actual_outcome_probability * 100).toFixed(0) }}%
          </span>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.review-insight-grid {
  display: grid;
  gap: 16px;
}

.insight-card {
  display: grid;
  gap: 14px;
  padding: 20px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.72);
}

.insight-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 12px;
}

.insight-kicker {
  color: var(--color-muted);
  font-size: 13px;
}

.insight-head h3 {
  margin: 4px 0 0;
  font-size: 20px;
}

.insight-score strong {
  font-size: 32px;
  line-height: 1;
}

.insight-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.metric {
  display: grid;
  gap: 4px;
  padding: 12px;
  border-radius: var(--radius-md);
  background: rgba(0, 0, 0, 0.02);
}

.metric span {
  color: var(--color-muted);
  font-size: 12px;
}

.metric strong {
  font-size: 20px;
}

.insight-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: var(--color-muted);
}

.text-green {
  color: #16a34a;
}

.text-red {
  color: #dc2626;
}

@media (max-width: 900px) {
  .insight-metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
```

- [ ] **步骤 2: 提交**

```bash
git add web/src/components/home/MatchReviewInsight.vue
git commit -m "feat: add MatchReviewInsight component for post-match analysis"
```

---

### 任务 6: 更新 HomePage

**文件：**
- 修改: `web/src/pages/HomePage.vue`

- [ ] **步骤 1: 添加数据获取和组件 import**

在 `<script setup>` 中：
- type import 添加 `MatchReviewRow`
- 添加新的 async state：`const matchReviews = useAsyncState<MatchReviewRow[]>()`
- 在 `onMounted` 中添加：`matchReviews.run(() => dashboardApi.matchReviews(8))`

具体改动 — 修改 import 语句：

```typescript
import type { DataQualityRow, HealthResponse, MatchReviewRow, ScorelineRow } from '@/types/api'
```

添加 import：

```typescript
import MatchReviewInsight from '@/components/home/MatchReviewInsight.vue'
```

添加 state：

```typescript
const matchReviews = useAsyncState<MatchReviewRow[]>()
```

在 `onMounted` 中添加调用：

```typescript
  matchReviews.run(() => dashboardApi.matchReviews(8))
```

- [ ] **步骤 2: 插入复盘区块到模板**

在"最新赛果复盘" section（`<RecentResultsReview>`）之后、"当前价值信号 Top 8" section 之前，插入：

```html
    <MatchReviewInsight :reviews="matchReviews.data.value ?? []" />
```

- [ ] **步骤 3: 提交**

```bash
git add web/src/pages/HomePage.vue
git commit -m "feat: add post-match review insights to HomePage"
```

---

### 任务 7: 验证 — 运行完整测试

- [ ] **步骤 1: 运行后端测试**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_dashboard_api.py -v
```

预期: 全部 11 个测试通过

- [ ] **步骤 2: 运行前端类型检查**

```powershell
cd web; npx vue-tsc --noEmit 2>&1
```

预期: 无类型错误

- [ ] **步骤 3: 运行完整测试套件**

```powershell
.venv\Scripts\python.exe -m pytest -q
```

预期: 140 passed

- [ ] **步骤 4: 提交**

```bash
# 如果一切通过，无需额外提交（前面各任务已提交）
git log --oneline -6
```
