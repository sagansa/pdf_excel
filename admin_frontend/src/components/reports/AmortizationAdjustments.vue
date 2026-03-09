<template>
  <div class="space-y-6">
    <!-- Header with Actions (if any needed for Amortization) -->

    <!-- Pending Transactions Alert (Compact) -->
    <div
      v-if="pendingTransactions?.length > 0"
      class="amortization-alert"
    >
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <i class="bi bi-exclamation-triangle-fill amortization-alert__icon"></i>
          <div>
            <h4 class="text-sm font-bold amortization-alert__title">
              {{ pendingTransactions.length }} transaksi aset belum terdaftar
            </h4>
            <p class="mt-0.5 text-xs amortization-alert__text">
              Terdapat transaksi yang ditandai sebagai Aset namun belum
              didaftarkan untuk diamortisasi.
            </p>
          </div>
        </div>
        <button
          @click="showAddAssetModal = true"
          class="amortization-alert__button"
        >
          <i class="bi bi-plus-circle-fill"></i> Daftarkan Aset Baru
        </button>
      </div>
    </div>
    <!-- Calculated Asset Amortization (Automatic) -->
    <div
      v-if="calculatedItems.length > 0"
      class="amortization-panel amortization-workspace mb-6"
    >
      <div class="amortization-workspace__header">
        <div>
          <h3 class="amortization-workspace__title">
            Calculated Asset Amortization
          </h3>
          <p class="mt-1 text-sm amortization-workspace__subtitle">
            Automatic calculation based on registered assets. Total:
            {{ formatCurrency(calculatedTotalAmortization) }}
          </p>
        </div>
        <div class="amortization-pill">
          Automatic
        </div>
      </div>

      <div class="amortization-workspace__body">
        <div class="overflow-x-auto amortization-table-shell">
          <table class="w-full">
            <thead class="amortization-table-head">
              <tr>
                <th
                  class="amortization-table-head__cell min-w-[120px]"
                >
                  Tx Date
                </th>
                <th
                  class="amortization-table-head__cell min-w-[200px]"
                >
                  Asset Name
                </th>
                <th
                  class="amortization-table-head__cell min-w-[120px]"
                >
                  Group / Deductible
                </th>
                <th
                  class="amortization-table-head__cell w-[110px] text-right"
                >
                  Original Cost (Rp)
                </th>
                <th
                  class="amortization-table-head__cell w-[110px] text-right"
                >
                  Accum. Depr (Prev) (Rp)
                </th>
                <th
                  class="amortization-table-head__cell w-[60px] text-center"
                >
                  Mult.
                </th>
                <th
                  class="amortization-table-head__cell w-[110px] text-right"
                >
                  Amortization (Curr) (Rp)
                </th>
                <th
                  class="amortization-table-head__cell w-[110px] text-right"
                >
                  Total Accum. Depr (Rp)
                </th>
                <th
                  class="amortization-table-head__cell w-[110px] text-right"
                >
                  Book Value (End) (Rp)
                </th>
                <th
                  class="amortization-table-head__cell w-[80px] text-center"
                >
                  Actions
                </th>
              </tr>
            </thead>
            <tbody class="amortization-table-body divide-y">
              <tr
                v-for="item in calculatedItems"
                :key="item.asset_id"
                class="amortization-row"
              >
                <td class="px-4 py-3 text-xs text-slate-600 font-mono">
                  {{ formatDate(item.txn_date || item.acquisition_date) }}
                </td>
                <td class="px-4 py-3">
                  <div class="flex flex-col gap-0.5 max-w-[250px]">
                    <!-- Notes as Main Title (Bold) if exists -->
                    <div
                      v-if="item.notes || item.amortization_notes"
                      class="text-sm font-bold text-slate-800 break-words leading-tight"
                    >
                      {{ item.notes || item.amortization_notes }}
                    </div>
                    <!-- Description/Asset Name as Subtitle (Italic) -->
                    <div
                      class="text-xs text-slate-500 italic break-words leading-tight"
                      :class="{
                        'font-semibold text-slate-700 not-italic text-sm': !(
                          item.notes || item.amortization_notes
                        ),
                      }"
                    >
                      {{ item.asset_name }}
                    </div>
                  </div>
                </td>
                <td class="px-4 py-3">
                  <div class="flex flex-col">
                    <span class="text-xs font-medium text-slate-700">{{
                      getCalculatedGroupLabel(item)
                    }}</span>
                    <span class="text-[10px] text-slate-500">{{
                      getDeductibleLabel(item)
                    }}</span>
                  </div>
                </td>
                <td class="px-4 py-3 text-sm text-right text-slate-600">
                  {{ formatCurrency(item.acquisition_cost, false) }}
                </td>
                <td class="px-4 py-3 text-sm text-right text-slate-500">
                  {{
                    formatCurrency(
                      item.accumulated_depreciation_prev_year || 0,
                      false,
                    )
                  }}
                </td>

                <td class="px-4 py-3 text-center">
                  <div class="flex flex-col items-center gap-1">
                    <span
                      class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-amber-100 text-amber-800"
                    >
                      {{ item.multiplier }}
                    </span>
                  </div>
                </td>
                <td
                  class="px-4 py-3 text-sm text-right font-bold text-indigo-700"
                >
                  {{ formatCurrency(item.annual_amortization, false) }}
                </td>
                <td class="px-4 py-3 text-sm text-right text-slate-600">
                  {{
                    formatCurrency(
                      item.total_accumulated_depreciation || 0,
                      false,
                    )
                  }}
                </td>
                <td
                  class="px-4 py-3 text-sm text-right font-bold text-slate-800"
                >
                  {{ formatCurrency(item.book_value_end_year || 0, false) }}
                </td>
                <td class="px-4 py-3">
                  <div class="flex items-center justify-center gap-2">
                    <!-- Manual Asset Actions -->
                    <template v-if="item.is_manual_asset">
                      <button
                        @click="editItem(item)"
                        class="text-gray-400 hover:text-indigo-600 transition-colors"
                        title="Edit"
                      >
                        <i class="bi bi-pencil-square"></i>
                      </button>
                      <button
                        @click="confirmDelete(item)"
                        class="text-gray-400 hover:text-red-600 transition-colors"
                        title="Delete"
                      >
                        <i class="bi bi-trash"></i>
                      </button>
                    </template>
                    <!-- Transaction Actions -->
                    <template v-else-if="item.is_from_ledger">
                      <button
                        @click="openTransactionDetail(item)"
                        class="text-gray-400 hover:text-teal-600 transition-colors"
                        title="View Details"
                      >
                        <i class="bi bi-eye"></i>
                      </button>
                    </template>
                    <!-- Registered Asset Actions -->
                    <template v-else-if="item.asset_id">
                      <button
                        @click="editRegisteredAsset(item)"
                        class="text-gray-400 hover:text-indigo-600 transition-colors"
                        title="Edit Asset"
                      >
                        <i class="bi bi-pencil-square"></i>
                      </button>
                      <button
                        @click="confirmDeleteAsset(item)"
                        class="text-gray-400 hover:text-red-600 transition-colors"
                        title="Delete Asset"
                      >
                        <i class="bi bi-trash"></i>
                      </button>
                    </template>
                    <span
                      v-else
                      class="text-slate-300 pointer-events-none"
                      title="No actions available"
                    >
                      <i class="bi bi-dash text-xs"></i>
                    </span>
                  </div>
                </td>
              </tr>
            </tbody>
            <tfoot class="amortization-table-foot">
              <tr class="font-bold">
                <td
                  colspan="3"
                  class="px-4 py-3 text-right text-sm uppercase tracking-wider"
                  style="color: var(--color-text)"
                >
                  Total Calculated Amortization
                </td>
                <td class="px-4 py-3 text-right text-sm" style="color: var(--color-text)">
                  {{ formatCurrency(totalOriginalCost, false) }}
                </td>
                <td colspan="2"></td>
                <td class="px-4 py-3 text-right text-sm" style="color: var(--color-text)">
                  {{ formatCurrency(calculatedTotalAmortization, false) }}
                </td>
                <td></td>
                <td class="px-4 py-3 text-right text-sm" style="color: var(--color-text)">
                  {{ formatCurrency(totalBookValueEnd, false) }}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>

    <!-- Amortization Items List (Manual & Transactions) -->
    <div
      class="amortization-panel amortization-workspace mb-6"
    >
      <div class="amortization-workspace__header">
        <div>
          <h3 class="amortization-workspace__title">
            Manual & Transaction Adjustments
          </h3>
          <p class="mt-1 text-sm amortization-workspace__subtitle">
            Manual and transactional adjustments. Total:
            {{ formatCurrency(manualTotalAmortization) }}
            <span v-if="manualItems.length > 0" style="color: var(--color-primary)"
              >({{ manualItems.length }} entries)</span
            >
          </p>
        </div>
        <div class="flex items-center gap-3">
          <div
            class="amortization-pill"
          >
            Manual/Tx
          </div>
          <button
            @click="openAddModal"
            :disabled="!companyId"
            class="btn-primary gap-2 px-4 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i class="bi bi-plus-lg"></i>
            Add Entry
          </button>
          <button
            @click="generateJournalEntries"
            :disabled="!companyId || manualItems.length === 0"
            class="btn-secondary gap-2 px-4 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i class="bi bi-journal-text"></i>
            Generate Journals
          </button>
        </div>
      </div>

      <div class="amortization-workspace__body">
        <!-- Empty State -->
        <div
          v-if="manualItems.length === 0"
          class="amortization-empty-state"
        >
          <i class="bi bi-calendar-check text-4xl text-muted"></i>
          <p class="mt-3 text-sm text-muted">
            No manual amortization entries yet
          </p>
          <p class="mt-1 text-xs text-muted">
            Click "Add Entry" to create a new amortization record
          </p>
        </div>

        <div v-if="manualItems.length > 0" class="overflow-x-auto amortization-table-shell">
          <table class="w-full">
            <thead class="amortization-table-head">
              <tr>
                <th
                  class="amortization-table-head__cell min-w-[120px]"
                >
                  Tx Date
                </th>
                <th
                  class="amortization-table-head__cell min-w-[200px]"
                >
                  Asset Name
                </th>
                <th
                  class="amortization-table-head__cell min-w-[120px]"
                >
                  Group / Deductible
                </th>
                <th
                  class="amortization-table-head__cell w-[110px] text-right"
                >
                  Original Cost (Rp)
                </th>
                <th
                  class="amortization-table-head__cell w-[110px] text-right"
                >
                  Accum. Depr (Prev) (Rp)
                </th>
                <th
                  class="amortization-table-head__cell w-[60px] text-center"
                >
                  Mult.
                </th>
                <th
                  class="amortization-table-head__cell w-[110px] text-right"
                >
                  Amortization (Curr) (Rp)
                </th>
                <th
                  class="amortization-table-head__cell w-[110px] text-right"
                >
                  Total Accum. Depr (Rp)
                </th>
                <th
                  class="amortization-table-head__cell w-[110px] text-right"
                >
                  Book Value (End) (Rp)
                </th>
                <th
                  class="amortization-table-head__cell w-[80px] text-center"
                >
                  Actions
                </th>
              </tr>
            </thead>
            <tbody class="amortization-table-body divide-y">
              <tr
                v-for="item in manualItems"
                :key="item.id"
                class="amortization-row"
                :class="{ 'opacity-80 amortization-row--muted': !item.is_manual }"
              >
                <td class="px-4 py-3 text-xs text-slate-600 font-mono">
                  {{
                    formatDate(
                      item.amortization_date ||
                        item.acquisition_date ||
                        item.txn_date ||
                        item.created_at,
                    )
                  }}
                </td>
                <td class="px-4 py-3">
                  <div class="flex flex-col gap-0.5 max-w-[250px]">
                    <div
                      v-if="item.notes"
                      class="text-sm font-bold text-slate-800 break-words leading-tight"
                    >
                      {{ item.notes }}
                    </div>
                    <div
                      class="text-xs text-slate-500 italic break-words leading-tight"
                      :class="{
                        'font-semibold text-slate-700 not-italic text-sm':
                          !item.notes,
                      }"
                    >
                      {{ item.description }}
                      <span
                        v-if="!item.is_manual"
                        class="ml-1 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase shrink-0"
                        style="background: rgba(15, 118, 110, 0.12); color: var(--color-primary)"
                        >Transaction</span
                      >
                    </div>
                  </div>
                </td>
                <td class="px-4 py-3">
                  <div class="flex flex-col">
                    <template v-if="item.asset_group_id">
                      <span class="text-xs font-medium text-slate-700">{{
                        getGroupName(item.asset_group_id)
                      }}</span>
                      <span class="text-[10px] text-slate-500">{{
                        getDeductibleLabel(item)
                      }}</span>
                    </template>
                    <template v-else>
                      <span class="text-xs font-medium text-slate-700">{{
                        item.coa_code
                      }}</span>
                      <span
                        class="text-[10px] text-slate-500 truncate max-w-[120px]"
                        >{{ item.coa_name }}</span
                      >
                    </template>
                  </div>
                </td>
                <td
                  class="px-4 py-3 text-sm text-right font-medium text-slate-600"
                >
                  {{ formatCurrency(item.amount, false) }}
                </td>
                <td class="px-4 py-3 text-sm text-right text-slate-400">
                  {{
                    item.asset_group_id
                      ? formatCurrency(
                          item.accumulated_depreciation_prev_year || 0,
                          false,
                        )
                      : "-"
                  }}
                </td>
                <td class="px-4 py-3 text-center">
                  <span
                    v-if="
                      item.multiplier !== null && item.multiplier !== undefined
                    "
                    class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-800"
                  >
                    {{ item.multiplier }}
                  </span>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td
                  class="px-4 py-3 text-sm text-right font-bold text-indigo-700"
                >
                  {{
                    formatCurrency(
                      item.annual_amortization ?? item.amount,
                      false,
                    )
                  }}
                </td>
                <td
                  class="px-4 py-3 text-sm text-right font-medium text-slate-600"
                >
                  {{
                    formatCurrency(
                      item.total_accumulated_depreciation || item.amount,
                      false,
                    )
                  }}
                </td>
                <td class="px-4 py-3 text-sm text-right text-slate-400">
                  {{
                    item.book_value_end_year !== undefined
                      ? formatCurrency(item.book_value_end_year, false)
                      : item.asset_group_id
                        ? "0"
                        : "-"
                  }}
                </td>
                <td class="px-4 py-3 text-sm text-center">
                  <div class="flex items-center justify-center gap-2">
                    <template v-if="item.is_manual">
                      <button
                        @click="editItem(item)"
                        class="text-gray-400 hover:text-indigo-600 transition-colors"
                        title="Edit"
                      >
                        <i class="bi bi-pencil-square"></i>
                      </button>
                      <button
                        @click="confirmDelete(item)"
                        class="text-gray-400 hover:text-red-600 transition-colors"
                        title="Delete"
                      >
                        <i class="bi bi-trash"></i>
                      </button>
                    </template>
                    <template v-else>
                      <button
                        @click="openTransactionDetail(item)"
                        class="text-gray-400 hover:text-teal-600 transition-colors"
                        title="View Details"
                      >
                        <i class="bi bi-eye"></i>
                      </button>
                    </template>
                  </div>
                </td>
              </tr>
            </tbody>
            <tfoot class="amortization-table-foot">
              <tr class="font-bold" style="color: var(--color-text)">
                <td
                  colspan="3"
                  class="px-4 py-3 text-sm text-right uppercase tracking-wider"
                >
                  Total Manual Adjustments
                </td>
                <td class="px-4 py-3 text-sm text-right">
                  {{ formatCurrency(manualTotalCalculated, false) }}
                </td>
                <td class="px-4 py-3 text-sm text-right">
                  {{ formatCurrency(manualTotalAccumPrev, false) }}
                </td>
                <td class="px-4 py-3 text-center">-</td>
                <td class="px-4 py-3 text-sm text-right">
                  {{ formatCurrency(manualTotalAmortization, false) }}
                </td>
                <td class="px-4 py-3 text-sm text-right">
                  {{ formatCurrency(manualTotalAccumTotal, false) }}
                </td>
                <td class="px-4 py-3 text-sm text-right">
                  {{ formatCurrency(manualTotalBookValue, false) }}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>

    <!-- Final Total Summary -->
    <div class="amortization-summary">
      <div>
        <h3 class="text-lg font-bold opacity-80 uppercase tracking-wider">
          Total Amortization Breakdown
        </h3>
      </div>
      <div class="flex gap-12">
        <div class="text-right">
          <span class="text-xs uppercase opacity-70"
            >Total Amortization (Curr)</span
          >
          <div class="text-3xl font-black text-indigo-100">
            {{ formatCurrency(grandTotalAmortization) }}
          </div>
        </div>
        <div class="text-right border-l border-indigo-700/50 pl-12">
          <span class="text-xs uppercase opacity-70"
            >Total Book Value (End)</span
          >
          <div class="text-3xl font-black text-indigo-100">
            {{ formatCurrency(grandTotalBookValue) }}
          </div>
        </div>
      </div>
    </div>

    <!-- Add/Edit Modal -->
    <div
      v-if="showModal"
      class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
    >
      <div
        class="bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto"
      >
        <div
          class="bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center justify-between"
        >
          <h3 class="text-lg font-bold text-slate-800">
            {{ editingItem ? "Edit" : "Add" }} Amortization Entry
          </h3>
          <button @click="closeModal" class="text-gray-400 hover:text-gray-600">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>

        <div class="p-6 space-y-4">
          <!-- Asset Mark Selection -->
          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-1">
              Asset Mark <span class="text-red-500">*</span>
            </label>
            <select
              v-model="form.mark_id"
              class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
            >
              <option value="">Select Asset Mark</option>
              <option
                v-for="mark in availableMarks"
                :key="mark.id"
                :value="mark.id"
              >
                {{ mark.personal_use }}
                <span v-if="mark.asset_type" class="text-gray-500">
                  ({{ mark.asset_type }})
                </span>
              </option>
            </select>
          </div>

          <!-- Date -->
          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-1">
              Amortization Date
            </label>
            <input
              v-model="form.amortization_date"
              type="date"
              class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
            />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <!-- Asset Group -->
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-1">
                Asset Group
              </label>
              <select
                v-model="form.asset_group_id"
                class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
              >
                <option value="">None (One-time adjustment)</option>
                <optgroup
                  v-for="(groups, type) in groupedAssetGroups"
                  :key="type"
                  :label="getAssetTypeLabel(type)"
                >
                  <option
                    v-for="group in groups"
                    :key="group.id"
                    :value="group.id"
                  >
                    {{ group.group_name }} ({{ group.tarif_rate }}%)
                  </option>
                </optgroup>
              </select>
            </div>

            <!-- Deductible Level -->
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-1">
                Deductible Level
              </label>
              <select
                v-model="form.use_half_rate"
                class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
              >
                <option :value="false">100% Deductible</option>
                <option :value="true">50% Deductible</option>
              </select>
            </div>
          </div>
          <div
            v-if="!form.asset_group_id && form.amount > 0"
            class="bg-orange-50 border border-orange-100 rounded-lg p-3 flex items-start gap-2 mt-4"
          >
            <i class="bi bi-info-circle-fill text-orange-500 mt-0.5"></i>
            <p class="text-[11px] text-orange-800 leading-tight">
              <strong>Calculation Note:</strong> No Asset Group selected. This
              will be treated as a direct amortization expense. Select a group
              to enable automatic annual depreciation.
            </p>
          </div>

          <!-- Description -->
          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-1">
              Description <span class="text-red-500">*</span>
            </label>
            <input
              v-model="form.description"
              type="text"
              class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
              placeholder="e.g., Amortization of intangible assets - Q1 2025"
            />
          </div>

          <!-- Amount -->
          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-1">
              Original Cost / Amount (Rp) <span class="text-red-500">*</span>
            </label>
            <div class="relative">
              <span
                class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-medium"
                >Rp</span
              >
              <input
                :value="formatDisplayNumber(form.amount)"
                type="text"
                inputmode="decimal"
                class="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
                placeholder="0"
                @input="updateAmountField($event.target.value)"
              />
            </div>
          </div>

          <!-- Notes -->
          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-1"
              >Notes</label
            >
            <textarea
              v-model="form.notes"
              rows="3"
              class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
              placeholder="Additional information about this amortization..."
            ></textarea>
          </div>
        </div>

        <div
          class="bg-slate-50 border-t border-slate-200 px-6 py-4 flex items-center justify-end gap-3"
        >
          <button
            @click="closeModal"
            class="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg font-medium text-sm transition-all"
          >
            Cancel
          </button>
          <button
            @click="saveItem"
            :disabled="!isFormValid || isSaving"
            class="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white px-6 py-2 rounded-lg font-medium text-sm transition-all flex items-center gap-2"
          >
            <i class="bi bi-check-lg" v-if="!isSaving"></i>
            <i class="bi bi-arrow-repeat spin" v-else></i>
            {{ editingItem ? "Update" : "Save" }}
          </button>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div
      v-if="showDeleteModal"
      class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full">
        <div class="p-6">
          <div class="flex items-center gap-3 mb-4">
            <div
              class="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center"
            >
              <i class="bi bi-exclamation-triangle text-red-600 text-xl"></i>
            </div>
            <div>
              <h3 class="text-lg font-bold text-slate-800">Delete Entry?</h3>
              <p class="text-sm text-slate-500">
                This action cannot be undone.
              </p>
            </div>
          </div>
          <p class="text-sm text-slate-600 mb-6">
            Are you sure you want to delete the amortization entry for
            <strong>{{ itemToDelete?.description }}</strong> ({{
              formatCurrency(itemToDelete?.amount)
            }})?
          </p>
          <div class="flex items-center justify-end gap-3">
            <button
              @click="showDeleteModal = false"
              class="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg font-medium text-sm transition-all"
            >
              Cancel
            </button>
            <button
              @click="deleteItem"
              :disabled="isDeleting"
              class="bg-red-600 hover:bg-red-700 disabled:bg-slate-300 text-white px-6 py-2 rounded-lg font-medium text-sm transition-all flex items-center gap-2"
            >
              <i class="bi bi-trash" v-if="!isDeleting"></i>
              <i class="bi bi-arrow-repeat spin" v-else></i>
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Transaction Detail Modal -->
    <div
      v-if="showTransactionDetailModal"
      class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-lg w-full">
        <div
          class="bg-teal-50 border-b border-teal-200 px-6 py-4 flex items-center justify-between"
        >
          <h3 class="text-lg font-bold text-teal-900">Transaction Details</h3>
          <button
            @click="closeTransactionDetailModal"
            class="text-gray-400 hover:text-gray-600"
          >
            <i class="bi bi-x-lg"></i>
          </button>
        </div>

        <div v-if="selectedTransaction" class="p-6 space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-gray-500 mb-1"
                >Transaction Date</label
              >
              <p class="text-sm text-gray-900">
                {{ selectedTransaction.txn_date }}
              </p>
            </div>
            <div>
              <label class="block text-xs font-semibold text-gray-500 mb-1"
                >Amount</label
              >
              <p class="text-sm font-bold text-gray-900">
                {{ formatCurrency(selectedTransaction.amount) }}
              </p>
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-500 mb-1"
              >Description</label
            >
            <p class="text-sm text-gray-900">
              {{ selectedTransaction.description }}
            </p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-500 mb-1"
              >Asset Mark</label
            >
            <p class="text-sm text-gray-900">
              {{
                selectedTransaction.mark_name ||
                selectedTransaction.coa_name ||
                "-"
              }}
            </p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-500 mb-1"
              >Notes</label
            >
            <p class="text-sm text-gray-900 italic">
              {{
                selectedTransaction.notes ||
                selectedTransaction.amortization_notes ||
                "-"
              }}
            </p>
          </div>

          <div class="border-t border-gray-200 pt-4">
            <h4 class="text-sm font-semibold text-gray-700 mb-3">
              Amortization Settings
            </h4>

            <div class="space-y-3">
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs font-semibold text-gray-500 mb-1"
                    >Asset Group</label
                  >
                  <select
                    v-model="selectedTransaction.asset_group_id"
                    class="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                  >
                    <option value="">Select Group...</option>
                    <optgroup
                      v-for="(groups, type) in groupedAssetGroups"
                      :key="type"
                      :label="getAssetTypeLabel(type)"
                    >
                      <option
                        v-for="group in groups"
                        :key="group.id"
                        :value="group.id"
                      >
                        {{ group.group_name }} ({{ group.tarif_rate }}%)
                      </option>
                    </optgroup>
                  </select>
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-500 mb-1"
                    >Deductible Level</label
                  >
                  <select
                    v-model="selectedTransaction.use_half_rate"
                    class="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                  >
                    <option :value="false">100% Deductible</option>
                    <option :value="true">50% Deductible</option>
                  </select>
                </div>
              </div>

              <div>
                <label class="block text-xs font-semibold text-gray-500 mb-1"
                  >Amortization Start Date</label
                >
                <input
                  type="date"
                  v-model="selectedTransaction.amortization_start_date"
                  class="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                />
              </div>

              <div>
                <label class="block text-xs font-semibold text-gray-500 mb-1"
                  >Notes</label
                >
                <textarea
                  v-model="selectedTransaction.notes"
                  rows="2"
                  class="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                  placeholder="Additional notes about amortization..."
                ></textarea>
              </div>
            </div>
          </div>
        </div>

        <div
          class="bg-gray-50 border-t border-gray-200 px-6 py-4 flex items-center justify-end gap-3"
        >
          <button
            @click="closeTransactionDetailModal"
            class="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg font-medium text-sm transition-all"
          >
            Cancel
          </button>
          <button
            @click="saveSelectedTransactionGroup"
            class="bg-teal-600 hover:bg-teal-700 text-white px-6 py-2 rounded-lg font-medium text-sm transition-all"
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <AddAssetModal
      :isOpen="showAddAssetModal"
      :company-id="companyId"
      :year="year"
      :asset-groups="assetGroups"
      :asset="editingAsset"
      @close="closeAddAssetModal"
      @save="handleAssetSaved"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useReportsStore } from "../../stores/reports";
import { useCoaStore } from "../../stores/coa";
import { useAmortizationStore } from "../../stores/amortization";
import { useMarksStore } from "../../stores/marks";
import api, { reportsApi, marksApi, historyApi } from "../../api/index";
import AddAssetModal from "./modals/AddAssetModal.vue";

const props = defineProps({
  companyId: {
    type: String,
    default: null,
  },
  year: {
    type: [String, Number],
    default: new Date().getFullYear(),
  },
});

const emit = defineEmits(["saved"]);
const store = useReportsStore();
const coaStore = useCoaStore();
const marksStore = useMarksStore();
const amortizationStore = useAmortizationStore();

// State
const items = ref([]);
const totalAmount = ref(0);
const calculatedTotal = ref(0);
const manualTotal = ref(0);
const settings = ref({});
const availableMarks = ref([]);
const assetGroups = ref([]);
const showTransactionDetailModal = ref(false);
const selectedTransaction = ref(null);

const pendingTransactions = ref([]);
const showAddAssetModal = ref(false);
const editingAsset = ref(null);

const calculatedItems = computed(() =>
  items.value.filter((item) => item.asset_id),
);
const manualItems = computed(() =>
  items.value.filter((item) => !item.asset_id),
);

const totalOriginalCost = computed(() =>
  calculatedItems.value.reduce(
    (sum, item) => sum + (item.acquisition_cost || 0),
    0,
  ),
);
const totalBookValueEnd = computed(() =>
  calculatedItems.value.reduce(
    (sum, item) => sum + (item.book_value_end_year || 0),
    0,
  ),
);

const calculatedTotalAmortization = computed(() =>
  calculatedItems.value.reduce(
    (sum, item) => sum + (item.annual_amortization || 0),
    0,
  ),
);

const manualTotalCalculated = computed(() =>
  manualItems.value.reduce((sum, item) => sum + (item.amount || 0), 0),
);

const manualTotalAccumPrev = computed(() =>
  manualItems.value.reduce(
    (sum, item) => sum + (item.accumulated_depreciation_prev_year || 0),
    0,
  ),
);

const manualTotalAmortization = computed(() =>
  manualItems.value.reduce(
    (sum, item) =>
      sum +
      (item.annual_amortization ||
        (item.asset_group_id ? 0 : item.amount) ||
        0),
    0,
  ),
);

const manualTotalAccumTotal = computed(() =>
  manualItems.value.reduce(
    (sum, item) =>
      sum +
      (item.total_accumulated_depreciation ||
        (item.asset_group_id ? 0 : item.amount) ||
        0),
    0,
  ),
);

const manualTotalBookValue = computed(() =>
  manualItems.value.reduce(
    (sum, item) => sum + (item.book_value_end_year || 0),
    0,
  ),
);

const grandTotalAmortization = computed(
  () => calculatedTotalAmortization.value + manualTotalAmortization.value,
);

const grandTotalBookValue = computed(
  () => totalBookValueEnd.value + manualTotalBookValue.value,
);

// Group asset groups by type for dropdown
const groupedAssetGroups = computed(() => {
  const grouped = { Tangible: [], Intangible: [], Building: [] };
  assetGroups.value.forEach((group) => {
    if (grouped[group.asset_type]) {
      grouped[group.asset_type].push(group);
    }
  });
  Object.keys(grouped).forEach((type) => {
    grouped[type].sort((a, b) => a.group_number - b.group_number);
  });
  return grouped;
});
const showModal = ref(false);
const showDeleteModal = ref(false);
const editingItem = ref(null);
const itemToDelete = ref(null);
const isSaving = ref(false);
const isDeleting = ref(false);

const form = ref({
  mark_id: "",
  description: "",
  amount: 0,
  notes: "",
  amortization_date: "",
  asset_group_id: "",
  use_half_rate: false,
});

const isFormValid = computed(() => {
  return form.value.mark_id && form.value.description && form.value.amount > 0;
});

// Methods
const fetchData = async () => {
  if (!props.companyId || !props.year) return;

  // Fetch asset groups first
  await fetchAssetGroups();
  await fetchPendingTransactions();

  // Fetch amortization items
  try {
    const data = await store.fetchAmortizationItems(
      props.year,
      props.companyId,
    );
    items.value = data.items || [];
    totalAmount.value = data.totalAmount || 0;
    calculatedTotal.value = data.calculated_total || 0;
    manualTotal.value = (data.totalAmount || 0) - calculatedTotal.value;
    settings.value = data.settings || {};
  } catch (e) {
    console.error("Failed to fetch amortization data:", e);
    items.value = [];
    totalAmount.value = 0;
    calculatedTotal.value = 0;
    manualTotal.value = 0;
  }

  await fetchAvailableMarks();
};

const fetchAvailableMarks = async () => {
  try {
    const response = await reportsApi.getAmortizationEligibleMarks(
      props.companyId,
    );
    availableMarks.value = response.data.marks || [];
  } catch (error) {
    console.error("Failed to fetch available marks:", error);
    availableMarks.value = [];
  }
};

const closeAddAssetModal = () => {
  showAddAssetModal.value = false;
  editingAsset.value = null;
};

const editRegisteredAsset = (item) => {
  editingAsset.value = item;
  showAddAssetModal.value = true;
};

const confirmDeleteAsset = async (item) => {
  if (
    confirm(
      `Apakah Anda yakin ingin menghapus aset terdaftar:\n${item.asset_name}?\n\nTransaksi yang ada akan dikembalikan menjadi tertunda (pending).`,
    )
  ) {
    try {
      await api.delete(`/amortization-assets/${item.asset_id}`);
      await fetchData();
    } catch (e) {
      alert(`Gagal menghapus aset. ${e.response?.data?.error || e.message}`);
    }
  }
};

const fetchPendingTransactions = async () => {
  if (!props.companyId) return;
  try {
    const response = await api.get("/reports/pending-amortization", {
      params: { company_id: props.companyId },
    });
    pendingTransactions.value = response.data.transactions || [];
  } catch (error) {
    console.error("Failed to fetch pending asset transactions", error);
    pendingTransactions.value = [];
  }
};

const handleAssetSaved = async (payload, isEdit) => {
  try {
    if (isEdit) {
      await api.put(`/amortization-assets/${payload.asset_id}`, payload);
    } else {
      await api.post("/amortization-assets", payload);
    }
    closeAddAssetModal();
    await fetchData(); // Refresh table and pending list
  } catch (error) {
    const errorMsg = error.response?.data?.error || error.message;
    alert(`Gagal menyimpan aset: ${errorMsg}`);
  }
};

const openAddModal = () => {
  editingItem.value = null;
  form.value = {
    mark_id: "",
    description: "",
    amount: 0,
    notes: "",
    amortization_date: new Date().toISOString().split("T")[0],
    asset_group_id: "",
    use_half_rate: false,
  };
  showModal.value = true;
};

const editItem = (item) => {
  editingItem.value = item;

  // Helper function to parse date to YYYY-MM-DD format
  const parseDate = (dateValue) => {
    if (!dateValue) return "";

    try {
      // If it's already in YYYY-MM-DD format, return it
      if (
        typeof dateValue === "string" &&
        /^\d{4}-\d{2}-\d{2}$/.test(dateValue)
      ) {
        return dateValue;
      }

      // Parse the date and convert to YYYY-MM-DD
      const date = new Date(dateValue);
      if (isNaN(date.getTime())) return "";

      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, "0");
      const day = String(date.getDate()).padStart(2, "0");
      return `${year}-${month}-${day}`;
    } catch (e) {
      console.error("Error parsing date:", e);
      return "";
    }
  };

  // Ensure proper data type conversions
  form.value = {
    mark_id: item.mark_id || "",
    description: item.description || "",
    amount: item.amount || 0,
    notes: item.notes || "",
    amortization_date: parseDate(item.amortization_date), // Parse date to YYYY-MM-DD
    asset_group_id: item.asset_group_id || "", // Convert null to empty string
    use_half_rate: item.use_half_rate === 1 || item.use_half_rate === true, // Convert 0/1 to boolean
  };

  showModal.value = true;
};

const closeModal = () => {
  showModal.value = false;
  editingItem.value = null;
};

const saveItem = async () => {
  if (!isFormValid.value || !props.companyId || !props.year) return;

  isSaving.value = true;
  try {
    if (editingItem.value) {
      // Update existing
      await store.updateAmortizationItem(editingItem.value.id, {
        mark_id: form.value.mark_id,
        description: form.value.description,
        amount: form.value.amount,
        notes: form.value.notes,
        amortization_date: form.value.amortization_date,
        asset_group_id: form.value.asset_group_id,
        use_half_rate: form.value.use_half_rate,
      });
    } else {
      // Create new
      await store.createAmortizationItem({
        company_id: props.companyId,
        year: parseInt(props.year),
        mark_id: form.value.mark_id,
        description: form.value.description,
        amount: form.value.amount,
        notes: form.value.notes,
        amortization_date: form.value.amortization_date,
        asset_group_id: form.value.asset_group_id,
        use_half_rate: form.value.use_half_rate,
      });
    }

    closeModal();
    await fetchData();
    emit("saved");
  } catch (err) {
    console.error("Failed to save item:", err);
  } finally {
    isSaving.value = false;
  }
};

const confirmDelete = (item) => {
  itemToDelete.value = item;
  showDeleteModal.value = true;
};

const deleteItem = async () => {
  if (!itemToDelete.value) return;

  isDeleting.value = true;
  try {
    await store.deleteAmortizationItem(itemToDelete.value.id);
    showDeleteModal.value = false;
    itemToDelete.value = null;
    await fetchData();
    emit("saved");
  } catch (err) {
    console.error("Failed to delete item:", err);
  } finally {
    isDeleting.value = false;
  }
};

const generateJournalEntries = async () => {
  try {
    isSaving.value = true;

    const result = await reportsApi.generateAmortizationJournals({
      company_id: props.companyId,
      year: parseInt(props.year),
    });

    // Show success message
    if (result.journal_count > 0) {
      alert(
        `✅ Success! Generated ${result.journal_count} journal entries for ${result.items_processed} manual amortization items.\n\nDebit entries (COA 5314): ${result.journal_count}\nCredit entries (COA 1530/1601): ${result.journal_count}\n\nJournals have been created in the balance sheet.`,
      );
    } else {
      alert(
        "ℹ️ No journal entries to generate. All manual amortization items already have journals.",
      );
    }

    // Refresh data to show updated balance sheet
    await fetchData();
  } catch (err) {
    console.error("Failed to generate journal entries:", err);
    alert(`❌ Failed to generate journal entries: ${err.message || err}`);
  } finally {
    isSaving.value = false;
  }
};

const parseFormattedNumber = (value) => {
  const raw = String(value || "").trim();
  if (!raw) return 0;

  const normalized = raw
    .replace(/\s/g, "")
    .replace(/\./g, "")
    .replace(/,/g, ".")
    .replace(/[^\d.-]/g, "");

  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
};

const formatDisplayNumber = (value) => {
  const numeric = Number(value || 0);
  return numeric.toLocaleString("id-ID", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
};

const updateAmountField = (value) => {
  form.value.amount = parseFormattedNumber(value);
};

const formatCurrency = (amount, includeSymbol = true) => {
  if (amount === null || amount === undefined)
    return includeSymbol ? "Rp 0" : "0";
  const formatted = new Intl.NumberFormat("id-ID", {
    style: "decimal",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
  return includeSymbol ? `Rp ${formatted}` : formatted;
};

const formatDate = (dateStr) => {
  if (!dateStr) return "-";
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr; // Return original if invalid date
    return date.toLocaleDateString("id-ID", {
      day: "numeric",
      month: "short",
      year: "numeric", // Changed to numeric for full year
    });
  } catch (e) {
    return dateStr;
  }
};

const getAssetTypeLabel = (type) => {
  const labels = {
    Tangible: "Harta Berwujud",
    Intangible: "Harta Tidak Berwujud",
    Building: "Bangunan",
  };
  return labels[type] || type;
};

const toBool = (value) => {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    return ["1", "true", "yes", "y", "on"].includes(normalized);
  }
  return false;
};

const getDeductibleLabel = (item) => {
  return toBool(item?.use_half_rate) ? "50%" : "100%";
};

const getCalculatedGroupLabel = (item) => {
  const typeLabel = getAssetTypeLabel(item?.asset_type || "Tangible");
  const groupName = String(item?.group_name || item?.mark_name || "").trim();
  const usefulLife = Number(item?.useful_life_years || 0);

  if (groupName) {
    if (Number.isFinite(usefulLife) && usefulLife > 0) {
      return `${typeLabel} - ${groupName} (${Math.round(usefulLife)} tahun)`;
    }
    return `${typeLabel} - ${groupName}`;
  }

  if (item?.group) return String(item.group);
  return typeLabel;
};

const getGroupName = (groupId) => {
  if (!groupId) return "";
  const group = assetGroups.value.find((g) => g.id === groupId);
  if (!group) return "Unknown Group";
  const typeLabel = getAssetTypeLabel(group.asset_type || "Tangible");
  const groupName = group.group_name || "Unknown Group";
  return group.useful_life_years
    ? `${typeLabel} - ${groupName} (${group.useful_life_years} tahun)`
    : `${typeLabel} - ${groupName}`;
};

// Fetch asset groups for dropdown
const fetchAssetGroups = async () => {
  try {
    assetGroups.value = await amortizationStore.fetchAssetGroups(
      props.companyId,
    );
  } catch (err) {
    console.error("Failed to fetch asset groups:", err);
  }
};

// Update transaction asset group
const updateTransactionGroup = async (item) => {
  try {
    const txnId = item?.asset_id || item?.id;
    if (!txnId) {
      alert("Failed to update transaction group: Transaction ID is missing");
      return false;
    }

    await historyApi.updateTransactionAmortizationGroup(txnId, {
      asset_group_id:
        item.asset_group_id || item.amortization_asset_group_id || null,
      is_amortizable: true,
      use_half_rate: Boolean(item.use_half_rate),
      amortization_start_date:
        item.amortization_start_date || item.start_date || null,
      amortization_useful_life: item.useful_life_years || null,
      amortization_notes: item.notes || item.amortization_notes || "",
    });
    emit("saved");
    await fetchData(); // Refresh to recalculate
    return true;
  } catch (err) {
    console.error("Failed to update transaction group:", err);
    alert(
      `Failed to update transaction group: ${
        err?.response?.data?.error || err?.message || "Unknown error"
      }`,
    );
    return false;
  }
};

const saveSelectedTransactionGroup = async () => {
  if (!selectedTransaction.value?.id) return;
  const isSaved = await updateTransactionGroup(selectedTransaction.value);
  if (isSaved) {
    closeTransactionDetailModal();
  }
};

// Open transaction detail modal
const openTransactionDetail = (item) => {
  selectedTransaction.value = {
    ...item,
    id: item.id || item.asset_id || null,
    asset_group_id:
      item.asset_group_id || item.amortization_asset_group_id || "",
    amortization_start_date:
      item.amortization_start_date || item.start_date || item.txn_date || "",
    notes: item.notes || item.amortization_notes || "",
    use_half_rate: !!item.use_half_rate, // Force boolean
  };
  showTransactionDetailModal.value = true;
};

// Close transaction detail modal
const closeTransactionDetailModal = () => {
  showTransactionDetailModal.value = false;
  selectedTransaction.value = null;
};

// Watchers
watch(
  () => [props.companyId, props.year],
  () => {
    fetchData();
  },
  { deep: true },
);

onMounted(() => {
  fetchData();
});
</script>

<style scoped>
.spin {
  animation: spin 1s linear infinite;
}

.amortization-alert {
  @apply rounded-2xl p-4 shadow-sm;
  background: rgba(180, 83, 9, 0.10);
  border: 1px solid rgba(180, 83, 9, 0.18);
}

.amortization-alert__icon {
  @apply text-xl;
  color: var(--color-warning);
}

.amortization-alert__title {
  color: var(--color-text);
}

.amortization-alert__text {
  color: var(--color-text-muted);
}

.amortization-alert__button {
  @apply inline-flex shrink-0 items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold text-white transition-colors;
  background: linear-gradient(135deg, var(--color-warning), #d97706);
}

.amortization-alert__button:hover {
  filter: brightness(1.03);
}

.amortization-panel {
  @apply overflow-hidden rounded-2xl;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
}

.amortization-workspace {
  background:
    linear-gradient(180deg, rgba(15, 118, 110, 0.04), transparent 140px),
    var(--color-surface);
}

.amortization-workspace__header {
  @apply flex flex-col gap-4 px-6 py-5 lg:flex-row lg:items-start lg:justify-between;
  background: linear-gradient(
    180deg,
    rgba(15, 118, 110, 0.05),
    rgba(15, 118, 110, 0.015)
  );
  border-bottom: 1px solid var(--color-border);
}

.amortization-workspace__title {
  @apply text-xl font-bold;
  color: var(--color-text);
}

.amortization-workspace__subtitle {
  color: var(--color-text-muted);
}

.amortization-workspace__body {
  @apply p-6;
  background: var(--color-surface);
}

.amortization-panel__header {
  @apply flex items-center justify-between px-6 py-4;
  background: var(--color-surface-muted);
  border-bottom: 1px solid var(--color-border);
}

.amortization-panel__title {
  @apply text-lg font-bold;
  color: var(--color-text);
}

.amortization-panel__subtitle {
  color: var(--color-text-muted);
}

.amortization-pill {
  @apply rounded px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-white;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-strong));
}

.amortization-table-shell {
  @apply overflow-hidden rounded-2xl;
  background: color-mix(in srgb, var(--color-surface) 90%, black 10%);
  border: 1px solid color-mix(in srgb, var(--color-border) 88%, black 12%);
}

.amortization-table-head {
  background: color-mix(in srgb, var(--color-surface-muted) 82%, black 18%);
  border-bottom: 1px solid var(--color-border);
}

.amortization-table-head__cell {
  @apply px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em];
  color: var(--color-text-muted);
}

.amortization-table-body {
  background: color-mix(in srgb, var(--color-surface) 95%, black 5%);
}

.amortization-row {
  background: transparent;
  transition:
    background-color 160ms ease,
    border-color 160ms ease;
}

.amortization-row:hover {
  background: rgba(15, 118, 110, 0.05);
}

.amortization-row--muted {
  background: rgba(148, 163, 184, 0.05);
}

.amortization-table-foot {
  background: color-mix(in srgb, var(--color-surface-muted) 78%, black 22%);
  border-top: 1px solid var(--color-border);
}

.amortization-empty-state {
  @apply flex flex-col items-center justify-center rounded-2xl px-6 py-12 text-center;
  background: color-mix(in srgb, var(--color-surface-muted) 76%, black 24%);
  border: 1px dashed var(--color-border);
}

.amortization-summary {
  @apply flex items-center justify-between rounded-2xl p-6 text-white;
  background: linear-gradient(135deg, #0f3d47, #12304f);
  box-shadow: var(--shadow-card);
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
