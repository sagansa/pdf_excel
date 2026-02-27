import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import ConverterView from '../views/ConverterView.vue'
import HistoryView from '../views/HistoryView.vue'
import CompaniesView from '../views/CompaniesView.vue'
import MarksView from '../views/MarksView.vue'
import ChartOfAccountsView from '../views/ChartOfAccountsView.vue'
import ReportsView from '../views/ReportsView.vue'
import UploadSummaryView from '../views/UploadSummaryView.vue'
import SettingsView from '../views/SettingsView.vue'
import ProductsView from '../views/ProductsView.vue'
import ManagementView from '../views/ManagementView.vue'
import InitialCapitalPage from '../views/InitialCapitalPage.vue'
import GeneralLedger from '../views/GeneralLedger.vue'

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
      path: '/settings',
      name: 'settings',
      component: SettingsView
    },
    {
      path: '/products',
      name: 'products',
      component: ProductsView
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
    }
  ]
})

export default router
