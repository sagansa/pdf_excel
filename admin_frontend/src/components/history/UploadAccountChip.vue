<template>
  <button
    v-if="!editing"
    type="button"
    class="acct-chip"
    :class="toneClass"
    :title="titleText"
    :disabled="disabled || busy"
    @click="openEditor"
  >
    <i v-if="busy" class="bi bi-arrow-repeat animate-spin"></i>
    <span class="acct-chip__label">{{ label }}</span>
    <i class="bi bi-pencil-square acct-chip__edit" aria-hidden="true"></i>
  </button>

  <div v-else ref="editorHost" class="acct-chip__editor" @keydown.esc.stop="closeEditor">
    <SelectInput
      v-if="options.length > 0"
      :model-value="currentValue"
      :options="options"
      placeholder="Pilih rekening…"
      size="sm"
      :disabled="disabled"
      @update:model-value="onPick"
      @blur="closeEditor"
    />
    <div v-else class="acct-chip__manual">
      <TextInput
        :model-value="manualValue"
        placeholder="Nomor rekening…"
        size="sm"
        :disabled="disabled"
        @update:model-value="manualValue = $event"
        @keydown.enter="commitManual"
      />
      <button
        type="button"
        class="acct-chip__apply"
        :disabled="!manualValue.trim() || disabled || busy"
        title="Simpan nomor rekening"
        @mousedown.prevent
        @click="commitManual"
      >
        Simpan
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue';
import SelectInput from '../ui/SelectInput.vue';
import TextInput from '../ui/TextInput.vue';

const props = defineProps({
  item: {
    type: Object,
    required: true
  },
  label: {
    type: String,
    default: ''
  },
  options: {
    type: Array,
    default: () => []
  },
  busy: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['assign']);

const editing = ref(false);
const editorHost = ref(null);

watch(editing, async (open) => {
  if (!open) return;
  await nextTick();
  editorHost.value?.querySelector('select, input')?.focus();
});

const isMixed = computed(() => Boolean(props.item?.is_account_mixed));
const isMapped = computed(() => Boolean(props.item?.bank_account_number) && !isMixed.value);

const toneClass = computed(() => (isMapped.value ? 'acct-chip--ok' : 'acct-chip--warn'));

const titleText = computed(() => {
  if (isMixed.value) return 'Multiple accounts detected — click to choose the correct account';
  if (!props.item?.bank_account_number) return 'Unmapped — click to assign a bank account';
  return `${props.label} — click to change`;
});

const currentValue = computed(() => (isMixed.value ? '' : props.item?.bank_account_number || ''));

const manualValue = ref(currentValue.value);

const openEditor = () => {
  if (props.disabled || props.busy) return;
  manualValue.value = currentValue.value;
  editing.value = true;
};

const closeEditor = () => {
  editing.value = false;
};

const onPick = (value) => {
  editing.value = false;
  emit('assign', value || '');
};

const commitManual = () => {
  const value = manualValue.value.trim();
  if (!value) return;
  editing.value = false;
  emit('assign', value);
};
</script>

<style scoped>
.acct-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  padding: 4px 8px;
  border-radius: 999px;
  font: 700 11.5px/1.2 var(--font-sans);
  letter-spacing: 0.02em;
  cursor: pointer;
  transition: background-color 140ms ease, border-color 140ms ease;
}

.acct-chip:disabled {
  cursor: default;
  opacity: 0.75;
}

.acct-chip--ok {
  background: rgba(15, 118, 110, 0.1);
  border: 1px solid rgba(15, 118, 110, 0.22);
  color: var(--color-primary);
}

.acct-chip--ok:hover:not(:disabled) {
  background: rgba(15, 118, 110, 0.16);
}

.acct-chip--warn {
  background: rgba(180, 83, 9, 0.1);
  border: 1px solid rgba(180, 83, 9, 0.24);
  color: var(--color-accent);
}

.acct-chip--warn:hover:not(:disabled) {
  background: rgba(180, 83, 9, 0.16);
}

.acct-chip__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.acct-chip__edit {
  font-size: 10px;
  opacity: 0;
  transition: opacity 140ms ease;
}

.acct-chip:hover .acct-chip__edit,
.acct-chip:focus-visible .acct-chip__edit {
  opacity: 0.7;
}

.acct-chip:focus-visible {
  outline: 2px solid var(--color-primary-ring);
  outline-offset: 1px;
}

.acct-chip__editor {
  min-width: 220px;
}

.acct-chip__manual {
  display: flex;
  align-items: center;
  gap: 6px;
}

.acct-chip__manual > :first-child {
  flex: 1;
  min-width: 0;
}

.acct-chip__apply {
  flex: none;
  border: 1px solid transparent;
  border-radius: 8px;
  background: var(--color-primary);
  color: #fff;
  font: 700 11px var(--font-sans);
  padding: 5px 10px;
  cursor: pointer;
  transition: background-color 140ms ease, opacity 140ms ease;
}

.acct-chip__apply:hover:not(:disabled) {
  background: var(--color-primary-strong);
}

.acct-chip__apply:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.acct-chip__apply:focus-visible {
  outline: 2px solid var(--color-primary-ring);
  outline-offset: 1px;
}

.acct-chip__editor:focus-within {
  outline: 2px solid var(--color-primary-ring);
  outline-offset: 2px;
  border-radius: 10px;
}
</style>
