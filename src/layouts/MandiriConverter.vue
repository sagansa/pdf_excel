<template>
  <div class="flex flex-col h-full">
    <FileUploader
      :accept="'.pdf'"
      :bank-type="'mandiri'"
      @file-selected="handleFileSelected"
      @conversion-complete="handleConversionComplete"
    />

    <div v-if="transactions.length > 0" class="overflow-auto flex-grow mt-4">
      <div class="inline-block min-w-full align-middle">
        <table class="min-w-full divide-y divide-gray-300">
          <thead>
            <tr class="bg-gray-50">
              <th
                v-for="header in tableHeaders"
                :key="header"
                class="px-3 py-3.5 text-sm font-semibold text-left text-gray-900"
              >
                {{ header }}
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="(transaction, index) in transactions" :key="index">
              <td
                v-for="header in tableHeaders"
                :key="header"
                class="px-3 py-4 text-sm text-gray-500 whitespace-nowrap"
              >
                {{ transaction[header] }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import FileUploader from '../components/FileUploader.vue'

const transactions = ref([])
const tableHeaders = ['Tanggal', 'Keterangan', 'Debet', 'Kredit', 'Saldo']

const handleFileSelected = () => {
  transactions.value = []
}

const handleConversionComplete = (data) => {
  transactions.value = data
}
</script>