<template>
  <div class="space-y-6">
    <!-- Calculated Asset Amortization (Automatic) -->
    <div
      v-if="calculatedItems.length > 0"
      class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden mb-6"
    >
      <div
        class="bg-indigo-50 border-b border-indigo-100 px-6 py-4 flex items-center justify-between"
      >
        <div>
          <h3 class="text-lg font-bold text-indigo-900">
            Calculated Asset Amortization
          </h3>
          <p class="text-xs text-indigo-700 mt-0.5">
            Automatic calculation based on registered assets. Total:
            {{ formatCurrency(calculatedTotalAmortization) }}
          </p>
        </div>
        <div
          class="bg-indigo-600 text-white text-[10px] font-bold px-2 py-1 rounded uppercase tracking-wider"
        >
          Automatic
        </div>
      </div>

      <div class="p-6">
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead class="bg-indigo-50/30 border-b border-indigo-100">
              <tr>
                <th
                  class="px-4 py-3 text-left text-xs font-medium text-indigo-700 uppercase min-w-[120px]"
                >
                  Tx Date
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-medium text-indigo-700 uppercase min-w-[200px]"
                >
                  Asset Name
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-medium text-indigo-700 uppercase min-w-[120px]"
                >
                  Type / Group
                </th>
                <th
                  class="px-4 py-3 text-right text-xs font-medium text-indigo-700 uppercase w-[110px]"
                >
                  Original Cost (Rp)
                </th>
                <th
                  class="px-4 py-3 text-right text-xs font-medium text-indigo-700 uppercase w-[110px]"
                >
                  Accum. Depr (Prev) (Rp)
                </th>
                <th
                  class="px-4 py-3 text-center text-xs font-medium text-indigo-700 uppercase w-[60px]"
                >
                  Mult.
                </th>
                <th
                  class="px-4 py-3 text-right text-xs font-medium text-indigo-700 uppercase w-[110px]"
                >
                  Amortization (Curr) (Rp)
                </th>
                <th
                  class="px-4 py-3 text-right text-xs font-medium text-indigo-700 uppercase w-[110px]"
                >
                  Total Accum. Depr (Rp)
                </th>
                <th
                  class="px-4 py-3 text-right text-xs font-medium text-indigo-700 uppercase w-[110px]"
                >
                  Book Value (End) (Rp)
                </th>
                <th
                  class="px-4 py-3 text-center text-xs font-medium text-indigo-700 uppercase w-[80px]"
                >
                  Actions
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr
                v-for="item in calculatedItems"
                :key="item.asset_id"
                class="hover:bg-indigo-50/20"
              >
                <td class="px-4 py-3 text-xs text-slate-600 font-mono">
                  {{ formatDate(item.txn_date || item.acquisition_date) }}
                </td>
                <td class="px-4 py-3">
                  <div class="flex flex-col gap-0.5 max-w-[250px]">
                    <!-- Notes as Main Title (Bold) if exists -->
                    <div
                      v-if="item.amortization_notes"
                      class="text-sm font-bold text-slate-800 break-words leading-tight"
                    >
                      {{ item.amortization_notes }}
                    </div>
                    <!-- Description/Asset Name as Subtitle (Italic) -->
                    <div
                      class="text-xs text-slate-500 italic break-words leading-tight"
                      :class="{
                        'font-semibold text-slate-700 not-italic text-sm':
                          !item.amortization_notes,
                      }"
                    >
                      {{ item.asset_name }}
                    </div>
                  </div>
                </td>
                <td class="px-4 py-3">
                  <div class="flex flex-col">
                    <span class="text-xs font-medium text-slate-700">{{
                      item.group
                    }}</span>
                    <span class="text-[10px] text-slate-500">{{
                      item.rate_type
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
                    <span
                      v-else
                      class="text-slate-300 pointer-events-none"
                      title="Asset details can be managed in settings"
                    >
                      <i class="bi bi-lock-fill text-xs"></i>
                    </span>
                  </div>
                </td>
              </tr>
            </tbody>
            <tfoot class="bg-indigo-50/50 border-t-2 border-indigo-100">
              <tr class="font-bold">
                <td
                  colspan="3"
                  class="px-4 py-3 text-sm text-indigo-900 text-right uppercase tracking-wider"
                >
                  Total Calculated Amortization
                </td>
                <td class="px-4 py-3 text-sm text-right text-indigo-900">
                  {{ formatCurrency(totalOriginalCost, false) }}
                </td>
                <td colspan="2"></td>
                <td class="px-4 py-3 text-sm text-right text-indigo-900">
                  {{ formatCurrency(calculatedTotalAmortization, false) }}
                </td>
                <td></td>
                <td class="px-4 py-3 text-sm text-right text-indigo-900">
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
      class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden mb-6"
    >
      <div
        class="bg-indigo-50 border-b border-indigo-100 px-6 py-4 flex items-center justify-between"
      >
        <div>
          <h3 class="text-lg font-bold text-indigo-900">
            Manual & Transaction Adjustments
          </h3>
          <p class="text-xs text-indigo-700 mt-0.5">
            Manual and transactional adjustments. Total:
            {{ formatCurrency(manualTotalAmortization) }}
            <span v-if="manualItems.length > 0" class="text-indigo-600"
              >({{ manualItems.length }} entries)</span
            >
          </p>
        </div>
        <div class="flex items-center gap-3">
          <div
            class="bg-indigo-600 text-white text-[10px] font-bold px-2 py-1 rounded uppercase tracking-wider"
          >
            Manual/Tx
          </div>
          <button
            @click="openAddModal"
            :disabled="!companyId"
            class="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white px-4 py-2 rounded-lg font-medium text-sm transition-all flex items-center gap-2"
          >
            <i class="bi bi-plus-lg"></i>
            Add Entry
          </button>
          <button
            @click="generateJournalEntries"
            :disabled="!companyId || manualItems.length === 0"
            class="bg-green-600 hover:bg-green-700 disabled:bg-slate-300 text-white px-4 py-2 rounded-lg font-medium text-sm transition-all flex items-center gap-2"
          >
            <i class="bi bi-journal-text"></i>
            Generate Journals
          </button>
        </div>
      </div>

      <div class="p-6">
        <!-- Empty State -->
        <div
          v-if="manualItems.length === 0"
          class="text-center py-12 bg-slate-50 rounded-lg border border-dashed border-slate-200"
        >
          <i class="bi bi-calendar-check text-4xl text-slate-300"></i>
          <p class="text-slate-500 mt-3 text-sm">
            No manual amortization entries yet
          </p>
          <p class="text-slate-400 text-xs mt-1">
            Click "Add Entry" to create a new amortization record
          </p>
        </div>

        <div v-if="manualItems.length > 0" class="overflow-x-auto">
          <table class="w-full">
            <thead class="bg-indigo-50/30 border-b border-indigo-100">
              <tr>
                <th
                  class="px-4 py-3 text-left text-xs font-medium text-indigo-700 uppercase min-w-[120px]"
                >
                  Tx Date
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-medium text-indigo-700 uppercase min-w-[200px]"
                >
                  Asset Name
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-medium text-indigo-700 uppercase min-w-[120px]"
                >
                  Type / Group
                </th>
                <th
                  class="px-4 py-3 text-right text-xs font-medium text-indigo-700 uppercase w-[110px]"
                >
                  Original Cost (Rp)
                </th>
                <th
                  class="px-4 py-3 text-right text-xs font-medium text-indigo-700 uppercase w-[110px]"
                >
                  Accum. Depr (Prev) (Rp)
                </th>
                <th
                  class="px-4 py-3 text-center text-xs font-medium text-indigo-700 uppercase w-[60px]"
                >
                  Mult.
                </th>
                <th
                  class="px-4 py-3 text-right text-xs font-medium text-indigo-700 uppercase w-[110px]"
                >
                  Amortization (Curr) (Rp)
                </th>
                <th
                  class="px-4 py-3 text-right text-xs font-medium text-indigo-700 uppercase w-[110px]"
                >
                  Total Accum. Depr (Rp)
                </th>
                <th
                  class="px-4 py-3 text-right text-xs font-medium text-indigo-700 uppercase w-[110px]"
                >
                  Book Value (End) (Rp)
                </th>
                <th
                  class="px-4 py-3 text-center text-xs font-medium text-indigo-700 uppercase w-[80px]"
                >
                  Actions
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr
                v-for="item in manualItems"
                :key="item.id"
                class="hover:bg-indigo-50/20"
                :class="{ 'opacity-80 bg-slate-50': !item.is_manual }"
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
                        class="ml-1 text-[10px] bg-teal-100 text-teal-700 px-1.5 py-0.5 rounded uppercase font-bold shrink-0"
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
                        item.use_half_rate
                          ? "50% Deductible"
                          : "100% Deductible"
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
            <tfoot class="bg-indigo-50/50 border-t-2 border-indigo-100">
              <tr class="font-bold text-indigo-900">
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
    <div
      class="bg-indigo-900 rounded-lg p-6 shadow-lg flex items-center justify-between text-white"
    >
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
                v-model.number="form.amount"
                type="number"
                class="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
                placeholder="0"
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
              {{ selectedTransaction.mark_name || selectedTransaction.coa_name || "-" }}
            </p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-500 mb-1"
              >Notes</label
            >
            <p class="text-sm text-gray-900 italic">
              {{ selectedTransaction.txn_notes || "-" }}
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
                    v-model="selectedTransaction.amortization_asset_group_id"
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
                  v-model="selectedTransaction.start_date"
                  class="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                />
              </div>

              <div>
                <label class="block text-xs font-semibold text-gray-500 mb-1"
                  >Notes</label
                >
                <textarea
                  v-model="selectedTransaction.amortization_notes"
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
            @click="
              () => {
                updateTransactionGroup(selectedTransaction);
                closeTransactionDetailModal();
              }
            "
            class="bg-teal-600 hover:bg-teal-700 text-white px-6 py-2 rounded-lg font-medium text-sm transition-all"
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useReportsStore } from "../../stores/reports";
import { useCoaStore } from "../../stores/coa";
import { useAmortizationStore } from "../../stores/amortization";
import { useMarksStore } from "../../stores/marks";
import { reportsApi, marksApi } from "../../api/index";
import axios from "axios";

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

  // Fetch available marks for dropdown
  console.log('🎯 About to call fetchAvailableMarks...');
  await fetchAvailableMarks();
  console.log('✅ fetchAvailableMarks completed');
};

const fetchAvailableMarks = async () => {
  console.log('🚀 fetchAvailableMarks called!');
  console.log('🏢 Company ID:', props.companyId);
  
  try {
    // Fetch marks that have asset-related COA mappings
    console.log('📡 Calling marks API...');
    const response = await reportsApi.getAmortizationEligibleMarks(props.companyId);
    console.log('📦 API Response:', response);
    
    // Extract marks from response.data
    availableMarks.value = response.data.marks || [];
    console.log('📦 Response data:', response.data);
    console.log('✅ Available marks loaded:', availableMarks.value.length);
    
    if (availableMarks.value.length > 0) {
      console.log('🎯 Marks sample:', availableMarks.value.slice(0, 3));
    } else {
      console.log('❌ No marks found in response');
    }
  } catch (error) {
    console.error('💥 Failed to fetch available marks:', error);
    console.error('📋 Error details:', error.response?.data || error.message);
    availableMarks.value = [];
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
  console.log("Editing item:", item); // Debug: check incoming data
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

  console.log("Form values after mapping:", form.value); // Debug: check form state
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
      year: parseInt(props.year)
    });
    
    // Show success message
    if (result.journal_count > 0) {
      alert(`✅ Success! Generated ${result.journal_count} journal entries for ${result.items_processed} manual amortization items.\n\nDebit entries (COA 5314): ${result.journal_count}\nCredit entries (COA 1530/1601): ${result.journal_count}\n\nJournals have been created in the balance sheet.`);
    } else {
      alert('ℹ️ No journal entries to generate. All manual amortization items already have journals.');
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

const getGroupName = (groupId) => {
  if (!groupId) return "";
  const group = assetGroups.value.find((g) => g.id === groupId);
  if (!group) return "Unknown Group";
  return group.tarif_rate
    ? `${group.group_name} (${group.tarif_rate}%)`
    : group.group_name;
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
    await axios.put(`/api/transactions/${item.id}/amortization-group`, {
      asset_group_id: item.amortization_asset_group_id || null,
      is_amortizable: true,
      use_half_rate: item.use_half_rate || false,
      amortization_start_date: item.start_date || null,
      amortization_useful_life: item.useful_life_years || null,
      amortization_notes: item.amortization_notes || "",
    });
    emit("saved");
    fetchData(); // Refresh to recalculate
  } catch (err) {
    console.error("Failed to update transaction group:", err);
    alert("Failed to update transaction group");
  }
};

// Open transaction detail modal
const openTransactionDetail = (item) => {
  selectedTransaction.value = {
    ...item,
    use_half_rate: !!item.use_half_rate, // Force boolean
    start_date: item.start_date || item.txn_date || "", // Default to txn_date
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

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
