# FIFA 2026 开发待办 — 淘汰赛阶段

> 创建：2026-06-29 | 当前：淘汰赛 32 强 | 剩余 15 场比赛

---

## P0：阻塞项（影响预测质量，必须做）

### P0-1 淘汰赛特征工程

- **状态**：🔴 待做
- **问题**：`match_feature_store_2026.parquet` 只覆盖小组赛（#1-#72），淘汰赛（#73-#88）无 Elo 差、状态特征、赔率特征
- **方案**：`build_2026_enhanced_features()` 需支持淘汰赛 fixture
- **文件**：`src/enhanced_features.py`、`src/feature_store.py`
- **验收**：`enhanced_predictions.csv` 包含 #73-#88 的完整概率

### P0-2 淘汰赛市场赔率接入模型

- **状态**：🔴 待做
- **问题**：`sporttery_score_odds_snapshots.parquet` 有 9 场体彩赔率，但 `scoreline_model.py` 没读取
- **方案**：在 `build_scoreline_analysis()` 中检测淘汰赛 + 读取体彩快照 → 用 `apply_market_probability_anchor()` 约束比分概率
- **文件**：`src/scoreline_model.py`（约 1588 行附近）
- **验收**：体彩高概率比分匹配模型输出（如 巴西 2:1 赔率 5.80 应对应模型概率 ~12%）

### P0-3 赛果数据对齐

- **状态**：🔴 待做
- **问题**：`official_match_results_2026.parquet` 与实际赛果有 11 场差距（49/60 匹配），match_no 编号不统一
- **方案**：重写 `NetEase → official_results` 同步脚本，统一用 `zh_team_name()` 双向映射
- **文件**：`src/official_results_pipeline.py`
- **验收**：60 场小组赛全量入 `official_results`

---

## P1：改进项（提升体验，应该做）

### P1-1 每日准确率自动统计

- **状态**：🟡 待做
- **方案**：每次同步后自动对比 `enhanced_predictions` vs `official_results`，输出分轮次报告
- **文件**：新建 `src/accuracy_tracker.py`
- **验收**：管道末尾输出 `胜平负 25/40=62% | Top3 10/40=25%`

### P1-2 淘汰赛对阵确认

- **状态**：🟡 待做
- **问题**：我们生成的 32 强对阵（墨西哥-加拿大）与体彩截图（巴西-日本）不一致
- **方案**：从 NetEase 官方赛程 API 拉取实际对阵，覆盖本地生成
- **文件**：`gen_bracket.py` 或新增 `src/fetch_bracket.py`
- **验收**：fixtures #73-#88 与体育彩票赛程完全一致

### P1-3 赔率实时抓取

- **状态**：🟡 待做
- **问题**：sporttery 有 WAF 防火墙，API 被拦截
- **方案**：用 Playwright/Selenium 启动无头浏览器 → 截图 → OCR 提取赔率
- **文件**：新建 `src/scrape_sporttery_odds.py`
- **验收**：定时自动拉取 `sporttery_score_odds_snapshots.parquet`

### P1-4 Web 淘汰赛页面适配

- **状态**：🟡 待做
- **问题**：`MatchAnalysisPage.vue` 的"明日赛事预览"和"预测 vs 实际"没适配淘汰赛
- **方案**：MatchSwitcher 显示淘汰赛对阵；淘汰赛不显示平局概率
- **文件**：`web/src/pages/MatchAnalysisPage.vue`、`web/src/components/match/`

---

## P2：增强项（锦上添花，可以做）

### P2-1 加时赛/点球概率

- **状态**：🟢 待做
- **方案**：在比分矩阵中为平局行添加"晋级概率"，基于 Elo 差调整
- **文件**：`src/scoreline_model.py`

### P2-2 球员事件模型

- **状态**：🟢 待做
- **方案**：利用 3383 条 `wangyi_match_players` 数据，预测红黄牌、进球球员
- **文件**：新建 `src/player_model.py`

### P2-3 投注方案生成器

- **状态**：🟢 待做
- **方案**：基于赔率-模型偏差，自动输出稳胆串关 + 博冷单场
- **文件**：新建 `src/betting_recommender.py`

---

## 变更记录

| 日期 | 任务 | 状态 |
|------|------|------|
| 6/29 | 初始创建 | — |
| 6/29 | P0-1 淘汰赛特征工程 | ✅ |
| 6/29 | P0-3 赛果对齐 | ✅ |
