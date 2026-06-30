---
name: fifa-odds-input
description: 体彩比分赔率录入：解析用户输入的赔率数据 → 保存 parquet → 重跑模型应用市场锚定
---

## 体彩赔率录入工作流

### 触发条件
用户粘贴体彩截图数据、或提供 H/D/A 概率 + 比分赔率时执行。

### 输入格式

用户通常以 Markdown 表格形式提供，包含：
- 比赛：主队 vs 客队，时间
- 胜平负初始概率：H%/D%/A%
- 比分赔率表（主胜/平局/客胜 三类）

### 步骤

#### 1. 解析数据
从用户输入中提取：
- `home_team`：英文队名（通过 `zh_team_name` 反查或直接指定）
- `away_team`：英文队名
- `home_win_prob / draw_prob / away_win_prob`：胜平负概率（小数）
- `match_date`：比赛日期

队名映射表（常用）：
```
巴西=Brazil 日本=Japan 德国=Germany 巴拉圭=Paraguay
荷兰=Netherlands 摩洛哥=Morocco 法国=France 瑞典=Sweden
墨西哥=Mexico 厄瓜多尔=Ecuador 英格兰=England 刚果金=DR Congo
比利时=Belgium 塞内加尔=Senegal 美国=United States 波黑=Bosnia and Herzegovina
西班牙=Spain 奥地利=Austria 葡萄牙=Portugal 克罗地亚=Croatia
瑞士=Switzerland 阿尔及利亚=Algeria 挪威=Norway 科特迪瓦=Ivory Coast
```

#### 2. 保存到 parquet
```python
import pandas as pd
from datetime import datetime, timezone

existing = pd.read_parquet('data/processed/sporttery_score_odds_snapshots.parquet')
now = datetime.now(timezone.utc)

# UPSERT: remove old entry for same matchup, insert new
existing = existing[~((existing['home_team']==home) & (existing['away_team']==away))]
new_row = {'home_team': home, 'away_team': away,
           'home_win_prob': hp, 'draw_prob': dp, 'away_win_prob': ap,
           'fetched_at': now, 'source': 'sporttery_score_odds',
           'match_date': match_date}
existing = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)
existing.to_parquet('data/processed/sporttery_score_odds_snapshots.parquet', index=False)
```

#### 3. 重跑模型
```bash
.venv\Scripts\python.exe -m src.scoreline_model --limit 88 --top-scores 10
```

#### 4. 验证
检查 `reports/world_cup_2026_scoreline_analysis.csv` 中 `has_market_outcome_constraint=True` 的行数是否增加。

#### 5. 反馈
输出：N 场赔率已录入，M 场已锚定到 fixtures。

### 注意事项
- 重复录入同一场比赛会自动覆盖旧数据（UPSERT）
- 如果比赛不在当前 fixtures 中（如 16 强未生成），数据仍保存但不会锚定——等 fixtures 更新后重新跑模型即可
- 比利时时区用 `Asia/Shanghai`，`match_date` 用北京日期
