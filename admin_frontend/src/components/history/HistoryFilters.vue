<template>
  <SectionCard body-class="p-4 md:p-5" class="history-filters">
    <!-- Baris utama: filter yang menyertai alur kerja marking selalu tampak -->
    <div class="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1.2fr)_minmax(190px,0.9fr)_minmax(380px,1.5fr)_minmax(190px,0.8fr)_auto] xl:items-end">
      <FormField label="Search" label-class="text-[11px]">
        <TextInput
          :model-value="store.filters.search"
          placeholder="Description, amount, mark, COA, source file..."
          leading-icon="bi bi-search text-[10px]"
          size="sm"
          @update:model-value="store.setFilter('search', $event)"
        />
      </FormField>

      <FormField label="Mark Status" label-class="text-[11px]">
        <MultiSelect
          :key="`mark-filter-${store.filterResetToken}`"
          :model-value="store.filters.markStatus"
          :options="markOptions"
          placeholder="All mark status"
          @update:model-value="store.setFilter('markStatus', $event)"
        />
      </FormField>

      <FormField label="Periode" label-class="text-[11px]">
        <div class="periode-group">
          <div class="periode-group__year">
            <SelectInput
              :model-value="store.filters.year"
              :options="yearOptions"
              placeholder="Tahun"
              size="sm"
              @update:model-value="store.setYearFilter($event)"
            />
          </div>
          <div class="periode-group__dates">
            <div class="periode-group__date">
              <TextInput
                :model-value="store.filters.dateStart"
                type="date"
                size="sm"
                aria-label="Dari tanggal"
                title="Dari tanggal (mengganti filter tahun)"
                @update:model-value="store.setDateFilter('dateStart', $event)"
              />
            </div>
            <span class="periode-group__sep" aria-hidden="true">–</span>
            <div class="periode-group__date">
              <TextInput
                :model-value="store.filters.dateEnd"
                type="date"
                size="sm"
                aria-label="s/d tanggal"
                title="s/d tanggal (mengganti filter tahun)"
                @update:model-value="store.setDateFilter('dateEnd', $event)"
              />
            </div>
          </div>
        </div>
      </FormField>

      <FormField label="Company" label-class="text-[11px]">
        <SelectInput
          :model-value="store.filters.company"
          :options="companyOptions"
          placeholder="All Companies"
          size="sm"
          @update:model-value="store.setFilter('company', $event)"
        />
      </FormField>

      <div class="flex items-center gap-2 xl:justify-end">
        <button
          type="button"
          class="btn-secondary !py-2 !text-xs whitespace-nowrap"
          :aria-expanded="showAdvanced"
          @click="showAdvanced = !showAdvanced"
        >
          <i class="bi bi-sliders me-1"></i> Lanjutan
          <span v-if="advancedActiveCount > 0" class="advanced-badge">{{ advancedActiveCount }}</span>
          <i class="bi ms-1 text-[10px]" :class="showAdvanced ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
        </button>
        <button type="button" class="btn-secondary !py-2 !text-xs whitespace-nowrap" @click="resetAllFilters">
          <i class="bi bi-x-circle me-1"></i> Reset
        </button>
      </div>
    </div>

    <!-- Chip filter aktif: terlihat sekilas apa yang mengunci hasil, hapus satu per satu -->
    <div v-if="activeFilterChips.length > 0" class="history-chips mt-3 flex flex-wrap items-center gap-1.5 border-t pt-3">
      <span class="history-chips__label">Filter aktif</span>
      <button
        v-for="chip in activeFilterChips"
        :key="chip.key"
        type="button"
        class="history-filter-chip"
        :title="`Hapus filter: ${chip.label}`"
        @click="removeChip(chip)"
      >
        <span class="history-filter-chip__label">{{ chip.label }}</span>
        <i class="bi bi-x-lg history-filter-chip__x" aria-hidden="true"></i>
      </button>
    </div>

    <!-- Filter lanjutan: jarang diubah tiap sesi, dibuka sesuai kebutuhan -->
    <transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="-translate-y-1 opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="-translate-y-1 opacity-0"
    >
      <div v-show="showAdvanced" class="mt-3 grid grid-cols-1 gap-3 border-t pt-3 md:grid-cols-2 xl:grid-cols-4">
        <FormField label="COA" label-class="text-[11px]">
          <MultiSelect
            :key="`coa-filter-${store.filterResetToken}`"
            :model-value="store.filters.coaIds"
            :options="store.coaOptions"
            placeholder="All accounts"
            @update:model-value="store.setFilter('coaIds', $event)"
          />
        </FormField>

        <FormField label="Bank" label-class="text-[11px]">
          <SelectInput
            :model-value="store.filters.bank"
            :options="bankOptions"
            placeholder="All Banks"
            size="sm"
            @update:model-value="store.setFilter('bank', $event)"
          />
        </FormField>

        <FormField label="Arah" label-class="text-[11px]">
          <SelectInput
            :model-value="store.filters.dbCr"
            :options="typeOptions"
            placeholder="All Types"
            size="sm"
            @update:model-value="store.setFilter('dbCr', $event)"
          />
        </FormField>

        <FormField label="Rentang Nominal" label-class="text-[11px]">
          <div class="flex items-center gap-1.5">
            <div class="min-w-0 flex-1">
              <TextInput
                :model-value="store.filters.amountMin"
                type="number"
                placeholder="Min"
                size="sm"
                aria-label="Nominal minimum"
                @update:model-value="store.setFilter('amountMin', $event)"
              />
            </div>
            <span class="shrink-0 text-[11px]" style="color: var(--color-text-muted)">s/d</span>
            <div class="min-w-0 flex-1">
              <TextInput
                :model-value="store.filters.amountMax"
                type="number"
                placeholder="Maks"
                size="sm"
                aria-label="Nominal maksimum"
                @update:model-value="store.setFilter('amountMax', $event)"
              />
            </div>
          </div>
        </FormField>
      </div>
    </transition>
  </SectionCard>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useHistoryStore } from '../../stores/history';
import FormField from '../ui/FormField.vue';
import MultiSelect from '../ui/MultiSelect.vue';
import SectionCard from '../ui/SectionCard.vue';
import SelectInput from '../ui/SelectInput.vue';
import TextInput from '../ui/TextInput.vue';

const store = useHistoryStore();

const buildMarkLabel = (mark) => {
  const parts = [mark?.internal_report, mark?.personal_use, mark?.tax_report]
    .map(value => String(value || '').trim())
    .filter(Boolean);
  const uniqueParts = [...new Set(parts)];
  return uniqueParts.length ? uniqueParts.join(' / ') : 'Unnamed Mark';
};

const bankOptions = [
  { value: 'BCA', label: 'BCA' },
  { value: 'BCA_CC', label: 'BCA CC' },
  { value: 'MANDIRI', label: 'Mandiri' },
  { value: 'MANDIRI_CC', label: 'Mandiri CC' },
  { value: 'DBS', label: 'DBS' },
  { value: 'BRI', label: 'BRI' },
  { value: 'SAQU', label: 'SAQU' },
  { value: 'BLU', label: 'BLU' }
];

const typeOptions = [
  { value: 'DB', label: 'Debit / Masuk (DB)' },
  { value: 'CR', label: 'Credit / Keluar (CR)' }
];

const yearOptions = computed(() => (
  (store.availableYears || []).map(year => ({ value: year, label: year }))
));

const companyOptions = computed(() => (
  (store.companies || []).map(company => ({
    value: company.id,
    label: `${company.name}${company.short_name ? ` (${company.short_name})` : ''}`
  }))
));

const markOptions = computed(() => {
  const options = [
    { id: 'marked', label: 'Marked Only' },
    { id: 'unmarked', label: 'Unmarked Only' },
    { id: 'multi_marked', label: 'Multi Marked (Split Parent)' },
    { id: 'missing_mark', label: 'Deleted Mark / Missing Mark' }
  ];
  if (store.aiSettings?.enabled) {
    options.push({ id: 'ai_any', label: 'Ada Saran AI (semua status)' });
    options.push({ id: 'ai_pending', label: 'Saran AI Menunggu Review' });
    options.push({ id: 'ai_auto', label: 'Ter-mark AI Otomatis' });
  }
  options.push({ id: 'separator-1', type: 'separator' });

  store.sortedMarks.forEach(m => {
    options.push({
      id: m.id.toString(),
      label: buildMarkLabel(m)
    });
  });

  return options;
});

// ---------------------------------------------------------------- Filter lanjutan

const isAdvancedActive = () => {
  const f = store.filters;
  return Boolean(
    f.bank ||
    f.dbCr ||
    (Array.isArray(f.coaIds) && f.coaIds.length > 0) ||
    (f.amountMin !== null && f.amountMin !== '') ||
    (f.amountMax !== null && f.amountMax !== '')
  );
};

// Panel lanjutan langsung terbuka bila filter lanjutan sudah tersimpan aktif.
const showAdvanced = ref(isAdvancedActive());

const advancedActiveCount = computed(() => {
  const f = store.filters;
  let count = 0;
  if (f.bank) count += 1;
  if (f.dbCr) count += 1;
  if (f.coaIds.length > 0) count += 1;
  if (f.amountMin !== null && f.amountMin !== '') count += 1;
  if (f.amountMax !== null && f.amountMax !== '') count += 1;
  return count;
});

// ---------------------------------------------------------------- Chip filter aktif

const activeFilterChips = computed(() => {
  const f = store.filters;
  const chips = [];

  if (f.search) {
    chips.push({ key: 'search', keys: ['search'], label: `Cari: "${f.search}"` });
  }
  if (f.year) {
    chips.push({ key: 'year', keys: ['year'], label: `Tahun: ${f.year}` });
  }
  if (f.dateStart || f.dateEnd) {
    const range = f.dateStart && f.dateEnd
      ? `${f.dateStart} s/d ${f.dateEnd}`
      : (f.dateStart ? `Dari ${f.dateStart}` : `s/d ${f.dateEnd}`);
    chips.push({ key: 'periode', keys: ['dateStart', 'dateEnd'], label: `Periode: ${range}` });
  }
  if (f.company) {
    const company = (store.companies || []).find(c => String(c.id) === String(f.company));
    chips.push({ key: 'company', keys: ['company'], label: `Company: ${company?.name || f.company}` });
  }
  if (f.bank) {
    const bank = bankOptions.find(b => b.value === f.bank);
    chips.push({ key: 'bank', keys: ['bank'], label: `Bank: ${bank?.label || f.bank}` });
  }
  if (f.dbCr) {
    const type = typeOptions.find(t => t.value === f.dbCr);
    chips.push({ key: 'dbCr', keys: ['dbCr'], label: `Arah: ${type?.label || f.dbCr}` });
  }
  if ((f.amountMin !== null && f.amountMin !== '') || (f.amountMax !== null && f.amountMax !== '')) {
    const parts = [];
    if (f.amountMin !== null && f.amountMin !== '') parts.push(`≥ ${f.amountMin}`);
    if (f.amountMax !== null && f.amountMax !== '') parts.push(`≤ ${f.amountMax}`);
    chips.push({ key: 'amount', keys: ['amountMin', 'amountMax'], label: `Nominal: ${parts.join(' & ')}` });
  }

  const markLabels = new Map(
    markOptions.value
      .filter(option => option.type !== 'separator')
      .map(option => [String(option.id), option.label])
  );
  for (const status of f.markStatus || []) {
    chips.push({
      key: `mark-${status}`,
      list: { key: 'markStatus', value: status },
      label: markLabels.get(String(status)) || status
    });
  }

  const coaById = new Map((store.coaList || []).map(coa => [String(coa.id), coa]));
  for (const coaId of f.coaIds || []) {
    const coa = coaById.get(String(coaId));
    const label = coa ? `${coa.code} - ${coa.name}` : String(coaId);
    chips.push({
      key: `coa-${coaId}`,
      list: { key: 'coaIds', value: coaId },
      label
    });
  }

  return chips;
});

const removeChip = (chip) => {
  if (chip.list) {
    const { key, value } = chip.list;
    const next = store.filters[key].filter(item => String(item) !== String(value));
    store.setFilter(key, next);
    return;
  }
  store.clearFilterKeys(chip.keys);
};

const resetAllFilters = () => {
  store.resetFilters();
};
</script>

<style scoped>
/* Satu tinggi kontrol untuk seluruh bar filter (34px = tinggi tombol Lanjutan/Reset):
   MultiSelect 36px, SelectInput/TextInput 30px — tanpa normalisasi baris ini terlihat miring. */
.history-filters :deep(.ui-input-shell),
.history-filters :deep(select.input-base),
.history-filters :deep(.ui-dropdown-trigger) {
  height: 34px;
  min-height: 34px;
}

.periode-group {
  @apply flex flex-wrap items-center gap-x-2 gap-y-1.5;
}

/* Wrapper eksplisit: attr class pada SelectInput/TextInput menempel ke input
   di dalamnya, bukan ke shell — lebar harus diatur dari pembungkusnya. */
.periode-group__year {
  @apply w-[104px] shrink-0;
}

.periode-group__dates {
  @apply flex min-w-[240px] flex-1 items-center gap-1.5;
}

.periode-group__date {
  @apply min-w-0 flex-1;
}

.periode-group__sep {
  @apply shrink-0 text-xs;
  color: var(--color-text-muted);
}

.advanced-badge {
  @apply ml-0.5 inline-flex h-4 min-w-[16px] items-center justify-center rounded-full px-1 text-[10px] font-bold;
  background: var(--color-primary);
  color: var(--color-surface);
}

.history-chips {
  border-color: var(--color-border);
}

.history-chips__label {
  @apply text-[10px] font-bold uppercase tracking-wider;
  color: var(--color-text-muted);
  margin-right: 4px;
}

.history-filter-chip {
  @apply inline-flex max-w-[240px] items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold transition-colors;
  background: var(--color-surface-muted);
  border-color: var(--color-border);
  color: var(--color-text);
}

.history-filter-chip:hover {
  border-color: var(--color-border-strong);
  background: var(--color-surface-raised);
}

.history-filter-chip__label {
  @apply min-w-0 truncate;
}

.history-filter-chip__x {
  @apply shrink-0 text-[9px];
  color: var(--color-text-muted);
}

.history-filter-chip:hover .history-filter-chip__x {
  color: var(--color-danger);
}
</style>
