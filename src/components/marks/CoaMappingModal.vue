<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
    @click.self="$emit('close')"
  >
    <div class="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
      <!-- Header -->
      <div class="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h2 class="text-xl font-bold text-gray-900">COA Mapping</h2>
          <p class="text-sm text-gray-500 mt-1">{{ mark?.personal_use || 'Mark' }}</p>
        </div>
        <button
          @click="$emit('close')"
          class="text-gray-400 hover:text-gray-600 transition-colors"
        >
          <i class="bi bi-x-lg text-xl"></i>
        </button>
      </div>

      <!-- Content -->
      <div class="p-6 space-y-6">
        <!-- Existing Mappings -->
        <div>
          <h3 class="text-sm font-semibold text-gray-700 mb-3">Current Mappings</h3>
          
          <div v-if="isLoading" class="text-center py-8">
            <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            <p class="text-sm text-gray-500 mt-2">Loading mappings...</p>
          </div>

          <div v-else-if="mappings.length === 0" class="text-center py-8 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
            <i class="bi bi-link-45deg text-4xl text-gray-300"></i>
            <p class="text-gray-500 mt-2">No COA mappings yet</p>
            <p class="text-xs text-gray-400 mt-1">Add a mapping below to link this mark to a Chart of Account</p>
          </div>

          <div v-else class="space-y-2">
            <div
              v-for="mapping in mappings"
              :key="mapping.id"
              class="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200"
            >
              <div class="flex-1">
                <div class="flex items-center gap-2">
                  <span class="font-mono text-sm font-semibold text-gray-900">{{ mapping.code }}</span>
                  <span class="text-sm text-gray-600">{{ mapping.name }}</span>
                </div>
                <div class="flex items-center gap-2 mt-1">
                  <span
                    class="px-2 py-0.5 text-xs font-medium rounded-full"
                    :class="getCategoryClass(mapping.category)"
                  >
                    {{ mapping.category }}
                  </span>
                  <span
                    class="px-2 py-0.5 text-xs font-medium rounded-full"
                    :class="mapping.mapping_type === 'DEBIT' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'"
                  >
                    {{ mapping.mapping_type }}
                  </span>
                </div>
                <p v-if="mapping.notes" class="text-xs text-gray-500 mt-1">{{ mapping.notes }}</p>
              </div>
              <button
                @click="openDeleteModal(mapping)"
                :disabled="isDeleting"
                class="ml-3 p-2 text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                title="Remove mapping"
              >
                <i class="bi bi-trash"></i>
              </button>
            </div>
          </div>
        </div>

        <!-- Add New Mapping Form -->
        <div class="border-t border-gray-200 pt-6">
          <h3 class="text-sm font-semibold text-gray-700 mb-3">Add New Mapping</h3>
          
          <form @submit.prevent="handleAddMapping" class="space-y-4">
            <!-- COA Selection -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Chart of Account <span class="text-red-500">*</span>
              </label>
              <select
                v-model="newMapping.coa_id"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="">Select account...</option>
                <optgroup
                  v-for="(accounts, category) in coaByCategory"
                  :key="category"
                  :label="category"
                >
                  <option
                    v-for="coa in accounts"
                    :key="coa.id"
                    :value="coa.id"
                  >
                    {{ coa.code }} - {{ coa.name }}
                  </option>
                </optgroup>
              </select>
            </div>

            <!-- Mapping Type -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Type <span class="text-red-500">*</span>
              </label>
              <div class="grid grid-cols-2 gap-3">
                <label class="flex items-center p-3 border-2 rounded-lg cursor-pointer transition-all" :class="newMapping.mapping_type === 'DEBIT' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'">
                  <input
                    type="radio"
                    v-model="newMapping.mapping_type"
                    value="DEBIT"
                    class="w-4 h-4 text-blue-600"
                  />
                  <span class="ml-2 text-sm font-medium text-gray-900">Debit</span>
                </label>
                <label class="flex items-center p-3 border-2 rounded-lg cursor-pointer transition-all" :class="newMapping.mapping_type === 'CREDIT' ? 'border-green-500 bg-green-50' : 'border-gray-200 hover:border-gray-300'">
                  <input
                    type="radio"
                    v-model="newMapping.mapping_type"
                    value="CREDIT"
                    class="w-4 h-4 text-green-600"
                  />
                  <span class="ml-2 text-sm font-medium text-gray-900">Credit</span>
                </label>
              </div>
              <p class="text-xs text-gray-500 mt-1">
                Choose DEBIT for expenses/assets, CREDIT for revenue/liabilities
              </p>
            </div>

            <!-- Notes -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Notes (optional)
              </label>
              <textarea
                v-model="newMapping.notes"
                rows="2"
                placeholder="Additional notes about this mapping..."
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              ></textarea>
            </div>

            <!-- Actions -->
            <div class="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                @click="resetForm"
                class="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Reset
              </button>
              <button
                type="submit"
                :disabled="isSaving"
                class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <span v-if="isSaving" class="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                <i v-else class="bi bi-plus-circle"></i>
                <span>Add Mapping</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <DeleteMappingModal
      :show="showDeleteModal"
      :mapping="mappingToDelete"
      :is-deleting="isDeleting"
      @close="closeDeleteModal"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useCoaStore } from '../../stores/coa';
import DeleteMappingModal from './DeleteMappingModal.vue';

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  mark: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['close', 'updated']);

const coaStore = useCoaStore();

const isLoading = ref(false);
const isSaving = ref(false);
const isDeleting = ref(false);
const mappings = ref([]);
const showDeleteModal = ref(false);
const mappingToDelete = ref(null);
const newMapping = ref({
  coa_id: '',
  mapping_type: 'DEBIT',
  notes: ''
});

const coaByCategory = computed(() => coaStore.coaByCategory);

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

const loadMappings = async () => {
  if (!props.mark?.id) return;
  
  isLoading.value = true;
  try {
    mappings.value = await coaStore.fetchMarkMappings(props.mark.id);
  } catch (error) {
    console.error('Failed to load mappings:', error);
  } finally {
    isLoading.value = false;
  }
};

const handleAddMapping = async () => {
  if (!props.mark?.id || !newMapping.value.coa_id) return;
  
  isSaving.value = true;
  try {
    await coaStore.createMapping(
      props.mark.id,
      newMapping.value.coa_id,
      newMapping.value.mapping_type,
      newMapping.value.notes || null
    );
    
    // Reload mappings
    await loadMappings();
    
    // Reset form
    resetForm();
    
    emit('updated');
  } catch (error) {
    alert(error.message);
  } finally {
    isSaving.value = false;
  }
};

const openDeleteModal = (mapping) => {
  mappingToDelete.value = mapping;
  showDeleteModal.value = true;
};

const closeDeleteModal = () => {
  showDeleteModal.value = false;
  mappingToDelete.value = null;
};

const confirmDelete = async () => {
  if (!mappingToDelete.value?.id) return;
  
  isDeleting.value = true;
  try {
    await coaStore.deleteMapping(mappingToDelete.value.id);
    await loadMappings();
    emit('updated');
    closeDeleteModal();
  } catch (error) {
    alert(error.message);
  } finally {
    isDeleting.value = false;
  }
};

const resetForm = () => {
  newMapping.value = {
    coa_id: '',
    mapping_type: 'DEBIT',
    notes: ''
  };
};

// Watch for mark changes
watch(() => props.mark, (newMark) => {
  if (newMark?.id) {
    loadMappings();
  }
}, { immediate: true });

// Load COA list if not already loaded
watch(() => props.isOpen, (isOpen) => {
  if (isOpen && coaStore.coaList.length === 0) {
    coaStore.fetchCoa();
  }
});
</script>
