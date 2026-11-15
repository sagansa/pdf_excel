<template>
  <aside
    class="app-sidebar flex flex-col h-full z-50 transition-all duration-300 ease-in-out transform lg:translate-x-0"
    :class="[
      isDesktop
        ? 'static translate-x-0'
        : (mobileOpen ? 'fixed translate-x-0' : '-translate-x-full fixed'),
      collapsed && isDesktop ? 'w-20 sidebar-collapsed' : 'w-64'
    ]"
  >
    <div class="px-5 py-5 mb-4 flex items-center gap-3 overflow-hidden whitespace-nowrap">
      <div class="brand-mark flex-shrink-0">
        <i class="bi bi-lightning-fill text-xl"></i>
      </div>
      <span
        class="text-xl font-bold brand-wordmark transition-opacity duration-300"
        :class="{ 'opacity-0 w-0': collapsed && isDesktop, 'opacity-100': !(collapsed && isDesktop) }"
      >StatementX</span>
    </div>

    <nav class="flex-1 px-3 pb-4 space-y-1 overflow-x-hidden overflow-y-auto">
      <SidebarSection
        v-for="(section, index) in navigation"
        :key="index"
        :section="section"
        :expanded="expandedSections.has(index)"
        :collapsed="collapsed && isDesktop"
        @toggle="toggleSection(index)"
        @close-mobile="$emit('close-mobile')"
      />
    </nav>

    <div class="p-4 border-t sidebar-footer overflow-hidden">
      <div class="surface-card-muted rounded-2xl p-4 flex items-center gap-3">
        <div class="account-chip flex-shrink-0">{{ userInitials }}</div>
        <div class="overflow-hidden transition-opacity duration-300" :class="{ 'opacity-0 w-0 hidden': collapsed && isDesktop }">
          <p class="text-xs font-bold text-theme truncate">{{ auth.user?.display_name || 'Admin' }}</p>
          <p class="text-[10px] text-muted uppercase tracking-[0.18em] truncate">{{ auth.user?.email || '' }}</p>
        </div>
        <button
          class="ml-auto flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-theme hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
          :class="{ 'opacity-0 w-0 hidden': collapsed && isDesktop }"
          title="Logout"
          :disabled="isLoggingOut"
          @click="handleLogout"
        >
          <i class="bi bi-box-arrow-right"></i>
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../../stores/auth';
import { navigation, isRouteActive } from '../../config/navigation';
import SidebarSection from './SidebarSection.vue';

const props = defineProps({
  collapsed: { type: Boolean, default: false },
  mobileOpen: { type: Boolean, default: false },
  isDesktop: { type: Boolean, default: false },
});

const emit = defineEmits(['close-mobile']);

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const isLoggingOut = ref(false);

const userInitials = computed(() => {
  const name = auth.user?.display_name || auth.user?.email || 'A';
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('');
});

const handleLogout = async () => {
  isLoggingOut.value = true;
  try {
    await auth.logout();
    router.push('/login');
  } finally {
    isLoggingOut.value = false;
  }
};

// Auto-open: section yang berisi item aktif selalu terbuka saat route berubah
// (termasuk deep-link). Section yang tidak relevan tidak pernah ditutup otomatis —
// keputusan manual user dihormati sampai dia sendiri menutupnya.
const expandedSections = ref(new Set());

const toggleSection = (index) => {
  const next = new Set(expandedSections.value);
  if (next.has(index)) {
    next.delete(index);
  } else {
    next.add(index);
  }
  expandedSections.value = next;
};

watch(
  () => route.path,
  () => {
    const next = new Set(expandedSections.value);
    navigation.forEach((section, index) => {
      if (section.label && section.items.some((item) => isRouteActive(item.to, route.path))) {
        next.add(index);
      }
    });
    expandedSections.value = next;
  },
  { immediate: true }
);
</script>

<style scoped>
.app-sidebar {
    background: var(--color-panel);
    border-right: 1px solid var(--color-border);
    backdrop-filter: blur(14px);
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

.sidebar-footer {
    border-color: var(--color-border);
}

.account-chip {
    @apply flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold;
    background: rgba(15, 118, 110, 0.12);
    color: var(--color-primary);
}

.sidebar-item {
    @apply mb-1 flex items-center rounded-2xl px-3 py-2.5 transition-all duration-200 cursor-pointer relative;
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

/* Accordion */
.sidebar-section-toggle {
    @apply w-full appearance-none bg-transparent border-0;
}

.nav-sub-list {
    margin-left: 14px;
    padding-left: 12px;
    border-left: 1px solid var(--color-border);
}

.sidebar-sub-item {
    @apply px-3 py-2 text-sm;
}

/* Mode collapsed */
.sidebar-collapsed .sidebar-item {
    justify-content: center;
}

.sidebar-collapsed .sidebar-item:hover::after,
.sidebar-collapsed .sidebar-item:focus-visible::after {
    content: attr(data-tip);
    position: absolute;
    left: calc(100% + 10px);
    top: 50%;
    transform: translateY(-50%);
    @apply px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap pointer-events-none;
    background: var(--color-panel-strong);
    color: var(--color-text);
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-soft);
    z-index: 60;
}

.nav-section-labeled {
    position: relative;
}

.sidebar-flyout {
    display: none;
    position: absolute;
    left: calc(100% + 10px);
    top: 0;
    min-width: 220px;
    @apply rounded-2xl p-3;
    background: var(--color-panel-strong);
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-soft);
    z-index: 60;
}

.sidebar-collapsed .nav-section-labeled:hover .sidebar-flyout,
.sidebar-collapsed .nav-section-labeled:focus-within .sidebar-flyout {
    display: block;
}

.sidebar-flyout-item {
    @apply text-sm px-3 py-2;
    color: var(--color-text-muted);
}
</style>
