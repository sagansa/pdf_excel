<template>
  <BaseModal
    :isOpen="isOpen"
    size="2xl"
    @close="$emit('close')"
  >
    <template #title>
      {{ editMode ? 'Edit Location' : 'Add New Location' }}
    </template>
    
    <form @submit.prevent="handleSubmit" class="space-y-4 px-6">
      <FormField label="Location Name *">
        <TextInput
          v-model="form.location_name"
          required
          placeholder="e.g., Ruko Permata Hijau"
        />
      </FormField>

      <FormField label="Address *">
        <textarea
          v-model="form.address"
          required
          rows="3"
          class="input-base w-full text-sm"
          placeholder="Full address"
        ></textarea>
      </FormField>

      <div class="grid grid-cols-2 gap-4">
        <FormField label="City">
          <TextInput
            v-model="form.city"
          />
        </FormField>
        <FormField label="Province">
          <TextInput
            v-model="form.province"
          />
        </FormField>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <FormField label="Postal Code">
          <TextInput
            v-model="form.postal_code"
          />
        </FormField>
        <FormField label="Area (sqm)">
          <TextInput
            v-model.number="form.area_sqm"
            type="number"
            step="0.01"
          />
        </FormField>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <FormField label="Latitude">
          <TextInput
            v-model.number="form.latitude"
            type="number"
            step="any"
            placeholder="-6.2088"
          />
        </FormField>
        <FormField label="Longitude">
          <TextInput
            v-model.number="form.longitude"
            type="number"
            step="any"
            placeholder="106.8456"
          />
        </FormField>
      </div>

      <FormField label="Notes">
        <textarea
          v-model="form.notes"
          rows="2"
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
import Button from '../../ui/Button.vue';

const props = defineProps({
  isOpen: Boolean,
  location: Object,
  companyId: String
});

const emit = defineEmits(['close', 'saved']);

const editMode = ref(false);
const loading = ref(false);

const form = ref({
  location_name: '',
  address: '',
  city: '',
  province: '',
  postal_code: '',
  latitude: null,
  longitude: null,
  area_sqm: null,
  notes: ''
});

watch(() => props.location, (newLocation) => {
  if (newLocation && newLocation.id) {
    editMode.value = true;
    form.value = { ...newLocation };
  } else {
    editMode.value = false;
    if (!props.isOpen) {
      resetForm();
    }
  }
});

watch(() => props.isOpen, (isOpen) => {
  if (!isOpen) {
    resetForm();
    editMode.value = false;
  }
});

const resetForm = () => {
  form.value = {
    location_name: '',
    address: '',
    city: '',
    province: '',
    postal_code: '',
    latitude: null,
    longitude: null,
    area_sqm: null,
    notes: ''
  };
};

const handleSubmit = async () => {
  loading.value = true;
  try {
    const data = {
      ...form.value,
      company_id: props.companyId
    };

    if (editMode.value) {
      await rentalApi.updateLocation(props.location.id, data);
    } else {
      await rentalApi.createLocation(data);
    }

    emit('saved');
    emit('close');
  } catch (error) {
    console.error('Failed to save location:', error);
    alert('Failed to save location: ' + (error.response?.data?.error || error.message));
  } finally {
    loading.value = false;
  }
};
</script>
