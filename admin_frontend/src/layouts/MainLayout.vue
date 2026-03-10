<template>
  <div class="app-shell flex h-screen overflow-hidden">
    <!-- Sidebar -->
    <aside 
        class="app-sidebar flex flex-col h-full z-50 transition-all duration-300 ease-in-out transform lg:translate-x-0"
        :class="[
            isDesktop
              ? 'static translate-x-0'
              : (isSidebarOpenMobile ? 'fixed translate-x-0' : '-translate-x-full fixed'),
            isSidebarCollapsed ? 'w-20' : 'w-64'
        ]"
    >
      <div class="px-5 py-5 mb-4 flex items-center gap-3 overflow-hidden whitespace-nowrap">
        <div class="brand-mark flex-shrink-0">
          <i class="bi bi-lightning-fill text-xl"></i>
        </div>
        <span 
            class="text-xl font-bold brand-wordmark transition-opacity duration-300"
            :class="{ 'opacity-0 w-0': isSidebarCollapsed, 'opacity-100': !isSidebarCollapsed }"
        >StatementX</span>
      </div>
      
      <nav class="flex-1 px-3 pb-4 space-y-1 overflow-x-hidden overflow-y-auto">
        <router-link to="/" class="sidebar-item" active-class="active" @click="closeMobileSidebar" :title="isSidebarCollapsed ? 'Dashboard' : ''">
          <i class="bi bi-grid-fill text-lg flex-shrink-0"></i>
          <span class="ml-3 font-medium transition-opacity duration-300" :class="{ 'opacity-0 w-0 hidden': isSidebarCollapsed }">Dashboard</span>
        </router-link>

        <router-link to="/converter" class="sidebar-item" active-class="active" @click="closeMobileSidebar" :title="isSidebarCollapsed ? 'Converter' : ''">
          <i class="bi bi-file-earmark-medical text-lg flex-shrink-0"></i>
          <span class="ml-3 font-medium transition-opacity duration-300" :class="{ 'opacity-0 w-0 hidden': isSidebarCollapsed }">Converter</span>
        </router-link>
        
        <router-link to="/history" class="sidebar-item" active-class="active" @click="closeMobileSidebar" :title="isSidebarCollapsed ? 'History' : ''">
          <i class="bi bi-database-fill text-lg flex-shrink-0"></i>
          <span class="ml-3 font-medium transition-opacity duration-300" :class="{ 'opacity-0 w-0 hidden': isSidebarCollapsed }">History & DB</span>
        </router-link>

        <router-link to="/upload-summary" class="sidebar-item" active-class="active" @click="closeMobileSidebar" :title="isSidebarCollapsed ? 'Upload Summary' : ''">
          <i class="bi bi-file-check-fill text-lg flex-shrink-0"></i>
          <span class="ml-3 font-medium transition-opacity duration-300" :class="{ 'opacity-0 w-0 hidden': isSidebarCollapsed }">Upload Summary</span>
        </router-link>

        <div class="pt-4 pb-2 transition-opacity duration-300" :class="{ 'opacity-0 hidden': isSidebarCollapsed }">
            <p class="sidebar-section-label px-2">HRD</p>
        </div>
        <div class="pt-4 pb-2 flex justify-center" v-if="isSidebarCollapsed">
            <i class="bi bi-three-dots section-dots"></i>
        </div>

        <router-link to="/hrd" class="sidebar-item" active-class="active" @click="closeMobileSidebar" :title="isSidebarCollapsed ? 'HRD' : ''">
          <i class="bi bi-calendar-check text-lg flex-shrink-0"></i>
          <span class="ml-3 font-medium transition-opacity duration-300" :class="{ 'opacity-0 w-0 hidden': isSidebarCollapsed }">Presences</span>
        </router-link>

        <div class="pt-4 pb-2 transition-opacity duration-300" :class="{ 'opacity-0 hidden': isSidebarCollapsed }">
            <p class="sidebar-section-label px-2">Management</p>
        </div>
        <div class="pt-4 pb-2 flex justify-center" v-if="isSidebarCollapsed">
            <i class="bi bi-three-dots section-dots"></i>
        </div>

        <router-link to="/companies" class="sidebar-item" active-class="active" @click="closeMobileSidebar" :title="isSidebarCollapsed ? 'Companies' : ''">
          <i class="bi bi-building text-lg flex-shrink-0"></i>
          <span class="ml-3 font-medium transition-opacity duration-300" :class="{ 'opacity-0 w-0 hidden': isSidebarCollapsed }">Companies</span>
        </router-link>

        <router-link to="/marks" class="sidebar-item" active-class="active" @click="closeMobileSidebar" :title="isSidebarCollapsed ? 'Marks' : ''">
          <i class="bi bi-tags-fill text-lg flex-shrink-0"></i>
          <span class="ml-3 font-medium transition-opacity duration-300" :class="{ 'opacity-0 w-0 hidden': isSidebarCollapsed }">Marks</span>
        </router-link>

        <router-link to="/chart-of-accounts" class="sidebar-item" active-class="active" @click="closeMobileSidebar" :title="isSidebarCollapsed ? 'Chart of Accounts' : ''">
          <i class="bi bi-journal-text text-lg flex-shrink-0"></i>
          <span class="ml-3 font-medium transition-opacity duration-300" :class="{ 'opacity-0 w-0 hidden': isSidebarCollapsed }">Chart of Accounts</span>
        </router-link>

        <router-link to="/management" class="sidebar-item" active-class="active" @click="closeMobileSidebar" :title="isSidebarCollapsed ? 'Locations & Stores' : ''">
          <i class="bi bi-geo-alt text-lg flex-shrink-0"></i>
          <span class="ml-3 font-medium transition-opacity duration-300" :class="{ 'opacity-0 w-0 hidden': isSidebarCollapsed }">Locations & Stores</span>
        </router-link>

        <div class="pt-4 pb-2 transition-opacity duration-300" :class="{ 'opacity-0 hidden': isSidebarCollapsed }">
            <p class="sidebar-section-label px-2">Reports</p>
        </div>
        <div class="pt-4 pb-2 flex justify-center" v-if="isSidebarCollapsed">
            <i class="bi bi-three-dots section-dots"></i>
        </div>

        <router-link to="/reports" class="sidebar-item" active-class="active" @click="closeMobileSidebar" :title="isSidebarCollapsed ? 'Financial Reports' : ''">
          <i class="bi bi-file-earmark-bar-graph text-lg flex-shrink-0"></i>
          <span class="ml-3 font-medium transition-opacity duration-300" :class="{ 'opacity-0 w-0 hidden': isSidebarCollapsed }">Financial Reports</span>
        </router-link>

        <div class="pt-4 pb-2 transition-opacity duration-300" :class="{ 'opacity-0 hidden': isSidebarCollapsed }">
            <p class="sidebar-section-label px-2">Configuration</p>
        </div>
        <div class="pt-4 pb-2 flex justify-center" v-if="isSidebarCollapsed">
            <i class="bi bi-three-dots section-dots"></i>
        </div>

        <router-link to="/settings" class="sidebar-item" active-class="active" @click="closeMobileSidebar" :title="isSidebarCollapsed ? 'Settings' : ''">
          <i class="bi bi-gear text-lg flex-shrink-0"></i>
          <span class="ml-3 font-medium transition-opacity duration-300" :class="{ 'opacity-0 w-0 hidden': isSidebarCollapsed }">Settings</span>
        </router-link>
      </nav>

      <div class="p-4 border-t sidebar-footer overflow-hidden">
        <div class="surface-card-muted rounded-2xl p-4 flex items-center gap-3">
          <div class="account-chip flex-shrink-0">A</div>
          <div class="overflow-hidden transition-opacity duration-300" :class="{ 'opacity-0 w-0 hidden': isSidebarCollapsed }">
            <p class="text-xs font-bold text-theme truncate">Admin Account</p>
            <p class="text-[10px] text-muted uppercase tracking-[0.18em]">Operations Console</p>
          </div>
        </div>
      </div>
    </aside>

    <!-- Overlay for mobile -->
    <div 
        v-if="!isDesktop && isSidebarOpenMobile" 
        class="fixed inset-0 bg-gray-900/50 z-40 lg:hidden"
        @click="isSidebarOpenMobile = false"
    ></div>

    <!-- Main Content -->
    <div class="app-content flex-1 flex flex-col min-w-0">
      <!-- Navbar -->
      <header class="app-header h-16 flex items-center justify-between px-4 md:px-6 sticky top-0 z-40">
        <div class="flex items-center gap-4">
          <button class="header-icon-button" @click="toggleSidebarControl">
            <i
              class="bi text-lg"
              :class="isDesktop ? (isSidebarCollapsed ? 'bi-layout-sidebar' : 'bi-layout-sidebar-inset') : 'bi-list'"
            ></i>
          </button>
          
          <div v-if="isDesktop" class="h-6 w-px nav-divider mx-1"></div>
          <div>
            <p class="text-[11px] font-bold uppercase tracking-[0.24em] header-eyebrow">Admin Workspace</p>
            <h2 class="text-sm font-semibold uppercase tracking-tight text-theme">{{ pageTitle }}</h2>
          </div>
        </div>
        
        <div class="flex items-center gap-3">
          <button class="theme-toggle" @click="toggleTheme">
            <i class="bi" :class="isDark ? 'bi-sun-fill' : 'bi-moon-stars-fill'"></i>
            <span>{{ isDark ? 'Light mode' : 'Dark mode' }}</span>
          </button>
          <div class="status-pill hidden md:flex">
            <span class="relative flex h-2 w-2">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </span>
            SERVER ONLINE
          </div>
        </div>
      </header>

      <main class="app-main flex-1 overflow-y-auto px-4 py-5 md:px-6 md:py-6">
         <router-view :key="route.fullPath"></router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRoute } from 'vue-router';
import { useTheme } from '../composables/useTheme';

const isSidebarCollapsed = ref(false);
const isSidebarOpenMobile = ref(false);
const isDesktop = ref(false);
const route = useRoute();
const { isDark, toggleTheme } = useTheme();

const pageTitle = computed(() => {
    switch(route.name) {
        case 'dashboard': return 'Dashboard Overview';
        case 'converter': return 'Bank Statement Converter';
        case 'history': return 'Transaction History';
        case 'upload-summary': return 'Upload Summary';
        case 'companies': return 'Company Management';
        case 'marks': return 'Mark Management';
        case 'chart-of-accounts': return 'Chart of Accounts';
        case 'products': return 'Product Management';
        case 'reports': return 'Financial Reports';
        case 'hrd': return 'HRD Presences';
        case 'settings': return 'System Settings';
        case 'management': return 'Locations & Stores';
        case 'general-ledger': return 'General Ledger';
        case 'initial-capital': return 'Initial Capital';
        default: return 'StatementX';
    }
});

const closeMobileSidebar = () => {
    isSidebarOpenMobile.value = false;
};

const syncViewportState = () => {
    isDesktop.value = window.innerWidth >= 1024;
    if (isDesktop.value) {
        isSidebarOpenMobile.value = true;
        return;
    }

    isSidebarOpenMobile.value = false;
};

const toggleSidebarControl = () => {
    if (isDesktop.value) {
        isSidebarCollapsed.value = !isSidebarCollapsed.value;
        return;
    }

    isSidebarOpenMobile.value = !isSidebarOpenMobile.value;
};

onMounted(() => {
    syncViewportState();
    window.addEventListener('resize', syncViewportState);
});

onBeforeUnmount(() => {
    window.removeEventListener('resize', syncViewportState);
});
</script>

<style scoped>
.app-sidebar {
    background: var(--color-panel);
    border-right: 1px solid var(--color-border);
    backdrop-filter: blur(14px);
}

.app-header {
    background: var(--color-panel-strong);
    border-bottom: 1px solid var(--color-border);
    backdrop-filter: blur(16px);
}

.brand-mark {
    @apply flex h-11 w-11 items-center justify-center rounded-2xl text-white;
    background: linear-gradient(135deg, var(--color-primary), var(--color-primary-strong));
    box-shadow: 0 16px 32px rgba(15, 118, 110, 0.22);
}

.brand-wordmark {
    background: linear-gradient(135deg, var(--color-text), var(--color-text-muted));
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}

.sidebar-section-label {
    @apply text-[10px] font-bold uppercase tracking-[0.24em];
    color: var(--color-text-muted);
}

.section-dots {
    color: var(--color-text-muted);
}

.sidebar-footer {
    border-color: var(--color-border);
}

.account-chip {
    @apply flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold;
    background: rgba(15, 118, 110, 0.12);
    color: var(--color-primary);
}

.nav-divider {
    background: var(--color-border);
}

.header-eyebrow {
    color: var(--color-text-muted);
}

.header-icon-button {
    @apply inline-flex items-center justify-center rounded-xl p-2 transition-colors;
    border: 1px solid var(--color-border);
    background: var(--color-surface);
    color: var(--color-text-muted);
    box-shadow: var(--shadow-soft);
}

.header-icon-button:hover {
    color: var(--color-text);
    border-color: var(--color-border-strong);
}

.sidebar-item {
    @apply mb-1 flex items-center rounded-2xl px-3 py-2.5 transition-all duration-200 cursor-pointer;
    color: var(--color-text-muted);
}

.sidebar-item:hover {
    background: var(--color-surface-muted);
    color: var(--color-primary);
}

.sidebar-item.active {
    @apply font-semibold;
    background: rgba(15, 118, 110, 0.12);
    color: var(--color-primary);
    border: 1px solid rgba(15, 118, 110, 0.18);
    box-shadow: var(--shadow-soft);
}
</style>
