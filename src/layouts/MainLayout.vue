<template>
  <div class="flex h-screen bg-[#f9fafb] overflow-hidden">
    <!-- Sidebar -->
    <aside 
        class="bg-white border-r border-gray-200 flex flex-col h-full z-50 transition-all duration-300 ease-in-out transform lg:translate-x-0"
        :class="[
            !isSidebarOpenMobile ? '-translate-x-full fixed lg:static' : 'translate-x-0 fixed',
            isSidebarCollapsed ? 'w-20' : 'w-64'
        ]"
    >
      <div class="p-6 mb-4 flex items-center gap-3 overflow-hidden whitespace-nowrap">
        <div class="bg-indigo-600 p-2.5 rounded-xl text-white shadow-lg shadow-indigo-100 flex-shrink-0">
          <i class="bi bi-lightning-fill text-xl"></i>
        </div>
        <span 
            class="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-600 transition-opacity duration-300"
            :class="{ 'opacity-0 w-0': isSidebarCollapsed, 'opacity-100': !isSidebarCollapsed }"
        >StatementX</span>
      </div>
      
      <nav class="flex-1 px-4 space-y-1 overflow-x-hidden">
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
            <p class="px-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">Management</p>
        </div>
        <div class="pt-4 pb-2 flex justify-center" v-if="isSidebarCollapsed">
            <i class="bi bi-three-dots text-gray-300"></i>
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

        <div class="pt-4 pb-2 transition-opacity duration-300" :class="{ 'opacity-0 hidden': isSidebarCollapsed }">
            <p class="px-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">Reports</p>
        </div>
        <div class="pt-4 pb-2 flex justify-center" v-if="isSidebarCollapsed">
            <i class="bi bi-three-dots text-gray-300"></i>
        </div>

        <router-link to="/reports" class="sidebar-item" active-class="active" @click="closeMobileSidebar" :title="isSidebarCollapsed ? 'Financial Reports' : ''">
          <i class="bi bi-file-earmark-bar-graph text-lg flex-shrink-0"></i>
          <span class="ml-3 font-medium transition-opacity duration-300" :class="{ 'opacity-0 w-0 hidden': isSidebarCollapsed }">Financial Reports</span>
        </router-link>
      </nav>

      <div class="p-4 border-t border-gray-100 overflow-hidden">
        <div class="bg-gray-50 rounded-xl p-4 flex items-center gap-3">
          <div class="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-bold text-xs flex-shrink-0">A</div>
          <div class="overflow-hidden transition-opacity duration-300" :class="{ 'opacity-0 w-0 hidden': isSidebarCollapsed }">
            <p class="text-xs font-bold text-gray-800 truncate">Admin Account</p>
            <p class="text-[10px] text-gray-500">Premium Plan</p>
          </div>
        </div>
      </div>
    </aside>

    <!-- Overlay for mobile -->
    <div 
        v-if="isSidebarOpenMobile" 
        class="fixed inset-0 bg-gray-900/50 z-40 lg:hidden"
        @click="isSidebarOpenMobile = false"
    ></div>

    <!-- Main Content -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Navbar -->
      <header class="h-16 bg-white/80 backdrop-blur-md border-b border-gray-200 flex items-center justify-between px-6 sticky top-0 z-40">
        <div class="flex items-center gap-4">
          <button class="lg:hidden p-1.5 rounded-lg border border-gray-100 shadow-sm text-gray-600" @click="isSidebarOpenMobile = !isSidebarOpenMobile">
            <i class="bi bi-list text-lg"></i>
          </button>
          <button class="hidden lg:block p-1.5 rounded-lg border border-gray-100 shadow-sm text-gray-600 hover:bg-gray-50" @click="isSidebarCollapsed = !isSidebarCollapsed">
            <i class="bi" :class="isSidebarCollapsed ? 'bi-layout-sidebar' : 'bi-layout-sidebar-inset'"></i>
          </button>
          
          <div class="hidden lg:block h-6 w-px bg-gray-200 mx-1"></div>
          <h2 class="text-sm font-semibold text-gray-800 uppercase tracking-tight">{{ pageTitle }}</h2>
        </div>
        
        <div class="flex items-center gap-4">
          <div class="hidden md:flex items-center gap-2 bg-green-50 text-green-700 px-3 py-1.5 rounded-full text-[10px] font-bold border border-green-100">
            <span class="relative flex h-2 w-2">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </span>
            SERVER ONLINE
          </div>
          <!-- Logout could go here -->
        </div>
      </header>

      <main class="p-6 flex-1 bg-[#f9fafb] overflow-y-auto">
         <router-view :key="route.fullPath"></router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRoute } from 'vue-router';

const isSidebarCollapsed = ref(false);
const isSidebarOpenMobile = ref(false);
const route = useRoute();

const pageTitle = computed(() => {
    switch(route.name) {
        case 'dashboard': return 'Dashboard Overview';
        case 'converter': return 'Bank Statement Converter';
        case 'history': return 'Transaction History';
        case 'upload-summary': return 'Upload Summary';
        case 'companies': return 'Company Management';
        case 'marks': return 'Mark Management';
        default: return 'StatementX';
    }
});

const closeMobileSidebar = () => {
    isSidebarOpenMobile.value = false;
};
</script>

<style scoped>
.sidebar-item {
    @apply flex items-center px-3 py-2.5 rounded-xl text-gray-600 hover:bg-gray-50 hover:text-indigo-600 transition-all duration-200 cursor-pointer mb-1;
}
.sidebar-item.active {
    @apply bg-indigo-50 text-indigo-600 font-semibold shadow-sm border border-indigo-100;
}
</style>
