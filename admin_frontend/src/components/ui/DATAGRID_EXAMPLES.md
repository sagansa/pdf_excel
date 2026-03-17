# DataGrid & Workspace - Quick Reference

## Import

```javascript
import { Workspace, DataGrid } from '@/components/ui';
```

## Minimal Example

```vue
<template>
  <Workspace title="My Data">
    <DataGrid :data="items" :columns="columns" />
  </Workspace>
</template>

<script setup>
const items = [
  { id: 1, name: 'Item 1', price: 10000 },
  { id: 2, name: 'Item 2', price: 20000 }
];

const columns = [
  { key: 'name', title: 'Name' },
  { key: 'price', title: 'Price', type: 'currency' }
];
</script>
```

## Column Types

```javascript
const columns = [
  // Text (default)
  { key: 'name', title: 'Name' },
  
  // Number with formatting
  { key: 'quantity', title: 'Qty', type: 'number', align: 'right' },
  
  // Currency (IDR)
  { key: 'price', title: 'Price', type: 'currency', align: 'right' },
  
  // Date (formatted)
  { key: 'created_at', title: 'Created', type: 'date' },
  
  // Badge (status)
  {
    key: 'status',
    title: 'Status',
    type: 'badge',
    badgeText: (item) => item.status.toUpperCase(),
    badgeClass: (item) => ({
      'bg-green-100 text-green-800': item.status === 'active',
      'bg-red-100 text-red-800': item.status === 'inactive'
    })
  }
];
```

## Common Features

### Sorting
```vue
<DataGrid
  :data="items"
  :columns="columns"
  :sortable="true"
  @sort="handleSort"
/>
```

### Filtering
```vue
<DataGrid
  :data="items"
  :columns="columns"
  :filterable="true"
  @filter="handleFilter"
/>
```

### Selection
```vue
<DataGrid
  v-model:selectedItems="selected"
  :data="items"
  :columns="columns"
  :selectable="true"
/>
```

### Pagination
```vue
<DataGrid
  :data="items"
  :columns="columns"
  :pagination="true"
  :page-size="20"
  @page-change="handlePageChange"
/>
```

### Row Click
```vue
<DataGrid
  :data="items"
  :columns="columns"
  @row-click="handleRowClick"
/>
```

### Custom Cell
```vue
<DataGrid :data="items" :columns="columns">
  <template #cell-name="{ item, value }">
    <strong>{{ value }}</strong>
  </template>
</DataGrid>
```

### Actions Column
```vue
<DataGrid
  :data="items"
  :columns="columns"
  :show-actions="true"
  :editable="true"
  :deletable="true"
  @edit="handleEdit"
  @delete="handleDelete"
/>
```

## Full Example

```vue
<template>
  <Workspace
    title="Products"
    subtitle="Manage your products"
    :is-loading="loading"
    :error="error"
    :total-items="products.length"
    has-filters
    @refresh="loadProducts"
  >
    <template #header-actions>
      <button class="btn-primary" @click="showAddModal = true">
        <i class="bi bi-plus mr-1"></i> Add Product
      </button>
    </template>

    <template #filters>
      <div class="grid grid-cols-3 gap-4">
        <TextInput v-model="filters.search" label="Search" />
        <SelectInput v-model="filters.category" :options="categories" label="Category" />
        <TextInput v-model="filters.minPrice" label="Min Price" type="number" />
      </div>
    </template>

    <template #toolbar-left>
      <button
        class="btn-secondary"
        :disabled="selected.length === 0"
        @click="bulkDelete"
      >
        Delete Selected ({{ selected.length }})
      </button>
    </template>

    <DataGrid
      v-model:selectedItems="selected"
      :data="products"
      :columns="columns"
      selectable
      show-actions
      editable
      deletable
      :pagination="true"
      :page-size="20"
      @edit="editProduct"
      @delete="deleteProduct"
      @row-click="viewProduct"
    >
      <template #cell-image="{ item }">
        <img :src="item.image" class="w-10 h-10 rounded" />
      </template>

      <template #cell-status="{ item }">
        <span
          class="px-2 py-1 rounded-full text-xs font-semibold"
          :class="{
            'bg-green-100 text-green-800': item.status === 'active',
            'bg-red-100 text-red-800': item.status === 'inactive'
          }"
        >
          {{ item.status }}
        </span>
      </template>
    </DataGrid>

    <template #footer>
      <div class="flex justify-between items-center">
        <div class="text-sm">
          <span class="mr-4">Total Products: <strong>{{ products.length }}</strong></span>
          <span>Total Value: <strong>{{ formatCurrency(totalValue) }}</strong></span>
        </div>
        <button class="btn-primary">Save Changes</button>
      </div>
    </template>
  </Workspace>
</template>

<script setup>
const loading = ref(false);
const error = ref('');
const selected = ref([]);
const filters = ref({});

const columns = [
  {
    key: 'image',
    title: 'Image',
    width: '80px',
    align: 'center'
  },
  {
    key: 'sku',
    title: 'SKU',
    type: 'text',
    sortable: true,
    filterable: true,
    width: '120px'
  },
  {
    key: 'name',
    title: 'Name',
    type: 'text',
    sortable: true,
    filterable: true
  },
  {
    key: 'category',
    title: 'Category',
    type: 'text',
    sortable: true
  },
  {
    key: 'price',
    title: 'Price',
    type: 'currency',
    sortable: true,
    align: 'right'
  },
  {
    key: 'stock',
    title: 'Stock',
    type: 'number',
    sortable: true,
    align: 'right'
  },
  {
    key: 'status',
    title: 'Status',
    type: 'badge',
    sortable: true
  }
];

const loadProducts = async () => {
  loading.value = true;
  error.value = '';
  try {
    // API call here
  } catch (err) {
    error.value = 'Failed to load products';
  } finally {
    loading.value = false;
  }
};

const editProduct = (item) => {
  console.log('Edit:', item);
};

const deleteProduct = (item) => {
  console.log('Delete:', item);
};

const bulkDelete = () => {
  console.log('Bulk delete:', selected.value);
};

const formatCurrency = (value) => {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR'
  }).format(value);
};
</script>
```
