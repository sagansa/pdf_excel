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
import BalanceCheckView from '../views/BalanceCheckView.vue'
import TrialBalanceView from '../views/TrialBalanceView.vue'
import AiReviewView from '../views/AiReviewView.vue'
import HrdView from '../views/HrdView.vue'
import LoginView from '../views/LoginView.vue'
import ForgotPasswordView from '../views/ForgotPasswordView.vue'
import ResetPasswordView from '../views/ResetPasswordView.vue'
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
      path: '/forgot-password',
      name: 'forgot-password',
      component: ForgotPasswordView,
      meta: { public: true }
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: ResetPasswordView,
      meta: { public: true }
    },
    {
      path: '/',
      name: 'dashboard',
      component: Dashboard,
      meta: { title: 'Dashboard Overview' }
    },
    {
      path: '/converter',
      name: 'converter',
      component: ConverterView,
      meta: { title: 'Bank Statement Converter' }
    },
    {
      path: '/history',
      name: 'history',
      component: HistoryView,
      meta: { title: 'Transaction History' }
    },
    {
      path: '/companies',
      name: 'companies',
      component: CompaniesView,
      meta: { title: 'Company Management' }
    },
    {
      path: '/marks',
      name: 'marks',
      component: MarksView,
      meta: { title: 'Mark Management' }
    },
    {
      path: '/chart-of-accounts',
      name: 'chart-of-accounts',
      component: ChartOfAccountsView,
      meta: { title: 'Chart of Accounts' }
    },
    {
      path: '/reports',
      name: 'reports',
      component: ReportsView,
      meta: { title: 'Financial Reports' }
    },
    {
      path: '/upload-summary',
      name: 'upload-summary',
      component: UploadSummaryView,
      meta: { title: 'Upload Summary' }
    },
    {
      path: '/upload-checklist',
      name: 'upload-checklist',
      component: UploadChecklistView,
      meta: { title: 'Upload Checklist' }
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
      meta: { title: 'System Settings' }
    },
    {
      path: '/management',
      name: 'management',
      component: ManagementView,
      meta: { title: 'Locations & Stores' }
    },
    {
      path: '/initial-capital',
      name: 'initial-capital',
      component: InitialCapitalPage,
      meta: { title: 'Initial Capital' }
    },
    {
      path: '/general-ledger',
      name: 'general-ledger',
      component: GeneralLedger,
      meta: { title: 'General Ledger' }
    },
    {
      path: '/balance-check',
      name: 'balance-check',
      component: BalanceCheckView,
      meta: { title: 'Cek Kontinuitas Saldo' }
    },
    {
      path: '/trial-balance',
      name: 'trial-balance',
      component: TrialBalanceView,
      meta: { title: 'Trial Balance' }
    },
    {
      path: '/ai-review',
      name: 'ai-review',
      component: AiReviewView,
      meta: { title: 'Review Saran AI' }
    },
    {
      path: '/hrd',
      name: 'hrd',
      component: HrdView,
      meta: { title: 'HRD Presences' }
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
