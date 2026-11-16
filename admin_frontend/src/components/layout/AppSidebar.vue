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

    <nav
      ref="navEl"
      class="flex-1 px-3 pb-4 space-y-1 overflow-x-hidden overflow-y-auto"
      @mousemove="onNavMouseMove"
      @mouseleave="onNavMouseLeave"
      @focusin="onNavFocusIn"
      @focusout="onNavFocusOut"
    >
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

    <!-- Overlay mode collapsed (desktop): tooltip & flyout di-teleport ke <body> dengan
         position: fixed. Overflow nav tidak lagi memotongnya, dan karena elemen ini
         ada di template AppSidebar sendiri, scoped style berlaku tanpa :deep(). -->
    <Teleport to="body">
      <div
        v-if="tooltip"
        ref="tooltipEl"
        class="sidebar-tooltip fixed px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap pointer-events-none"
        :style="{ left: `${tooltip.left}px`, top: `${tooltip.top}px` }"
      >{{ tooltip.text }}</div>

      <div
        v-if="flyout"
        ref="flyoutPanelEl"
        class="sidebar-flyout-panel fixed rounded-2xl p-3"
        :style="{ left: `${flyout.left}px`, top: `${flyout.top}px` }"
        @pointerenter="cancelFlyoutClose"
        @pointerleave="scheduleFlyoutClose"
        @focusin="cancelFlyoutClose"
        @focusout="scheduleFlyoutClose"
      >
        <p class="sidebar-section-label px-2 pb-2">{{ flyout.section.label }}</p>
        <template v-for="item in flyout.section.items" :key="item.to || item.title">
          <router-link
            v-if="item.to"
            :to="item.to"
            class="sidebar-flyout-item"
            :class="{ active: isRouteActive(item.to, route.path) }"
            @click="$emit('close-mobile')"
          >
            <span class="font-medium">{{ item.title }}</span>
          </router-link>
          <!-- Coming-soon: tanpa route, nonaktif + badge "Segera" -->
          <span
            v-else
            class="sidebar-flyout-item sidebar-soon justify-between"
            aria-disabled="true"
            :data-tip="item.title"
          >
            <span class="font-medium">{{ item.title }}</span>
            <span class="soon-badge">Segera</span>
          </span>
        </template>
      </div>
    </Teleport>
  </aside>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../../stores/auth';
import { navigation, isRouteActive } from '../../config/navigation';
import SidebarSection from './SidebarSection.vue';

const props = defineProps({
  collapsed: { type: Boolean, default: false },
  mobileOpen: { type: Boolean, default: false },
  isDesktop: { type: Boolean, default: false },
});

defineEmits(['close-mobile']);

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

// ===== Overlay mode collapsed (desktop): tooltip item + flyout section =====
// Semua path di-guard collapsedDesktop; markup ter-teleport hanya muncul
// bila state terisi lewat path yang sudah di-guard tersebut.
const collapsedDesktop = computed(() => props.collapsed && props.isDesktop);

const navEl = ref(null);
const tooltipEl = ref(null);
const flyoutPanelEl = ref(null);

const tooltip = ref(null); // { text, left, top }
const flyout = ref(null); // { section, left, top }

let flyoutCloseTimer = null;
let flyoutAnchorEl = null; // toggle section yang sedang membuka flyout
let activeSectionLabel = null; // label section yang sedang di-hover di nav

const hideTooltip = () => {
  tooltip.value = null;
};

// Geser bubble/panel agar tetap di dalam viewport setelah ter-render (ukuran baru diketahui).
const clampIntoViewport = async (el, box) => {
  await nextTick();
  if (!el || !box.value) return;
  const rect = el.getBoundingClientRect();
  let dx = 0;
  let dy = 0;
  if (rect.right > window.innerWidth - 8) dx = window.innerWidth - 8 - rect.right;
  if (rect.top < 8) dy = 8 - rect.top;
  else if (rect.bottom > window.innerHeight - 8) dy = window.innerHeight - 8 - rect.bottom;
  if (dx || dy) {
    box.value = { ...box.value, left: box.value.left + dx, top: box.value.top + dy };
  }
};

const showTooltip = (el) => {
  const rect = el.getBoundingClientRect();
  tooltip.value = {
    text: el.dataset.tip || '',
    left: rect.right + 10,
    top: rect.top + rect.height / 2,
  };
  clampIntoViewport(tooltipEl, tooltip);
};

const closeFlyout = () => {
  if (flyoutCloseTimer) {
    clearTimeout(flyoutCloseTimer);
    flyoutCloseTimer = null;
  }
  flyout.value = null;
  flyoutAnchorEl = null;
  activeSectionLabel = null;
};

const scheduleFlyoutClose = () => {
  if (!flyout.value) return;
  if (flyoutCloseTimer) clearTimeout(flyoutCloseTimer);
  flyoutCloseTimer = setTimeout(() => {
    flyoutCloseTimer = null;
    closeFlyout();
  }, 120);
};

const cancelFlyoutClose = () => {
  if (flyoutCloseTimer) {
    clearTimeout(flyoutCloseTimer);
    flyoutCloseTimer = null;
  }
};

const openFlyout = (sectionEl) => {
  const toggle = sectionEl.querySelector('.sidebar-section-toggle');
  if (!toggle) return;
  const label = toggle.dataset.tip;
  const section = navigation.find((s) => s.label && s.label === label);
  if (!section) return;
  if (flyout.value && flyout.value.section.label === label) return; // sudah terbuka untuk section ini
  cancelFlyoutClose();
  const rect = toggle.getBoundingClientRect();
  flyout.value = { section, left: rect.right + 10, top: rect.top };
  flyoutAnchorEl = toggle;
  clampIntoViewport(flyoutPanelEl, flyout);
};

const closeOverlays = () => {
  closeFlyout();
  hideTooltip();
};

// Delegasi event di <nav> (bukan per-item): elemen [data-tip] → tooltip,
// wrapper .nav-section-labeled → flyout. Flyout menang di atas tooltip
// agar keduanya tidak tumpang tindih di posisi yang sama.
const onNavMouseMove = (event) => {
  if (!collapsedDesktop.value) return;
  const sectionEl = event.target.closest('.nav-section-labeled');
  if (sectionEl) {
    const label = sectionEl.querySelector('.sidebar-section-toggle')?.dataset.tip || null;
    if (label !== activeSectionLabel) {
      openFlyout(sectionEl);
      activeSectionLabel = label;
    }
    cancelFlyoutClose();
    hideTooltip();
    return;
  }
  if (activeSectionLabel !== null) {
    activeSectionLabel = null;
    scheduleFlyoutClose();
  }
  const tipEl = event.target.closest('[data-tip]');
  if (tipEl) showTooltip(tipEl);
  else hideTooltip();
};

const onNavMouseLeave = () => {
  hideTooltip();
  if (activeSectionLabel !== null) {
    activeSectionLabel = null;
    scheduleFlyoutClose();
  }
};

const onNavFocusIn = (event) => {
  if (!collapsedDesktop.value) return;
  const sectionEl = event.target.closest('.nav-section-labeled');
  if (sectionEl) {
    hideTooltip();
    openFlyout(sectionEl);
    return;
  }
  const tipEl = event.target.closest('[data-tip]');
  if (tipEl) showTooltip(tipEl);
};

const onNavFocusOut = (event) => {
  if (!collapsedDesktop.value) return;
  const to = event.relatedTarget;
  if (to && navEl.value && navEl.value.contains(to)) return; // fokus pindah di dalam nav
  scheduleFlyoutClose(); // focusin pada panel flyout akan membatalkan ini
  hideTooltip();
};

const onWindowKeydown = (event) => {
  if (event.key !== 'Escape' || !collapsedDesktop.value) return;
  closeOverlays();
};

const onDocumentPointerDown = (event) => {
  if (!collapsedDesktop.value || !flyout.value) return;
  const target = event.target;
  if (flyoutPanelEl.value && flyoutPanelEl.value.contains(target)) return;
  if (flyoutAnchorEl && flyoutAnchorEl.contains(target)) return;
  closeOverlays();
};

const onWindowBlurOrResize = () => {
  if (!collapsedDesktop.value) return;
  closeOverlays();
};

// Listener global dipasang sekali saat mount dan dilepas saat unmount (tanpa leak).
onMounted(() => {
  window.addEventListener('keydown', onWindowKeydown);
  window.addEventListener('blur', onWindowBlurOrResize);
  window.addEventListener('resize', onWindowBlurOrResize);
  document.addEventListener('pointerdown', onDocumentPointerDown);
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onWindowKeydown);
  window.removeEventListener('blur', onWindowBlurOrResize);
  window.removeEventListener('resize', onWindowBlurOrResize);
  document.removeEventListener('pointerdown', onDocumentPointerDown);
  if (flyoutCloseTimer) {
    clearTimeout(flyoutCloseTimer);
    flyoutCloseTimer = null;
  }
});

// Ganti mode (toggle expand/collapse, pindah desktop/mobile) → tutup overlay.
watch(collapsedDesktop, (isCollapsedDesktop) => {
  if (!isCollapsedDesktop) closeOverlays();
});

watch(
  () => route.path,
  () => {
    const next = new Set(expandedSections.value);
    navigation.forEach((section, index) => {
      if (section.label && section.items.some((item) => item.to && isRouteActive(item.to, route.path))) {
        next.add(index);
      }
    });
    expandedSections.value = next;
    closeOverlays(); // navigasi menutup tooltip/flyout seketika
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

/* Elemen di bawah ini di-render <SidebarSection> (multi-root/fragment): scoped style
   parent tidak menjangkau isi child, sehingga semua rule yang menarget elemen tersebut
   wajib lewat :deep(). */
nav :deep(.sidebar-item) {
    @apply mb-1 flex items-center rounded-2xl px-3 py-2.5 transition-all duration-200 cursor-pointer relative;
    color: var(--color-text-muted);
}

nav :deep(.sidebar-item:hover) {
    background: var(--color-surface-muted);
    color: var(--color-primary);
}

nav :deep(.sidebar-item.active) {
    @apply font-semibold;
    background: rgba(15, 118, 110, 0.12);
    color: var(--color-primary);
    border: 1px solid rgba(15, 118, 110, 0.18);
    box-shadow: var(--shadow-soft);
}

/* Accordion */
nav :deep(.sidebar-section-toggle) {
    @apply w-full appearance-none bg-transparent border-0;
}

nav :deep(.nav-sub-list) {
    margin-left: 14px;
    padding-left: 12px;
    border-left: 1px solid var(--color-border);
}

nav :deep(.sidebar-sub-item) {
    @apply px-3 py-2 text-sm;
}

/* Mode collapsed: ikon item di-tengah; tooltip & flyout disediakan AppSidebar via Teleport. */
.sidebar-collapsed :deep(.sidebar-item) {
    justify-content: center;
}

/* Tooltip ter-teleport (pengganti ::after). Left/top di-set inline; transform
   di bawah untuk vertical centering terhadap item. */
.sidebar-tooltip {
    transform: translateY(-50%);
    background: var(--color-panel-strong);
    color: var(--color-text);
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-soft);
    z-index: 70;
}

/* Panel flyout ter-teleport (pengganti flyout in-place di SidebarSection). */
.sidebar-flyout-panel {
    min-width: 220px;
    background: var(--color-panel-strong);
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-soft);
    z-index: 70;
}

.sidebar-flyout-panel :deep(.sidebar-flyout-item) {
    @apply mb-1 flex items-center rounded-2xl px-3 py-2 text-sm font-medium transition-colors;
    color: var(--color-text-muted);
}

.sidebar-flyout-panel :deep(.sidebar-flyout-item:hover) {
    background: var(--color-surface-muted);
    color: var(--color-primary);
}

.sidebar-flyout-panel :deep(.sidebar-flyout-item.active) {
    background: rgba(15, 118, 110, 0.12);
    color: var(--color-primary);
    border: 1px solid rgba(15, 118, 110, 0.18);
    box-shadow: var(--shadow-soft);
}

/* ===== Item coming-soon (flag soon: true, tanpa `to`) =====
   Nonaktif di semua jalur render: opacity turun, cursor default,
   tanpa hover ke warna primary, tanpa active state (tidak punya route).
   Jalur nav butuh :deep(); panel flyout ter-teleport memakai plain scoped
   karena vnode-nya membawa scope attr komponen ini sendiri. */
nav :deep(.sidebar-item.sidebar-soon),
.sidebar-flyout-panel .sidebar-soon {
    cursor: default;
    opacity: 0.55;
}

nav :deep(.sidebar-item.sidebar-soon:hover),
.sidebar-flyout-panel .sidebar-soon:hover {
    background: transparent;
    color: var(--color-text-muted);
}

/* Badge "Segera": jalur nav = tepat setelah judul (ml-2);
   panel flyout = rata kanan baris (margin-left: auto + justify-between di baris). */
nav :deep(.soon-badge),
.sidebar-flyout-panel .soon-badge {
    @apply flex-shrink-0 text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-md;
    background: var(--color-surface-muted);
    color: var(--color-text-muted);
    border: 1px solid var(--color-border);
}

nav :deep(.soon-badge) {
    @apply ml-2;
}

.sidebar-flyout-panel .soon-badge {
    margin-left: auto;
}
</style>
