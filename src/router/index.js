import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import ConverterView from '../views/ConverterView.vue'
import HistoryView from '../views/HistoryView.vue'
import CompaniesView from '../views/CompaniesView.vue'
import MarksView from '../views/MarksView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: Dashboard
    },
    {
      path: '/converter',
      name: 'converter',
      component: ConverterView
    },
    {
      path: '/history',
      name: 'history',
      component: HistoryView
    },
    {
      path: '/companies',
      name: 'companies',
      component: CompaniesView
    },
    {
      path: '/marks',
      name: 'marks',
      component: MarksView
    }
    // Add other routes here later
  ]
})

export default router
