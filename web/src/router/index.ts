import { createRouter, createWebHistory } from 'vue-router'

import GroupAdvancePage from '@/pages/GroupAdvancePage.vue'
import HomePage from '@/pages/HomePage.vue'
import MatchAnalysisPage from '@/pages/MatchAnalysisPage.vue'
import TeamPage from '@/pages/TeamPage.vue'
import ModelExplainPage from '@/pages/ModelExplainPage.vue'
import SchedulePage from '@/pages/SchedulePage.vue'
import SimulatorPage from '@/pages/SimulatorPage.vue'
import ScorelineValuePage from '@/pages/ScorelineValuePage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomePage },
    { path: '/schedule', component: SchedulePage },
    { path: '/matches/:matchNo', component: MatchAnalysisPage },
    { path: '/value', component: ScorelineValuePage },
    { path: '/groups', component: GroupAdvancePage },
    { path: '/simulator', component: SimulatorPage },
    { path: '/model', component: ModelExplainPage },
  { path: '/team/:teamName', component: TeamPage },
  ],
})

export default router
