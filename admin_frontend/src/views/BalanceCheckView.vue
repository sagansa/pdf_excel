<template>
  <div class="space-y-6">
    <PageHeader
      eyebrow="Integritas Data"
      icon="bi bi-shield-check"
      title="Cek Kontinuitas Saldo"
      subtitle="Verifikasi saldo berjalan antar-transaksi & deteksi statement yang bolong per akun bank."
    >
      <template #actions>
        <Button variant="secondary" :disabled="loading" @click="loadBalanceCheck" class="gap-2">
          <i class="bi bi-arrow-clockwise" :class="{ 'animate-spin': loading }"></i>
          <span>Refresh</span>
        </Button>
      </template>
    </PageHeader>

    <!-- Summary -->
    <div v-if="!loading && summary" class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <StatCard icon="bi bi-bank" label="Akun Bank" :value="summary.accounts_total" variant="primary" />
      <StatCard icon="bi bi-exclamation-triangle" label="Akun dengan Break" :value="summary.accounts_with_breaks" variant="warning" />
      <StatCard icon="bi bi-bug" label="Total Break" :value="summary.total_breaks" variant="danger" />
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-20 grayscale opacity-50">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
      <p class="mt-4 text-xs font-bold uppercase tracking-widest text-theme-muted">Memuat Analisis Saldo...</p>
    </div>

    <!-- No data -->
    <div v-if="!loading && accounts.length === 0" class="flex flex-col items-center justify-center py-24 text-center">
      <i class="bi bi-inbox text-5xl text-theme-muted opacity-30"></i>
      <p class="mt-4 text-sm font-bold text-theme-muted">Belum ada transaksi bank untuk dianalisis.</p>
    </div>

    <!-- Accounts list -->
    <div v-if="!loading" class="space-y-4">
      <SectionCard
        v-for="account in accounts"
        :key="`${account.bank_code}-${account.account_number}`"
        body-class="p-4"
      >
        <div class="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div class="flex items-center gap-2">
              <span class="font-bold">{{ account.bank_code }}</span>
              <span class="text-xs text-theme-muted font-mono">{{ account.account_number }}</span>
              <span
                class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
                :class="account.breaks.length
                  ? 'bg-danger/10 text-danger'
                  : 'bg-success/10 text-success'"
              >
                {{ account.breaks.length ? `${account.breaks.length} break` : 'Kontinu' }}
              </span>
              <span
                v-if="!account.has_running_balance"
                class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-theme-surface-2 text-theme-muted"
                title="Data lama sebelum kolom saldo tersimpan — belum bisa diverifikasi"
              >
                Tanpa data saldo
              </span>
            </div>
            <p class="text-xs text-theme-muted mt-1">
              {{ account.transaction_count }} transaksi · {{ account.first_date || '-' }} s/d {{ account.last_date || '-' }}
              <template v-if="account.has_running_balance">· {{ account.verified_count }} diverifikasi</template>
            </p>
          </div>
          <button
            v-if="account.breaks.length"
            class="text-xs font-bold flex items-center gap-1 text-theme-muted hover:text-primary"
            @click="toggleAccount(account)"
          >
            <i class="bi" :class="isExpanded(account) ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
            {{ isExpanded(account) ? 'Tutup detail' : 'Lihat detail' }}
          </button>
        </div>

        <!-- Breaks detail -->
        <div v-if="account.breaks.length && isExpanded(account)" class="mt-4 space-y-2">
          <div
            v-for="(brk, index) in account.breaks"
            :key="index"
            class="rounded-xl border p-3 text-xs"
            :class="brk.type === 'balance_mismatch'
              ? 'bg-danger/5 border-danger/20'
              : 'bg-warning/5 border-warning/20'"
          >
            <template v-if="brk.type === 'balance_mismatch'">
              <div class="flex items-center gap-2 font-bold">
                <i class="bi bi-graph-down-arrow text-danger"></i>
                Saldo tidak nyambung · {{ brk.txn_date }}
              </div>
              <p class="mt-1 text-theme-muted">
                {{ brk.description }} <span class="opacity-60">({{ brk.source_file || '-' }})</span>
              </p>
              <p class="mt-1 font-mono">
                Diharapkan {{ formatCurrency(brk.expected) }} · Tercatat {{ formatCurrency(brk.actual) }}
                · Selisih <strong :class="brk.diff < 0 ? 'text-danger' : 'text-success'">{{ formatCurrency(brk.diff) }}</strong>
              </p>
              <p class="mt-1 text-theme-muted italic">
                Kemungkinan ada transaksi atau statement yang belum diupload di antara titik ini.
              </p>
            </template>
            <template v-else-if="brk.type === 'statement_gap'">
              <div class="flex items-center gap-2 font-bold">
                <i class="bi bi-calendar-x text-warning"></i>
                Celah {{ brk.gap_days }} hari antar statement
              </div>
              <p class="mt-1 font-mono">{{ brk.gap_from }} s/d {{ brk.gap_to }}</p>
              <p class="mt-1 text-theme-muted">
                {{ brk.previous_file }} → {{ brk.next_file }} — periksa statement periode tersebut.
              </p>
            </template>
          </div>
        </div>
      </SectionCard>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import PageHeader from '../components/ui/PageHeader.vue';
import SectionCard from '../components/ui/SectionCard.vue';
import StatCard from '../components/ui/StatCard.vue';
import Button from '../components/ui/Button.vue';

const loading = ref(false);
const accounts = ref([]);
const summary = ref(null);
const expanded = ref(new Set());

const formatCurrency = (amount) => `Rp ${new Intl.NumberFormat('id-ID').format(amount || 0)}`;

const isExpanded = (account) => expanded.value.has(`${account.bank_code}-${account.account_number}`);

const toggleAccount = (account) => {
  const key = `${account.bank_code}-${account.account_number}`;
  if (expanded.value.has(key)) {
    expanded.value.delete(key);
  } else {
    expanded.value.add(key);
  }
};

const loadBalanceCheck = async () => {
  loading.value = true;
  try {
    const response = await fetch('/api/reports/balance-check');
    const data = await response.json();
    if (data.success) {
      accounts.value = data.data.accounts;
      summary.value = data.data;
      // Auto-expand akun yang bermasalah.
      expanded.value = new Set(
        accounts.value
          .filter((account) => account.breaks.length)
          .map((account) => `${account.bank_code}-${account.account_number}`),
      );
    }
  } catch (error) {
    console.error('Error loading balance check:', error);
  } finally {
    loading.value = false;
  }
};

onMounted(loadBalanceCheck);
</script>
