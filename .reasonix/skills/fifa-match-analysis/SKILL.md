---
name: fifa-match-analysis
description: FIFA 比赛预测分析：明日赛程、比分 Top 10、赔率对比、准确率统计
---

## 比赛分析与预测简报工作流

当用户请求"明天什么比赛"、"预测分析"、"命中率"时使用。

### 明天赛程

```python
from datetime import datetime, timezone, timedelta
now_bj = datetime.now(timezone.utc) + timedelta(hours=8)
tomorrow = (now_bj + timedelta(days=1)).strftime('%Y-%m-%d')
fixtures = pd.read_parquet('data/processed/fixtures_2026.parquet')
tomorrow_matches = fixtures[fixtures['date_bj'].astype(str).str[:10] == tomorrow]
```

### 比分预测

优先使用 `reports/world_cup_2026_scoreline_analysis.csv`（含完整模型）。淘汰赛降级用 Elo 简化版（xG × 0.85）。

### 市场赔率对比

读取 `data/processed/sporttery_score_odds_snapshots.parquet`，与 Elo 模型对比。

### 准确率统计

用 `enhanced_predictions.csv` vs `official_match_results_2026.parquet` 统计：
- 胜平负命中率
- Top1/3/5/10 比分命中率
- 按轮次拆分统计

### 简报格式

```
=== 6/30 赛果 ===
✅ #74 巴西 2-0 日本 (预测主胜 61%)

=== 6/30 预测准确率 ===
胜平负 1/1=100% | Top3 1/1=100%

=== 明日赛程 (7/1) ===
#77 法国 vs 瑞典  xG 1.59-0.62  主胜 79%  1-0(17.4%)·2-0(13.8%)·2-1(8.6%)
```

### 输出要求

- 简洁、直接
- 表格形式优先
- 关键偏差标注 🔴⚠️
