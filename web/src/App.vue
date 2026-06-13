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
        <span class="brand-kicker">FIFA WORLD CUP 2026</span>
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
  grid-template-columns: 260px 1fr;
  color: var(--color-ink);
}

.side-nav {
  position: sticky;
  top: 0;
  height: 100vh;
  padding: 30px 22px;
  background: #081220;
  border-right: 1px solid rgba(212, 168, 67, 0.12);
  color: #c8d0d8;
}

.brand {
  display: grid;
  gap: 8px;
  margin-bottom: 32px;
}

.brand-kicker {
  color: var(--color-accent);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.22em;
}

.brand strong {
  font-size: 22px;
  font-weight: 800;
  line-height: 1.2;
  color: #e8e0d0;
}

.nav-list {
  display: grid;
  gap: 6px;
}

.nav-link {
  padding: 10px 14px;
  border: 1px solid rgba(212, 168, 67, 0.1);
  border-radius: 10px;
  color: #8899aa;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.15s;
}

.nav-link:hover {
  color: #d4a843;
  border-color: rgba(212, 168, 67, 0.25);
}

.nav-link.router-link-active {
  color: #0a1628;
  background: linear-gradient(135deg, #d4a843, #c4942e);
  border-color: #d4a843;
  font-weight: 700;
}

.compliance-note {
  position: absolute;
  left: 22px;
  right: 22px;
  bottom: 24px;
  color: rgba(200, 208, 216, 0.4);
  line-height: 1.6;
  font-size: 12px;
}

.main-panel {
  min-width: 0;
  padding: 28px;
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
    margin-top: 20px;
  }

  .main-panel {
    padding: 18px;
  }
}
</style>
