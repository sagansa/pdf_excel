<template>
  <div class="overflow-hidden rounded-2xl border border-border">
    <table class="w-full text-xs">
      <thead v-if="$slots.header || columns.length > 0" class="bg-surface-muted border-b border-border">
        <tr>
          <th
            v-for="(column, index) in columns"
            :key="index"
            :class="[
              'px-3 py-2 text-left font-semibold uppercase tracking-[0.12em] text-muted',
              column.class || '',
              column.align === 'center' ? 'text-center' : '',
              column.align === 'right' ? 'text-right' : ''
            ]"
            :style="column.width ? { width: column.width } : {}"
          >
            <slot :name="`header-${column.key}`" :column="column">
              {{ column.label }}
            </slot>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-if="data.length === 0 && $slots.empty"
          class="border-b border-border last:border-0"
        >
          <td :colspan="columns.length" class="px-3 py-8 text-center text-muted">
            <slot name="empty"></slot>
          </td>
        </tr>
        <tr
          v-for="(row, rowIndex) in data"
          :key="rowKey ? row[rowKey] : rowIndex"
          :class="[
            'border-b border-border last:border-0 transition-colors',
            rowClass ? rowClass(row, rowIndex) : 'hover:bg-surface-muted'
          ]"
        >
          <td
            v-for="(column, colIndex) in columns"
            :key="colIndex"
            :class="[
              'px-3 py-2',
              column.class || '',
              column.align === 'center' ? 'text-center' : '',
              column.align === 'right' ? 'text-right' : ''
            ]"
          >
            <slot :name="`cell-${column.key}`" :row="row" :column="column" :index="rowIndex">
              {{ column.render ? column.render(row[column.key], row) : row[column.key] }}
            </slot>
          </td>
        </tr>
      </tbody>
      <tfoot v-if="$slots.footer" class="bg-surface-muted border-t border-border">
        <slot name="footer" :columns="columns"></slot>
      </tfoot>
    </table>
  </div>
</template>

<script setup>
defineProps({
  data: {
    type: Array,
    default: () => []
  },
  columns: {
    type: Array,
    default: () => []
  },
  rowKey: {
    type: String,
    default: ''
  },
  rowClass: {
    type: Function,
    default: null
  }
});
</script>
