<template>
  <BaseModal :isOpen="isOpen" size="3xl" @close="$emit('close')">
    <template #title>COA Mapping — {{ mark?.personal_use || mark?.internal_report || 'Mark' }}</template>

    <!-- Content -->
    <div class="p-6 space-y-6">
      <!-- Existing Mappings -->
      <div>
        <div class="flex items-center justify-between mb-3 gap-3">
          <h3 class="section-title">Current Mappings</h3>
          <div class="lens-toggle" role="group" aria-label="Pilih lensa reporting">
            <button
              type="button"
              class="lens-toggle__btn"
              :class="{ 'lens-toggle__btn--active': selectedReportType === 'real' }"
              :aria-pressed="selectedReportType === 'real' ? 'true' : 'false'"
              @click="selectedReportType = 'real'"
            >
              Real
            </button>
            <button
              type="button"
              class="lens-toggle__btn"
              :class="{ 'lens-toggle__btn--active': selectedReportType === 'coretax' }"
              :aria-pressed="selectedReportType === 'coretax' ? 'true' : 'false'"
              @click="selectedReportType = 'coretax'"
            >
              Coretax
            </button>
          </div>
        </div>

        <div v-if="isLoading" class="text-center py-8">
          <div class="spinner-primary inline-block animate-spin rounded-full h-8 w-8 border-b-2"></div>
          <p class="text-sm text-muted mt-2">Loading mappings...</p>
        </div>

        <div v-else-if="mappings.length === 0" class="empty-state">
          <i class="bi bi-link-45deg empty-state__icon"></i>
          <p class="text-theme font-medium">No COA mappings yet</p>
          <p class="text-xs text-muted mt-1">
            Add a mapping below to link this mark to a Chart of Account ({{ selectedReportType === 'coretax' ? 'Coretax' : 'Real' }}).
          </p>
        </div>

        <div v-else class="space-y-2">
          <div
            v-for="mapping in mappings"
            :key="mapping.id"
            class="mapping-item"
          >
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="mono text-sm font-semibold text-theme">{{ mapping.code }}</span>
                <span class="text-sm text-muted truncate">{{ mapping.name }}</span>
              </div>
              <div class="flex items-center gap-2 mt-1 flex-wrap">
                <span class="badge" :class="`badge--cat-${categoryTone(mapping.category)}`">
                  {{ mapping.category }}
                </span>
                <span class="badge" :class="mapping.mapping_type === 'DEBIT' ? 'badge--db' : 'badge--cr'">
                  {{ mapping.mapping_type }}
                </span>
                <span class="badge" :class="mapping.report_type === 'coretax' ? 'badge--coretax' : 'badge--neutral'">
                  {{ mapping.report_type === 'coretax' ? 'CORETAX' : 'REAL' }}
                </span>
              </div>
              <p v-if="mapping.notes" class="text-xs text-muted mt-1">{{ mapping.notes }}</p>
            </div>
            <button
              @click="openDeleteModal(mapping)"
              :disabled="isDeleting"
              class="mapping-item__delete"
              title="Remove mapping"
            >
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Add New Mapping Form -->
      <div class="border-t pt-6 add-form" >
        <h3 class="section-title mb-3">Add New Mapping</h3>

        <form @submit.prevent="handleAddMapping" class="space-y-4">
          <!-- COA Selection -->
          <div>
            <label class="label-base">Chart of Account <span class="field-required">*</span></label>
              <div v-if="availableCoaCount === 0" class="all-mapped-hint">
                <i class="bi bi-check2-circle"></i>
                Semua akun COA sudah di-mapping untuk lensa {{ selectedReportType === 'coretax' ? 'Coretax' : 'Real' }}.
              </div>
              <select
                v-else
                v-model="newMapping.coa_id"
                required
                class="input-base w-full"
              >
                <option value="">Select account...</option>
                <optgroup
                  v-for="(accounts, category) in availableCoaByCategory"
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
            <label class="label-base">Type <span class="field-required">*</span></label>
            <div class="grid grid-cols-2 gap-3">
              <label class="type-card" :class="{ 'type-card--active': newMapping.mapping_type === 'DEBIT' }">
                <input
                  type="radio"
                  v-model="newMapping.mapping_type"
                  value="DEBIT"
                  class="type-card__radio"
                />
                <span class="text-sm font-medium text-theme">Debit</span>
              </label>
              <label class="type-card" :class="{ 'type-card--active': newMapping.mapping_type === 'CREDIT' }">
                <input
                  type="radio"
                  v-model="newMapping.mapping_type"
                  value="CREDIT"
                  class="type-card__radio"
                />
                <span class="text-sm font-medium text-theme">Credit</span>
              </label>
            </div>
            <p class="text-xs text-muted mt-1">
              Choose DEBIT for expenses/assets, CREDIT for revenue/liabilities
            </p>
          </div>

          <!-- Notes -->
          <div>
            <label class="label-base">Notes (optional)</label>
            <textarea
              v-model="newMapping.notes"
              rows="2"
              placeholder="Additional notes about this mapping..."
              class="input-base w-full"
            ></textarea>
          </div>

            <!-- Actions -->
            <div class="flex items-center justify-end gap-3 pt-2">
              <button type="button" @click="resetForm" class="btn-secondary">Reset</button>
              <button type="submit" :disabled="isSaving || availableCoaCount === 0" class="btn-primary">
                <span v-if="isSaving" class="spinner-border w-4 h-4 me-2"></span>
                <i v-else class="bi bi-plus-circle me-2"></i>
                <span>Add Mapping</span>
              </button>
            </div>
        </form>
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
  </BaseModal>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import BaseModal from '../ui/BaseModal.vue';
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

// Akun yang sudah di-mapping pada lensa aktif tidak boleh dipilih lagi (cegah mapping dobel).
const availableCoaByCategory = computed(() => {
  const mappedKeys = new Set(
    mappings.value.flatMap((m) => [String(m.coa_id), String(m.code)]),
  );
  const result = {};
  Object.entries(coaByCategory.value).forEach(([category, accounts]) => {
    const remaining = (accounts || []).filter(
      (coa) => !mappedKeys.has(String(coa.id)) && !mappedKeys.has(String(coa.code)),
    );
    if (remaining.length > 0) result[category] = remaining;
  });
  return result;
});

const availableCoaCount = computed(() => (
  Object.values(availableCoaByCategory.value).reduce((sum, list) => sum + list.length, 0)
));

const CATEGORY_TONES = {
  ASSET: 'success',
  LIABILITY: 'danger',
  EQUITY: 'primary',
  REVENUE: 'revenue',
  EXPENSE: 'warning'
};

const categoryTone = (category) => CATEGORY_TONES[category] || 'neutral';

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
  // Pilihan akun berubah per lensa; reset agar tidak mempertahankan id yang tak tersedia.
  newMapping.value.coa_id = '';
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

<style scoped>
.section-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text);
}

.field-required {
  color: var(--color-danger);
}

.all-mapped-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
  background: color-mix(in srgb, var(--color-success) 10%, transparent);
  color: var(--color-success);
}

.add-form {
  border-color: var(--color-border);
}

.lens-toggle {
  display: inline-flex;
  gap: 2px;
  padding: 3px;
  border-radius: 10px;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
}

.lens-toggle__btn {
  padding: 4px 12px;
  border-radius: 8px;
  border: none;
  background: transparent;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: color 160ms ease, background-color 160ms ease;
}

.lens-toggle__btn:hover {
  color: var(--color-text);
}

.lens-toggle__btn--active {
  background: var(--color-surface-raised);
  color: var(--color-primary);
}

.lens-toggle__btn:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 1px;
}

.spinner-primary {
  border-color: var(--color-primary) transparent transparent transparent;
}

.empty-state {
  text-align: center;
  padding: 32px 16px;
  border-radius: 12px;
  background: var(--color-surface-muted);
  border: 2px dashed var(--color-border);
}

.empty-state__icon {
  display: block;
  font-size: 36px;
  color: var(--color-text-muted);
  margin-bottom: 8px;
}

.mapping-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
}

.mapping-item__delete {
  padding: 8px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--color-danger);
  cursor: pointer;
  transition: background-color 160ms ease;
  flex-shrink: 0;
}

.mapping-item__delete:hover {
  background: color-mix(in srgb, var(--color-danger) 10%, transparent);
}

.mapping-item__delete:focus-visible {
  outline: 2px solid var(--color-danger);
  outline-offset: 1px;
}

.mapping-item__delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.03em;
  white-space: nowrap;
}

.badge--neutral {
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
}

.badge--primary {
  background: color-mix(in srgb, var(--color-primary) 12%, transparent);
  color: var(--color-primary);
}

.badge--success {
  background: color-mix(in srgb, var(--color-success) 12%, transparent);
  color: var(--color-success);
}

.badge--warning {
  background: color-mix(in srgb, var(--color-warning) 13%, transparent);
  color: var(--color-warning);
}

.badge--danger {
  background: color-mix(in srgb, var(--color-danger) 12%, transparent);
  color: var(--color-danger);
}

.badge--revenue {
  --badge-accent: #7c3aed;
  background: color-mix(in srgb, var(--badge-accent) 11%, transparent);
  color: var(--badge-accent);
}

html.dark .badge--revenue {
  --badge-accent: #c4b5fd;
}

.badge--db {
  background: color-mix(in srgb, var(--color-primary) 12%, transparent);
  color: var(--color-primary);
}

.badge--cr {
  background: color-mix(in srgb, var(--color-success) 12%, transparent);
  color: var(--color-success);
}

.badge--coretax {
  background: transparent;
  border: 1px solid color-mix(in srgb, var(--color-primary) 35%, transparent);
  color: var(--color-primary);
}

.type-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--color-border);
  cursor: pointer;
  transition: border-color 160ms ease, background-color 160ms ease;
}

.type-card:hover {
  border-color: var(--color-border-strong);
}

.type-card--active {
  border-color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 8%, transparent);
}

.type-card__radio {
  width: 16px;
  height: 16px;
  accent-color: var(--color-primary);
}
</style>
