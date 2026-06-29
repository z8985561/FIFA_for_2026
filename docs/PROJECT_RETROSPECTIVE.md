# FIFA 2026 世界杯预测系统 — 项目沉淀

> 最后更新：2026-06-29 | 累计 66+ 场小组赛完赛 | 淘汰赛进行中

## 1. 模型优化清单

### ✅ 已实施

| 优化 | 文件 | 效果 |
|------|------|------|
| 平局按轮次上调（R1×1.8, R2×1.3） | `scoreline_model.py` | 胜平负 31%→62% |
| 首战节奏 Elo 上限 300 | `scoreline_model.py` | 德国 xG 3.94→3.77 |
| 淘汰赛 xG 压缩 ×0.85 | `scoreline_model.py` | 大比分概率下降 |
| 出线压力因子 | `scoreline_model.py` | 落后强队 +15% 预期进球 |
| 淘汰赛对阵生成 | `gen_bracket.py` | 从小组结果自动生成 32 强对阵 |

### 🔴 待实施

| 优先级 | 任务 | 预期效果 |
|--------|------|----------|
| **P0** | 淘汰赛市场赔率约束集成 | 体彩数据已有 9 场，未接入模型 |
| **P0** | 淘汰赛比分特征工程 | 当前 Elo 简化版，需完整特征 |
| **P1** | 自动准确率追踪面板 | 按轮次统计胜平负/Top3/Top10 |
| **P1** | 实时赔率抓取管道 | sporttery WAF 需绕过 |
| **P2** | 加时赛/点球概率 | 淘汰赛 90 分钟平局后概率 |
| **P2** | 球员事件模型 | 3383 条事件可用于红黄牌/停赛预测 |

---

## 2. 每日工作流（Daily Workflow）

```bash
# Step 1: 同步比赛数据
.venv\Scripts\python.exe -m src.wangyi_tech_pipeline

# Step 2: 更新官方赛果
.venv\Scripts\python.exe -c "..." # 从 NetEase API 同步到 official_results parquet

# Step 3: 跑预测流水线
.venv\Scripts\python.exe -m src.enhanced_model
.venv\Scripts\python.exe -m src.scoreline_model --limit 88 --top-scores 10

# Step 4: 锦标赛模拟
.venv\Scripts\python.exe -m src.tournament_simulator --simulations 10000

# Step 5: 价值投注
.venv\Scripts\python.exe -m src.value_bets_report

# Step 6: 同步数据库
.venv\Scripts\python.exe -m src.postgres_sync

# Step 7: 提交
git add -f data/processed/*.parquet reports/*.csv
git commit -m "data: sync $(date +%Y-%m-%d)"
git push
```

### 赔率同步

```bash
# 体彩赔率（国内）
.venv\Scripts\python.exe -m src.sporttery_market_odds_pipeline --limit 88

# 比分赔率（从用户截图手动录入 → data/processed/sporttery_score_odds_snapshots.parquet）

# 国际赔率
.venv\Scripts\python.exe -m src.odds_pipeline
```

---

## 3. 系统架构

```
┌─────────────────────────────────────────────────┐
│                  数据源                           │
│  NetEase API │ Sporttery │ The Odds API │ Wikipedia │
└─────────────────┬───────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────┐
│              Python 管道 (src/)                    │
│  wangyi_pipeline  odds_pipeline  scoreline_model  │
│  enhanced_model   tournament_simulator             │
│  postgres_sync    value_bets_report               │
└─────────┬───────────────────────────┬───────────┘
          ▼                           ▼
┌─────────────────────┐   ┌─────────────────────┐
│   PostgreSQL (Docker)│   │   Parquet/CSV 文件   │
│   33 tables         │   │  data/processed/     │
│   research schema   │   │  reports/            │
└──────────┬──────────┘   └──────────┬──────────┘
           ▼                          ▼
┌─────────────────────┐   ┌─────────────────────┐
│   FastAPI (Python)  │   │   Vue 3 (Vite)      │
│   api/main.py       │◄──│   web/src/          │
│   :8000             │   │   :5173             │
└─────────────────────┘   └─────────────────────┘
```

---

## 4. 快速启动

```bash
# Docker 服务
docker compose up -d postgres app

# API
.venv\Scripts\python.exe -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

# 前端
cd web && npm run dev

# 测试
.venv\Scripts\python.exe -m pytest -q

# 构建前端
cd web && npm run build
```

---

## 5. 关键文件索引

| 路径 | 用途 |
|------|------|
| `src/scoreline_model.py` | 比分概率模型（1740+ 行，核心） |
| `src/enhanced_model.py` | 胜平负预测 |
| `src/tournament_simulator.py` | 蒙特卡洛锦标赛模拟 |
| `api/data_store.py` | FastAPI 数据聚合（1550+ 行） |
| `api/main.py` | API 路由 |
| `web/src/pages/` | 8 个 Vue 页面 |
| `web/src/components/match/` | 11 个比赛组件 |
| `data/processed/fixtures_2026.parquet` | 赛程（含淘汰赛对阵） |
| `data/processed/official_match_results_2026.parquet` | 官方赛果 |
| `data/processed/sporttery_score_odds_snapshots.parquet` | 体彩比分赔率 |
| `reports/odds_probability_comparison.csv` | 赔率-概率对比表 |

---

## 6. 注意事项

- **不要手动编辑 parquet 文件**，用管道更新
- **official_results 和 fixtures 的 match_no 不一致**——用 `zh_team_name()` 映射
- **NetEase API 用中文队名**，如 "民主刚果" ≠ "刚果民主共和国"
- **淘汰赛预测需要特征工程**——当前用 Elo 简化版
- **体彩 API 有 WAF**——当前从截图手动录入赔率
- **测试 148 条必须全部通过再提交**
