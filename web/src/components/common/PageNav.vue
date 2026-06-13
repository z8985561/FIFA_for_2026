<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

interface NavItem {
  id: string
  label: string
}

const props = defineProps<{
  items: NavItem[]
}>()

const activeId = ref('')

function scrollTo(id: string) {
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

let observer: IntersectionObserver | null = null

onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          activeId.value = entry.target.id
        }
      }
    },
    { rootMargin: '-10% 0px -70% 0px' },
  )
  for (const item of props.items) {
    const el = document.getElementById(item.id)
    if (el) observer.observe(el)
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
})
</script>

<template>
  <nav v-if="props.items.length" class="page-nav">
    <span class="nav-label">本页导航</span>
    <ul>
      <li v-for="item in props.items" :key="item.id">
        <a
          :class="{ active: activeId === item.id }"
          href="javascript:void(0)"
          @click="scrollTo(item.id)"
        >
          {{ item.label }}
        </a>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.page-nav {
  position: sticky;
  top: 100px;
  padding: 16px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  background: var(--surface-glass);
}

.nav-label {
  display: block;
  margin-bottom: 10px;
  color: var(--color-accent);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 4px;
}

a {
  display: block;
  padding: 6px 10px;
  color: var(--color-muted);
  text-decoration: none;
  font-size: 13px;
  border-radius: 6px;
  transition: all 0.15s;
}

a:hover,
a.active {
  color: var(--color-accent);
  background: rgba(212, 168, 67, 0.08);
}

@media (max-width: 1280px) {
  .page-nav {
    display: none;
  }
}
</style>
