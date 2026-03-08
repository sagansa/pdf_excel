<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
    <!-- Loading State -->
    <div v-if="isLoading" class="p-12 text-center">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      <p class="text-sm text-gray-500 mt-2">Loading accounts...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="coaList.length === 0" class="p-12 text-center">
      <i class="bi bi-inbox text-4xl text-gray-300"></i>
      <p class="text-gray-500 mt-2">No accounts found</p>
    </div>

    <!-- Table -->
    <div v-else class="overflow-x-auto">
      <table class="w-full">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Code
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Name
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Category
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Subcategory
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Description
            </th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr
            v-for="coa in coaList"
            :key="coa.id"
            class="hover:bg-gray-50 transition-colors"
          >
            <td class="px-6 py-4 whitespace-nowrap">
              <span class="text-sm font-mono font-semibold text-gray-900">{{ coa.code }}</span>
            </td>
            <td class="px-6 py-4">
              <span class="text-sm font-medium text-gray-900">{{ coa.name }}</span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span
                class="px-2 py-1 text-xs font-medium rounded-full"
                :class="getCategoryClass(coa.category)"
              >
                {{ coa.category }}
              </span>
            </td>
            <td class="px-6 py-4">
              <span class="text-sm text-gray-600">{{ coa.subcategory || '-' }}</span>
            </td>
            <td class="px-6 py-4">
              <span class="text-sm text-gray-500 line-clamp-2">{{ coa.description || '-' }}</span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right">
              <div class="flex items-center justify-end gap-2">
                <button
                  @click="$emit('edit', coa)"
                  class="p-1.5 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                  title="Edit"
                >
                  <i class="bi bi-pencil"></i>
                </button>
                <button
                  @click="$emit('delete', coa)"
                  class="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors"
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
    <div v-if="!isLoading && coaList.length > 0" class="bg-gray-50 px-6 py-3 border-t border-gray-200">
      <p class="text-xs text-gray-500">
        Showing {{ coaList.length }} account{{ coaList.length !== 1 ? 's' : '' }}
      </p>
    </div>
  </div>
</template>

<script setup>
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

const getCategoryClass = (category) => {
  const classes = {
    ASSET: 'bg-green-100 text-green-800',
    LIABILITY: 'bg-red-100 text-red-800',
    EQUITY: 'bg-blue-100 text-blue-800',
    REVENUE: 'bg-purple-100 text-purple-800',
    EXPENSE: 'bg-orange-100 text-orange-800'
  };
  return classes[category] || 'bg-gray-100 text-gray-800';
};
</script>
