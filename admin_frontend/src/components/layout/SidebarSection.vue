<template>
  <!-- Section tanpa label: item langsung, gaya top-level -->
  <template v-if="!section.label">
    <router-link
      v-for="item in section.items"
      :key="item.to"
      :to="item.to"
      class="sidebar-item"
      :class="{ active: isRouteActive(item.to, route.path) }"
      :data-tip="item.title"
      @click="$emit('close-mobile')"
    >
      <i class="bi text-lg flex-shrink-0" :class="item.icon"></i>
      <span v-if="!collapsed" class="ml-3 font-medium">{{ item.title }}</span>
    </router-link>
  </template>

  <!-- Section berlabel: accordion -->
  <div v-else class="nav-section-labeled">
    <button
      type="button"
      class="sidebar-item sidebar-section-toggle"
      :aria-expanded="expanded && !collapsed"
      :aria-controls="sectionId"
      :data-tip="section.label"
      @click="onToggle"
    >
      <i class="bi text-lg flex-shrink-0" :class="section.items[0].icon"></i>
      <template v-if="!collapsed">
        <span class="ml-3 font-medium flex-1 text-left">{{ section.label }}</span>
        <i
          class="bi text-xs transition-transform duration-200"
          :class="expanded ? 'bi-chevron-down' : 'bi-chevron-right'"
        ></i>
      </template>
      <i v-else class="bi bi-chevron-right text-[10px] text-muted"></i>
    </button>

    <ul v-show="expanded && !collapsed" :id="sectionId" class="nav-sub-list space-y-1">
      <li v-for="item in section.items" :key="item.to">
        <router-link
          :to="item.to"
          class="sidebar-item sidebar-sub-item"
          :class="{ active: isRouteActive(item.to, route.path) }"
          @click="$emit('close-mobile')"
        >
          <span class="font-medium">{{ item.title }}</span>
        </router-link>
      </li>
    </ul>

    <!-- Flyout saat collapsed (desktop) — terbuka via :hover / :focus-within, lihat CSS -->
    <div v-if="collapsed" class="sidebar-flyout" :aria-label="section.label">
      <p class="sidebar-section-label px-2 pb-2">{{ section.label }}</p>
      <router-link
        v-for="item in section.items"
        :key="item.to"
        :to="item.to"
        class="sidebar-item sidebar-flyout-item"
        :class="{ active: isRouteActive(item.to, route.path) }"
        @click="$emit('close-mobile')"
      >
        <span class="font-medium">{{ item.title }}</span>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { isRouteActive } from '../../config/navigation';

const props = defineProps({
  section: { type: Object, required: true },
  expanded: { type: Boolean, default: false },
  collapsed: { type: Boolean, default: false },
});

const emit = defineEmits(['toggle', 'close-mobile']);

const route = useRoute();

const sectionId = computed(() =>
  `nav-section-${String(props.section.label || '').toLowerCase().replace(/\s+/g, '-')}`
);

const onToggle = () => {
  if (!props.collapsed) {
    emit('toggle');
  }
  // Saat collapsed, klik tidak melipat — flyout muncul via hover/focus (CSS).
};
</script>
