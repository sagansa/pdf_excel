<template>
  <div class="app-shell flex h-screen overflow-hidden">
    <!-- Sidebar -->
    <AppSidebar
        :collapsed="isSidebarCollapsed"
        :mobile-open="isSidebarOpenMobile"
        :is-desktop="isDesktop"
        @close-mobile="isSidebarOpenMobile = false"
    />

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
import AppSidebar from '../components/layout/AppSidebar.vue';

const isSidebarCollapsed = ref(false);
const isSidebarOpenMobile = ref(false);
const isDesktop = ref(false);
const route = useRoute();

const pageTitle = computed(() => route.meta.title ?? 'StatementX');

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
.app-header {
    background: var(--color-panel-strong);
    border-bottom: 1px solid var(--color-border);
    backdrop-filter: blur(16px);
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
</style>
