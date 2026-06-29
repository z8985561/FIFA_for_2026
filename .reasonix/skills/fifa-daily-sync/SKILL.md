---
name: fifa-daily-sync
description: 每日 FIFA 世界杯数据同步流程：拉取 NetEase 赛果 → 技术统计 → 预测管道 → 数据库同步 → 提交推送
---

## 每日 FIFA 数据同步流程

按顺序执行以下步骤，每步验证后再进行下一步。

### 1. 拉取最新赛果

```bash
curl -s "https://gw.m.163.com/base/worldCup/qatar/schedule" | python -c "import sys,json; ..."
```

### 2. 同步技术统计

```bash
.venv\Scripts\python.exe -m src.wangyi_tech_pipeline
```

### 3. 更新官方赛果

用 `zh_team_name()` 映射 NetEase 中文队名 → 英文队名，更新 `data/processed/official_match_results_2026.parquet`。

⚠️ 注意 `民主刚果` → `刚果民主共和国`（DR Congo），`科特迪瓦` → `Côte d'Ivoire` 等。

### 4. 运行预测管道

```bash
.venv\Scripts\python.exe -m src.enhanced_model
.venv\Scripts\python.exe -m src.scoreline_model --limit 88 --top-scores 10
```

### 5. 锦标赛模拟 + 价值投注

```bash
.venv\Scripts\python.exe -m src.tournament_simulator --simulations 10000 --seed $(date +%Y%m%d)
.venv\Scripts\python.exe -m src.value_bets_report
```

### 6. 数据库同步

```bash
.venv\Scripts\python.exe -m src.postgres_sync
```

### 7. 准确率统计

```bash
.venv\Scripts\python.exe -c "..."  # 用 enhanced_predictions vs official_results 对比
```

### 8. 测试 + 提交

```bash
.venv\Scripts\python.exe -m pytest -q  # 必须 148 passed
git add -f data/processed/*.parquet reports/*.csv
git commit -m "data: sync YYYY-MM-DD"
git push
```

### 9. 重启 Web 服务

重启 API 和前端让新数据生效。
