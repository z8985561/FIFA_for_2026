<script setup lang="ts">
const navItems = [
  { path: '/', label: '总览' },
  { path: '/schedule', label: '完整赛程' },
  { path: '/matches/1', label: '比赛分析' },
  { path: '/value', label: '比分价值' },
  { path: '/groups', label: '小组出线' },
  { path: '/simulator', label: '模拟器' },
  { path: '/model', label: '模型解释' },
]
</script>

<template>
  <div class="app-shell">
    <aside class="side-nav">
      <div class="brand">
        <span class="brand-kicker">FIFA 2026</span>
        <strong>世界杯研究看板</strong>
      </div>
      <nav class="nav-list">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-link"
        >
          {{ item.label }}
        </RouterLink>
      </nav>
      <p class="compliance-note">
        仅用于概率研究与模拟复盘，不提供真实下单、支付或账户功能。
      </p>
    </aside>

    <main class="main-panel">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 280px 1fr;
  color: var(--color-ink);
}

.side-nav {
  position: sticky;
  top: 0;
  height: 100vh;
  padding: 32px 24px;
  background:
    linear-gradient(180deg, rgba(22, 45, 54, 0.94), rgba(8, 22, 28, 0.96)),
    radial-gradient(circle at top left, rgba(223, 180, 102, 0.24), transparent 34%);
  color: #f7efe0;
}

.brand {
  display: grid;
  gap: 8px;
  margin-bottom: 34px;
}

.brand-kicker {
  color: var(--color-sand);
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.brand strong {
  font-size: 25px;
  line-height: 1.15;
}

.nav-list {
  display: grid;
  gap: 10px;
}

.nav-link {
  padding: 12px 14px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 18px;
  color: rgba(255, 255, 255, 0.74);
  text-decoration: none;
}

.nav-link.router-link-active {
  color: #11272d;
  background: var(--color-sand);
  border-color: var(--color-sand);
}

.compliance-note {
  position: absolute;
  left: 24px;
  right: 24px;
  bottom: 28px;
  color: rgba(255, 255, 255, 0.58);
  line-height: 1.7;
  font-size: 13px;
}

.main-panel {
  min-width: 0;
  padding: 32px;
}

@media (max-width: 900px) {
  .app-shell {
    grid-template-columns: 1fr;
  }

  .side-nav {
    position: static;
    height: auto;
  }

  .compliance-note {
    position: static;
    margin-top: 24px;
  }

  .main-panel {
    padding: 20px;
  }
}
</style>
