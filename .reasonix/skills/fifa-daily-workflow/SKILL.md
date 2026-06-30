---
name: fifa-daily-workflow
description: FIFA 每日完整工作流：同步数据 → 运行管道 → 准确率统计 → 生成简报。一步到位。
---

## FIFA 每日工作流

### 触发条件
当用户说"同步数据"、"今日简报"、"今天比赛"、"明天预测"、"命中率"时执行。

### 步骤

#### 1. 拉取最新赛果
```bash
curl -s "https://gw.m.163.com/base/worldCup/qatar/schedule" | python -c "import sys,json;..."
```

检查是否有新完成的比赛。如果有，继续；否则跳到简报。

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

#### 6. 提交
```bash
git add -f data/processed/*.parquet reports/*.csv
git commit -m "data: sync YYYY-MM-DD"
git push
```

### 编码注意事项
- 所有 Python 输出用 `sys.stdout.reconfigure(encoding='utf-8')`
- 不要直接运行 `.py` 文件，用 `-m src.module_name`
- 测试必须 148 passed
- 不要编辑 parquet 文件，用 pipeline 更新
- 淘汰赛 xG 已内置 ×0.85 压缩，不需要再次手动调整
