<template>
  <div class="space-y-6">
    <SectionCard
      title="Inventory Balances"
      subtitle="Use 31 December remaining storage snapshots with latest COGS price, then review before saving."
      body-class="p-6 space-y-6"
    >
      <template #actions>
        <div class="flex items-center gap-3">
          <div v-if="isAutoLoading" class="inventory-saving">
            <div class="inventory-saving__spinner"></div>
            <span>Calculating auto value...</span>
          </div>
          <div v-if="isSaving" class="inventory-saving">
            <div class="inventory-saving__spinner"></div>
            <span>Saving...</span>
          </div>
        </div>
      </template>

      <div class="space-y-4">
        <div v-if="autoError" class="inventory-alert inventory-alert--danger">
          <i class="bi bi-exclamation-octagon-fill"></i>
          <span>{{ autoError }}</span>
        </div>

        <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <section class="inventory-auto-card">
            <div class="inventory-auto-card__header">
              <div>
                <h4 class="inventory-auto-card__title">Beginning Auto Snapshot</h4>
                <p class="inventory-auto-card__subtitle">
                  Quantity on {{ autoBalances.beginning.snapshot_date || `${yearDisplay - 1}-12-31` }}
                </p>
              </div>
              <button
                type="button"
                class="btn-secondary !py-2 !text-xs"
                :disabled="isAutoLoading || !getSnapshotItems('beginning').length"
                @click="applyAutoBalance('beginning')"
              >
                Apply to Form
              </button>
            </div>

            <div v-if="isAutoLoading" class="inventory-auto-card__loading">
              <div class="inventory-auto-card__skeleton"></div>
              <div class="inventory-auto-card__skeleton"></div>
              <div class="inventory-auto-card__skeleton"></div>
            </div>

            <div v-else class="inventory-auto-card__body">
              <div class="inventory-auto-metric">
                <span class="inventory-auto-metric__label">Valuation</span>
                <span class="inventory-auto-metric__value">{{ formatCurrency(getResolvedAutoAmount('beginning')) }}</span>
              </div>
              <div class="inventory-auto-metric">
                <span class="inventory-auto-metric__label">Quantity</span>
                <span class="inventory-auto-metric__value">{{ formatDisplayNumber(autoBalances.beginning.quantity || 0) }}</span>
              </div>
              <div class="inventory-auto-metric">
                <span class="inventory-auto-metric__label">Priced Products</span>
                <span class="inventory-auto-metric__value">
                  {{ getResolvedPricedCount('beginning') }}/{{ getSnapshotLineCount('beginning') }}
                </span>
              </div>
              <div class="inventory-auto-metric">
                <span class="inventory-auto-metric__label">Missing Price</span>
                <span class="inventory-auto-metric__value" :class="{ 'text-[var(--color-warning)]': getResolvedMissingCount('beginning') > 0 }">
                  {{ getResolvedMissingCount('beginning') }}
                </span>
              </div>
            </div>

            <div
              v-if="!isAutoLoading && getSnapshotItems('beginning').length > 0"
              class="inventory-detail-list"
            >
              <div class="inventory-detail-list__header">
                <h5 class="inventory-detail-list__title">Detailed Product Valuation</h5>
                <p class="inventory-detail-list__subtitle">
                  Product mengikuti monitoring list. Price dapat diambil dari referensi COGS agar sumber nominal jelas.
                </p>
              </div>

              <div class="inventory-detail-list__body">
                <div class="inventory-detail-table">
                  <div class="inventory-detail-table__head">
                    <div>Product</div>
                    <div>Quantity</div>
                    <div>COGS Price</div>
                    <div>Total Price</div>
                  </div>

                  <div
                    v-for="item in getSnapshotItems('beginning')"
                    :key="`begin-${item.product_id}`"
                    class="inventory-detail-row"
                  >
                    <div class="inventory-detail-row__product">
                      <div class="inventory-detail-row__name">{{ item.product_name }}</div>
                      <div class="inventory-detail-row__meta">
                        <span v-if="item.unit_name">{{ item.unit_name }}</span>
                        <span v-for="monitor in item.monitoring_names || []" :key="`${item.product_id}-${monitor}`">
                          {{ monitor }}
                        </span>
                      </div>
                    </div>

                    <div class="inventory-detail-row__quantity">
                      {{ formatDisplayNumber(item.quantity || 0) }}
                      <div
                        v-if="Number(item.raw_quantity || 0) || Number(item.coefficient || 1) !== 1"
                        class="inventory-detail-row__quantity-meta"
                      >
                        {{ formatDisplayNumber(item.raw_quantity || 0) }}
                        <span>×</span>
                        {{ formatDisplayNumber(item.coefficient || 1) }}
                      </div>
                    </div>

                    <div class="inventory-detail-row__price">
                      <SelectInput
                        :model-value="getDisplayedPriceReference('beginning', item)"
                        :options="getSnapshotPriceOptions(item)"
                        :placeholder="item.has_price ? 'Use auto matched price' : 'Select COGS price'"
                        size="sm"
                        @update:model-value="updateManualPriceSelection('beginning', item.product_id, $event)"
                      />
                      <div class="inventory-detail-row__price-meta">
                        <template v-if="getSelectedManualPrice('beginning', item.product_id)">
                          Manual:
                          {{ formatCurrency(getSelectedManualPrice('beginning', item.product_id, item)?.unit_price || 0) }}
                          <span v-if="getSelectedManualPrice('beginning', item.product_id, item)?.batch_memo">
                            • {{ getSelectedManualPrice('beginning', item.product_id, item)?.batch_memo }}
                          </span>
                          <span v-if="getSelectedManualPrice('beginning', item.product_id, item)?.effective_date">
                            • {{ getSelectedManualPrice('beginning', item.product_id, item)?.effective_date }}
                          </span>
                        </template>
                        <template v-else-if="item.has_price">
                          Auto: {{ formatCurrency(item.unit_price || 0) }}
                          <span v-if="item.price_batch_memo"> • {{ item.price_batch_memo }}</span>
                          <span v-if="item.price_effective_date"> • {{ item.price_effective_date }}</span>
                        </template>
                        <template v-else>
                          No auto price
                        </template>
                      </div>
                    </div>

                    <div class="inventory-detail-row__total">
                      <template v-if="getResolvedTotalValue('beginning', item) !== null">
                        {{ formatCurrency(getResolvedTotalValue('beginning', item)) }}
                        <div class="inventory-detail-row__total-meta">
                          {{ formatDisplayNumber(item.quantity || 0) }}
                          <span>×</span>
                          {{ formatCurrency(getResolvedUnitPrice('beginning', item) || 0) }}
                        </div>
                      </template>
                      <template v-else>
                        No price
                      </template>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section class="inventory-auto-card">
            <div class="inventory-auto-card__header">
              <div>
                <h4 class="inventory-auto-card__title">Ending Auto Snapshot</h4>
                <p class="inventory-auto-card__subtitle">
                  Quantity on {{ autoBalances.ending.snapshot_date || `${yearDisplay}-12-31` }}
                </p>
              </div>
              <button
                type="button"
                class="btn-secondary !py-2 !text-xs"
                :disabled="isAutoLoading || !getSnapshotItems('ending').length"
                @click="applyAutoBalance('ending')"
              >
                Apply to Form
              </button>
            </div>

            <div v-if="isAutoLoading" class="inventory-auto-card__loading">
              <div class="inventory-auto-card__skeleton"></div>
              <div class="inventory-auto-card__skeleton"></div>
              <div class="inventory-auto-card__skeleton"></div>
            </div>

            <div v-else class="inventory-auto-card__body">
              <div class="inventory-auto-metric">
                <span class="inventory-auto-metric__label">Valuation</span>
                <span class="inventory-auto-metric__value">{{ formatCurrency(getResolvedAutoAmount('ending')) }}</span>
              </div>
              <div class="inventory-auto-metric">
                <span class="inventory-auto-metric__label">Quantity</span>
                <span class="inventory-auto-metric__value">{{ formatDisplayNumber(autoBalances.ending.quantity || 0) }}</span>
              </div>
              <div class="inventory-auto-metric">
                <span class="inventory-auto-metric__label">Priced Products</span>
                <span class="inventory-auto-metric__value">
                  {{ getResolvedPricedCount('ending') }}/{{ getSnapshotLineCount('ending') }}
                </span>
              </div>
              <div class="inventory-auto-metric">
                <span class="inventory-auto-metric__label">Missing Price</span>
                <span class="inventory-auto-metric__value" :class="{ 'text-[var(--color-warning)]': getResolvedMissingCount('ending') > 0 }">
                  {{ getResolvedMissingCount('ending') }}
                </span>
              </div>
            </div>

            <div
              v-if="!isAutoLoading && getSnapshotItems('ending').length > 0"
              class="inventory-detail-list"
            >
              <div class="inventory-detail-list__header">
                <h5 class="inventory-detail-list__title">Detailed Product Valuation</h5>
                <p class="inventory-detail-list__subtitle">
                  Product mengikuti monitoring list. Price dapat diambil dari referensi COGS agar sumber nominal jelas.
                </p>
              </div>

              <div class="inventory-detail-list__body">
                <div class="inventory-detail-table">
                  <div class="inventory-detail-table__head">
                    <div>Product</div>
                    <div>Quantity</div>
                    <div>COGS Price</div>
                    <div>Total Price</div>
                  </div>

                  <div
                    v-for="item in getSnapshotItems('ending')"
                    :key="`end-${item.product_id}`"
                    class="inventory-detail-row"
                  >
                    <div class="inventory-detail-row__product">
                      <div class="inventory-detail-row__name">{{ item.product_name }}</div>
                      <div class="inventory-detail-row__meta">
                        <span v-if="item.unit_name">{{ item.unit_name }}</span>
                        <span v-for="monitor in item.monitoring_names || []" :key="`${item.product_id}-${monitor}`">
                          {{ monitor }}
                        </span>
                      </div>
                    </div>

                    <div class="inventory-detail-row__quantity">
                      {{ formatDisplayNumber(item.quantity || 0) }}
                      <div
                        v-if="Number(item.raw_quantity || 0) || Number(item.coefficient || 1) !== 1"
                        class="inventory-detail-row__quantity-meta"
                      >
                        {{ formatDisplayNumber(item.raw_quantity || 0) }}
                        <span>×</span>
                        {{ formatDisplayNumber(item.coefficient || 1) }}
                      </div>
                    </div>

                    <div class="inventory-detail-row__price">
                      <SelectInput
                        :model-value="getDisplayedPriceReference('ending', item)"
                        :options="getSnapshotPriceOptions(item)"
                        :placeholder="item.has_price ? 'Use auto matched price' : 'Select COGS price'"
                        size="sm"
                        @update:model-value="updateManualPriceSelection('ending', item.product_id, $event)"
                      />
                      <div class="inventory-detail-row__price-meta">
                        <template v-if="getSelectedManualPrice('ending', item.product_id)">
                          Manual:
                          {{ formatCurrency(getSelectedManualPrice('ending', item.product_id, item)?.unit_price || 0) }}
                          <span v-if="getSelectedManualPrice('ending', item.product_id, item)?.batch_memo">
                            • {{ getSelectedManualPrice('ending', item.product_id, item)?.batch_memo }}
                          </span>
                          <span v-if="getSelectedManualPrice('ending', item.product_id, item)?.effective_date">
                            • {{ getSelectedManualPrice('ending', item.product_id, item)?.effective_date }}
                          </span>
                        </template>
                        <template v-else-if="item.has_price">
                          Auto: {{ formatCurrency(item.unit_price || 0) }}
                          <span v-if="item.price_batch_memo"> • {{ item.price_batch_memo }}</span>
                          <span v-if="item.price_effective_date"> • {{ item.price_effective_date }}</span>
                        </template>
                        <template v-else>
                          No auto price
                        </template>
                      </div>
                    </div>

                    <div class="inventory-detail-row__total">
                      <template v-if="getResolvedTotalValue('ending', item) !== null">
                        {{ formatCurrency(getResolvedTotalValue('ending', item)) }}
                        <div class="inventory-detail-row__total-meta">
                          {{ formatDisplayNumber(item.quantity || 0) }}
                          <span>×</span>
                          {{ formatCurrency(getResolvedUnitPrice('ending', item) || 0) }}
                        </div>
                      </template>
                      <template v-else>
                        No price
                      </template>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section class="inventory-panel inventory-panel--start">
          <div class="inventory-panel__header">
            <div class="inventory-panel__icon inventory-panel__icon--start">
              <i class="bi bi-box-arrow-in-right"></i>
            </div>
            <div>
              <h4 class="inventory-panel__title">Beginning Inventory</h4>
              <p class="inventory-panel__subtitle">Nilai dan kuantitas saldo awal.</p>
            </div>
          </div>

          <div class="space-y-4">
            <FormField label="Valuation Amount (Rp)" label-class="!text-xs">
              <div class="relative">
                <span class="inventory-prefix">Rp</span>
                <input
                  :value="formatDisplayNumber(form.beginning_inventory_amount)"
                  type="text"
                  inputmode="decimal"
                  class="inventory-input inventory-input--currency"
                  placeholder="0"
                  @input="updateNumericField('beginning_inventory_amount', $event.target.value)"
                >
              </div>
            </FormField>

            <FormField label="Quantity (Unit)" label-class="!text-xs">
              <input
                :value="formatDisplayNumber(form.beginning_inventory_qty)"
                type="text"
                inputmode="decimal"
                class="inventory-input"
                placeholder="0"
                @input="updateNumericField('beginning_inventory_qty', $event.target.value)"
              >
            </FormField>
          </div>
        </section>

        <section class="inventory-panel inventory-panel--end">
          <div class="inventory-panel__header">
            <div class="inventory-panel__icon inventory-panel__icon--end">
              <i class="bi bi-box-arrow-left"></i>
            </div>
            <div>
              <h4 class="inventory-panel__title">Ending Inventory</h4>
              <p class="inventory-panel__subtitle">Nilai dan kuantitas saldo akhir.</p>
            </div>
          </div>

          <div class="space-y-4">
            <FormField label="Valuation Amount (Rp)" label-class="!text-xs">
              <div class="relative">
                <span class="inventory-prefix">Rp</span>
                <input
                  :value="formatDisplayNumber(form.ending_inventory_amount)"
                  type="text"
                  inputmode="decimal"
                  class="inventory-input inventory-input--currency"
                  placeholder="0"
                  @input="updateNumericField('ending_inventory_amount', $event.target.value)"
                >
              </div>
            </FormField>

            <FormField label="Quantity (Unit)" label-class="!text-xs">
              <input
                :value="formatDisplayNumber(form.ending_inventory_qty)"
                type="text"
                inputmode="decimal"
                class="inventory-input"
                placeholder="0"
                @input="updateNumericField('ending_inventory_qty', $event.target.value)"
              >
            </FormField>
          </div>
        </section>
      </div>

      <div class="inventory-footer">
        <div class="inventory-note">
          <i class="bi bi-info-circle"></i>
          <span>These values will be used to calculate HPP (COGS) in the Income Statement.</span>
        </div>
        <button
          @click="saveBalances"
          :disabled="isSaving || !companyId"
          class="btn-primary gap-2 px-5 py-3 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <i class="bi bi-check-lg text-base"></i>
          Save Adjustments
        </button>
      </div>
    </SectionCard>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useNotifications } from '../../composables/useNotifications';
import FormField from '../ui/FormField.vue';
import SectionCard from '../ui/SectionCard.vue';
import SelectInput from '../ui/SelectInput.vue';
import { useReportsStore } from '../../stores/reports';

const props = defineProps({
  companyId: {
    type: String,
    default: null
  },
  year: {
    type: [String, Number],
    default: new Date().getFullYear()
  }
});

const emit = defineEmits(['saved', 'update:year']);
const store = useReportsStore();
const notifications = useNotifications();
const isSaving = ref(false);
const isAutoLoading = ref(false);
const autoError = ref('');
const autoBalances = ref({
  beginning: {},
  ending: {}
});
const manualPriceSelections = ref({
  beginning: {},
  ending: {}
});

const form = ref({
  beginning_inventory_amount: 0,
  beginning_inventory_qty: 0,
  ending_inventory_amount: 0,
  ending_inventory_qty: 0,
  is_manual: true
});

const inventoryDelta = computed(() => (
  Number(form.value.ending_inventory_amount || 0) - Number(form.value.beginning_inventory_amount || 0)
));

const yearDisplay = computed(() => Number(props.year || new Date().getFullYear()));

const getSnapshotPriceOptions = (item) => (
  ((item?.price_options) || []).map((priceOption) => ({
    value: priceOption.reference_id,
    label: `${formatCurrency(priceOption.unit_price || 0)}${priceOption.batch_memo ? ` • ${priceOption.batch_memo}` : ''}${priceOption.effective_date ? ` • ${priceOption.effective_date}` : ''}`
  }))
);

const getSnapshotItems = (target) => (
  ((autoBalances.value[target]?.items) || []).filter(
    (item) => Number(item?.quantity || 0) > 0
  )
);

const getSnapshotLineCount = (target) => getSnapshotItems(target).length;

const getSelectedManualPrice = (target, productId, item = null) => {
  const selectedReferenceId = manualPriceSelections.value[target]?.[productId];
  if (!selectedReferenceId) return null;

  const rowItem = item || getSnapshotItems(target).find(
    (entry) => String(entry.product_id) === String(productId)
  );
  return ((rowItem?.price_options) || []).find(
    (priceOption) => String(priceOption.reference_id) === String(selectedReferenceId)
  ) || null;
};

const getDisplayedPriceReference = (target, item) => (
  manualPriceSelections.value[target]?.[item.product_id]
  || item.price_reference_id
  || ''
);

const getResolvedAutoAmount = (target) => {
  return getSnapshotItems(target).reduce((sum, item) => {
    const totalValue = getResolvedTotalValue(target, item);
    if (totalValue === null) return sum;
    return sum + Number(totalValue || 0);
  }, 0);
};

const updateManualPriceSelection = (target, missingProductId, selectedProductId) => {
  manualPriceSelections.value = {
    ...manualPriceSelections.value,
    [target]: {
      ...manualPriceSelections.value[target],
      [missingProductId]: selectedProductId || ''
    }
  };
};

const getResolvedUnitPrice = (target, item) => {
  const selectedPrice = getSelectedManualPrice(target, item.product_id, item);
  if (selectedPrice) {
    return Number(selectedPrice.unit_price || 0);
  }

  if (item.has_price) {
    return Number(item.unit_price || 0);
  }

  return null;
};

const getResolvedTotalValue = (target, item) => {
  const resolvedUnitPrice = getResolvedUnitPrice(target, item);
  if (resolvedUnitPrice === null) {
    return null;
  }

  return Number(item.quantity || 0) * resolvedUnitPrice;
};

const getResolvedPricedCount = (target) => (
  getSnapshotItems(target).filter((item) => getResolvedUnitPrice(target, item) !== null).length
);

const getResolvedMissingCount = (target) => (
  getSnapshotItems(target).filter((item) => getResolvedUnitPrice(target, item) === null).length
);

const parseFormattedNumber = (value) => {
  const raw = String(value || '').trim();
  if (!raw) return 0;

  const normalized = raw
    .replace(/\s/g, '')
    .replace(/\./g, '')
    .replace(/,/g, '.')
    .replace(/[^\d.-]/g, '');

  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
};

const formatDisplayNumber = (value) => {
  const numeric = Number(value || 0);
  return numeric.toLocaleString('id-ID', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  });
};

const formatCurrency = (value) => `Rp ${formatDisplayNumber(value)}`;

const updateNumericField = (key, inputValue) => {
  form.value[key] = parseFormattedNumber(inputValue);
};

const fetchBalances = async () => {
  if (!props.companyId || !props.year) return;

  const balance = await store.fetchInventoryBalances(props.year, props.companyId);
  if (balance && Object.keys(balance).length > 0) {
    form.value = {
      beginning_inventory_amount: balance.beginning_inventory_amount || 0,
      beginning_inventory_qty: balance.beginning_inventory_qty || 0,
      ending_inventory_amount: balance.ending_inventory_amount || 0,
      ending_inventory_qty: balance.ending_inventory_qty || 0,
      is_manual: balance.is_manual ?? true
    };
    return;
  }

  form.value = {
    beginning_inventory_amount: 0,
    beginning_inventory_qty: 0,
    ending_inventory_amount: 0,
    ending_inventory_qty: 0,
    is_manual: true
  };
};

const fetchAutoBalances = async () => {
  if (!props.companyId || !props.year) return;

  isAutoLoading.value = true;
  autoError.value = '';
  try {
    const result = await store.fetchAutoInventoryBalances(props.year, props.companyId);
    autoBalances.value = {
      beginning: result.beginning || {},
      ending: result.ending || {}
    };
    manualPriceSelections.value = {
      beginning: {},
      ending: {}
    };
  } catch (err) {
    autoError.value = err?.response?.data?.error || err?.message || 'Failed to calculate auto inventory values';
  } finally {
    isAutoLoading.value = false;
  }
};

const applyAutoBalance = (target) => {
  const snapshot = autoBalances.value[target] || {};
  const resolvedAmount = getResolvedAutoAmount(target);
  if (target === 'beginning') {
    form.value.beginning_inventory_amount = Number(resolvedAmount || 0);
    form.value.beginning_inventory_qty = Number(snapshot.quantity || 0);
    return;
  }

  form.value.ending_inventory_amount = Number(resolvedAmount || 0);
  form.value.ending_inventory_qty = Number(snapshot.quantity || 0);
};

const saveBalances = async () => {
  if (!props.companyId || !props.year) return;

  isSaving.value = true;
  try {
    await store.saveInventoryBalances({
      ...form.value,
      company_id: props.companyId,
      year: parseInt(props.year, 10)
    });
    notifications.success('Inventory adjustment berhasil disimpan.');
    emit('saved');
  } catch (err) {
    notifications.error(err?.response?.data?.error || err?.message || 'Gagal menyimpan inventory adjustment.');
  } finally {
    isSaving.value = false;
  }
};

watch(() => [props.companyId, props.year], () => {
  fetchBalances();
  fetchAutoBalances();
}, { deep: true });

onMounted(() => {
  fetchBalances();
  fetchAutoBalances();
});
</script>

<style scoped>
.inventory-saving {
  @apply inline-flex items-center gap-2 text-xs font-medium;
  color: var(--color-primary);
}

.inventory-saving__spinner {
  @apply h-4 w-4 animate-spin rounded-full border-2 border-t-transparent;
  border-color: var(--color-primary);
}

.inventory-panel {
  @apply rounded-2xl p-5;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
}

.inventory-panel__header {
  @apply mb-5 flex items-center gap-3 border-b pb-3;
  border-color: var(--color-border);
}

.inventory-panel__icon {
  @apply flex h-10 w-10 items-center justify-center rounded-xl text-base;
}

.inventory-panel__icon--start {
  background: rgba(37, 99, 235, 0.12);
  color: #2563eb;
}

.inventory-panel__icon--end {
  background: rgba(180, 83, 9, 0.12);
  color: var(--color-warning);
}

.inventory-panel__title {
  @apply text-sm font-bold uppercase tracking-[0.18em];
  color: var(--color-text);
}

.inventory-panel__subtitle {
  @apply mt-1 text-xs;
  color: var(--color-text-muted);
}

.inventory-prefix {
  @apply pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm font-medium;
  color: var(--color-text-muted);
}

.inventory-input {
  @apply w-full rounded-xl px-3 py-2 text-right text-sm shadow-sm transition-all duration-200;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  color: var(--color-text);
}

.inventory-input--currency {
  @apply pl-10;
}

.inventory-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px var(--color-primary-ring);
  outline: none;
}

.inventory-footer {
  @apply flex flex-col gap-4 border-t pt-5 lg:flex-row lg:items-center lg:justify-between;
  border-color: var(--color-border);
}

.inventory-note {
  @apply flex items-center gap-2 text-xs italic;
  color: var(--color-text-muted);
}

.inventory-alert {
  @apply flex items-center gap-2 rounded-2xl px-4 py-3 text-xs font-medium;
}

.inventory-alert--danger {
  background: rgba(185, 28, 28, 0.08);
  border: 1px solid rgba(185, 28, 28, 0.18);
  color: var(--color-danger);
}

.inventory-auto-card {
  @apply rounded-2xl p-5;
  background: color-mix(in srgb, var(--color-surface-muted) 86%, transparent 14%);
  border: 1px solid var(--color-border);
}

.inventory-auto-card__header {
  @apply mb-4 flex flex-col gap-3 border-b pb-3 md:flex-row md:items-start md:justify-between;
  border-color: var(--color-border);
}

.inventory-auto-card__title {
  @apply text-sm font-bold uppercase tracking-[0.18em];
  color: var(--color-text);
}

.inventory-auto-card__subtitle {
  @apply mt-1 text-xs;
  color: var(--color-text-muted);
}

.inventory-auto-card__body {
  @apply grid grid-cols-2 gap-3;
}

.inventory-auto-card__loading {
  @apply grid grid-cols-1 gap-3;
}

.inventory-auto-card__skeleton {
  @apply h-14 rounded-2xl animate-pulse;
  background: var(--color-surface-raised);
}

.inventory-auto-metric {
  @apply rounded-2xl px-4 py-3;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
}

.inventory-auto-metric__label {
  @apply text-[10px] font-bold uppercase tracking-[0.16em];
  color: var(--color-text-muted);
}

.inventory-auto-metric__value {
  @apply mt-2 block text-sm font-semibold;
  color: var(--color-text);
}

.inventory-detail-list {
  @apply mt-4 rounded-2xl border;
  border-color: var(--color-border);
  background: color-mix(in srgb, var(--color-surface) 88%, transparent 12%);
}

.inventory-detail-list__header {
  @apply border-b px-4 py-3;
  border-color: var(--color-border);
}

.inventory-detail-list__title {
  @apply text-xs font-bold uppercase tracking-[0.16em];
  color: var(--color-text);
}

.inventory-detail-list__subtitle {
  @apply mt-1 text-xs;
  color: var(--color-text-muted);
}

.inventory-detail-list__body {
  @apply max-h-[30rem] overflow-auto;
}

.inventory-detail-table {
  @apply min-w-[860px];
}

.inventory-detail-table__head {
  @apply grid grid-cols-[minmax(240px,1.2fr)_120px_minmax(320px,1fr)_140px] gap-3 border-b px-4 py-3 text-[11px] font-bold uppercase tracking-[0.16em];
  border-color: var(--color-border);
  color: var(--color-text-muted);
}

.inventory-detail-row {
  @apply grid grid-cols-[minmax(240px,1.2fr)_120px_minmax(320px,1fr)_140px] gap-3 border-b px-4 py-4 items-start;
  border-color: color-mix(in srgb, var(--color-border) 78%, transparent 22%);
}

.inventory-detail-row:last-child {
  border-bottom: none;
}

.inventory-detail-row__product {
  @apply min-w-0;
}

.inventory-detail-row__name {
  @apply text-sm font-semibold;
  color: var(--color-text);
}

.inventory-detail-row__meta {
  @apply mt-1 flex flex-wrap gap-2 text-xs;
  color: var(--color-text-muted);
}

.inventory-detail-row__meta span {
  @apply inline-flex items-center rounded-full px-2 py-1;
  background: color-mix(in srgb, var(--color-surface-raised) 78%, transparent 22%);
  border: 1px solid color-mix(in srgb, var(--color-border) 75%, transparent 25%);
}

.inventory-detail-row__quantity,
.inventory-detail-row__total {
  @apply pt-2 text-sm font-semibold;
  color: var(--color-text);
}

.inventory-detail-row__quantity-meta,
.inventory-detail-row__total-meta {
  @apply mt-1 text-xs font-medium;
  color: var(--color-text-muted);
}

.inventory-detail-row__price {
  @apply space-y-2;
}

.inventory-detail-row__price-meta {
  @apply text-xs;
  color: var(--color-text-muted);
}

.inventory-detail-row__total {
  @apply text-right;
}

@media (max-width: 1024px) {
  .inventory-detail-table {
    @apply min-w-[760px];
  }
}
</style>
