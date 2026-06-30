---
name: fifa-backtest
description: FIFA 预测模型回测：准确率统计、校准曲线、投注价值评估、风险指标。借鉴量化分析师方法论。
---

## FIFA 预测回测与风险评估

### 触发条件
用户说"回测"、"准确率评估"、"风险评估"、"投注分析"时执行。

### 角色
FIFA 预测模型量化分析师。基于历史预测 vs 实际赛果，评估模型质量、计算风险指标、识别投注价值。

### 核心指标

| 指标 | 公式 | 基准 |
|------|------|------|
| 胜平负准确率 | 正确 / 总数 | > 55% 优秀 |
| Top3 比分命中率 | Top3 命中 / 总数 | > 30% 优秀 |
| 平均比分排名 | 实际比分在预测中的平均排名 | < 5 优秀 |
| 预测信心校准 | 各概率档位实际频率 vs 理论频率 | 偏离 < 10% |
| 市场偏差度 | 模型预测 vs 体彩市场概率的平均差异 | |
| 投注价值分 | Σ(模型概率 - 市场概率) × 正边际 的比赛数 | > 0 有正向收益 |

### 执行步骤

#### 1. 加载数据
```python
import pandas as pd
off = pd.read_parquet('data/processed/official_match_results_2026.parquet')
ep = pd.read_csv('reports/world_cup_2026_enhanced_predictions.csv')
sa = pd.read_csv('reports/world_cup_2026_scoreline_analysis.csv')
comp = off[off['completed'] == True]
```

#### 2. 按轮次统计
```python
# 小组赛 (round 1-3) vs 淘汰赛 (round 4+)
for stage in ['Group', 'Knockout']:
    # Filter, compute accuracy metrics
```

#### 3. 校准曲线
按预测概率分档（0-10%, 10-20%...），统计各档实际胜率。

#### 4. 投注价值
```python
# 读取市场赔率
so = pd.read_parquet('data/processed/sporttery_score_odds_snapshots.parquet')
# 对比模型概率 vs 市场隐含概率
# edge = model_prob - market_implied
# positive_edge_matches = edge > 0
```

#### 5. 输出报告

```
=== FIFA 2026 预测模型回测报告 ===
评估场次: N | 日期范围: YYYY-MM-DD ~ YYYY-MM-DD

胜平负准确率: XX% (N/M)
Top3 比分命中率: XX%
平均比分排名: X.X

按阶段:
  小组赛: 胜平负 XX% | Top3 XX%
  淘汰赛: 胜平负 XX% | Top3 XX%

校准度: 预测高概率(>60%)的比赛实际胜率 XX%
市场偏差: 模型平均比市场乐观/保守 X%

投注价值:
  正边际场次: N | 平均边际: X.X%
  理论收益率: +X.X%（仅参考）

风险提示:
  - 平局预测精度: XX%（实际平局率 XX%）
  - 大比分盲区: N 场掉出 Top10
```

### 风险警告
- 回测不代表未来表现
- 足球比赛高度随机，样本量 (N<100) 统计显著性有限
