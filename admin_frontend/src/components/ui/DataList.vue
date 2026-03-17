<template>
  <div :class="['data-list', wrapperClass]">
    <div
      v-for="(item, index) in items"
      :key="itemKey ? item[itemKey] : index"
      :class="[
        'data-list__item transition-all duration-200',
        itemClass ? itemClass(item, index) : 'hover:bg-surface-muted/50'
      ]"
    >
      <slot :item="item" :index="index">
        {{ item }}
      </slot>
    </div>
  </div>
</template>

<script setup>
defineProps({
  items: {
    type: Array,
    default: () => []
  },
  itemKey: {
    type: String,
    default: 'id'
  },
  wrapperClass: {
    type: String,
    default: ''
  },
  itemClass: {
    type: Function,
    default: null
  }
});
</script>

<style scoped>
.data-list__item {
  border-bottom: 1px solid var(--color-border);
}

.data-list__item:last-child {
  border-bottom: none;
}
</style>
