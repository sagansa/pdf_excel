<template>
  <section
    v-if="totalIssues > 0"
    class="attention surface-card"
    aria-label="Uploads needing attention"
  >
    <div class="attention__head">
      <h2 class="attention__title">Needs attention</h2>
      <span class="attention__count">{{ totalIssues }}</span>
      <span class="attention__caption">Perbaiki sebelum data dipakai untuk laporan.</span>
    </div>

    <div class="attention__groups" role="tablist">
      <button
        v-for="group in groups"
        :key="group.id"
        type="button"
        role="tab"
        class="group-chip"
        :class="[
          `group-chip--${group.tone}`,
          { 'group-chip--open': openGroupId === group.id }
        ]"
        :aria-expanded="openGroupId === group.id"
        :aria-selected="openGroupId === group.id"
        @click="toggleGroup(group.id)"
      >
        <i class="group-chip__dot" aria-hidden="true"></i>
        <span class="group-chip__label">{{ group.label }}</span>
        <span class="group-chip__count">· {{ group.items.length }}</span>
        <i class="bi group-chip__chev" :class="openGroupId === group.id ? 'bi-chevron-up' : 'bi-chevron-down'" aria-hidden="true"></i>
      </button>
    </div>

    <TransitionGroup v-if="openGroup" name="queue" tag="div" class="attention__issues">
      <div
        v-for="item in openGroupVisibleItems"
        :key="rowKeyOf(item)"
        class="issue"
      >
        <span class="issue__file" :title="item.source_file || ''">{{ item.source_file || '(no filename)' }}</span>
        <span class="issue__bank">{{ formatBankCode(item.bank_code) }}</span>
        <span class="issue__meta">
          <span class="issue__txns">{{ item.transaction_count }} txns</span>
          <span class="issue__period">{{ shortPeriod(item) }}</span>
        </span>
        <span class="issue__amounts">
          <span>DB {{ formatAmount(item.total_debit) }}</span>
          <span>CR {{ formatAmount(item.total_credit) }}</span>
        </span>
        <span class="issue__fix">
          <div class="issue__select">
            <SelectInput
              v-if="optionsFor(item).length > 0"
              :model-value="draftFor(item)"
              :options="optionsFor(item)"
              placeholder="Pilih rekening…"
              size="sm"
              :disabled="busyKey === rowKeyOf(item)"
              @update:model-value="setDraft(item, $event)"
            />
            <TextInput
              v-else
              :model-value="draftFor(item)"
              placeholder="Nomor rekening…"
              size="sm"
              :disabled="busyKey === rowKeyOf(item)"
              @update:model-value="setDraft(item, $event)"
            />
          </div>
          <button
            type="button"
            class="assign-btn"
            :disabled="!draftFor(item) || busyKey === rowKeyOf(item)"
            @click="emitAssign(item)"
          >
            <i v-if="busyKey === rowKeyOf(item)" class="bi bi-arrow-repeat animate-spin"></i>
            <span>Assign</span>
          </button>
        </span>
      </div>
      <p v-if="openGroup && openGroup.items.length > MAX_VISIBLE" class="issue-overflow" role="note">
        +{{ openGroup.items.length - MAX_VISIBLE }} file lainnya — gunakan filter Status di tabel untuk mengerjakan sisanya.
      </p>
    </TransitionGroup>
  </section>

  <section v-else class="allclear surface-card" role="status">
    <i class="bi bi-check2-circle allclear__icon" aria-hidden="true"></i>
    <span>Semua beres — tidak ada upload yang perlu diperbaiki.</span>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import SelectInput from '../ui/SelectInput.vue';
import TextInput from '../ui/TextInput.vue';

const MAX_VISIBLE = 4;

const props = defineProps({
  groups: {
    type: Array,
    default: () => []
  },
  totalIssues: {
    type: Number,
    default: 0
  },
  busyKey: {
    type: String,
    default: ''
  },
  optionsFor: {
    type: Function,
    required: true
  },
  rowKeyOf: {
    type: Function,
    required: true
  }
});

const emit = defineEmits(['assign']);

const drafts = ref({});

const visibleGroups = computed(() => props.groups.filter((group) => group.items.length > 0));

const openGroupId = ref(null);

watch(
  visibleGroups,
  (groups) => {
    if (!groups.some((group) => group.id === openGroupId.value)) {
      openGroupId.value = groups.length ? groups[0].id : null;
    }
  },
  { immediate: true }
);

const openGroup = computed(
  () => visibleGroups.value.find((group) => group.id === openGroupId.value) || null
);

const openGroupVisibleItems = computed(() => (openGroup.value ? openGroup.value.items.slice(0, MAX_VISIBLE) : []));

const toggleGroup = (id) => {
  openGroupId.value = openGroupId.value === id ? null : id;
};

const draftFor = (item) => drafts.value[props.rowKeyOf(item)] ?? '';
const setDraft = (item, value) => {
  drafts.value = { ...drafts.value, [props.rowKeyOf(item)]: value || '' };
};
const emitAssign = (item) => {
  const value = draftFor(item);
  if (!value) return;
  drafts.value = { ...drafts.value, [props.rowKeyOf(item)]: '' };
  emit('assign', item, value);
};

const formatBankCode = (bankCode) => {
  const value = (bankCode || '').toString();
  if (!value) return 'Unknown Bank';
  return value.replace('_CC', ' Credit Card');
};

const formatAmount = (amount) => new Intl.NumberFormat('id-ID').format(amount || 0);

const shortPeriod = (item) => {
  const start = (item.start_date || '').split(' ')[0];
  const end = (item.end_date || '').split(' ')[0];
  if (!start && !end) return '-';
  return `${start || '-'} – ${end || '-'}`;
};
</script>

<style scoped>
.attention {
  padding: 16px 20px 14px;
}

.attention__head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.attention__title {
  margin: 0;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: -0.01em;
  color: var(--color-text);
}

.attention__count {
  font: 700 11px var(--font-mono);
  color: var(--color-primary);
  background: rgba(15, 118, 110, 0.12);
  border: 1px solid rgba(15, 118, 110, 0.24);
  border-radius: 999px;
  padding: 1px 9px;
}

.attention__caption {
  font-size: 12px;
  color: var(--color-text-muted);
}

.attention__groups {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.group-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-surface-muted);
  color: var(--color-text);
  font: 600 12.5px var(--font-sans);
  cursor: pointer;
  transition: border-color 140ms ease, background-color 140ms ease;
}

.group-chip:hover {
  border-color: var(--color-border-strong);
}

.group-chip--open {
  background: var(--color-surface-raised);
  border-color: var(--color-border-strong);
}

.group-chip:focus-visible {
  outline: 2px solid var(--color-primary-ring);
  outline-offset: 1px;
}

.group-chip__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: none;
}

.group-chip--amber .group-chip__dot {
  background: var(--color-accent);
}

.group-chip--danger .group-chip__dot {
  background: var(--color-danger);
}

.group-chip__count {
  color: var(--color-text-muted);
  font-weight: 500;
}

.group-chip__chev {
  font-size: 10px;
  color: var(--color-text-muted);
}

.attention__issues {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.issue {
  display: grid;
  grid-template-columns: minmax(140px, 1.6fr) 110px minmax(180px, 1.2fr) minmax(190px, 1.2fr) auto;
  align-items: center;
  gap: 12px;
  padding: 8px 14px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-surface-muted);
}

.issue__file {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.issue__bank {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.issue__meta {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.issue__txns {
  font: 500 12px var(--font-mono);
  color: var(--color-text);
}

.issue__period {
  font: 400 11px var(--font-mono);
  color: var(--color-text-muted);
}

.issue__amounts {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  font: 500 11.5px var(--font-mono);
  color: var(--color-text);
  white-space: nowrap;
}

.issue__fix {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: flex-end;
}

.issue__select {
  width: 210px;
}

.assign-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 13px;
  border-radius: 9px;
  border: 1px solid transparent;
  background: var(--color-primary);
  color: #fff;
  font: 700 12px var(--font-sans);
  cursor: pointer;
  transition: background-color 140ms ease, opacity 140ms ease;
}

.assign-btn:hover:not(:disabled) {
  background: var(--color-primary-strong);
}

.assign-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.assign-btn:focus-visible {
  outline: 2px solid var(--color-primary-ring);
  outline-offset: 1px;
}

.allclear {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  font-size: 12.5px;
  color: var(--color-text-muted);
}

.allclear__icon {
  color: var(--color-success);
  font-size: 14px;
}

.issue-overflow {
  margin: 6px 2px 0;
  font-size: 11.5px;
  color: var(--color-text-muted);
}

.queue-enter-active {
  transition: opacity 200ms ease-out, transform 200ms ease-out;
}

.queue-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.queue-leave-active {
  transition: opacity 140ms ease-in;
}

.queue-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .queue-enter-active,
  .queue-leave-active {
    transition: none;
  }
}

@media (max-width: 1100px) {
  .issue {
    grid-template-columns: 1fr auto;
    row-gap: 8px;
  }

  .issue__file {
    grid-column: 1;
  }

  .issue__bank {
    grid-column: 1;
  }

  .issue__meta {
    grid-column: 1;
    flex-direction: row;
    gap: 12px;
    align-items: baseline;
  }

  .issue__amounts {
    grid-column: 2;
    grid-row: 1 / span 2;
  }

  .issue__fix {
    grid-column: 1 / -1;
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .issue__select {
    width: 180px;
  }
}

@media (max-width: 900px) {
  .issue {
    grid-template-columns: 1fr;
  }

  .issue__amounts {
    grid-column: 1;
    grid-row: auto;
    flex-direction: row;
    gap: 12px;
  }

  .attention__caption {
    display: none;
  }
}
</style>
