<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">Income Statement</h2>
          <p class="text-sm text-gray-500 mt-1">Laporan Laba Rugi</p>
        </div>
        <div v-if="hasData" class="text-right">
          <p class="text-xs text-gray-500">Period</p>
          <p class="text-sm font-semibold text-gray-900">
            {{ formatDate(data.period.start_date) }} -
            {{ formatDate(data.period.end_date) }}
          </p>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-if="!hasData"
      class="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center"
    >
      <i class="bi bi-file-earmark-bar-graph text-6xl text-gray-300"></i>
      <p class="text-gray-500 mt-4 text-lg font-medium">No Report Generated</p>
      <p class="text-gray-400 text-sm mt-2">
        Select a date range and click "Generate Report" to view the income
        statement
      </p>
    </div>

    <!-- Report Content -->
    <div v-else class="space-y-6">
      <!-- Summary Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div
          class="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg shadow-sm border border-purple-200 p-6"
        >
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs font-medium text-purple-600 uppercase">
                Total Revenue
              </p>
              <p class="text-2xl font-bold text-purple-900 mt-1 whitespace-nowrap tabular-nums">
                {{ formatCurrency(data.total_revenue) }}
              </p>
            </div>
            <div
              class="w-12 h-12 rounded-full bg-purple-200 flex items-center justify-center"
            >
              <i class="bi bi-graph-up-arrow text-purple-700 text-xl"></i>
            </div>
          </div>
        </div>

        <div
          class="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg shadow-sm border border-orange-200 p-6"
        >
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs font-medium text-orange-600 uppercase">
                Total Expenses
              </p>
              <p class="text-2xl font-bold text-orange-900 mt-1 whitespace-nowrap tabular-nums">
                {{ formatCurrency(data.total_expenses) }}
              </p>
            </div>
            <div
              class="w-12 h-12 rounded-full bg-orange-200 flex items-center justify-center"
            >
              <i class="bi bi-graph-down-arrow text-orange-700 text-xl"></i>
            </div>
          </div>
        </div>

        <div
          class="bg-gradient-to-br from-green-50 to-green-100 rounded-lg shadow-sm border border-green-200 p-6"
        >
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs font-medium text-green-600 uppercase">
                Net Income
              </p>
              <p class="text-2xl font-bold text-green-900 mt-1 whitespace-nowrap tabular-nums">
                {{ formatCurrency(data.net_income) }}
              </p>
            </div>
            <div
              class="w-12 h-12 rounded-full bg-green-200 flex items-center justify-center"
            >
              <i class="bi bi-cash-coin text-green-700 text-xl"></i>
            </div>
          </div>
        </div>
      </div>

      <!-- Revenue Section -->
      <div
        class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
      >
        <div class="bg-purple-50 border-b border-purple-100 px-6 py-3">
          <h3 class="text-sm font-bold text-purple-900 uppercase">
            Revenue (Pendapatan)
          </h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th
                  class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                >
                  Code
                </th>
                <th
                  class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                >
                  Account Name
                </th>
                <th
                  class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                >
                  Subcategory
                </th>
                <th
                  class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase"
                >
                  Amount
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-if="data.revenue.length === 0">
                <td
                  colspan="4"
                  class="px-6 py-8 text-center text-gray-400 text-sm"
                  >
                  No revenue entries
                </td>
              </tr>
              <tr
                v-for="item in data.revenue"
                :key="item.code"
                class="group"
              >
                <td
                  class="px-6 py-3 text-sm font-mono font-semibold text-gray-900"
                >
                  {{ item.code }}
                </td>
                <td class="px-6 py-3 text-sm text-gray-900">{{ item.name }}</td>
                <td class="px-6 py-3 text-sm text-gray-500">
                  {{ item.subcategory || "-" }}
                </td>
                <td
                  class="px-6 py-3 text-right text-sm font-semibold text-purple-700"
                >
                  <div class="flex items-center justify-end gap-2">
                    <span class="whitespace-nowrap tabular-nums">{{ formatCurrency(item.amount) }}</span>
                    <button
                      @click.stop.prevent="copyToClipboard(item.amount)"
                      class="text-gray-400 hover:text-purple-600 transition-colors"
                      title="Copy amount"
                    >
                      <i class="bi bi-clipboard text-xs"></i>
                    </button>
                    <button
                      @click.stop.prevent="openCoaDetail(item)"
                      class="text-gray-400 hover:text-indigo-600 transition-colors"
                      title="View transactions"
                    >
                      <i class="bi bi-list-ul text-xs"></i>
                    </button>
                  </div>
                </td>
              </tr>
              <tr class="bg-purple-50 font-bold">
                <td colspan="3" class="px-6 py-3 text-sm text-purple-900">
                  Total Revenue
                </td>
                <td class="px-6 py-3 text-right text-purple-900">
                  <div class="flex items-center justify-end gap-2">
                    <span class="whitespace-nowrap tabular-nums">{{ formatCurrency(data.total_revenue) }}</span>
                    <button
                      @click.stop.prevent="copyToClipboard(data.total_revenue)"
                      class="text-gray-400 hover:text-purple-600 transition-colors"
                      title="Copy amount"
                    >
                      <i class="bi bi-clipboard text-xs"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

       <!-- COGS Section -->
       <div
         v-if="data.cogs_breakdown && data.cogs_breakdown.total_cogs > 0"
         class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
       >
         <div class="bg-blue-50 border-b border-blue-100 px-6 py-3">
           <h3 class="text-sm font-bold text-blue-900 uppercase">
             Cost of Goods Sold
           </h3>
         </div>
         <div class="p-6 space-y-6">
           <!-- Inventory Summary Cards -->
           <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
             <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
               <p class="text-xs font-medium text-blue-600 uppercase mb-1">Beginning Inventory - 5008</p>
               <p class="text-lg font-bold text-blue-900 whitespace-nowrap tabular-nums">{{ formatCurrency(data.cogs_breakdown.beginning_inventory) }}</p>
             </div>
             <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
               <p class="text-xs font-medium text-blue-600 uppercase mb-1">- Ending Inventory - 5009</p>
               <p class="text-lg font-bold text-blue-900 whitespace-nowrap tabular-nums">{{ formatCurrency(data.cogs_breakdown.ending_inventory) }}</p>
             </div>
             <div class="bg-blue-100 border border-blue-200 rounded-lg p-4">
               <p class="text-xs font-medium text-blue-600 uppercase mb-1">Total COGS</p>
               <p class="text-lg font-bold text-blue-900 whitespace-nowrap tabular-nums">{{ formatCurrency(data.cogs_breakdown.total_cogs) }}</p>
             </div>
           </div>

           <!-- Purchases Breakdown Table -->
           <div v-if="data.cogs_breakdown.purchases_items && data.cogs_breakdown.purchases_items.length > 0">
             <div class="bg-blue-100 border-b border-blue-200 px-6 py-2 mb-3">
               <h4 class="text-xs font-bold text-blue-800 uppercase">
                 Purchases Breakdown
               </h4>
             </div>
             <div class="overflow-x-auto">
               <table class="w-full">
                 <thead class="bg-gray-50 border-b border-gray-200">
                   <tr>
                     <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                     <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Account Name</th>
                     <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Subcategory</th>
                     <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                   </tr>
                 </thead>
                 <tbody class="divide-y divide-gray-100">
                   <tr
                     v-for="item in data.cogs_breakdown.purchases_items"
                     :key="item.code"
                     class="group"
                   >
                     <td class="px-6 py-3 text-sm font-mono font-semibold text-gray-900">
                       {{ item.code }}
                     </td>
                     <td class="px-6 py-3 text-sm text-gray-900">{{ item.name }}</td>
                     <td class="px-6 py-3 text-sm text-gray-500">
                       {{ item.subcategory || "-" }}
                     </td>
                     <td class="px-6 py-3 text-sm text-right font-semibold text-blue-700">
                       <div class="flex items-center justify-end gap-2">
                         <span class="whitespace-nowrap tabular-nums">{{ formatCurrency(item.amount) }}</span>
                         <button
                           @click.stop.prevent="copyToClipboard(item.amount)"
                           class="text-gray-400 hover:text-blue-600 transition-colors"
                           title="Copy amount"
                         >
                           <i class="bi bi-clipboard text-xs"></i>
                         </button>
                         <button
                           @click.stop.prevent="openCoaDetail(item)"
                           class="text-gray-400 hover:text-indigo-600 transition-colors"
                           title="View transactions"
                         >
                           <i class="bi bi-list-ul text-xs"></i>
                         </button>
                       </div>
                     </td>
                   </tr>
                   <tr class="bg-blue-50 font-bold">
                     <td colspan="3" class="px-6 py-3 text-sm text-blue-900">
                       Total Purchases
                     </td>
                     <td class="px-6 py-3 text-sm text-right text-blue-900">
                       <div class="flex items-center justify-end gap-2">
                         <span class="whitespace-nowrap tabular-nums">{{ formatCurrency(data.cogs_breakdown.purchases) }}</span>
                         <button
                           @click.stop.prevent="copyToClipboard(data.cogs_breakdown.purchases)"
                           class="text-gray-400 hover:text-blue-600 transition-colors"
                           title="Copy amount"
                         >
                           <i class="bi bi-clipboard text-xs"></i>
                         </button>
                       </div>
                     </td>
                   </tr>
                 </tbody>
               </table>
             </div>
           </div>

           <!-- Other COGS Items -->
           <div v-if="data.cogs_breakdown.other_cogs_items && data.cogs_breakdown.other_cogs_items.length > 0">
             <div class="bg-blue-100 border-b border-blue-200 px-6 py-2 mb-3">
               <h4 class="text-xs font-bold text-blue-800 uppercase">
                 Other COGS Items
               </h4>
             </div>
             <div class="overflow-x-auto">
               <table class="w-full">
                 <thead class="bg-gray-50 border-b border-gray-200">
                   <tr>
                     <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                     <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Account Name</th>
                     <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Subcategory</th>
                     <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                   </tr>
                 </thead>
                 <tbody class="divide-y divide-gray-100">
                   <tr
                     v-for="item in data.cogs_breakdown.other_cogs_items"
                     :key="item.code"
                     class="group"
                   >
                     <td class="px-6 py-3 text-sm font-mono font-semibold text-gray-900">
                       {{ item.code }}
                     </td>
                     <td class="px-6 py-3 text-sm text-gray-900">{{ item.name }}</td>
                     <td class="px-6 py-3 text-sm text-gray-500">
                       {{ item.subcategory || "-" }}
                     </td>
                     <td class="px-6 py-3 text-sm text-right font-semibold text-blue-700">
                       <div class="flex items-center justify-end gap-2">
                         <span class="whitespace-nowrap tabular-nums">{{ formatCurrency(item.amount) }}</span>
                         <button
                           @click.stop.prevent="copyToClipboard(item.amount)"
                           class="text-gray-400 hover:text-blue-600 transition-colors"
                           title="Copy amount"
                         >
                           <i class="bi bi-clipboard text-xs"></i>
                         </button>
                         <button
                           @click.stop.prevent="openCoaDetail(item)"
                           class="text-gray-400 hover:text-indigo-600 transition-colors"
                           title="View transactions"
                         >
                           <i class="bi bi-list-ul text-xs"></i>
                         </button>
                       </div>
                     </td>
                   </tr>
                   <tr class="bg-blue-50 font-bold">
                     <td colspan="3" class="px-6 py-3 text-sm text-blue-900">
                       Total Other COGS
                     </td>
                     <td class="px-6 py-3 text-sm text-right text-blue-900">
                       <div class="flex items-center justify-end gap-2">
                         <span class="whitespace-nowrap tabular-nums">{{ formatCurrency(data.cogs_breakdown.total_other_cogs) }}</span>
                         <button
                           @click.stop.prevent="copyToClipboard(data.cogs_breakdown.total_other_cogs)"
                           class="text-gray-400 hover:text-blue-600 transition-colors"
                           title="Copy amount"
                         >
                           <i class="bi bi-clipboard text-xs"></i>
                         </button>
                       </div>
                     </td>
                   </tr>
                 </tbody>
               </table>
             </div>
           </div>
         </div>
       </div>

      <!-- Expenses Section -->
      <div
        class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
      >
        <div class="bg-orange-50 border-b border-orange-100 px-6 py-3">
          <h3 class="text-sm font-bold text-orange-900 uppercase">
            Expenses (Beban)
          </h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Account Name</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Subcategory</th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
              </tr>
            </thead>
              <tr v-if="data.expenses.length === 0">
                <td colspan="4" class="px-6 py-8 text-center text-gray-400 text-sm">No expenses recorded</td>
              </tr>
              <tr v-for="item in data.expenses.filter(e => e.fiscal_category !== 'NON_DEDUCTIBLE_PERMANENT')" :key="item.code" class="group dark:hover:bg-gray-800/50 transition-colors">
                <td class="px-6 py-3 text-sm font-mono font-semibold text-gray-900 dark:text-gray-300">{{ item.code }}</td>
                <td class="px-6 py-3 text-sm text-gray-900 dark:text-gray-200">
                  <div class="flex items-center gap-2">
                    {{ item.name }}
                    <FiscalCategoryBadge v-if="item.fiscal_category === 'NON_DEDUCTIBLE_PERMANENT'" :category="item.fiscal_category" size="sm" />
                  </div>
                </td>
                <td class="px-6 py-3 text-sm text-gray-500 dark:text-gray-400">{{ item.subcategory || "-" }}</td>
                <td class="px-6 py-3 text-sm text-right font-semibold text-rose-700 dark:text-rose-400">
                   <div class="flex items-center justify-end gap-2">
                     <span class="whitespace-nowrap tabular-nums">{{ formatCurrency(item.amount) }}</span>
                     <button @click.stop.prevent="openCoaDetail(item)" class="text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors opacity-0 group-hover:opacity-100"><i class="bi bi-list-ul text-xs"></i></button>
                   </div>
                </td>
              </tr>

              <!-- Total Row -->
              <tr class="bg-gray-900 dark:bg-gray-800 font-bold border-t-2 border-gray-800 dark:border-gray-700">
                <td colspan="3" class="px-6 py-4 text-sm text-white uppercase tracking-wider">Total Operational Expenses</td>
                <td class="px-6 py-4 text-sm text-right text-white">
                  <span class="whitespace-nowrap tabular-nums">{{ formatCurrency(data.total_expenses - (data.fiscal_reconciliation?.total_positive_correction || 0)) }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

       <!-- Final Net Income Summary & Reconciliation -->
       <div v-if="data.fiscal_reconciliation" class="bg-white dark:bg-[#1f2937] rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden text-gray-900 dark:text-gray-100">
         
         <!-- COMMERCIAL NET INCOME -->
         <div class="px-6 py-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between"
              :class="data.net_income >= 0 ? 'bg-emerald-50 dark:bg-emerald-900/20' : 'bg-rose-50 dark:bg-rose-900/20'">
           <div>
             <p class="text-xs font-bold uppercase tracking-wider mb-1" :class="data.net_income >= 0 ? 'text-emerald-800 dark:text-emerald-400' : 'text-rose-800 dark:text-rose-400'">Commercial Net Income</p>
             <p class="text-[10px] uppercase opacity-70">Laba (Rugi) Bersih Sebelum Pajak</p>
           </div>
           <div class="text-right flex flex-col items-end">
             <p class="text-2xl font-black whitespace-nowrap tabular-nums" :class="data.net_income >= 0 ? 'text-emerald-700 dark:text-emerald-300' : 'text-rose-700 dark:text-rose-300'">
               {{ formatCurrency(data.net_income) }}
             </p>
           </div>
         </div>

         <!-- NON DEDUCTIBLE ITEMS -->
         <div v-if="data.fiscal_reconciliation.total_positive_correction > 0" class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-[#111827]/50">
           <div class="flex items-center justify-between mb-3 text-sm">
             <div class="flex items-center gap-2">
               <i class="bi bi-plus-circle text-rose-600 dark:text-rose-400 font-bold"></i>
               <span class="font-bold text-gray-800 dark:text-gray-200 uppercase tracking-widest text-xs">Non-Deductible Expenses (Koreksi Fiskal Positif)</span>
             </div>
             <span class="font-bold text-rose-600 dark:text-rose-400 tabular-nums">{{ formatCurrency(data.fiscal_reconciliation.total_positive_correction) }}</span>
           </div>
           
           <!-- List of specific accounts -->
           <ul class="space-y-2 pl-6">
             <li v-for="item in data.fiscal_reconciliation.positive_corrections" :key="item.code" class="flex justify-between items-center text-xs text-gray-600 dark:text-gray-400">
               <span class="flex items-center gap-2">
                 <span class="font-mono bg-gray-200 dark:bg-gray-800 px-1 py-0.5 rounded text-[10px]">{{ item.code }}</span>
                 {{ item.name }}
               </span>
               <span class="font-mono tabular-nums">{{ formatCurrency(item.amount) }}</span>
             </li>
           </ul>
         </div>

         <!-- FISCAL NET INCOME -->
         <div class="px-6 py-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between"
              :class="data.fiscal_reconciliation.fiscal_net_income >= 0 ? 'bg-indigo-50 dark:bg-indigo-900/20' : 'bg-red-50 dark:bg-red-900/20'">
           <div>
             <p class="text-xs font-bold uppercase tracking-wider mb-1 text-indigo-800 dark:text-indigo-400">Fiscal Net Income</p>
             <p class="text-[10px] uppercase opacity-70">Laba (Rugi) Bersih Fiskal</p>
           </div>
           <div class="text-right flex flex-col items-end">
             <p class="text-2xl font-black whitespace-nowrap tabular-nums text-indigo-700 dark:text-indigo-300">
               {{ formatCurrency(data.fiscal_reconciliation.fiscal_net_income) }}
             </p>
           </div>
         </div>

         <!-- TAX & NET AFTER TAX -->
         <div class="px-6 py-6 bg-gradient-to-br from-gray-900 to-gray-800 dark:from-[#111827] dark:to-gray-900 text-white">
           <!-- Tax estimate -->
           <div class="flex items-center justify-between text-sm opacity-90 mb-4 pb-4 border-b border-white/20">
             <div>Estimated Corp. Income Tax (22%)</div>
             <div class="font-bold tabular-nums text-rose-300">
               ({{ formatCurrency(data.fiscal_reconciliation.fiscal_net_income > 0 ? data.fiscal_reconciliation.fiscal_net_income * 0.22 : 0) }})
             </div>
           </div>
           
           <!-- After Tax -->
           <div class="flex items-center justify-between">
             <div>
               <p class="text-lg font-bold uppercase tracking-wider">Net Income After Tax</p>
               <p class="text-xs opacity-70 italic">Laba Bersih Setelah Pajak</p>
             </div>
             <p class="text-3xl font-black whitespace-nowrap tabular-nums text-emerald-400">
               {{ formatCurrency(data.net_income - (data.fiscal_reconciliation.fiscal_net_income > 0 ? data.fiscal_reconciliation.fiscal_net_income * 0.22 : 0)) }}
             </p>
           </div>
         </div>
       </div>
           </div>
         </div>

         <!-- Fiscal Reconciliation Expansion -->
         <div
           v-if="data.fiscal_reconciliation"
           class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden"
         >
           <div class="bg-gray-900 px-6 py-4 flex items-center justify-between">
             <div class="flex items-center gap-3">
               <div class="w-8 h-8 rounded-lg bg-orange-500/20 flex items-center justify-center">
                 <i class="bi bi- calculator-fill text-orange-500"></i>
               </div>
               <h3 class="text-sm font-bold text-white uppercase tracking-widest">
                 Rekonsiliasi Fiskal (Tax Reconciliation)
               </h3>
             </div>
             <FiscalCategoryBadge category="NON_DEDUCTIBLE_PERMANENT" />
           </div>
           
           <div class="p-0">
             <table class="w-full text-sm">
                <tbody class="divide-y divide-gray-100">
                  <tr class="bg-gray-50/50">
                    <td class="px-6 py-4 text-gray-600 font-medium">Laba (Rugi) Bersih Komersial</td>
                    <td class="px-6 py-4 text-right font-bold text-gray-900 tabular-nums">
                      {{ formatCurrency(data.fiscal_reconciliation.commercial_net_income) }}
                    </td>
                  </tr>
                  
                  <!-- Positive Corrections -->
                  <tr v-if="data.fiscal_reconciliation.total_positive_correction > 0">
                    <td class="px-6 py-4">
                      <div class="flex items-center gap-2">
                        <span class="text-emerald-600 font-bold">(+)</span>
                        <span class="text-gray-700">Koreksi Fiskal Positif (Non-Deductible)</span>
                      </div>
                      <ul class="mt-2 space-y-1 ml-6 text-[10px] text-gray-500">
                        <li v-for="item in data.fiscal_reconciliation.positive_corrections" :key="item.code" class="flex justify-between">
                          <span>{{ item.name }} ({{ item.code }})</span>
                          <span class="font-mono">{{ formatCurrency(item.amount) }}</span>
                        </li>
                      </ul>
                    </td>
                    <td class="px-6 py-4 text-right font-semibold text-emerald-600 tabular-nums">
                      {{ formatCurrency(data.fiscal_reconciliation.total_positive_correction) }}
                    </td>
                  </tr>

                  <!-- Negative Corrections -->
                  <tr v-if="data.fiscal_reconciliation.total_negative_correction > 0">
                    <td class="px-6 py-4">
                      <div class="flex items-center gap-2">
                        <span class="text-rose-600 font-bold">(-)</span>
                        <span class="text-gray-700">Koreksi Fiskal Negatif (Non-Taxable)</span>
                      </div>
                      <ul class="mt-2 space-y-1 ml-6 text-[10px] text-gray-500">
                        <li v-for="item in data.fiscal_reconciliation.negative_corrections" :key="item.code" class="flex justify-between">
                          <span>{{ item.name }} ({{ item.code }})</span>
                          <span class="font-mono">{{ formatCurrency(item.amount) }}</span>
                        </li>
                      </ul>
                    </td>
                    <td class="px-6 py-4 text-right font-semibold text-rose-600 tabular-nums">
                      {{ formatCurrency(-data.fiscal_reconciliation.total_negative_correction) }}
                    </td>
                  </tr>

                  <!-- Fiscal Result -->
                  <tr class="bg-orange-50/50 border-t-2 border-orange-200">
                    <td class="px-6 py-5">
                      <div class="flex flex-col">
                        <span class="text-orange-900 font-bold text-base">Penghasilan Netto Fiskal</span>
                        <span class="text-orange-700 text-[10px] uppercase tracking-wider font-bold">Fiscal Net Income</span>
                      </div>
                    </td>
                    <td class="px-6 py-5 text-right">
                      <span class="text-2xl font-black text-orange-900 tabular-nums">
                        {{ formatCurrency(data.fiscal_reconciliation.fiscal_net_income) }}
                      </span>
                    </td>
                  </tr>
                </tbody>
             </table>
           </div>
         </div>
       </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue';
import { useReportsStore } from '../../stores/reports';
import FiscalCategoryBadge from '../ui/FiscalCategoryBadge.vue';
import BaseBadge from '../ui/BaseBadge.vue'; // Might be needed for consistency

const props = defineProps({
  data: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['view-coa']);

const store = useReportsStore();

const hasData = computed(() => {
  return store.incomeStatement !== null;
});

const data = computed(() => {
  return store.incomeStatement || {
    period: { start_date: null, end_date: null },
    total_revenue: 0,
    total_expenses: 0,
    revenue: [],
    expenses: [],
    cogs_breakdown: null,
    amortization_breakdown: null,
    net_income: 0
  };
});

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('id-ID', {
    day: '2-digit',
    month: 'long',
    year: 'numeric'
  });
};

const formatCurrency = (value) => {
  if (value === null || value === undefined) return 'Rp 0';
  const numValue = Number(value);
  const formatted = new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(Math.abs(numValue));
  return numValue < 0 ? `(${formatted})` : formatted;
};

const copyToClipboard = async (value) => {
  const numericValue = Number(value ?? 0);
  const textToCopy = Number.isFinite(numericValue)
    ? numericValue.toString()
    : '0';

  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(textToCopy);
      return;
    }

    const textarea = document.createElement('textarea');
    textarea.value = textToCopy;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
  } catch (error) {
    console.error('Failed to copy amount:', error);
  }
};

const openCoaDetail = (coa) => {
  emit('view-coa', coa);
};

const getAssetTypeLabel = (type) => {
  const labels = {
    'Tangible': 'Harta Berwujud',
    'Intangible': 'Harta Tidak Berwujud',
    'Building': 'Bangunan',
    'LandRights': 'Hak Guna'
  };
  return labels[type] || type;
};

const getAssetTypeBadgeClass = (type) => {
  const classes = {
    'Tangible': 'bg-blue-100 text-blue-800',
    'Intangible': 'bg-purple-100 text-purple-800',
    'Building': 'bg-orange-100 text-orange-800',
    'LandRights': 'bg-green-100 text-green-800'
  };
  return classes[type] || 'bg-gray-100 text-gray-800';
};

const getAccumulatedDepreciationCoa = (assetType) => {
  if (!data.value.amortization_breakdown || !data.value.amortization_breakdown.accumulated_depreciation_coa_codes) {
    return '-';
  }
  return data.value.amortization_breakdown.accumulated_depreciation_coa_codes[assetType] || '-';
};

const getTotalAmortization = () => {
  if (!data.value.amortization_breakdown || !data.value.amortization_breakdown.by_asset_type) {
    return 0;
  }
  return Object.values(data.value.amortization_breakdown.by_asset_type).reduce((sum, val) => sum + (val || 0), 0);
};

const getUniqueGroups = (items) => {
  if (!items) return [];
  const groups = [...new Set(items.map(item => item.group_name))];
  return groups.filter(g => g && g !== 'null').sort();
};

const getGroupTotal = (items, groupName) => {
  if (!items) return 0;
  return items
    .filter(item => item.group_name === groupName)
    .reduce((sum, item) => sum + (item.annual_amortization || 0), 0);
};
</script>
