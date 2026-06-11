# Web 看板下一阶段开发规划

## 1. 阶段目标

当前 Web 看板已经完成 MVP：FastAPI 后端、Vue 3 前端、完整赛程、比赛分析、比分价值、小组出线、虚拟组合模拟器和模型解释页均已可浏览。

下一阶段目标是把 MVP 从“能浏览的原型”推进到“可用于研究分析的第一版产品”。

核心方向：

- 赛程页更好用。
- 比赛分析页更直观。
- 数据完整度更透明。

本阶段继续坚持产品边界：

- 不做真实下单。
- 不做支付。
- 不做账户余额。
- 不提供购彩跳转。
- 虚拟组合模拟器仅用于概率、理论返奖和风险研究。

## 2. 产品审阅结论

整体规格合理，可以进入开发。

本阶段最重要的产品修订：

- 统一使用“数据完整度”，不使用“数据可信度”“准确率”“胜率可靠度”等容易误导的表述。
- 数据完整度只表示数据是否齐全，不表示模型预测是否正确。
- 前端数据完整度展示先做轻量版本，避免一期范围膨胀。

## 3. 需求一：数据完整度 API

### 3.1 当前问题

页面可以展示模型结果，但用户不知道每场比赛的数据是否完整。例如：

- 是否有胜平负预测。
- 是否有比分模型。
- 是否有比分赔率。
- 是否有市场赔率。
- 是否有阵容修正。
- 是否有赔率快照时间。

### 3.2 目标

后端输出每场比赛的数据完整度，让前端可以展示当前比赛或赛程项的数据状态。

### 3.3 接口

新增接口：

```text
GET /api/data-quality
```

返回全部赛程比赛的数据完整度，覆盖 104 场。

### 3.4 建议响应字段

```json
{
  "match_no": 1,
  "stage": "Group Stage",
  "group_name": "Group A",
  "home_team": "Mexico",
  "away_team": "South Africa",
  "home_team_zh": "墨西哥",
  "away_team_zh": "南非",
  "has_fixture": true,
  "has_prediction": true,
  "has_scoreline_model": true,
  "has_score_odds": true,
  "has_market_odds": true,
  "has_lineup_adjustment": true,
  "latest_score_odds_fetched_at": "2026-06-10T16:16:39Z",
  "latest_market_fetched_at": "2026-06-10T16:34:50Z",
  "completeness_score": 95,
  "completeness_level": "High",
  "missing_items": []
}
```

### 3.5 评分规则

总分 100：

| 项目 | 分值 |
|---|---:|
| 基础赛程存在 | 10 |
| 胜平负预测存在 | 20 |
| 比分模型存在 | 20 |
| 比分赔率存在 | 20 |
| 市场赔率存在 | 15 |
| 阵容修正存在 | 10 |
| 快照时间存在 | 5 |

等级规则：

| 等级 | 分数 |
|---|---:|
| High | 80-100 |
| Medium | 50-79 |
| Low | 0-49 |

### 3.6 缺失项枚举

后端返回稳定枚举，前端负责翻译：

```text
missing_prediction
missing_scoreline_model
missing_score_odds
missing_market_odds
missing_lineup_adjustment
missing_snapshot_time
```

### 3.7 验收标准

- `/api/data-quality` 返回 104 场。
- 前四场小组赛应为 High 或接近 High。
- 决赛等 TBD 淘汰赛应返回 Low 或 Medium。
- 缺失项能说明具体缺什么。
- API 测试覆盖至少一场高完整度比赛和一场 TBD 淘汰赛。

## 4. 需求二：赛程页日期分组

### 4.1 当前问题

`/schedule` 已展示 104 场，但长表格扫描成本高。

### 4.2 目标

按北京时间日期分组展示赛程，让用户快速找到每天有哪些比赛。

### 4.3 需求细节

- 按 `date_bj` 分组。
- 日期标题展示为类似 `2026年6月12日 周五 · 2场`。
- 每个日期组内按 `time_bj` 和 `match_no` 排序。
- 小组赛显示小组名。
- 淘汰赛显示阶段中文名。
- 小组赛提供“查看分析”入口。
- 淘汰赛未定对阵显示 `待定 vs 待定`。
- 保留阶段筛选和小组筛选。
- 筛选后无结果时显示空状态。
- 移动端优先用卡片布局，减少宽表格依赖。

### 4.4 验收标准

- 打开 `/schedule` 能看到按日期分组的 104 场赛程。
- 筛选阶段后，日期分组随结果变化。
- 筛选 `Group A` 后，只展示 Group A 的比赛日期。
- 小组赛点击“查看分析”能进入 `/matches/{match_no}`。
- 决赛显示 `待定 vs 待定`。

## 5. 需求三：赛程页质量标签

### 5.1 当前问题

用户看到赛程时，不知道每场比赛数据是否完整。

### 5.2 目标

在赛程页每场比赛旁显示数据完整度标签。

### 5.3 需求细节

- 前端接入 `/api/data-quality`。
- 按 `match_no` 关联赛程项。
- 每场显示 `High / Medium / Low` 标签。
- Low 用弱化样式。
- 缺失项一期可先用简短文本展示，不做复杂展开。
- 若数据完整度接口失败，赛程页仍应正常展示。

### 5.4 验收标准

- 赛程页每场比赛都能显示完整度标签。
- TBD 淘汰赛显示较低完整度。
- 前四场显示较高完整度。
- 数据完整度接口异常时页面不崩溃。

## 6. 需求四：比赛分析页数据完整度卡片

### 6.1 当前问题

比赛分析页展示了概率和因素，但没有明确当前比赛用了哪些数据。

### 6.2 目标

在比赛分析页展示当前比赛的数据完整度卡片。

### 6.3 需求细节

- 显示完整度分数。
- 显示完整度等级。
- 显示已具备数据：
  - 赛程
  - 胜平负预测
  - 比分模型
  - 比分赔率
  - 市场赔率
  - 阵容修正
- 显示缺失项。
- 明确说明“数据完整度不等于预测准确率”。

### 6.4 验收标准

- 打开 `/matches/1` 能看到数据完整度卡片。
- 切换前四场后，卡片随比赛更新。
- 缺失项为空时显示“核心数据已接入”。
- 缺失项不为空时显示“暂未接入”的项目。

## 7. 需求五：比赛分析页比分概率图

### 7.1 当前问题

比赛分析页有 Top 10 比分表格，但不够直观看出概率集中度和长尾。

### 7.2 目标

新增比分概率柱状图，帮助用户快速理解精确比分分布。

### 7.3 需求细节

- 新增 `ScorelineProbabilityChart.vue`。
- 数据来自 `/api/matches/{match_no}/scorelines`。
- 默认展示 Top 10。
- 横轴：比分，如 `2-0`、`1-1`。
- 纵轴：模型概率。
- strong_value 使用强调色。
- missing_odds 使用弱化色。
- tooltip 展示：
  - 比分
  - 模型概率
  - 公平赔率
  - 市场赔率，没有则显示“暂未获取赔率”
  - 价值信号
- 图表放在比分表格上方。
- 移动端不溢出。

### 7.4 可选增强

- Top 5 / Top 10 切换。
- 按概率或市场边际切换排序。

### 7.5 验收标准

- 打开比赛分析页能看到 Top 10 比分柱状图。
- 切换前四场后图表更新。
- strong_value 视觉上可区分。
- 缺赔率比分显示为弱化状态。
- tooltip 不出现任何“建议购买”措辞。

## 8. 需求六：首页数据完整度摘要

### 8.1 当前问题

首页能看到数据规模，但不能快速了解整体数据完整度。

### 8.2 目标

首页展示整体 High / Medium / Low 数量。

### 8.3 需求细节

- 接入 `/api/data-quality`。
- 汇总 High / Medium / Low 数量。
- 展示前四场是否具备核心数据：
  - 胜平负预测
  - 比分模型
  - 比分赔率
  - 市场赔率
- 不做复杂解释层。

### 8.4 验收标准

- 首页能看到 High / Medium / Low 总数。
- 前四场核心数据状态可见。
- 接口失败时首页仍显示原有内容。

## 9. 执行计划

### 批次 1：数据完整度 API

开发内容：

- 在 `api/schemas.py` 增加 `DataQualityRow`。
- 在 `api/data_store.py` 增加 `list_data_quality()`。
- 在 `api/main.py` 增加 `GET /api/data-quality`。
- 在 `tests/test_dashboard_api.py` 增加测试。

验证：

```powershell
.venv\Scripts\python -m pytest tests/test_dashboard_api.py
.venv\Scripts\python -m ruff check api tests/test_dashboard_api.py
```

提交建议：

```text
Add dashboard data completeness API
```

### 批次 2：赛程页日期分组 + 质量标签

开发内容：

- 在 `web/src/types/api.ts` 增加 `DataQualityRow`。
- 在 `web/src/services/api.ts` 增加 `dataQuality()`。
- 改造 `SchedulePage.vue`：
  - 日期分组。
  - 卡片式展示。
  - 质量标签。
  - 空状态。
  - 保留筛选。

验证：

```powershell
cd web
npm run build
```

手动验收：

- 打开 `/schedule`。
- 检查日期分组。
- 检查阶段和小组筛选。
- 检查质量标签。

提交建议：

```text
Group schedule by date with completeness badges
```

### 批次 3：比赛分析页数据完整度卡片

开发内容：

- 新增 `MatchCompletenessCard.vue`。
- 在 `MatchAnalysisPage.vue` 接入当前比赛数据完整度。
- 展示分数、等级、已接入项、缺失项。

验证：

```powershell
cd web
npm run build
```

手动验收：

- 打开 `/matches/1`。
- 切换前四场。
- 检查完整度卡片更新。

提交建议：

```text
Surface match data completeness
```

### 批次 4：比赛分析页比分概率图

开发内容：

- 新增 `ScorelineProbabilityChart.vue`。
- 使用 ECharts 柱状图。
- 接入 `MatchAnalysisPage.vue`。
- tooltip 展示概率、赔率、价值信号。

验证：

```powershell
cd web
npm run build
```

手动验收：

- 打开 `/matches/1`。
- 切换前四场。
- 检查图表更新和 tooltip。

提交建议：

```text
Add scoreline probability chart
```

### 批次 5：首页数据完整度摘要

开发内容：

- 新增或复用完整度摘要组件。
- 首页展示 High / Medium / Low 数量。
- 首页展示前四场核心数据状态。

验证：

```powershell
cd web
npm run build
```

手动验收：

- 打开首页。
- 检查完整度摘要。
- 确认接口失败时不影响首页主体展示。

提交建议：

```text
Add dashboard completeness summary
```

## 10. 推荐开发顺序

最终推荐顺序：

1. 数据完整度 API。
2. 赛程页日期分组 + 质量标签。
3. 比赛分析页数据完整度卡片。
4. 比赛分析页比分概率图。
5. 首页数据完整度摘要。

原因：

- 数据完整度 API 是后续多个页面的基础。
- 赛程页是当前最长、最需要结构化的信息页。
- 比赛分析页需要先解释“数据是否齐全”，再强化“比分概率图”。
- 首页摘要放最后，避免过早做展示而底层口径还没稳定。

## 11. 暂不纳入本阶段

以下内容暂不纳入本阶段，避免范围膨胀：

- 真实下单功能。
- 支付或账户系统。
- 复杂投注策略推荐。
- 自动抓取新赔率。
- 新闻、天气、裁判特征接入。
- 严格联合概率模型。
- 复杂破产风险模型。

## 12. 当前状态

截至本规划创建时：

- FastAPI 后端已存在。
- Vue 3 前端已存在。
- 完整赛程页已存在。
- 数据快照条已存在。
- 比赛分析页已有前四场快速切换。
- 比分价值页已存在。
- 小组出线页已存在。
- 虚拟组合模拟器已存在。
- 模型解释页已存在。

下一步建议从“批次 1：数据完整度 API”开始。
