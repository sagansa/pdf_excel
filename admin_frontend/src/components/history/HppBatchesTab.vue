<template>
  <div class="space-y-6">
    <SectionCard
      title="COGS Batches"
      subtitle="Kelompokkan transaksi pembelian dan turunkan harga pokok per item secara konsisten."
      body-class="hidden"
    >
      <template #actions>
        <button @click="openCreateModal" class="btn-primary gap-2 text-sm">
          <i class="bi bi-plus-lg"></i>
          Create New Batch
        </button>
      </template>
    </SectionCard>

    <!-- Loading State -->
    <SectionCard v-if="batchStore.isLoading && !batchStore.batches.length" body-class="p-12">
      <div class="flex justify-center">
        <div class="hpp-batches__spinner"></div>
      </div>
    </SectionCard>
    
    <SectionCard v-else-if="!batchStore.batches.length" body-class="p-12">
      <div class="flex flex-col items-center text-center">
        <div class="hpp-batches__empty-icon">
          <i class="bi bi-boxes text-3xl"></i>
        </div>
        <h3 class="mt-4 text-lg font-bold text-theme">No COGS Batches Found</h3>
        <p class="mt-2 max-w-sm text-sm text-muted">
          Buat batch baru untuk mengikat transaksi pembelian ke referensi item dan menghasilkan unit cost yang bisa diaudit.
        </p>
        <button @click="openCreateModal" class="btn-primary mt-6 gap-2">
          <i class="bi bi-plus-lg"></i>
          Create First Batch
        </button>
      </div>
    </SectionCard>

    <div v-else class="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
      <article
        v-for="batch in batchStore.batches"
        :key="batch.id"
        class="surface-card interactive-card hpp-batch-card group p-5"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0 space-y-3">
            <div class="flex flex-wrap items-center gap-2">
              <span class="stat-pill !px-2.5 !py-1 text-[10px] uppercase tracking-[0.18em]">Batch</span>
              <span class="text-xs text-muted">{{ formatDate(batch.batch_date || batch.created_at) }}</span>
            </div>

            <div>
              <h4 class="truncate text-xl font-bold text-theme" :title="batch.memo">{{ batch.memo || 'Unnamed Batch' }}</h4>
              <p class="mt-1 text-sm text-muted">Hubungkan transaksi IDR ke item referensi untuk membentuk harga pokok per unit.</p>
            </div>
          </div>

          <div class="flex gap-2 opacity-100 transition-opacity md:opacity-0 md:group-hover:opacity-100">
            <button @click="openEditModal(batch)" class="btn-ghost rounded-xl p-2" title="Edit Batch">
              <i class="bi bi-pencil-square"></i>
            </button>
            <button @click="confirmDelete(batch)" class="btn-ghost rounded-xl p-2 text-red-500 hover:!text-red-400" title="Delete Batch">
              <i class="bi bi-trash3"></i>
            </button>
          </div>
        </div>

        <div class="mt-5 grid grid-cols-2 gap-3">
          <div class="surface-card-muted p-4">
            <p class="text-[11px] font-bold uppercase tracking-[0.22em] text-muted">Transactions</p>
            <p class="mt-2 text-2xl font-bold text-theme mono">{{ batch.txn_count }}</p>
          </div>
          <div class="surface-card-muted p-4">
            <p class="text-[11px] font-bold uppercase tracking-[0.22em] text-muted">Items Linked</p>
            <p class="mt-2 text-2xl font-bold text-theme mono">{{ batch.item_count ?? batch.product_count }}</p>
          </div>
        </div>

        <div class="mt-5 rounded-2xl border p-4 hpp-batch-card__prices">
          <div class="flex items-center justify-between gap-3">
            <span class="text-[11px] font-bold uppercase tracking-[0.22em] text-muted">Unit Prices</span>
            <span class="text-xs text-muted">{{ batch.unit_prices?.length || 0 }} item</span>
          </div>

          <div v-if="batch.unit_prices?.length" class="mt-3 space-y-2">
            <div
              v-for="(price, idx) in batch.unit_prices"
              :key="idx"
              class="hpp-batch-card__price-row"
            >
              <div class="min-w-0">
                <div class="truncate text-sm text-theme" :title="price.item_name || price.product_name">
                  {{ price.item_name || price.product_name }}
                </div>
                <div
                  v-if="price.details_summary"
                  class="truncate text-[11px] text-muted"
                  :title="price.details_summary"
                >
                  {{ price.details_summary }}
                </div>
              </div>
              <span class="mono text-sm font-bold text-theme whitespace-nowrap">
                Rp {{ formatNumber(price.unit_price) }}/unit
              </span>
            </div>
          </div>

          <div v-else class="mt-3 rounded-xl border border-dashed px-4 py-5 text-center text-sm text-muted">
            Belum ada unit price yang diturunkan dari batch ini.
          </div>
        </div>
      </article>
    </div>

    <!-- Modal Form -->
    <HppBatchFormModal
      v-if="showFormModal"
      :is-open="showFormModal"
      :batch-id="selectedBatchId"
      :company-id="companyId"
      @close="closeFormModal"
      @saved="onBatchSaved"
    />

    <!-- Delete Confirm -->
    <ConfirmModal
      :is-open="showDeleteConfirm"
      title="Delete Batch"
      message="Are you sure you want to delete this COGS batch? The specific transactions and products will not be deleted, but they will be unlinked from each other."
      confirm-text="Delete Batch"
      variant="danger"
      :loading="isDeleting"
      @close="showDeleteConfirm = false"
      @confirm="executeDelete"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useHppBatchStore } from '../../stores/hppBatch';
import ConfirmModal from '../ui/ConfirmModal.vue';
import HppBatchFormModal from './HppBatchFormModal.vue';
import SectionCard from '../ui/SectionCard.vue';
import { useNotifications } from '../../composables/useNotifications';

const props = defineProps({
  companyId: String,
  year: [String, Number]
});

const batchStore = useHppBatchStore();
const notifications = useNotifications();

const showFormModal = ref(false);
const selectedBatchId = ref(null);

const showDeleteConfirm = ref(false);
const batchToDelete = ref(null);
const isDeleting = ref(false);

const loadData = async () => {
  await batchStore.fetchBatches(props.companyId);
};

onMounted(() => {
  loadData();
});

watch(() => props.companyId, () => {
  loadData();
});

const openCreateModal = () => {
  selectedBatchId.value = null;
  showFormModal.value = true;
};

const openEditModal = (batch) => {
  selectedBatchId.value = batch.id;
  showFormModal.value = true;
};

const closeFormModal = () => {
  showFormModal.value = false;
  selectedBatchId.value = null;
};

const onBatchSaved = () => {
  loadData();
  closeFormModal();
  notifications.success('COGS batch berhasil disimpan.');
};

const confirmDelete = (batch) => {
  batchToDelete.value = batch;
  showDeleteConfirm.value = true;
};

const executeDelete = async () => {
  if (!batchToDelete.value) return;
  isDeleting.value = true;
  try {
    await batchStore.deleteBatch(batchToDelete.value.id);
    showDeleteConfirm.value = false;
    batchToDelete.value = null;
    notifications.success('COGS batch berhasil dihapus.');
  } catch (err) {
    notifications.error(`Failed to delete batch: ${err.message}`);
  } finally {
    isDeleting.value = false;
  }
};

const formatNumber = (val) => {
  return Number(val || 0).toLocaleString('id-ID');
};

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  // Handle ISO date format (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return dateStr.split(' ')[0]; // Fallback to original
  return date.toLocaleDateString('id-ID', { year: 'numeric', month: 'short', day: 'numeric' });
};
</script>

<style scoped>
.hpp-batches__spinner {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 9999px;
  border: 3px solid rgba(15, 118, 110, 0.14);
  border-top-color: var(--color-primary);
  animation: hpp-spin 0.8s linear infinite;
}

.hpp-batches__empty-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 4rem;
  height: 4rem;
  border-radius: 1.25rem;
  background: rgba(15, 118, 110, 0.1);
  color: var(--color-primary);
  border: 1px solid rgba(15, 118, 110, 0.18);
}

.hpp-batch-card {
  position: relative;
  overflow: hidden;
}

.hpp-batch-card::before {
  content: '';
  position: absolute;
  inset: 0 auto auto 0;
  width: 100%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(15, 118, 110, 0.45), transparent);
}

.hpp-batch-card__prices {
  background: var(--color-surface-muted);
  border-color: var(--color-border);
}

.hpp-batch-card__price-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.7rem 0.85rem;
  border-radius: 1rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

@keyframes hpp-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
