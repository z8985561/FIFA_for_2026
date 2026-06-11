# 世界杯预测研究看板 PRD

## 1. 产品定位

第一期 Web 版本定位为本地运行的 2026 世界杯概率分析研究看板。它用于展示模型输出、市场赔率对比、比分推理过程、小组出线概率，以及模拟组合的收益与风险。

本产品不是博彩或购彩平台。

明确不做：

- 不提供真实彩票下单功能
- 不处理支付、账户余额、彩票订单或出票流程
- 不提供任何跳转真实购买的链接或按钮
- 不保存用户真实投注记录

模拟器仅用于基于用户选择的虚拟组合，进行概率、理论返奖和风险分析。

## 2. 第一期目标

- 让现有模型结果可以通过 Web 页面浏览。
- 解释得分比概率是如何一步一步形成的。
- 对比模型概率与中国体育彩票赔率。
- 展示 48 支球队的小组赛出线概率。
- 提供虚拟组合模拟器，用于研究和风险教育。
- 第一期所有数据只读，不触发新的数据采集。

## 3. 核心页面

### 3.1 首页总览

目标：快速展示当前模型状态和重点结论。

展示内容：

- 重点比赛列表
- 每场比赛 Top 3 得分比概率
- 最高价值比分信号
- 小组出线概率摘要
- 模型和数据更新时间
- 数据来源摘要

核心组件：

- 比赛卡片
- 价值比分列表
- 小组出线迷你排行
- 模型健康状态区块

### 3.2 比赛分析页

目标：深入查看单场比赛。

展示内容：

- 比赛基础信息：中文队名、英文队名、小组、开赛时间、场地
- 胜平负概率
- Top 10 精确比分概率
- 体彩比分赔率
- 模型公平赔率
- 市场边际
- Kelly 比例
- 影响因素拆解

影响因素包括：

- 基础 Poisson 预期进球
- 预计阵容修正
- 小组首轮强弱局节奏修正
- Dixon-Coles 低比分修正
- 体彩胜平负市场约束
- 体彩总进球市场约束

可视化要求：

- 使用 ECharts 瀑布图展示每一个修正因子如何把基础预期逐步推向最终比分或边际概率。
- 图表旁边提供简短文字解释，方便非技术用户理解。

### 3.3 小组出线页

目标：展示小组赛晋级路径。

每支球队展示字段：

- 小组第一概率
- 小组前二概率
- 第三名晋级概率
- 总进入 32 强概率
- 未出线概率

交互要求：

- 支持按小组筛选
- 支持按总出线概率排序
- 高亮竞争最激烈的小组
- 第三名晋级概率需要提供 Tooltip 说明：
  “2026 赛制为 12 个小组，每组前两名直接晋级，另外 8 支成绩最好的小组第三名晋级。该概率通过跨组模拟计算得出。”

### 3.4 比分价值页

目标：分析模型与市场赔率之间的分歧。

表格字段：

- 比赛
- 比分
- 模型概率
- 模型公平赔率
- 体彩赔率
- 市场原始隐含概率
- 比分市场去水后概率
- 市场边际
- Kelly 比例
- 信号类型：`strong_value`、`thin_value`、`no_value`、`missing_odds`

交互要求：

- 支持按比赛筛选
- 支持按信号类型筛选
- 支持按市场边际、模型概率、Kelly 比例排序
- 页面明确提示：价值信号是模型诊断结果，不构成购彩建议

### 3.5 虚拟组合模拟器

目标：对用户选择的虚拟组合进行理论返奖和风险模拟。

该功能仅用于研究，不做真实下单，也不连接任何真实购买流程。

第一期支持玩法：

- 单关
- 2串1
- 4串1

输入项：

- 模拟预算
- 组合类型
- 选择的比赛和比分
- 每注金额，默认 2 元

输出项：

- 注数
- 模拟总投入
- 理论最低返奖
- 理论最高返奖
- 每个组合的模型命中概率
- 期望收益
- 模拟风险评级

风险评级：

- 低风险：命中概率相对更高，理论返奖区间较低
- 中风险：命中概率和返奖区间相对均衡
- 高风险：命中概率低或理论返奖波动较大
- 极高风险：命中概率极低，通常由高赔冷门精确比分驱动

第一期风险评级采用启发式规则，不使用复杂方差模型或破产风险模型。核心计算公式：

```text
单组合命中概率 = 组合内每个比分模型概率的乘积
单组合赔率 = 组合内每个比分体彩赔率的乘积
单组合理论返奖 = 单组合赔率 × 每注金额
单组合期望返奖 = 单组合命中概率 × 单组合理论返奖
总期望返奖 = Σ 单组合期望返奖
期望净收益 = 总期望返奖 - 模拟总投入
```

组合整体命中概率第一期采用独立事件近似：

```text
总命中概率 ≈ 1 - Π(1 - 单组合命中概率)
```

模型限制说明：

- 该公式假设不同组合之间近似独立，但真实组合通常会共享比赛或比分，因此严格数学意义上并不完全独立。
- 第一期总命中概率主要用于启发式风险分层，不代表严谨的联合概率分布。
- 后续版本可以基于蒙特卡洛或精确互斥事件枚举优化该指标。

第一期建议风险阈值：

| 风险等级 | 建议规则 |
|---|---|
| 低风险 | 总命中概率 ≥ 5%，且最大返奖 / 总投入 < 20 |
| 中风险 | 总命中概率 ≥ 1%，且最大返奖 / 总投入 < 100 |
| 高风险 | 总命中概率 ≥ 0.2%，或最大返奖 / 总投入 < 1000 |
| 极高风险 | 总命中概率 < 0.2%，或最大返奖 / 总投入 ≥ 1000 |

API 需要同时返回 `risk_score`、`risk_rating` 和 `risk_reasons`，前端必须展示风险原因，避免风险评级变成黑盒。

必须展示的免责声明：

```text
本模拟器仅用于概率与理论返奖研究，不提供真实下单功能，也不构成购彩建议。
```

### 3.6 模型解释页

目标：说明模型是如何工作的。

展示内容：

- 数据来源
- 模型链路
- 当前特征组
- 得分比修正层
- 当前限制
- 风险与不确定性说明

模型链路：

```text
历史国家队比赛
-> Elo / FIFA 排名 / 近期状态 / 阵容上下文
-> Poisson 预期进球
-> 阵容修正
-> 小组首轮强弱局节奏修正
-> Dixon-Coles 低比分修正
-> 体彩胜平负 / 总进球市场约束
-> 最终得分比概率
```

## 4. API 需求

第一期 API 以只读为主。唯一的 `POST` 接口是虚拟组合模拟器，用于无状态计算，不保存用户输入。

接口列表：

```text
GET /api/health
GET /api/matches
GET /api/matches/{match_no}
GET /api/matches/{match_no}/scorelines
GET /api/matches/{match_no}/explanation
GET /api/value-bets
GET /api/groups/advance-probabilities
GET /api/model/metadata
POST /api/simulator/settle
```

### 4.1 模拟器请求 Schema

```json
{
  "budget": 20,
  "stake_per_combination": 2,
  "bet_type": "2x1",
  "legs": [
    {
      "match_no": 1,
      "scorelines": ["2-0", "3-0"]
    },
    {
      "match_no": 2,
      "scorelines": ["1-1"]
    }
  ]
}
```

校验规则：

- `budget` 必须大于 0。
- `stake_per_combination` 必须大于 0。
- `bet_type` 只能是 `single`、`2x1`、`4x1`。
- `legs` 必须包含所选组合类型需要的不同比赛数量。
- 用户选择的比分必须存在于当前比分概率和赔率数据中。
- 模拟总投入不能超过预算，除非后续版本明确支持自动裁剪组合。

### 4.2 模拟器响应 Schema

```json
{
  "bet_type": "2x1",
  "budget": 20,
  "stake_per_combination": 2,
  "combination_count": 10,
  "total_stake": 20,
  "min_payout": 58.0,
  "max_payout": 3900.0,
  "expected_return": 12.8,
  "expected_net_return": -7.2,
  "estimated_hit_probability": 0.032,
  "payout_spread_ratio": 67.24,
  "risk_score": 86,
  "risk_rating": "High",
  "risk_reasons": [
    "总命中概率低于5%",
    "最大返奖超过总投入100倍",
    "组合包含多个高赔率精确比分"
  ],
  "combinations": [
    {
      "legs": [
        {"match_no": 1, "scoreline": "2-0"},
        {"match_no": 2, "scoreline": "1-1"}
      ],
      "combined_probability": 0.01656,
      "combined_odds": 29.68,
      "payout": 59.36,
      "expected_return": 0.98
    }
  ],
  "disclaimer": "本模拟器仅用于概率与理论返奖研究，不提供真实下单功能，也不构成购彩建议。"
}
```

## 5. 数据来源

第一期只读取已有本地模型输出，不触发新的数据采集。

主要文件：

- `reports/world_cup_2026_scoreline_analysis.csv`
- `reports/scoreline_value_bets.csv`
- `reports/world_cup_2026_enhanced_predictions.csv`
- `reports/world_cup_2026_tournament_simulation.csv`
- `reports/world_cup_2026_group_advance_probabilities.csv`
- `data/processed/score_odds_snapshots.parquet`
- `data/processed/sporttery_market_odds_snapshots.parquet`
- `data/features/match_feature_store_2026.parquet`

### 5.1 模拟器基准测试集

第一期后端应提供一份固定的模拟器基准测试集，用于校准风险评级阈值和保证回归测试稳定。

建议文件：

- `tests/fixtures/simulator_benchmark_cases.json`

基准测试集至少覆盖以下场景：

- 单关高概率比分：验证低风险或中风险边界
- 单关高赔率冷门比分：验证高风险边界
- 20 元 2串1 偏稳组合：验证中高风险边界
- 20 元 2串1 高赔率价值组合：验证高风险或极高风险
- 50 元 4串1 多注覆盖组合：验证极高风险和返奖跨度
- 包含缺失赔率的组合：验证 `missing_odds` 处理
- 超预算组合：验证预算校验失败

每个测试用例建议包含：

```json
{
  "case_id": "two_combo_balanced_20",
  "description": "20元2串1偏稳组合",
  "request": {
    "budget": 20,
    "stake_per_combination": 2,
    "bet_type": "2x1",
    "legs": [
      {"match_no": 1, "scorelines": ["2-0", "3-0"]},
      {"match_no": 2, "scorelines": ["1-1"]},
      {"match_no": 7, "scorelines": ["2-0"]}
    ]
  },
  "expected": {
    "min_risk_rating": "Medium",
    "max_risk_rating": "High",
    "max_total_stake": 20,
    "requires_risk_reasons": true
  }
}
```

该测试集不用于预测真实结果，只用于验证模拟器计算逻辑、风险评级边界和前后端展示一致性。

## 6. 后端架构

推荐后端技术栈：

- FastAPI
- Pydantic
- Pandas
- PyArrow

性能要求：

- 使用 FastAPI lifespan 在服务启动时一次性加载 CSV 和 Parquet 文件到内存。
- API 处理函数从内存中的 DataFrame 或字典读取数据。
- 后续版本可增加手动 reload 能力，但第一期不需要实时刷新。

建议目录结构：

```text
api/
  main.py
  data_store.py
  schemas.py
  services/
    matches.py
    groups.py
    simulator.py
```

## 7. 前端架构

推荐前端技术栈：

- Vue 3
- Vite
- TypeScript
- Vue Router
- Pinia
- ECharts
- Element Plus

体验方向：

- 分析优先，而不是投注优先
- 默认显示中文队名，英文队名作为辅助信息
- 支持桌面端和基础移动端响应式布局
- 在比分价值页和模拟器页清晰展示模型免责声明

Vue 约定：

- 全部业务组件使用 Composition API 和 `<script setup lang="ts">`。
- 路由级页面只负责页面编排，具体图表、表格、模拟器表单拆成独立组件。
- 跨页面共享状态放入 Pinia，页面内局部派生数据优先使用 `computed`。
- API 调用封装在 `services/` 或 `composables/` 中，避免直接散落在组件模板里。
- 图表组件统一封装 ECharts 初始化、resize、销毁和空状态展示。
- 小组长表格、比分长列表等高密度区域预留虚拟滚动或分页能力。
- 大型图表、低频页面和重组件优先使用异步组件按需挂载。
- 只读的大型元数据字典使用 `shallowRef`、冻结对象或模块常量，避免深层响应式代理。

视觉约定：

- 基于 Element Plus 做二次主题定制，不直接使用默认后台管理模板视觉。
- 使用全局 Design Tokens 管理颜色、圆角、阴影、间距、字体层级和图表语义色。
- 看板整体采用研究报告风格：充足留白、清晰表格密度、弱化博彩站点视觉暗示。
- 概率、风险、价值信号不能只依赖红绿颜色，必须同时有文字标签或图标说明。

异常与边界状态：

- 所有接口请求必须提供加载态、错误态和空状态。
- 体彩赔率缺失时展示 `暂未获取赔率`，仍保留模型概率和公平赔率。
- 数据快照时间必须展示在赔率、价值信号和模拟器结果附近。
- 模拟器增删比分选项时对结算请求做防抖，并展示明确的计算中状态。
- API 返回字段缺失或模型版本不一致时，前端应降级展示而不是页面崩溃。

建议 Pinia Store：

- `useMatchStore`：比赛列表、当前比赛、前四场重点比赛。
- `useGroupStore`：小组积分、出线概率、第三名横向排名。
- `useSimulatorStore`：虚拟组合选择、预算、串关类型、模拟结果。
- `useModelMetadataStore`：模型版本、数据快照时间、免责声明配置。

建议 Composables / Services：

- `useMatches`：读取比赛列表和比赛详情。
- `useScorelines`：读取比分概率、体彩赔率、价值信号。
- `useGroups`：读取小组出线概率和小组强度。
- `useSimulator`：提交虚拟组合并接收风险评级。
- `useModelExplain`：读取影响因素瀑布图和模型解释数据。

建议目录结构：

```text
web/
  src/
    main.ts
    App.vue
    router/
    stores/
    pages/
    components/
      match/
      group/
      simulator/
      common/
    composables/
    services/
    charts/
    types/
    styles/
```

## 8. 第一期验收标准

功能验收：

- Web 应用可以在本地启动。
- 用户可以看到中文球队名和重点比赛。
- 用户可以打开比赛详情页查看 Top 10 得分比概率。
- 用户可以查看体彩赔率、模型公平赔率、市场边际和信号类型。
- 用户可以查看全部小组出线概率。
- 用户可以查看“墨西哥 vs 南非”的完整推理链路。
- 用户可以使用 20 元或 50 元预算做虚拟组合模拟。
- 模拟器展示总投入、理论返奖区间、期望收益和风险评级。

合规与安全验收：

- 不存在真实下单功能。
- 不存在支付或账户功能。
- 模拟器页面明确声明不构成购彩建议。

技术验收：

- 后端启动时将数据加载到内存。
- API 返回 JSON，并由 Pydantic Schema 约束。
- 首页、比赛详情页、小组表格页、模拟器页在移动端基础可用。
- 打开 Web 应用不会触发新的数据采集。

## 9. 第一期开发顺序

1. 搭建 FastAPI 后端和内存数据仓库。
2. 实现 Pydantic Schema。
3. 实现比赛、比分、小组、价值信号等只读接口。
4. 实现模拟器计算接口。
5. 搭建 Vue 3/Vite/TypeScript 前端，配置 Vue Router、Pinia 和 Element Plus。
6. 实现首页总览。
7. 实现带瀑布图的比赛分析页。
8. 实现带第三名晋级 Tooltip 的小组出线页。
9. 实现比分价值页。
10. 实现虚拟组合模拟器页。
11. 实现模型解释页。
12. 验证响应式布局。
13. 使用浏览器进行本地 QA。
14. 提交代码并推送远端。

## 10. 后续版本方向

- 赔率变化趋势图
- 模型版本对比
- 天气和裁判特征
- 伤停和新闻特征层
- 历史回测可视化
- 可配置模拟策略
- 可下载研究报告
