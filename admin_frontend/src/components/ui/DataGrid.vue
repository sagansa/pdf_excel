<template>
  <div class="data-grid">
    <div v-if="showHeader && title" class="data-grid__header">
      <div class="data-grid__header-content">
        <h3 class="data-grid__title">{{ title }}</h3>
        <div class="data-grid__header-actions"><slot name="header-actions"></slot></div>
      </div>
    </div>

    <div class="data-grid__table-wrapper">
      <table class="data-grid__table">
        <thead class="data-grid__head">
          <tr>
            <th v-if="selectable" class="data-grid__cell data-grid__cell--checkbox">
              <input type="checkbox" class="data-grid__checkbox" :checked="isAllSelected" :indeterminate.prop="isIndeterminate" @change="toggleSelectAll" />
            </th>
            <th v-if="showRowNumbers" class="data-grid__cell data-grid__cell--number">#</th>
            <th v-for="column in columns" :key="column.key" class="data-grid__cell" :class="getColumnHeaderClass(column)" :style="{ minWidth: column.width, textAlign: column.align || 'left' }">
              <div class="data-grid__header-cell">
                <button v-if="column.sortable" type="button" class="data-grid__sort-button" @click="handleSort(column.key)">
                  <span>{{ column.title }}</span>
                  <i v-if="sortKey === column.key" :class="sortOrder === 'asc' ? 'bi bi-caret-up-fill' : 'bi bi-caret-down-fill'" class="data-grid__sort-icon"></i>
                  <i v-else class="bi bi-caret-down-fill data-grid__sort-icon data-grid__sort-icon--inactive"></i>
                </button>
                <span v-else>{{ column.title }}</span>
                <input v-if="column.filterable" v-model="filters[column.key]" type="text" class="data-grid__filter-input" :placeholder="`Filter ${column.title}...`" @input="handleFilter" />
              </div>
            </th>
            <th v-if="showActions" class="data-grid__cell data-grid__cell--actions">Actions</th>
          </tr>
        </thead>
        <tbody class="data-grid__body">
          <tr v-for="(item, index) in paginatedData" :key="getItemKey(item, index)" class="data-grid__row" :class="getRowClass(item, index)" @click="handleRowClick(item, $event)">
            <td v-if="selectable" class="data-grid__cell data-grid__cell--checkbox">
              <input type="checkbox" class="data-grid__checkbox" :checked="isItemSelected(item)" @change.stop="toggleSelectItem(item)" />
            </td>
            <td v-if="showRowNumbers" class="data-grid__cell data-grid__cell--number">{{ ((currentPage - 1) * pageSize) + index + 1 }}</td>
            <td v-for="column in columns" :key="column.key" class="data-grid__cell" :class="getCellClass(column, item)" :style="{ textAlign: column.align || 'left' }">
              <slot :name="`cell-${column.key}`" :item="item" :index="index" :value="getItemValue(item, column.key)">
                <span v-if="column.type === 'currency'" class="mono">{{ formatCurrency(getItemValue(item, column.key)) }}</span>
                <span v-else-if="column.type === 'number'" class="mono">{{ formatNumber(getItemValue(item, column.key)) }}</span>
                <span v-else-if="column.type === 'date'">{{ formatDate(getItemValue(item, column.key)) }}</span>
                <span v-else-if="column.type === 'badge'" class="data-grid__badge" :class="getBadgeClass(item, column)">{{ getBadgeText(item, column) }}</span>
                <span v-else>{{ getItemValue(item, column.key) || '-' }}</span>
              </slot>
            </td>
            <td v-if="showActions" class="data-grid__cell data-grid__cell--actions">
              <div class="data-grid__actions">
                <slot name="actions" :item="item" :index="index">
                  <button v-if="editable" type="button" class="btn-icon" title="Edit" @click.stop="handleEdit(item)"><i class="bi bi-pencil"></i></button>
                  <button v-if="deletable" type="button" class="btn-icon btn-icon--danger" title="Delete" @click.stop="handleDelete(item)"><i class="bi bi-trash"></i></button>
                </slot>
              </div>
            </td>
          </tr>
          <tr v-if="paginatedData.length === 0">
            <td :colspan="totalColumns" class="data-grid__cell data-grid__cell--empty">
              <i class="bi bi-inbox data-grid__empty-icon"></i>
              <p>{{ emptyText || 'No data available' }}</p>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="pagination && totalPages > 1" class="data-grid__pagination">
      <div class="data-grid__pagination-info">Showing {{ startItem }} to {{ endItem }} of {{ totalItems }} entries</div>
      <div class="data-grid__pagination-controls">
        <button type="button" class="btn-icon" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)"><i class="bi bi-chevron-left"></i></button>
        <template v-if="totalPages <= 7">
          <button v-for="page in totalPages" :key="page" type="button" class="data-grid__page-btn" :class="{ 'data-grid__page-btn--active': currentPage === page }" @click="goToPage(page)">{{ page }}</button>
        </template>
        <template v-else>
          <button v-if="currentPage > 3" type="button" class="data-grid__page-btn" @click="goToPage(1)">1</button>
          <span v-if="currentPage > 4" class="data-grid__ellipsis">...</span>
          <button v-for="page in visiblePages" :key="page" type="button" class="data-grid__page-btn" :class="{ 'data-grid__page-btn--active': currentPage === page }" @click="goToPage(page)">{{ page }}</button>
          <span v-if="currentPage < totalPages - 3" class="data-grid__ellipsis">...</span>
          <button v-if="currentPage < totalPages - 2" type="button" class="data-grid__page-btn" @click="goToPage(totalPages)">{{ totalPages }}</button>
        </template>
        <button type="button" class="btn-icon" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)"><i class="bi bi-chevron-right"></i></button>
      </div>
      <div class="data-grid__page-size">
        <span class="data-grid__page-size-label">Show:</span>
        <select :value="pageSize" class="data-grid__page-size-select" @change="handlePageSizeChange">
          <option v-for="size in pageSizes" :key="size" :value="size">{{ size }} / page</option>
        </select>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';

const props = defineProps({
  data: { type: Array, required: true },
  columns: { type: Array, required: true },
  title: { type: String, default: '' },
  showHeader: { type: Boolean, default: true },
  showRowNumbers: { type: Boolean, default: false },
  showActions: { type: Boolean, default: false },
  emptyText: { type: String, default: 'No data available' },
  selectable: { type: Boolean, default: false },
  selectedItems: { type: Array, default: () => [] },
  itemKey: { type: String, default: 'id' },
  sortable: { type: Boolean, default: true },
  defaultSortKey: { type: String, default: '' },
  defaultSortOrder: { type: String, default: 'asc', validator: (value) => ['asc', 'desc'].includes(value) },
  filterable: { type: Boolean, default: true },
  pagination: { type: Boolean, default: true },
  pageSize: { type: Number, default: 20 },
  pageSizes: { type: Array, default: () => [10, 20, 50, 100] },
  editable: { type: Boolean, default: false },
  deletable: { type: Boolean, default: false },
  rowClass: { type: [String, Function], default: '' },
  cellClass: { type: [String, Function], default: '' }
});

const emit = defineEmits(['update:selectedItems', 'sort', 'filter', 'row-click', 'edit', 'delete', 'page-change', 'page-size-change']);

const currentPage = ref(1);
const sortKey = ref(props.defaultSortKey);
const sortOrder = ref(props.defaultSortOrder);
const filters = ref({});

const isAllSelected = computed(() => props.selectable && props.data.length > 0 && props.selectedItems.length === props.data.length);
const isIndeterminate = computed(() => props.selectable && props.selectedItems.length > 0 && props.selectedItems.length < props.data.length);
const totalColumns = computed(() => props.columns.length + (props.selectable ? 1 : 0) + (props.showRowNumbers ? 1 : 0) + (props.showActions ? 1 : 0));

const filteredData = computed(() => {
  let result = [...props.data];
  Object.entries(filters.value).forEach(([key, value]) => {
    if (value) {
      const filterValue = value.toLowerCase();
      result = result.filter(item => String(getItemValue(item, key) || '').toLowerCase().includes(filterValue));
    }
  });
  if (sortKey.value) {
    result.sort((a, b) => {
      const aVal = getItemValue(a, sortKey.value);
      const bVal = getItemValue(b, sortKey.value);
      if (aVal === bVal) return 0;
      const comparison = aVal > bVal ? 1 : -1;
      return sortOrder.value === 'asc' ? comparison : -comparison;
    });
  }
  return result;
});

const totalItems = computed(() => filteredData.value.length);
const totalPages = computed(() => props.pagination ? Math.ceil(totalItems.value / props.pageSize) : 1);
const paginatedData = computed(() => {
  if (!props.pagination) return filteredData.value;
  const start = (currentPage.value - 1) * props.pageSize;
  return filteredData.value.slice(start, start + props.pageSize);
});
const startItem = computed(() => totalItems.value === 0 ? 0 : ((currentPage.value - 1) * props.pageSize) + 1);
const endItem = computed(() => { const end = currentPage.value * props.pageSize; return end > totalItems.value ? totalItems.value : end; });
const visiblePages = computed(() => {
  const current = currentPage.value, total = totalPages.value, delta = 2, range = [];
  for (let i = Math.max(2, current - delta); i <= Math.min(total - 1, current + delta); i++) range.push(i);
  if (current - delta > 2) range.unshift(current - delta - 1);
  if (current + delta < total - 2) range.push(current + delta + 1);
  return range;
});

const getItemValue = (item, key) => key.split('.').reduce((obj, k) => obj && obj[k], item);
const getItemKey = (item, index) => item[props.itemKey] || index;
const getColumnHeaderClass = (column) => { const c = []; if (column.sortable) c.push('data-grid__cell--sortable'); if (column.filterable) c.push('data-grid__cell--filterable'); if (column.class) c.push(column.class); return c; };
const getCellClass = (column, item) => { const c = ['data-grid__cell']; if (column.class) c.push(typeof column.class === 'function' ? column.class(item) : column.class); if (props.cellClass && typeof props.cellClass === 'function') c.push(props.cellClass(item, column)); return c; };
const getRowClass = (item, index) => { const c = []; if (props.rowClass) c.push(typeof props.rowClass === 'function' ? props.rowClass(item, index) : props.rowClass); return c; };
const getBadgeClass = (item, column) => column.badgeClass ? (typeof column.badgeClass === 'function' ? column.badgeClass(item) : column.badgeClass) : '';
const getBadgeText = (item, column) => column.badgeText ? (typeof column.badgeText === 'function' ? column.badgeText(item) : column.badgeText) : getItemValue(item, column.key);
const isItemSelected = (item) => props.selectedItems.some(selected => selected[props.itemKey] === item[props.itemKey]);

const toggleSelectAll = () => emit('update:selectedItems', isAllSelected.value ? [] : [...props.data]);
const toggleSelectItem = (item) => {
  const isSelected = isItemSelected(item);
  emit('update:selectedItems', isSelected ? props.selectedItems.filter(s => s[props.itemKey] !== item[props.itemKey]) : [...props.selectedItems, item]);
};
const handleSort = (key) => {
  if (sortKey.value === key) sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc';
  else { sortKey.value = key; sortOrder.value = 'asc'; }
  emit('sort', { key: sortKey.value, order: sortOrder.value });
};
const handleFilter = () => { currentPage.value = 1; emit('filter', { ...filters.value }); };
const handleRowClick = (item, event) => emit('row-click', { item, event });
const handleEdit = (item) => emit('edit', item);
const handleDelete = (item) => emit('delete', item);
const goToPage = (page) => { if (page < 1 || page > totalPages.value) return; currentPage.value = page; emit('page-change', { page, pageSize: props.pageSize }); };
const handlePageSizeChange = (event) => { currentPage.value = 1; emit('page-size-change', { pageSize: Number(event.target.value) }); };

const formatNumber = (value) => value === null || value === undefined || Number.isNaN(Number(value)) ? '-' : new Intl.NumberFormat('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(Number(value));
const formatCurrency = (value) => value === null || value === undefined || Number.isNaN(Number(value)) ? '-' : new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(Number(value));
const formatDate = (value) => { if (!value) return '-'; try { return new Date(value).toLocaleDateString('id-ID', { year: 'numeric', month: 'short', day: 'numeric' }); } catch { return value; } };

defineExpose({ goToPage, handleSort, handleFilter });
</script>

<style scoped>
.data-grid { @apply surface-card; border-radius: 12px; border: 1px solid var(--color-border); overflow: hidden; }
.data-grid__header { @apply px-4 py-3; background: var(--color-surface); border-bottom: 1px solid var(--color-border); }
.data-grid__header-content { @apply flex items-center justify-between; }
.data-grid__title { @apply text-sm font-bold color: var(--color-text); }
.data-grid__header-actions { @apply flex items-center gap-2; }
.data-grid__table-wrapper { @apply overflow-x-auto; }
.data-grid__table { @apply min-w-full text-xs; border-collapse: collapse; }
.data-grid__head { @apply bg-surface-muted; }
.data-grid__cell { @apply px-3 py-2.5; border-bottom: 1px solid var(--color-border); color: var(--color-text); }
.data-grid__head .data-grid__cell { @apply font-semibold uppercase color: var(--color-text-muted) tracking-wide; border-bottom: 2px solid var(--color-border); }
.data-grid__cell--checkbox, .data-grid__cell--number, .data-grid__cell--actions { @apply text-center; }
.data-grid__cell--sortable { @apply cursor-pointer hover:bg-surface-hover; transition: background-color 160ms ease; }
.data-grid__header-cell { @apply flex flex-col gap-1.5; }
.data-grid__sort-button { @apply flex items-center gap-1.5 w-full text-left font-semibold; background: none; border: none; padding: 0; color: inherit; cursor: pointer; }
.data-grid__sort-icon { @apply text-[10px]; color: var(--color-primary); }
.data-grid__sort-icon--inactive { @apply opacity-30; }
.data-grid__filter-input { @apply w-full !px-2 !py-1 !text-xs; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; }
.data-grid__row { @apply transition-colors; }
.data-grid__row:hover { @apply cursor-pointer; background: rgba(15, 118, 110, 0.04); }
.data-grid__cell--empty { @apply text-center py-12 color: var(--color-text-muted); }
.data-grid__empty-icon { @apply text-4xl block mb-3; }
.data-grid__badge { @apply inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase; }
.data-grid__actions { @apply flex items-center justify-center gap-1; }
.btn-icon { @apply p-1.5 rounded-md; background: none; border: none; cursor: pointer; color: var(--color-color: var(--color-text-muted)); transition: all 160ms ease; }
.btn-icon:hover { background: var(--color-surface-hover); color: var(--color-primary); }
.btn-icon--danger:hover { color: var(--color-danger); background: rgba(185, 28, 28, 0.1); }
.data-grid__checkbox { @apply w-4 h-4 rounded; cursor: pointer; }
.data-grid__pagination { @apply flex items-center justify-between px-4 py-3; background: var(--color-surface-muted); border-top: 1px solid var(--color-border); }
.data-grid__pagination-info { @apply text-xs color: var(--color-text-muted); }
.data-grid__pagination-controls { @apply flex items-center gap-1; }
.data-grid__page-btn { @apply min-w-[32px] h-8 rounded-md text-xs font-semibold; background: var(--color-surface); border: 1px solid var(--color-border); color: var(--color-text); transition: all 160ms ease; }
.data-grid__page-btn:hover { background: var(--color-surface-hover); border-color: var(--color-primary); }
.data-grid__page-btn--active { background: var(--color-primary); border-color: var(--color-primary); color: white; }
.data-grid__ellipsis { @apply px-2 color: var(--color-text-muted); }
.data-grid__page-size { @apply flex items-center gap-2; }
.data-grid__page-size-label { @apply text-xs color: var(--color-text-muted); }
.data-grid__page-size-select { @apply !px-2 !py-1 !text-xs; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; }
</style>
