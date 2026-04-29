<template>
  <BaseModal :isOpen="show" size="md" @close="$emit('close')">
    <template #title>Assign Bank Account</template>

    <div class="space-y-4 p-6">
      <div v-if="item" class="assign-summary">
        <div><strong>File:</strong> {{ item.source_file }}</div>
        <div><strong>Bank:</strong> {{ formatBankCode(item.bank_code) }}</div>
        <div><strong>Current:</strong> {{ currentAccountLabel }}</div>
      </div>

      <div>
        <label class="assign-label">Target Account</label>
        <SelectInput
          v-model="selectedAccountNumber"
          :options="accountOptions"
          placeholder="Clear / Unmapped"
          :disabled="isLoading || isSaving"
        />
      </div>

      <div v-if="!isLoading && definitions.length === 0" class="assign-note">
        Belum ada definisi akun untuk bank ini. Buat dulu di halaman `Upload Checklist`.
      </div>
    </div>

    <template #footer>
      <button class="btn-secondary" :disabled="isSaving" @click="$emit('close')">Cancel</button>
      <button
        class="btn-primary"
        :disabled="isLoading || isSaving"
        @click="submit"
      >
        <i v-if="isSaving" class="bi bi-arrow-repeat animate-spin mr-2"></i>
        Save
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { historyApi } from '../../api';
import { useNotifications } from '../../composables/useNotifications';
import BaseModal from '../ui/BaseModal.vue';
import SelectInput from '../ui/SelectInput.vue';

const props = defineProps({
  show: Boolean,
  item: {
    type: Object,
    default: null,
  }
});

const emit = defineEmits(['close', 'saved']);

const notifications = useNotifications();
const definitions = ref([]);
const selectedAccountNumber = ref('');
const isLoading = ref(false);
const isSaving = ref(false);

const formatBankCode = (bankCode) => String(bankCode || '').replace('_CC', ' Credit Card');

const currentAccountLabel = computed(() => {
  if (!props.item) return '-';
  if (props.item.is_account_mixed) return 'Mixed Accounts';
  return props.item.bank_account_display_name || props.item.bank_account_number || 'Unmapped';
});

const accountOptions = computed(() => (
  definitions.value.map((definition) => ({
    value: definition.account_number,
    label: `${definition.display_name} (${definition.account_number})`
  }))
));

const loadDefinitions = async () => {
  if (!props.show || !props.item?.bank_code) return;

  isLoading.value = true;
  try {
    const response = await historyApi.getBankAccountDefinitions(props.item.bank_code);
    definitions.value = response.data.definitions || [];
    selectedAccountNumber.value = props.item.is_account_mixed ? '' : (props.item.bank_account_number || '');
  } catch (error) {
    notifications.error(error?.response?.data?.error || 'Failed to load bank account definitions');
    definitions.value = [];
  } finally {
    isLoading.value = false;
  }
};

const submit = async () => {
  if (!props.item) return;

  isSaving.value = true;
  try {
    await historyApi.assignUploadedFileBankAccount({
      source_file: props.item.source_file,
      bank_code: props.item.bank_code,
      account_number: selectedAccountNumber.value || null,
    });
    notifications.success('Uploaded file account updated');
    emit('saved');
  } catch (error) {
    notifications.error(error?.response?.data?.error || 'Failed to assign bank account to uploaded file');
  } finally {
    isSaving.value = false;
  }
};

watch(() => props.show, (visible) => {
  if (visible) {
    loadDefinitions();
  } else {
    definitions.value = [];
    selectedAccountNumber.value = '';
  }
});
</script>

<style scoped>
.assign-summary {
  @apply rounded-2xl px-4 py-3 text-sm leading-relaxed;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  color: var(--color-text);
}

.assign-label {
  @apply mb-2 block text-sm font-medium;
  color: var(--color-text);
}

.assign-note {
  @apply rounded-xl px-4 py-3 text-xs;
  background: rgba(180, 83, 9, 0.08);
  border: 1px solid rgba(180, 83, 9, 0.16);
  color: var(--color-text-muted);
}
</style>
