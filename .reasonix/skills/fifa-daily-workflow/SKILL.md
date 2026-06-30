---
name: fifa-daily-workflow
description: FIFA 每日完整工作流：同步数据 → 运行管道 → 准确率统计 → 生成简报。一步到位。
---

## FIFA 每日工作流

### 触发条件
当用户说"同步数据"、"今日简报"、"今天比赛"、"明天预测"、"命中率"时执行。

### 步骤

#### 1. 拉取最新赛果（带网络防御）
```bash
curl --connect-timeout 5 --retry 3 --max-time 15 -s   "https://gw.m.163.com/base/worldCup/qatar/schedule"   | python -c "
import sys,json
try:
    data=json.load(sys.stdin)
    finish=data['data']['finishScheduleList']
    print(f'完赛:{len(finish)}')
except (KeyError,json.JSONDecodeError) as e:
    print(f'DATA_STRUCTURE_ERROR:{e}')
    sys.exit(2)
"
```
- 超时 5s，最多重试 3 次
- JSON 结构异常时退出码 2，通知开发者
- 比对  vs 本地，仅在有增量时继续

#### 2. 同步管道（有比赛已结束时）
```bash
.venv\Scripts\python.exe -m src.sync_results        # 赛果对齐
.venv\Scripts\python.exe -m src.wangyi_tech_pipeline  # 技术统计
.venv\Scripts\python.exe -m src.enhanced_model         # 胜平负
.venv\Scripts\python.exe -m src.scoreline_model --limit 88 --top-scores 10  # 比分
.venv\Scripts\python.exe -m src.tournament_simulator --simulations 10000     # 冠军概率
```

#### 3. 准确率统计
用 `enhanced_predictions.csv` vs `official_match_results_2026.parquet` 计算：
- 胜平负命中率
- Top1/3/5/10 比分命中率
- 按轮次分类统计

#### 4. 生成简报

简报模板（必须严格遵循）：

```
=== YYYY-MM-DD 赛果 (N场) ===
✅ #match_no 主队 vs 客队: X-Y (预测: 方向 概率%)
❌ #match_no 主队 vs 客队: X-Y (预测: 方向 概率%)

=== 今日准确率 ===
胜平负: N/M=XX% | Top3: N/M=XX% | Top10: N/M=XX%
累计: 胜平负 N/M=XX% | Top10: N/M=XX%

=== 小组/淘汰赛形势 ===
[如有重大变化才写，否则省略]

=== 明日赛程 (YYYY-MM-DD) ===
#match_no 主队 vs 客队  时间 BJ  [阶段]
  xG: H-A | 方向胜 XX% | Top3: 比分(XX%)·比分(XX%)·比分(XX%)
```

#### 5. 简报规则
- **优先表格**，不要长段落
- 用 ✅❌ 标记预测正确/错误
- 仅标注预测最可能的方向与实际不符的行
- 对比分 Top10 单独列一个表
- 如果平局概率 > 30%，特别标注 ⚠️
- 如果有体彩赔率数据，追加市场 vs 模型对比

#### 6. 提交（含准确率摘要）
```bash
git add -f data/processed/*.parquet reports/*.csv
git commit -m "data: sync YYYY-MM-DD | settled: N | acc: XX% top10: XX%"
git push
```
- Commit 消息包含结算场次 + 准确率，af21903 skill: consolidate daily sync + match analysis into fifa-daily-workflow
fecb76a feat(P0-2): load sporttery score odds into market constraints pipeline
5471d33 feat(P0-1): knockout feature engineering - 16 R32 matches with full predictions
8c325c7 feat(P0-3): robust NetEase sync script with team name aliases and swapped lookup
0995f46 docs: project retrospective, skill workflows for daily sync and match analysis
a986ff3 report: full odds-probability comparison table for 9 knockout matches
99ae36a data: add Belgium-Senegal and USA-Bosnia sporttery odds to knockout predictions
9756536 data: add sporttery score odds for 7 knockout matches from user screenshot
4eac90a feat: knockout stage xG compression (0.85 factor)
32c7075 feat: generate R32 knockout bracket, 16 matchups filled
83a1ab4 data: group stage complete — 66/72 matches synced, knockout starts June 28
0ac1bd7 data: sync through June 26 - Ecuador 2-1 Germany upset, 60 matches complete
0712891 chore: update confederation corrections data
c0d92bc data: sync through June 25 — 46/72 complete, Portugal 5-0, Brazil 3-0
5ddd1bd data: sync June 23 — Argentina 2-0, model #1 scoreline hit
99f066a data: sync through June 22 — 40 matches, outcome 59%
20bc0c6 fix: add missing Portugal 1-1 DR Congo result (team name mismatch)
8608314 data: sync through June 18 - 24 matches complete, outcome improves to 53%
47fa1f0 feat: add match times to tomorrow preview, add AI team strength summary
5e7a885 chore: regenerate full predictions with per-round draw boost
f36ff0e feat: add per-round draw probability boost (R1×1.8, R2×1.3, R3×1.0)
86a6af2 fix: group standings merge by team names instead of match_no, regenerate tournament simulation
fbc3498 data: sync latest odds (sporttery 365 snapshots, 15 match features) and regenerate scorelines
8871642 data: sync June 16 — brutal draw day (4/4 draws, model 0/3 outcome)
6dd850b data: sync June 15 match results (Germany 7-1, Netherlands 2-2, Sweden 5-1, Ivory Coast 1-0)
2accc84 fix: cap group opener boost at Elo diff 300 to prevent over-amplification
e0da027 feat: add team profile page with squad, form, tournament path
f2354b7 chore: regenerate full pipeline with must-win pressure adjustment
ce3b2a1 feat: add must-win pressure adjustment to scoreline model
2ae395a data: sync June 14 match results (Haiti 0-1 Scotland, Australia 2-0 Turkey)
b445259 fix: TeamCompare watches prop changes, re-pull all wangyi tech data
37d16a5 fix: scoreline model now generates all 72 matches (was defaulting to --limit 4)
f20ee67 data: sync latest match results (Qatar 1-1 Switzerland, Brazil 1-1 Morocco)
4a66452 chore: regenerate full model predictions (enhanced + scoreline + tournament + value bets)
2acabc8 feat: sync new data tables (wangyi tech, pre-match context, match reviews, apifootball) to Postgres
284fea5 feat: add API-Football pipeline for match statistics and events
e1ac589 feat: add FIFA rank + squad features, and time-decay training weights
53b8744 feat: add FIFA rank + squad features, and time-decay training weights
58639d7 feat: add World Cup confederation bias correction
d4ad443 feat: add Elo distribution chart to model explain page
1aad6a9 feat: add sticky page navigation to MatchAnalysisPage
d7f7817 style: World Cup bold theme — dark navy base, gold accents, 11 component fixes
506a5c8 feat: add TeamCompare module — radar chart + stats cards for team strength comparison
aff7911 feat: add Superpowers and Taste skills for development workflow
5fb840a fix: remove v-if on radar section, always render to avoid chart init race condition
e0d0dae fix: use readonly types to fix TypeScript readonly mismatch in component props
4e98c1a fix: merge official results by team names instead of match_no to handle FIFA numbering mismatch
1971fe9 feat: add MatchTechRadar component, display match tech stats on analysis page
d0d34e0 feat: add MatchTechStats to API, expose match tech data in MatchDetail
76c9324 docs: add design spec for match tech stats display
332f927 feat: add Wangyi tech pipeline for match stats and player events
a4ba38f feat: add post-match review insights to HomePage
9b8d296 feat: add MatchReviewInsight component for post-match analysis
10d7b8a feat: add pre-match context and team context cards to MatchAnalysisPage
aac5dd9 feat: add TeamContextCard component for Wangyi team data display
8cd080f feat: add PreMatchContextCard component for Firecrawl news display
a165e13 feat: add TeamContext and MatchPreviewSource types, extend MatchDetail
a33d34f docs: add implementation plan for frontend preview and review display
4c0f84f docs: add frontend design spec for pre-match context and match review display
efaf726 Add Firecrawl pre-match context pipeline and integrate into scoreline model
2d14a6a Integrate Wangyi suspensions and Firecrawl setup
5515774 Add Wangyi API pipeline for coach and squad stats (P2 data collection)
4bc96eb Add prediction info to schedule, fix fixture dates, expand player/team data
c53aaa1 Expand predicted lineups for additional 2026 fixtures
c9b61db Add match review insights and scoreline combo recommendations
cd3875a Show actual results in match analysis and home cards
3ea465d Show next four unfinished matches on home page
76dfc52 Fix line length in data_store schedule list comprehension
9ce4904 Add official results sync and live schedule results
a11e2ec Add dashboard completeness insights
6de3afa Group schedule by date with completeness badges
187a14e Add dashboard data completeness API
44c855f Document dashboard next phase plan
b5b18df Add dashboard schedule and metadata
a35bc78 Add match analysis quick switcher
826056e Build dashboard API and Vue prototype
8ae0b7e Document Vue dashboard MVP plan
41aad9d Add web dashboard PRD link to README
a8cddf1 Adjust group opener scorelines for mismatch tempo
9790380 Anchor scoreline probabilities to Sporttery markets
fe593ad Use Sporttery HAD odds in enhanced predictions
3dfcb3b Add Sporttery fixed-bonus market pipeline
6c33436 Track Sporttery score odds history
1ae436c Add Sporttery score odds ingestion
43d7e84 Adjust scoreline model with predicted lineups
cf4e9d3 Add predicted lineup pipeline
5893c16 Sync odds data into Postgres
de8211e Support manual historical odds CSV imports
da47052 Add market odds backtest integration
0019393 Add World Cup backtest diagnostics
7290d78 Add World Cup backtest reports
73dc145 Add team goal form features
bcf16a0 Sync scoreline analysis to Postgres
c81751f Add Dixon-Coles scoreline correction
5f33116 Add Poisson scoreline model
22abf1b Add tournament simulation model
4d83e3e Sync enhanced predictions to Postgres
9106a13 Add enhanced model with recent form features
b7435c4 Add 2026 match feature store
d842f9e Add roster composition and schedule difficulty analysis
b324f7c Add world cup identity data to Postgres queries
0f6f3bc Add world cup identity collection pipeline
bf39ce0 Add charts to team and group reports
c57768f Add charts to research pack index
586af64 Enhance research pack index summaries
20da677 Add batch World Cup research pack generation
e4682d7 Add Markdown research report generator
d29563b Add group strength and prediction screening queries
7ba2b6d Add recent form and team-vs-field queries
ef7c3b0 Add group overview and CSV export
60e1211 Add Postgres research query tools
6a61e02 Add Postgres sync workflow
9059a0d Initial project setup and baseline pipeline 即可追踪趋势
- 网络故障时 Commit 本地保留，后续手动 push

### 集成 Skill

本工作流集成了以下子 Skill，可单独调用：

| Skill | 用途 | 调用 |
|-------|------|------|
|  | 体彩赔率录入 |  |

### 编码注意事项
- 所有 Python 输出用 `sys.stdout.reconfigure(encoding='utf-8')`
- 不要直接运行 `.py` 文件，用 `-m src.module_name`
- 测试必须 148 passed
- 不要编辑 parquet 文件，用 pipeline 更新
- 淘汰赛 xG 已内置 ×0.85 压缩
- **时区锚定**：所有时间显式声明 `Asia/Shanghai`
- **性能跳转**：当天无比赛或积分无变化时，跳过 tournament_simulator
- **数据回滚**：落库带 `fetched_at` UTC 时间戳
