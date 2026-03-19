<template>
  <BaseModal
    :isOpen="isOpen"
    size="2xl"
    @close="$emit('close')"
  >
    <template #title>
      {{ editMode ? 'Edit Store' : 'Add New Store' }}
    </template>
    
    <form @submit.prevent="handleSubmit" class="space-y-4 px-6">
      <div class="grid grid-cols-2 gap-4">
        <FormField label="Store Code *">
          <TextInput
            v-model="form.store_code"
            required
            placeholder="e.g., APB"
          />
        </FormField>
        <FormField label="Store Name *">
          <TextInput
            v-model="form.store_name"
            required
            placeholder="e.g., Alam Sutera"
          />
        </FormField>
      </div>

      <FormField label="Current Location">
        <SelectInput
          v-model="form.current_location_id"
          placeholder="No location assigned"
          :options="locations.map(l => ({ value: l.id, label: `${l.location_name} - ${l.address}` }))"
        />
      </FormField>

      <div class="grid grid-cols-2 gap-4">
        <FormField label="Status">
          <SelectInput
            v-model="form.status"
            :options="[
              { value: 'active', label: 'Active' },
              { value: 'inactive', label: 'Inactive' },
              { value: 'closed', label: 'Closed' }
            ]"
          />
        </FormField>
        <FormField label="Opened Date">
          <TextInput
            v-model="form.opened_date"
            type="date"
          />
        </FormField>
      </div>

      <FormField v-if="form.status === 'closed'" label="Closed Date">
        <TextInput
          v-model="form.closed_date"
          type="date"
        />
      </FormField>

      <FormField label="Notes">
        <textarea
          v-model="form.notes"
          rows="3"
          class="input-base w-full text-sm"
          placeholder="Additional notes..."
        ></textarea>
      </FormField>
    </form>

    <template #footer>
      <Button
        variant="secondary"
        @click="$emit('close')"
        :disabled="loading"
      >
        Cancel
      </Button>
      <Button
        variant="primary"
        :loading="loading"
        :disabled="loading"
        @click="handleSubmit"
      >
        {{ editMode ? 'Update' : 'Create' }}
      </Button>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch } from 'vue';
import { rentalApi } from '../../../api';
import BaseModal from '../../ui/BaseModal.vue';
import FormField from '../../ui/FormField.vue';
import TextInput from '../../ui/TextInput.vue';
import SelectInput from '../../ui/SelectInput.vue';
import Button from '../../ui/Button.vue';

const props = defineProps({
  isOpen: Boolean,
  store: Object,
  companyId: String
});

const emit = defineEmits(['close', 'saved']);

const editMode = ref(false);
const loading = ref(false);
const locations = ref([]);

const form = ref({
  store_code: '',
  store_name: '',
  current_location_id: '',
  status: 'active',
  opened_date: '',
  closed_date: '',
  notes: ''
});

watch(() => props.store, (newStore) => {
  if (newStore && newStore.id) {
    editMode.value = true;
    form.value = { ...newStore };
  } else {
    editMode.value = false;
    if (!props.isOpen) {
      resetForm();
    }
  }
});

watch(() => props.isOpen, async (isOpen) => {
  if (isOpen) {
    await loadLocations();
    if (!props.store) {
      resetForm();
    }
  } else {
    resetForm();
    editMode.value = false;
  }
});

const loadLocations = async () => {
  try {
    const response = await rentalApi.getLocations(props.companyId);
    locations.value = response.data.locations || [];
  } catch (error) {
    console.error('Failed to load locations:', error);
  }
};

const resetForm = () => {
  form.value = {
    store_code: '',
    store_name: '',
    current_location_id: '',
    status: 'active',
    opened_date: '',
    closed_date: '',
    notes: ''
  };
};

const handleSubmit = async () => {
  loading.value = true;
  try {
    const data = {
      ...form.value,
      company_id: props.companyId,
      current_location_id: form.value.current_location_id || null
    };

    if (editMode.value) {
      await rentalApi.updateStore(props.store.id, data);
    } else {
      await rentalApi.createStore(data);
    }

    emit('saved');
    emit('close');
  } catch (error) {
    console.error('Failed to save store:', error);
    alert('Failed to save store: ' + (error.response?.data?.error || error.message));
  } finally {
    loading.value = false;
  }
};
</script>
