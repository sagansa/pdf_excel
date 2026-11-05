import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import ConverterView from '../views/ConverterView.vue'
import HistoryView from '../views/HistoryView.vue'
import CompaniesView from '../views/CompaniesView.vue'
import MarksView from '../views/MarksView.vue'
import ChartOfAccountsView from '../views/ChartOfAccountsView.vue'
import ReportsView from '../views/ReportsView.vue'
import UploadSummaryView from '../views/UploadSummaryView.vue'
import UploadChecklistView from '../views/UploadChecklistView.vue'
import SettingsView from '../views/SettingsView.vue'
import ManagementView from '../views/ManagementView.vue'
import InitialCapitalPage from '../views/InitialCapitalPage.vue'
import GeneralLedger from '../views/GeneralLedger.vue'
import HrdView from '../views/HrdView.vue'
import LoginView from '../views/LoginView.vue'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { public: true }
    },
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
    },
    {
      path: '/chart-of-accounts',
      name: 'chart-of-accounts',
      component: ChartOfAccountsView
    },
    {
      path: '/reports',
      name: 'reports',
      component: ReportsView
    },
    {
      path: '/upload-summary',
      name: 'upload-summary',
      component: UploadSummaryView
    },
    {
      path: '/upload-checklist',
      name: 'upload-checklist',
      component: UploadChecklistView
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView
    },
    {
      path: '/management',
      name: 'management',
      component: ManagementView
    },
    {
      path: '/initial-capital',
      name: 'initial-capital',
      component: InitialCapitalPage
    },
    {
      path: '/general-ledger',
      name: 'general-ledger',
      component: GeneralLedger
    },
    {
      path: '/hrd',
      name: 'hrd',
      component: HrdView
    }
  ]
})

// Auth guard: every route except /login requires an authenticated session.
// The session lives in an HttpOnly cookie, so on first navigation (page load)
// we ask the backend who we are.
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.isAuthChecked) {
    await auth.fetchMe()
  }
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    const redirect = typeof to.query.redirect === 'string' ? to.query.redirect : '/'
    return redirect
  }
  return true
})

export default router
