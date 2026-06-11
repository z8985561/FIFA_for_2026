<script setup lang="ts">
defineProps<{
  label: string
  value: string
  hint?: string
}>()
</script>

<template>
  <article class="stat-card">
    <span class="stat-label">{{ label }}</span>
    <strong class="stat-value">{{ value }}</strong>
    <small v-if="hint" class="stat-hint">{{ hint }}</small>
  </article>
</template>

<style scoped>
.stat-card {
  padding: 20px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  background: var(--surface-glass);
  box-shadow: var(--shadow-soft);
}

.stat-label {
  display: block;
  margin-bottom: 10px;
  color: var(--color-muted);
  font-size: 13px;
}

.stat-value {
  display: block;
  color: var(--color-ink);
  font-size: clamp(24px, 4vw, 38px);
  letter-spacing: -0.04em;
}

.stat-hint {
  display: block;
  margin-top: 8px;
  color: var(--color-muted);
}
</style>
