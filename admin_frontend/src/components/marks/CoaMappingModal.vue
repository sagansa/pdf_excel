<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
    @click.self="$emit('close')"
  >
    <div class="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto dark:bg-[color:var(--color-surface)] dark:text-[color:var(--color-text)] dark:border dark:border-[color:var(--color-border)]">
      <!-- Header -->
      <div class="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between dark:bg-[color:var(--color-surface)] dark:border-[color:var(--color-border)]">
        <div>
          <h2 class="text-xl font-bold text-gray-900 dark:text-[color:var(--color-text)]">COA Mapping</h2>
          <p class="text-sm text-gray-500 mt-1 dark:text-[color:var(--color-text-muted)]">{{ mark?.personal_use || 'Mark' }}</p>
        </div>
        <button
          @click="$emit('close')"
          class="text-gray-400 hover:text-gray-600 transition-colors dark:text-[color:var(--color-text-muted)] dark:hover:text-[color:var(--color-text)]"
        >
          <i class="bi bi-x-lg text-xl"></i>
        </button>
      </div>

      <!-- Content -->
      <div class="p-6 space-y-6">
        <!-- Existing Mappings -->
        <div>
          <div class="flex items-center justify-between mb-3 gap-3">
            <h3 class="text-sm font-semibold text-gray-700 dark:text-[color:var(--color-text)]">Current Mappings</h3>
            <div class="inline-flex rounded-lg border border-gray-200 bg-gray-50 p-1 dark:border-[color:var(--color-border)] dark:bg-[color:var(--color-surface-muted)]">
              <button
                type="button"
                class="px-3 py-1 text-xs font-semibold rounded-md transition-colors"
                :class="selectedReportType === 'real' ? 'bg-white text-indigo-700 shadow-sm dark:bg-[color:var(--color-surface)] dark:text-[color:var(--color-primary-strong)]' : 'text-gray-600 hover:text-gray-900 dark:text-[color:var(--color-text-muted)] dark:hover:text-[color:var(--color-text)]'"
                @click="selectedReportType = 'real'"
              >
                Real
              </button>
              <button
                type="button"
                class="px-3 py-1 text-xs font-semibold rounded-md transition-colors"
                :class="selectedReportType === 'coretax' ? 'bg-white text-cyan-700 shadow-sm dark:bg-[color:var(--color-surface)] dark:text-[color:var(--color-primary-strong)]' : 'text-gray-600 hover:text-gray-900 dark:text-[color:var(--color-text-muted)] dark:hover:text-[color:var(--color-text)]'"
                @click="selectedReportType = 'coretax'"
              >
                Coretax
              </button>
            </div>
          </div>
          
          <div v-if="isLoading" class="text-center py-8">
            <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            <p class="text-sm text-gray-500 mt-2 dark:text-[color:var(--color-text-muted)]">Loading mappings...</p>
          </div>

          <div v-else-if="mappings.length === 0" class="text-center py-8 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200 dark:bg-[color:var(--color-surface-muted)] dark:border-[color:var(--color-border)]">
            <i class="bi bi-link-45deg text-4xl text-gray-300 dark:text-[color:var(--color-text-muted)]"></i>
            <p class="text-gray-500 mt-2 dark:text-[color:var(--color-text-muted)]">No COA mappings yet</p>
            <p class="text-xs text-gray-400 mt-1 dark:text-[color:var(--color-text-muted)]">
              Add a mapping below to link this mark to a Chart of Account ({{ selectedReportType === 'coretax' ? 'Coretax' : 'Real' }}).
            </p>
          </div>

          <div v-else class="space-y-2">
            <div
              v-for="mapping in mappings"
              :key="mapping.id"
              class="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200 dark:bg-[color:var(--color-surface-muted)] dark:border-[color:var(--color-border)]"
            >
              <div class="flex-1">
                <div class="flex items-center gap-2">
                  <span class="font-mono text-sm font-semibold text-gray-900 dark:text-[color:var(--color-text)]">{{ mapping.code }}</span>
                  <span class="text-sm text-gray-600 dark:text-[color:var(--color-text-muted)]">{{ mapping.name }}</span>
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
                    :class="mapping.mapping_type === 'DEBIT' ? 'bg-blue-100 text-blue-800 dark:bg-[color:var(--color-surface)] dark:text-[color:var(--color-text)]' : 'bg-green-100 text-green-800 dark:bg-[color:var(--color-surface)] dark:text-[color:var(--color-text)]'"
                  >
                    {{ mapping.mapping_type }}
                  </span>
                  <span
                    class="px-2 py-0.5 text-xs font-medium rounded-full"
                    :class="mapping.report_type === 'coretax' ? 'bg-cyan-100 text-cyan-800 dark:bg-[color:var(--color-surface)] dark:text-[color:var(--color-text)]' : 'bg-slate-100 text-slate-700 dark:bg-[color:var(--color-surface)] dark:text-[color:var(--color-text)]'"
                  >
                    {{ mapping.report_type === 'coretax' ? 'CORETAX' : 'REAL' }}
                  </span>
                </div>
                <p v-if="mapping.notes" class="text-xs text-gray-500 mt-1 dark:text-[color:var(--color-text-muted)]">{{ mapping.notes }}</p>
              </div>
              <button
                @click="openDeleteModal(mapping)"
                :disabled="isDeleting"
                class="ml-3 p-2 text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50 dark:text-[color:var(--color-danger)] dark:hover:bg-[color:var(--color-surface)]"
                title="Remove mapping"
              >
                <i class="bi bi-trash"></i>
              </button>
            </div>
          </div>
        </div>

        <!-- Add New Mapping Form -->
        <div class="border-t border-gray-200 pt-6 dark:border-[color:var(--color-border)]">
          <h3 class="text-sm font-semibold text-gray-700 mb-3 dark:text-[color:var(--color-text)]">Add New Mapping</h3>
          
          <form @submit.prevent="handleAddMapping" class="space-y-4">
            <!-- COA Selection -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1 dark:text-[color:var(--color-text)]">
                Chart of Account <span class="text-red-500">*</span>
              </label>
              <select
                v-model="newMapping.coa_id"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white text-gray-900 dark:bg-[color:var(--color-surface)] dark:text-[color:var(--color-text)] dark:border-[color:var(--color-border)] dark:focus:border-[color:var(--color-primary)] dark:focus:ring-[color:var(--color-primary-ring)]"
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
              <label class="block text-sm font-medium text-gray-700 mb-1 dark:text-[color:var(--color-text)]">
                Type <span class="text-red-500">*</span>
              </label>
              <div class="grid grid-cols-2 gap-3">
                <label class="flex items-center p-3 border-2 rounded-lg cursor-pointer transition-all dark:border-[color:var(--color-border)] dark:hover:border-[color:var(--color-border-strong)]" :class="newMapping.mapping_type === 'DEBIT' ? 'border-blue-500 bg-blue-50 dark:border-[color:var(--color-primary)] dark:bg-[color:var(--color-surface-muted)]' : 'border-gray-200 hover:border-gray-300'">
                  <input
                    type="radio"
                    v-model="newMapping.mapping_type"
                    value="DEBIT"
                    class="w-4 h-4 text-blue-600"
                  />
                  <span class="ml-2 text-sm font-medium text-gray-900 dark:text-[color:var(--color-text)]">Debit</span>
                </label>
                <label class="flex items-center p-3 border-2 rounded-lg cursor-pointer transition-all dark:border-[color:var(--color-border)] dark:hover:border-[color:var(--color-border-strong)]" :class="newMapping.mapping_type === 'CREDIT' ? 'border-green-500 bg-green-50 dark:border-[color:var(--color-primary)] dark:bg-[color:var(--color-surface-muted)]' : 'border-gray-200 hover:border-gray-300'">
                  <input
                    type="radio"
                    v-model="newMapping.mapping_type"
                    value="CREDIT"
                    class="w-4 h-4 text-green-600"
                  />
                  <span class="ml-2 text-sm font-medium text-gray-900 dark:text-[color:var(--color-text)]">Credit</span>
                </label>
              </div>
              <p class="text-xs text-gray-500 mt-1 dark:text-[color:var(--color-text-muted)]">
                Choose DEBIT for expenses/assets, CREDIT for revenue/liabilities
              </p>
            </div>

            <!-- Notes -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1 dark:text-[color:var(--color-text)]">
                Notes (optional)
              </label>
              <textarea
                v-model="newMapping.notes"
                rows="2"
                placeholder="Additional notes about this mapping..."
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white text-gray-900 placeholder-gray-400 dark:bg-[color:var(--color-surface)] dark:text-[color:var(--color-text)] dark:placeholder-[color:var(--color-text-muted)] dark:border-[color:var(--color-border)] dark:focus:border-[color:var(--color-primary)] dark:focus:ring-[color:var(--color-primary-ring)]"
              ></textarea>
            </div>

            <!-- Actions -->
            <div class="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                @click="resetForm"
                class="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors dark:bg-[color:var(--color-surface)] dark:text-[color:var(--color-text)] dark:border-[color:var(--color-border)] dark:hover:bg-[color:var(--color-surface-muted)]"
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
const selectedReportType = ref('real');
const newMapping = ref({
  coa_id: '',
  mapping_type: 'DEBIT',
  notes: ''
});

const coaByCategory = computed(() => coaStore.coaByCategory);

const getCategoryClass = (category) => {
  const classes = {
    ASSET: 'bg-green-100 text-green-800 dark:bg-emerald-500/20 dark:text-emerald-200',
    LIABILITY: 'bg-red-100 text-red-800 dark:bg-red-500/20 dark:text-red-200',
    EQUITY: 'bg-blue-100 text-blue-800 dark:bg-blue-500/20 dark:text-blue-200',
    REVENUE: 'bg-purple-100 text-purple-800 dark:bg-purple-500/20 dark:text-purple-200',
    EXPENSE: 'bg-orange-100 text-orange-800 dark:bg-orange-500/20 dark:text-orange-200'
  };
  return classes[category] || 'bg-gray-100 text-gray-800 dark:bg-slate-500/20 dark:text-slate-200';
};

const loadMappings = async () => {
  if (!props.mark?.id) return;
  
  isLoading.value = true;
  try {
    mappings.value = await coaStore.fetchMarkMappings(props.mark.id, selectedReportType.value);
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
      newMapping.value.notes || null,
      selectedReportType.value
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
    selectedReportType.value = 'real';
    loadMappings();
  }
}, { immediate: true });

watch(selectedReportType, () => {
  if (props.isOpen && props.mark?.id) {
    loadMappings();
  }
});

// Load COA list if not already loaded
watch(() => props.isOpen, (isOpen) => {
  if (!isOpen) return;

  if (coaStore.coaList.length === 0) {
    coaStore.fetchCoa();
  }
  if (props.mark?.id) {
    loadMappings();
  }
});
</script>
