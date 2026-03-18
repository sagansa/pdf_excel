<template>
  <TableShell>
    <!-- Loading State -->
    <div v-if="isLoading" class="p-12 text-center">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2" style="border-color: var(--color-primary)"></div>
      <p class="text-sm text-muted mt-2">Loading accounts...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="coaList.length === 0" class="p-12 text-center">
      <i class="bi bi-inbox text-4xl text-muted"></i>
      <p class="text-muted mt-2">No accounts found</p>
    </div>

    <!-- Table -->
    <div v-else>
      <table class="w-full table-compact">
        <thead>
          <tr>
            <th class="px-6 py-3 text-left">
              Code
            </th>
            <th class="px-6 py-3 text-left">
              Name
            </th>
            <th class="px-6 py-3 text-left">
              Category
            </th>
            <th class="px-6 py-3 text-left">
              Fiscal Category
            </th>
            <th class="px-6 py-3 text-left">
              Subcategory
            </th>
            <th class="px-6 py-3 text-left text-muted/50 font-normal">
              Description
            </th>
            <th class="px-6 py-3 text-right">
              Actions
            </th>
          </tr>
        </thead>
        <tbody class="divide-y" style="border-color: var(--color-border)">
          <tr
            v-for="coa in coaList"
            :key="coa.id"
            class="coa-row"
          >
            <td class="px-6 py-4 whitespace-nowrap">
              <span class="text-sm mono font-semibold text-theme">{{ coa.code }}</span>
            </td>
            <td class="px-6 py-4">
              <span class="text-sm font-medium text-theme">{{ coa.name }}</span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <BaseBadge :variant="getCategoryVariant(coa.category)" :label="coa.category" />
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <FiscalCategoryBadge :category="coa.fiscal_category" />
            </td>
            <td class="px-6 py-4">
              <span class="text-xs font-semibold text-muted">{{ coa.subcategory || '-' }}</span>
            </td>
            <td class="px-6 py-4">
              <span class="text-sm text-muted line-clamp-2">{{ coa.description || '-' }}</span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right">
              <div class="flex items-center justify-end gap-2">
                <button
                  @click="$emit('edit', coa)"
                  class="coa-action coa-action--primary"
                  title="Edit"
                >
                  <i class="bi bi-pencil"></i>
                </button>
                <button
                  @click="$emit('delete', coa)"
                  class="coa-action coa-action--danger"
                  title="Delete"
                >
                  <i class="bi bi-trash"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Footer -->
    <template #footer>
      <div v-if="!isLoading && coaList.length > 0" class="coa-footer px-6 py-3 border-t">
        <p class="text-xs text-muted">
          Showing {{ coaList.length }} account{{ coaList.length !== 1 ? 's' : '' }}
        </p>
      </div>
    </template>
  </TableShell>
</template>

<script setup>
import TableShell from '../ui/TableShell.vue';
import BaseBadge from '../ui/BaseBadge.vue';
import FiscalCategoryBadge from '../ui/FiscalCategoryBadge.vue';

defineProps({
  coaList: {
    type: Array,
    required: true
  },
  isLoading: {
    type: Boolean,
    default: false
  }
});

defineEmits(['edit', 'delete']);

const getCategoryVariant = (category) => {
  const map = {
    ASSET: 'primary',
    LIABILITY: 'danger',
    EQUITY: 'indigo',
    REVENUE: 'success',
    EXPENSE: 'warning'
  };
  return map[category] || 'muted';
};
</script>

<style scoped>
.coa-row {
  transition: background-color 160ms ease;
}

.coa-row:hover {
  background: rgba(15, 118, 110, 0.05);
}

.coa-action {
  @apply rounded p-1.5 transition-colors;
}

.coa-action--primary {
  color: var(--color-primary);
}

.coa-action--primary:hover {
  background: rgba(15, 118, 110, 0.08);
}

.coa-action--danger {
  color: var(--color-danger);
}

.coa-action--danger:hover {
  background: rgba(185, 28, 28, 0.08);
}

.coa-footer {
  background: var(--color-surface-muted);
  border-color: var(--color-border);
}
</style>
