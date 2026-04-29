<template>
  <div class="space-y-6">
    <!-- Header Card -->
    <SectionCard body-class="p-6">
      <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h2 class="text-2xl font-bold" style="color: var(--color-text)">Payroll Employee Master</h2>
          <p class="text-sm mt-1" style="color: var(--color-text-muted)">
            Tandai user Sagansa yang termasuk employee. Data disimpan di database bank_converter.
          </p>
        </div>
        <div class="flex items-center gap-2">
          <TextInput
            v-model="search"
            placeholder="Search user..."
            leading-icon="bi bi-search"
            class="w-64"
          />
          <button
            @click="loadUsers"
            class="btn-secondary flex items-center gap-2 py-2"
            :disabled="loading"
          >
            <i class="bi bi-arrow-clockwise" :class="{ 'animate-spin': loading }"></i>
            Refresh
          </button>
        </div>
      </div>
      <p
        v-if="pageMessage"
        class="text-xs mt-3 font-medium"
        :class="pageMessageType === 'error' ? 'text-red-500' : 'text-emerald-500'"
      >
        <i :class="pageMessageType === 'error' ? 'bi bi-exclamation-circle mr-1' : 'bi bi-check-circle mr-1'"></i>
        {{ pageMessage }}
      </p>
    </SectionCard>

    <!-- Users Grid Card -->
    <SectionCard body-class="p-0">
      <template #header>
        <div class="flex items-center justify-between w-full">
          <h4 class="section-card__title">Sagansa Users</h4>
          <span class="text-xs" style="color: var(--color-text-muted)">
            <span class="font-semibold" style="color: var(--color-primary)">{{ employeeCount }}</span>
            employee dari {{ users.length }} user
          </span>
        </div>
      </template>

      <div class="p-4">
        <!-- Loading state -->
        <div v-if="loading" class="py-10 text-center">
          <span class="spinner-border h-7 w-7" style="color: var(--color-primary)" role="status"></span>
          <p class="text-sm mt-3" style="color: var(--color-text-muted)">Memuat users...</p>
        </div>

        <!-- Empty state -->
        <div v-else-if="filteredUsers.length === 0" class="py-10 text-center text-sm italic" style="color: var(--color-text-muted)">
          <i class="bi bi-people text-2xl block mb-2"></i>
          {{ users.length === 0 ? 'Tidak ada user ditemukan.' : 'Tidak ada user yang cocok dengan pencarian.' }}
        </div>

        <!-- User grid -->
        <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2 max-h-[540px] overflow-auto pr-1">
          <label
            v-for="user in filteredUsers"
            :key="`employee-master-${user.id}`"
            class="user-row"
            :class="{ 'user-row--employee': user.is_employee, 'user-row--saving': savingUserId === user.id }"
          >
            <div class="min-w-0 pr-3 flex-1">
              <div class="text-sm font-semibold truncate" style="color: var(--color-text)">{{ user.name }}</div>
              <div class="text-xs font-mono truncate" style="color: var(--color-text-muted)">{{ user.id }}</div>
            </div>
            <div class="flex items-center gap-2.5 shrink-0">
              <span
                class="text-[11px] font-semibold transition-colors"
                :class="user.is_employee ? 'text-emerald-500' : ''"
                :style="user.is_employee ? '' : 'color: var(--color-text-muted)'"
              >
                {{ user.is_employee ? 'Employee' : 'Non-employee' }}
              </span>
              <span v-if="savingUserId === user.id" class="spinner-border h-3.5 w-3.5 text-primary shrink-0"></span>
              <input
                v-else
                type="checkbox"
                class="employee-checkbox"
                :checked="Boolean(user.is_employee)"
                :disabled="savingUserId === user.id"
                @change="toggleEmployee(user, $event.target.checked)"
              />
            </div>
          </label>
        </div>
      </div>
    </SectionCard>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { historyApi } from '../../api';
import SectionCard from '../ui/SectionCard.vue';
import TextInput from '../ui/TextInput.vue';

const users = ref([]);
const search = ref('');
const loading = ref(false);
const savingUserId = ref(null);
const pageMessage = ref('');
const pageMessageType = ref('success');

const filteredUsers = computed(() => {
  const keyword = search.value.trim().toLowerCase();
  if (!keyword) return users.value;
  return users.value.filter((user) => {
    const userName = String(user.name || '').toLowerCase();
    const userId = String(user.id || '').toLowerCase();
    return userName.includes(keyword) || userId.includes(keyword);
  });
});

const employeeCount = computed(() => users.value.filter((user) => Boolean(user.is_employee)).length);

const loadUsers = async () => {
  loading.value = true;
  try {
    const response = await historyApi.getPayrollUsers();
    users.value = (response.data.users || []).map((user) => ({
      ...user,
      is_employee: Boolean(user.is_employee)
    }));
  } catch (error) {
    users.value = [];
    pageMessageType.value = 'error';
    pageMessage.value = error.response?.data?.error || 'Failed to load Sagansa users';
  } finally {
    loading.value = false;
  }
};

const toggleEmployee = async (user, checked) => {
  if (!user?.id) return;
  const nextValue = Boolean(checked);
  const previousValue = Boolean(user.is_employee);
  user.is_employee = nextValue;
  savingUserId.value = user.id;
  pageMessage.value = '';
  try {
    const response = await historyApi.setPayrollUserEmployee(user.id, nextValue);
    user.is_employee = Boolean(response.data?.user?.is_employee);
    pageMessageType.value = 'success';
    pageMessage.value = `${user.name} ${user.is_employee ? 'ditandai sebagai employee' : 'dihapus dari employee'}.`;
  } catch (error) {
    user.is_employee = previousValue;
    pageMessageType.value = 'error';
    if (error.response?.status === 404) {
      pageMessage.value = 'Endpoint employee tidak ditemukan. Restart backend ke versi terbaru, lalu coba lagi.';
    } else {
      pageMessage.value = error.response?.data?.error || 'Failed to update employee status';
    }
  } finally {
    savingUserId.value = null;
  }
};

onMounted(loadUsers);
</script>

<style scoped>
/* ── User Row ────────────────────────────────────── */
.user-row {
  @apply flex items-center rounded-xl border px-3 py-2.5 cursor-pointer transition-all duration-150;
  border-color: var(--color-border);
  background: var(--color-surface);
}

.user-row:hover {
  background: var(--color-surface-muted);
  border-color: var(--color-border-strong);
}

.user-row--employee {
  background: rgba(16, 185, 129, 0.06);
  border-color: rgba(16, 185, 129, 0.22);
}

.user-row--employee:hover {
  background: rgba(16, 185, 129, 0.10);
}

.user-row--saving {
  opacity: 0.65;
  cursor: wait;
}

/* ── Checkbox ────────────────────────────────────── */
.employee-checkbox {
  @apply h-4 w-4 rounded cursor-pointer transition-all;
  accent-color: var(--color-primary);
  border-color: var(--color-border);
}
</style>
