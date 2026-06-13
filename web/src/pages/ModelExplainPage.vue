<script setup lang="ts">
import EloChart from '@/components/common/EloChart.vue'

const modelLayers = [
  {
    title: '1. 实力基准层',
    tag: 'Elo / FIFA / 近期状态',
    body: '先用球队长期强度、FIFA 排名、近期胜率和净胜球趋势建立基础强弱差。这个阶段回答的是：如果不考虑赔率和阵容，哪支球队更强。',
  },
  {
    title: '2. 比分生成层',
    tag: 'Dixon-Coles',
    body: '用修正泊松模型生成 0-0、1-0、1-1 等精确比分概率，并对低比分相关性做修正，避免把双方进球当成完全独立事件。',
  },
  {
    title: '3. 阵容与节奏层',
    tag: 'Lineup / Group Opener',
    body: '根据预测首发、关键球员和小组首战强弱差，调整双方期望进球。比如强队面对弱队时，首战可能更主动争取净胜球。',
  },
  {
    title: '4. 市场校准层',
    tag: 'Odds Constraint',
    body: '接入体彩与国际赔率快照，把市场共识作为外部信息源。赔率不会直接替代模型，但会帮助识别轮换、伤停、战意等模型难捕捉因素。',
  },
  {
    title: '5. 风险解释层',
    tag: 'Simulator Heuristic',
    body: '模拟器使用命中概率、理论返奖跨度、高赔率组合数量和预算约束给出风险评级，并返回白盒化原因。',
  },
]

const limitations = [
  '当前比分概率按 90 分钟常规时间口径理解，不包含加时赛和点球大战。',
  '前四场赔率数据来自当前已入库快照，赔率会随时间变化，复盘时必须看快照时间。',
  '虚拟组合的总命中概率采用独立事件近似，用于风险分层，不是严格联合概率。',
  '模型不会考虑真实下单、资金账户、支付或任何购彩流程。',
]
</script>

<template>
  <section class="page-stack">
    <header class="page-heading">
      <span class="eyebrow">Model Explainability</span>
      <h1>模型是怎么一步步推理的</h1>
      <p>
        这个页面把“黑盒概率”拆成可解释链路：实力基准、比分生成、阵容节奏、赔率校准和风险解释。
      </p>
    </header>

    <section class="explain-grid">
      <article v-for="layer in modelLayers" :key="layer.title" class="layer-card">
        <span>{{ layer.tag }}</span>
        <h2>{{ layer.title }}</h2>
        <p>{{ layer.body }}</p>
      </article>
    </section>

    <section class="section-card">
      <div class="section-title">
        <h2>一个比分概率如何形成</h2>
        <span>以墨西哥 vs 南非为例</span>
      </div>
      <ol class="reason-flow">
        <li>
          <strong>基础强度：</strong>
          墨西哥 Elo、排名和阵容经验占优，基础胜率高于南非。
        </li>
        <li>
          <strong>期望进球：</strong>
          Dixon-Coles 把强弱差转换为主客队期望进球，再生成完整比分矩阵。
        </li>
        <li>
          <strong>小组首战：</strong>
          强队首战若面对弱队，模型会温和提高热门方进攻节奏，解释 2-0、3-0 这类比分上升。
        </li>
        <li>
          <strong>市场对照：</strong>
          体彩赔率进入价值计算，若模型概率高于市场隐含概率，就形成正向市场边际。
        </li>
        <li>
          <strong>风险输出：</strong>
          模拟器不会告诉你“买什么”，只告诉你组合命中概率、返奖跨度和风险原因。
        </li>
      </ol>
    </section>

    <EloChart />

    <section class="section-card">
      <div class="section-title">
        <h2>边界与限制</h2>
        <span>研究看板不是下单工具</span>
      </div>
      <ul class="limitation-list">
        <li v-for="item in limitations" :key="item">{{ item }}</li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.explain-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
}

.layer-card {
  min-height: 260px;
  padding: 22px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-xl);
  background:
    var(--surface-glass);
  box-shadow: var(--shadow-soft);
}

.layer-card span {
  color: var(--color-accent);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.layer-card h2 {
  margin: 18px 0 12px;
  font-size: 22px;
}

.layer-card p,
.reason-flow,
.limitation-list {
  color: var(--color-muted);
  line-height: 1.8;
}

.reason-flow,
.limitation-list {
  display: grid;
  gap: 12px;
  margin: 0;
}

@media (max-width: 1200px) {
  .explain-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .explain-grid {
    grid-template-columns: 1fr;
  }
}
</style>
