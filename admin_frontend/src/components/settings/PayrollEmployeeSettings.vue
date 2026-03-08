<template>
  <div class="space-y-6">
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">Payroll Employee Master</h2>
          <p class="text-sm text-gray-500 mt-1">
            Tandai user Sagansa yang termasuk employee. Data disimpan di database bank_converter.
          </p>
        </div>
        <div class="flex items-center gap-2">
          <input
            v-model="search"
            type="text"
            placeholder="Search user..."
            class="w-64 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
          <button
            @click="loadUsers"
            class="px-3 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-60"
            :disabled="loading"
          >
            Refresh
          </button>
        </div>
      </div>
      <p v-if="pageMessage" class="text-xs mt-3" :class="pageMessageType === 'error' ? 'text-red-600' : 'text-emerald-600'">
        {{ pageMessage }}
      </p>
    </div>

    <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div class="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
        <h4 class="text-sm font-semibold text-gray-800">Sagansa Users</h4>
        <span class="text-xs text-gray-500">
          {{ employeeCount }} employee dari {{ users.length }} user
        </span>
      </div>
      <div class="p-4">
        <div v-if="loading" class="text-sm text-gray-500 py-6 text-center">Loading users...</div>
        <div v-else-if="filteredUsers.length === 0" class="text-sm text-gray-500 py-6 text-center">No user found</div>
        <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2 max-h-[520px] overflow-auto pr-1">
          <label
            v-for="user in filteredUsers"
            :key="`employee-master-${user.id}`"
            class="flex items-center justify-between rounded-lg border border-gray-200 px-3 py-2 hover:bg-gray-50"
          >
            <div class="min-w-0 pr-3">
              <div class="text-sm font-medium text-gray-900 truncate">{{ user.name }}</div>
              <div class="text-xs text-gray-500 truncate">{{ user.id }}</div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <span class="text-[11px] font-semibold" :class="user.is_employee ? 'text-emerald-700' : 'text-gray-400'">
                {{ user.is_employee ? 'Employee' : 'Non-employee' }}
              </span>
              <input
                type="checkbox"
                class="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                :checked="Boolean(user.is_employee)"
                :disabled="savingUserId === user.id"
                @change="toggleEmployee(user, $event.target.checked)"
              />
            </div>
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { historyApi } from '../../api';

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
