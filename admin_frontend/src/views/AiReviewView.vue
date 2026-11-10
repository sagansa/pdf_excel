<template>
  <div class="space-y-6">
    <PageHeader
      eyebrow="AI Review"
      icon="bi bi-stars"
      title="Review Saran AI"
      subtitle="Transaksi dengan saran mark ber-confidence rendah — terima atau tolak sekaligus."
    >
      <template #actions>
        <div class="flex items-center gap-2">
          <Button variant="secondary" :disabled="loading || !items.length" @click="loadQueue" class="gap-2">
            <i class="bi bi-arrow-clockwise" :class="{ 'animate-spin': loading }"></i>
            <span>Refresh</span>
          </Button>
          <Button
            variant="primary"
            :disabled="loading || !selected.size || deciding"
            @click="decide('accept')"
            class="gap-2"
          >
            <i class="bi bi-check-lg"></i>
            <span>Terima ({{ selected.size }})</span>
          </Button>
          <Button
            variant="danger"
            :disabled="loading || !selected.size || deciding"
            @click="decide('reject')"
            class="gap-2"
          >
            <i class="bi bi-x-lg"></i>
            <span>Tolak</span>
          </Button>
        </div>
      </template>
    </PageHeader>

    <!-- Threshold info -->
    <div class="rounded-2xl border bg-theme-surface border-theme-border p-4 text-xs flex items-center gap-3">
      <i class="bi bi-info-circle text-primary"></i>
      <span>
        Menampilkan saran ber-status <strong>pending</strong> dengan confidence &lt;
        <strong>{{ (threshold || 0.9).toFixed(2) }}</strong> (threshold auto-apply — atur di Settings).
        {{ items.length }} transaksi menunggu review.
      </span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-20 grayscale opacity-50">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
      <p class="mt-4 text-xs font-bold uppercase tracking-widest text-theme-muted">Memuat Antrian Review...</p>
    </div>

    <!-- Empty -->
    <div v-if="!loading && !items.length" class="flex flex-col items-center justify-center py-24 text-center">
      <i class="bi bi-emoji-smile text-5xl text-theme-muted opacity-30"></i>
      <p class="mt-4 text-sm font-bold text-theme-muted">Tidak ada saran yang menunggu review. 🎉</p>
    </div>

    <!-- Items -->
    <SectionCard v-if="!loading && items.length" body-class="p-0">
      <div class="overflow-x-auto">
        <table class="report-table">
          <thead>
            <tr>
              <th class="w-10">
                <input
                  type="checkbox"
                  class="rounded border-[var(--color-border)] text-[var(--color-primary)]"
                  :checked="allSelected"
                  @change="toggleAll"
                >
              </th>
              <th class="text-left">Tanggal</th>
              <th class="text-left">Deskripsi</th>
              <th class="text-left">Saran Mark</th>
              <th class="text-right">Confidence</th>
              <th class="text-right">Jumlah</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td>
                <input
                  type="checkbox"
                  class="rounded border-[var(--color-border)] text-[var(--color-primary)]"
                  :checked="selected.has(item.id)"
                  @change="toggle(item.id)"
                >
              </td>
              <td class="whitespace-nowrap">{{ formatDate(item.txn_date) }}</td>
              <td class="text-left">
                <p class="truncate max-w-md" :title="item.clean_description || item.description">
                  {{ item.clean_description || item.description }}
                </p>
                <p v-if="item.ai_reason" class="text-[10px] text-theme-muted truncate max-w-md">{{ item.ai_reason }}</p>
              </td>
              <td class="text-left font-medium">{{ item.suggested_mark_name || '—' }}</td>
              <td class="text-right">
                <span
                  class="font-mono font-bold"
                  :class="confidenceClass(item.ai_confidence)"
                >{{ formatConfidence(item.ai_confidence) }}</span>
              </td>
              <td class="text-right font-mono">{{ getAmountSign(item.db_cr) }}{{ formatAmount(item.amount) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </SectionCard>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import PageHeader from '../components/ui/PageHeader.vue';
import SectionCard from '../components/ui/SectionCard.vue';
import Button from '../components/ui/Button.vue';

const loading = ref(false);
const deciding = ref(false);
const items = ref([]);
const threshold = ref(null);
const selected = ref(new Set());

const allSelected = computed(() =>
  items.value.length > 0 && items.value.every((item) => selected.value.has(item.id)),
);

const toggle = (id) => {
  const next = new Set(selected.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  selected.value = next;
};

const toggleAll = () => {
  selected.value = allSelected.value
    ? new Set()
    : new Set(items.value.map((item) => item.id));
};

const formatAmount = (num) => new Intl.NumberFormat('id-ID').format(num || 0);
const getAmountSign = (dbCr) => (String(dbCr || '').toUpperCase() === 'DB' ? '+' : '−');
const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('id-ID', { year: 'numeric', month: 'short', day: 'numeric' });
};
const formatConfidence = (value) => (value == null ? '—' : `${Math.round((value || 0) * 100)}%`);
const confidenceClass = (value) => {
  if (value == null) return 'text-theme-muted';
  if (value >= 0.75) return 'text-success';
  if (value >= 0.5) return 'text-warning';
  return 'text-danger';
};

const loadQueue = async () => {
  loading.value = true;
  try {
    const response = await fetch('/api/transactions/ai-review-queue');
    const data = await response.json();
    items.value = data.items || [];
    threshold.value = data.threshold;
    selected.value = new Set();
  } catch (error) {
    console.error('Error loading review queue:', error);
  } finally {
    loading.value = false;
  }
};

const decide = async (decision) => {
  if (!selected.value.size) return;
  deciding.value = true;
  try {
    await fetch('/api/transactions/ai-decision-bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision, transaction_ids: [...selected.value] }),
    });
    await loadQueue();
  } catch (error) {
    console.error('Error deciding suggestions:', error);
  } finally {
    deciding.value = false;
  }
};

onMounted(loadQueue);
</script>
