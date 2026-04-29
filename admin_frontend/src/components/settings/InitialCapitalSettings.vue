<template>
  <div class="space-y-6">
    <SectionCard>
      <template #header>
        <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between w-full">
          <div>
            <h2 class="text-xl font-bold text-theme">Initial Capital</h2>
            <p class="text-sm text-muted">Configure company initial capital settings for financial reporting.</p>
          </div>
          <div class="flex items-center gap-3">
            <SegmentedControl
              v-model="selectedReportType"
              :options="[
                { label: 'Real', value: 'real' },
                { label: 'Coretax', value: 'coretax' }
              ]"
              @change="loadData"
            />
          </div>
        </div>
      </template>

      <div class="p-6">
        <!-- Company Selector -->
        <div class="mb-8">
          <label class="label-base mb-2 flex items-center gap-2">
            <i class="bi bi-building text-primary"></i>
            Select Company
          </label>
          <div class="max-w-md">
            <select 
              class="ui-dropdown-trigger" 
              v-model="selectedCompany"
              :disabled="loadingCompanies"
              @change="loadData"
            >
              <option value="">-- Select Company --</option>
              <option 
                v-for="company in companies" 
                :key="company.id" 
                :value="company.id"
              >
                {{ company.name || company.id }}
              </option>
            </select>
          </div>
        </div>

        <div v-if="loading" class="flex flex-col items-center justify-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p class="mt-4 text-muted text-sm font-medium">Loading data...</p>
        </div>

        <div v-else-if="!selectedCompany" class="py-12 text-center">
          <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-surface-muted mb-4">
            <i class="bi bi-building text-2xl text-muted"></i>
          </div>
          <h3 class="text-lg font-semibold text-theme">No Company Selected</h3>
          <p class="text-muted text-sm max-w-xs mx-auto mt-1">Please select a company to configure its initial capital settings.</p>
        </div>

        <div v-else class="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <!-- Form Section -->
          <div class="lg:col-span-8 space-y-8">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div class="field-stack">
                <label class="label-base">Initial Capital Amount</label>
                <TextInput
                  v-model="formattedAmount"
                  placeholder="0"
                  @update:model-value="handleAmountInput"
                >
                  <template #leading>
                    <span class="text-[10px] font-bold text-primary opacity-80 px-1">Rp</span>
                  </template>
                </TextInput>
                <p class="field-hint">Initial capital contributed when established.</p>
              </div>

              <div class="field-stack">
                <label class="label-base">Previous Retained Earnings</label>
                <TextInput
                  v-model="formattedRetainedEarnings"
                  placeholder="0"
                  @update:model-value="handleRetainedEarningsInput"
                >
                  <template #leading>
                    <span class="text-[10px] font-bold text-primary opacity-80 px-1">Rp</span>
                  </template>
                </TextInput>
                <p class="field-hint">Historical earnings prior to system migration.</p>
              </div>

              <div class="field-stack">
                <label class="label-base">Recognition Start Year</label>
                <TextInput
                  v-model="formData.startYear"
                  type="number"
                  placeholder="2025"
                  :min="2000"
                  :max="new Date().getFullYear()"
                >
                  <template #leading>
                    <i class="bi bi-calendar text-muted"></i>
                  </template>
                </TextInput>
                <p class="field-hint">Year when this capital starts appearing in reports.</p>
              </div>

              <div class="field-stack">
                <label class="label-base">Description</label>
                <TextInput
                  v-model="formData.description"
                  placeholder="e.g., Founder's Capital"
                >
                  <template #leading>
                    <i class="bi bi-tag text-muted"></i>
                  </template>
                </TextInput>
                <p class="field-hint">Optional reference text for the report.</p>
              </div>
            </div>

            <!-- Actions -->
            <div class="flex items-center gap-3 pt-4 border-t border-border">
              <button 
                class="btn-primary"
                @click="saveData"
                :disabled="saving || !isFormValid"
              >
                <i v-if="saving" class="bi bi-arrow-repeat spin mr-2"></i>
                <i v-else class="bi bi-check-lg mr-2"></i>
                {{ saving ? 'Saving Changes...' : 'Save Settings' }}
              </button>
              
              <button 
                v-if="hasData"
                class="btn-secondary"
                @click="resetForm"
                :disabled="saving"
              >
                <i class="bi bi-arrow-counterclockwise mr-2"></i>
                Reset
              </button>

              <button 
                v-if="hasData"
                class="ml-auto btn-danger text-xs px-4"
                @click="deleteData"
                :disabled="saving || deleting"
              >
                <i v-if="deleting" class="bi bi-arrow-repeat spin mr-2"></i>
                <i v-else class="bi bi-trash mr-2"></i>
                Delete Data
              </button>
            </div>
          </div>

          <!-- Summary Sidebar -->
          <div class="lg:col-span-4 space-y-4">
            <div class="bg-surface-muted rounded-2xl p-6 border border-border">
              <h3 class="text-xs font-bold uppercase tracking-wider text-muted mb-6">Current Configuration</h3>
              
              <div v-if="!hasData" class="py-4 text-center">
                <p class="text-sm text-muted">No data saved for <strong>{{ selectedReportType }}</strong>.</p>
              </div>

              <div v-else class="space-y-6">
                <StatCard 
                  label="Capital Amount" 
                  :value="'Rp ' + formatCompact(currentData.amount)"
                  variant="primary"
                  wrapper-class="bg-surface border-border shadow-soft"
                  icon="bi bi-cash-stack"
                />
                
                <StatCard 
                  label="Retained Earnings" 
                  :value="'Rp ' + formatCompact(currentData.previousRetainedEarningsAmount)"
                  variant="success"
                  wrapper-class="bg-surface border-border shadow-soft"
                  icon="bi bi-bar-chart-line"
                />

                <div class="flex items-center justify-between text-xs font-medium border-t border-border pt-4">
                  <span class="text-muted">Start Year:</span>
                  <span class="text-theme">{{ currentData.startYear }}</span>
                </div>

                <div v-if="currentData.description" class="text-xs leading-relaxed text-muted bg-surface p-3 rounded-xl border border-border italic">
                  "{{ currentData.description }}"
                </div>

                <div class="text-[10px] text-muted text-right italic mt-4">
                  Last updated: {{ formatDate(currentData.updatedAt) }}
                </div>
              </div>
            </div>
            
            <div class="bg-primary/5 rounded-2xl p-6 border border-primary/10">
              <div class="flex gap-4">
                <i class="bi bi-info-circle-fill text-primary"></i>
                <div class="text-xs leading-relaxed">
                  <p class="font-bold text-primary mb-1">Configuration Scope</p>
                  <p class="text-muted">These settings are specific to <strong>{{ selectedReportType.toUpperCase() }}</strong>. Switching types allows you to maintain independent balances for audit vs coretax reports.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </SectionCard>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useNotifications } from '../../composables/useNotifications';
import SectionCard from '../ui/SectionCard.vue';
import StatCard from '../ui/StatCard.vue';
import TextInput from '../ui/TextInput.vue';
import SegmentedControl from '../ui/SegmentedControl.vue';

const props = defineProps({
  companyId: {
    type: String,
    default: ''
  }
});

const notifications = useNotifications();

// Selection State
const selectedCompany = ref('');
const selectedReportType = ref('real');
const loadingCompanies = ref(false);
const companies = ref([]);

// Data State
const loading = ref(false);
const saving = ref(false);
const deleting = ref(false);
const hasData = ref(false);

const formData = ref({
  amount: 0,
  previousRetainedEarningsAmount: 0,
  startYear: new Date().getFullYear(),
  description: ''
});

const currentData = ref({
  amount: 0,
  previousRetainedEarningsAmount: 0,
  startYear: 0,
  description: '',
  updatedAt: ''
});

// Formatting Helpers
const formattedAmount = ref('0');
const formattedRetainedEarnings = ref('0');

const isIncompleteNegativeInput = (value) => {
  return String(value ?? '').trim() === '-';
};

const parseNumber = (str, { allowNegative = false } = {}) => {
  if (str === null || str === undefined || str === '') return 0;

  const raw = str.toString().trim();
  const isNegative = allowNegative && raw.startsWith('-');
  const cleaned = raw.replace(/[^\d]/g, '');

  if (!cleaned) return 0;

  const numeric = parseFloat(cleaned) || 0;
  return isNegative ? -numeric : numeric;
};

const formatThousand = (num) => {
  if (!num && num !== 0) return '';
  if (isIncompleteNegativeInput(num)) return '-';

  const val = typeof num === 'string' ? parseNumber(num, { allowNegative: true }) : num;
  return new Intl.NumberFormat('id-ID').format(val);
};

const handleAmountInput = (val) => {
  const numeric = parseNumber(val);
  formData.value.amount = numeric;
  formattedAmount.value = formatThousand(numeric);
};

const handleRetainedEarningsInput = (val) => {
  if (isIncompleteNegativeInput(val)) {
    formData.value.previousRetainedEarningsAmount = 0;
    formattedRetainedEarnings.value = '-';
    return;
  }

  const numeric = parseNumber(val, { allowNegative: true });
  formData.value.previousRetainedEarningsAmount = numeric;
  formattedRetainedEarnings.value = formatThousand(numeric);
};

const isFormValid = computed(() => {
  const year = parseInt(formData.value.startYear, 10);
  return selectedCompany.value && 
         formData.value.amount >= 0 && 
         formattedRetainedEarnings.value !== '-' &&
         !isNaN(year) &&
         year >= 2000 && 
         year <= new Date().getFullYear() + 1; // allow next year too
});

// Lifecycle
onMounted(() => {
  loadCompanies();
});

// Actions
const loadCompanies = async () => {
  loadingCompanies.value = true;
  try {
    const response = await fetch('/api/companies');
    const data = await response.json();
    companies.value = data.companies || data || [];
    
    if (props.companyId) {
      selectedCompany.value = props.companyId;
    } else if (companies.value.length === 1) {
      selectedCompany.value = companies.value[0].id;
    }
    
    if (selectedCompany.value) {
      loadData();
    }
  } catch (error) {
    console.error('Error loading companies:', error);
    notifications.error('Failed to load companies list');
  } finally {
    loadingCompanies.value = false;
  }
};

const loadData = async () => {
  if (!selectedCompany.value) return;
  
  loading.value = true;
  try {
    const url = `/api/initial-capital?company_id=${encodeURIComponent(selectedCompany.value)}&report_type=${selectedReportType.value}`;
    const response = await fetch(url);
    const data = await response.json();
    
    if (data.setting) {
      hasData.value = true;
      currentData.value = {
        amount: data.setting.amount,
        previousRetainedEarningsAmount: data.setting.previous_retained_earnings_amount || 0,
        startYear: data.setting.start_year,
        description: data.setting.description || '',
        updatedAt: data.setting.updated_at
      };
      formData.value = { ...currentData.value };
      formattedAmount.value = formatThousand(formData.value.amount);
      formattedRetainedEarnings.value = formatThousand(formData.value.previousRetainedEarningsAmount);
    } else {
      hasData.value = false;
      formData.value = {
        amount: 0,
        previousRetainedEarningsAmount: 0,
        startYear: new Date().getFullYear(),
        description: ''
      };
      formattedAmount.value = '0';
      formattedRetainedEarnings.value = '0';
    }
  } catch (error) {
    console.error('Error loading initial capital:', error);
    notifications.error('Failed to load initial capital data');
  } finally {
    loading.value = false;
  }
};

const saveData = async () => {
  if (!selectedCompany.value) return;
  
  saving.value = true;
  try {
    const response = await fetch('/api/initial-capital', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        company_id: selectedCompany.value,
        report_type: selectedReportType.value,
        amount: formData.value.amount,
        previous_retained_earnings_amount: formData.value.previousRetainedEarningsAmount,
        start_year: formData.value.startYear,
        description: formData.value.description
      })
    });
    
    const data = await response.json();
    if (response.ok) {
      notifications.success('Initial capital saved successfully for ' + selectedReportType.value);
      await loadData();
    } else {
      notifications.error(data.error || 'Failed to save data');
    }
  } catch (error) {
    console.error('Error saving data:', error);
    notifications.error('Internal server error while saving');
  } finally {
    saving.value = false;
  }
};

const deleteData = async () => {
  if (!confirm('Are you sure? This will remove the initial capital configuration for this report type.')) return;
  
  deleting.value = true;
  try {
    const url = `/api/initial-capital?company_id=${selectedCompany.value}&report_type=${selectedReportType.value}`;
    const response = await fetch(url, { method: 'DELETE' });
    if (response.ok) {
      notifications.success('Data removed successfully');
      await loadData();
    } else {
      notifications.error('Failed to delete data');
    }
  } catch (error) {
    notifications.error('Internal server error while deleting');
  } finally {
    deleting.value = false;
  }
};

const resetForm = () => {
  formData.value = { ...currentData.value };
  formattedAmount.value = formatThousand(formData.value.amount);
  formattedRetainedEarnings.value = formatThousand(formData.value.previousRetainedEarningsAmount);
};

// UI Utils
const formatCompact = (num) => {
  return new Intl.NumberFormat('id-ID').format(num);
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleString('id-ID', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
};

const spinClass = "animate-spin";
</script>

<style scoped>
.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Custom transitions */
.v-enter-active,
.v-leave-active {
  transition: opacity 0.3s ease;
}

.v-enter-from,
.v-leave-to {
  opacity: 0;
}
</style>
