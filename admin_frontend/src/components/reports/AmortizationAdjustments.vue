<template>
  <div class="space-y-6">
    <!-- Header with Actions (if any needed for Amortization) -->

    <!-- Pending Transactions Alert (Compact) -->
    <Alert
      v-if="pendingTransactions?.length > 0"
      variant="warning"
    >
      <template #title>
        {{ pendingTransactions.length }} transaksi aset belum terdaftar
      </template>
      <template #message>
        Terdapat transaksi yang ditandai sebagai Aset namun belum didaftarkan untuk diamortisasi.
      </template>
      <template #actions>
        <Button
          size="sm"
          variant="primary"
          icon="bi bi-plus-circle-fill"
          @click="showAddAssetModal = true"
        >
          Daftarkan Aset Baru
        </Button>
      </template>
    </Alert>
    <!-- Calculated Asset Amortization (Automatic, Grouped) -->
    <div v-if="calculatedItems.length > 0" class="space-y-0 mb-6">
      <!-- Grand Header -->
      <SectionCard contentClass="overflow-hidden" bodyClass="p-0">
        <template #header>
          <div>
            <h3 class="section-card__title">Calculated Asset Amortization</h3>
            <p class="mt-1 text-xs section-card__subtitle">
              Automatic calculation based on registered assets. Total amortization:
              <strong>{{ formatCurrency(calculatedTotalAmortization) }}</strong>
            </p>
          </div>
        </template>
        <template #actions>
          <div class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
            Automatic
          </div>
        </template>

        <div class="overflow-x-auto">
          <table class="table-compact min-w-full">
            <thead>
              <tr>
                <th class="w-[120px]">Tx Date</th>
                <th class="min-w-[200px]">Asset Name</th>
                <th class="min-w-[100px]">Deductible</th>
                <th class="w-[110px] text-right">Original Cost</th>
                <th class="w-[110px] text-right">Accum. Depr (Prev)</th>
                <th class="w-[60px] text-center">Mult.</th>
                <th class="w-[110px] text-right">Amortization</th>
                <th class="w-[110px] text-right">Total Accum.</th>
                <th class="w-[110px] text-right">Book Value (End)</th>
                <th class="w-[80px] text-center">Actions</th>
              </tr>
            </thead>

            <tbody>
              <!-- Iterate over types (Tangible, Building, Intangible) -->
              <template v-for="(groups, typeName) in groupedCalculatedItems" :key="typeName">

                <!-- ─── TYPE HEADER ─────────────────────────────────────────── -->
                <tr class="amort-type-header">
                  <td colspan="10" class="px-4 py-2.5">
                    <div class="flex items-center gap-3">
                      <div class="w-1.5 h-5 rounded-full"
                        :class="{
                          'bg-primary': typeName === 'Tangible',
                          'bg-warning': typeName === 'Building',
                          'bg-success': typeName === 'Intangible',
                        }">
                      </div>
                      <div class="flex items-center gap-2">
                        <i class="bi text-sm"
                          :class="{
                            'bi-boxes text-primary': typeName === 'Tangible',
                            'bi-building text-warning': typeName === 'Building',
                            'bi-lightbulb text-success': typeName === 'Intangible',
                          }">
                        </i>
                        <span class="text-[11px] font-black uppercase tracking-[0.18em]"
                          :class="{
                            'text-primary': typeName === 'Tangible',
                            'text-warning': typeName === 'Building',
                            'text-success': typeName === 'Intangible',
                          }">
                          {{ getAssetTypeLabel(typeName) }}
                        </span>
                      </div>
                    </div>
                  </td>
                </tr>

                <!-- Iterate over groups within this type -->
                <template v-for="(groupItems, groupName) in groups" :key="`${typeName}-${groupName}`">

                  <!-- ─── GROUP SUB-HEADER ──────────────────────────────────── -->
                  <tr class="amort-group-header">
                    <td colspan="10" class="px-6 py-1.5">
                      <div class="flex items-center gap-2">
                        <i class="bi bi-folder2-open text-[10px] text-muted"></i>
                        <span class="text-[10px] font-bold text-muted uppercase tracking-wider">
                          {{ groupName }}
                        </span>
                        <span class="text-[9px] bg-surface-raised border border-border px-1.5 py-0.5 rounded text-muted font-bold ml-1">
                          {{ groupItems.length }} aset
                        </span>
                      </div>
                    </td>
                  </tr>

                  <!-- ─── ROWS IN THIS GROUP ──────────────────────────────── -->
                  <tr
                    v-for="item in groupItems"
                    :key="item.asset_id"
                    class="amortization-row"
                  >
                    <td class="px-3 py-2 text-xs text-muted font-mono pl-8">
                      {{ formatDate(item.txn_date || item.acquisition_date) }}
                    </td>
                    <td class="px-3 py-2 pl-8">
                      <div class="flex flex-col gap-0.5 max-w-[250px]">
                        <div v-if="item.notes || item.amortization_notes" class="text-xs font-bold text-theme break-words leading-tight">
                          {{ item.notes || item.amortization_notes }}
                        </div>
                        <div class="text-xs text-muted italic break-words leading-tight"
                          :class="{ 'font-semibold text-theme not-italic': !(item.notes || item.amortization_notes) }">
                          {{ item.asset_name }}
                        </div>
                      </div>
                    </td>
                    <td class="px-3 py-2">
                      <span class="text-[10px] font-bold px-1.5 py-0.5 rounded"
                        :class="item.use_half_rate ? 'bg-warning/10 text-warning border border-warning/20' : 'bg-surface-raised text-muted border border-border'">
                        {{ getDeductibleLabel(item) }}
                      </span>
                    </td>
                    <td class="px-3 py-2 text-xs text-right text-muted">{{ formatCurrency(item.acquisition_cost, false) }}</td>
                    <td class="px-3 py-2 text-xs text-right text-muted">{{ formatCurrency(item.accumulated_depreciation_prev_year || 0, false) }}</td>
                    <td class="px-3 py-2 text-center">
                      <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                        {{ item.multiplier }}
                      </span>
                    </td>
                    <td class="px-3 py-2 text-xs text-right font-bold text-theme">{{ formatCurrency(item.annual_amortization, false) }}</td>
                    <td class="px-3 py-2 text-xs text-right text-muted">{{ formatCurrency(item.total_accumulated_depreciation || 0, false) }}</td>
                    <td class="px-3 py-2 text-xs text-right font-bold text-theme">{{ formatCurrency(item.book_value_end_year || 0, false) }}</td>
                    <td class="px-3 py-2">
                      <div class="flex items-center justify-center gap-2">
                        <template v-if="item.is_manual_asset">
                          <button @click="editItem(item)" class="text-muted hover:text-theme transition-colors" title="Edit">
                            <i class="bi bi-pencil-square"></i>
                          </button>
                          <button @click="confirmDelete(item)" class="text-muted hover:text-danger transition-colors" title="Delete">
                            <i class="bi bi-trash"></i>
                          </button>
                        </template>
                        <template v-else-if="item.is_from_ledger">
                          <button @click="openTransactionDetail(item)" class="text-muted hover:text-theme transition-colors" title="View Details">
                            <i class="bi bi-eye"></i>
                          </button>
                        </template>
                        <template v-else-if="item.asset_id">
                          <button @click="editRegisteredAsset(item)" class="text-muted hover:text-theme transition-colors" title="Edit Asset">
                            <i class="bi bi-pencil-square"></i>
                          </button>
                          <button @click="confirmDeleteAsset(item)" class="text-muted hover:text-danger transition-colors" title="Delete Asset">
                            <i class="bi bi-trash"></i>
                          </button>
                        </template>
                        <span v-else class="text-muted pointer-events-none" title="No actions">
                          <i class="bi bi-dash text-xs"></i>
                        </span>
                      </div>
                    </td>
                  </tr>

                </template>

                <!-- ─── TYPE SUBTOTAL ─────────────────────────────────────── -->
                <tr class="amort-type-subtotal">
                  <td colspan="3" class="px-4 py-2 text-right">
                    <span class="text-[10px] font-black uppercase tracking-wider"
                      :class="{
                        'text-primary': typeName === 'Tangible',
                        'text-warning': typeName === 'Building',
                        'text-success': typeName === 'Intangible',
                      }">
                      Subtotal {{ getAssetTypeLabel(typeName) }}
                    </span>
                  </td>
                  <td class="px-3 py-2 text-right text-xs font-bold text-theme">{{ formatCurrency(typeTotals[typeName]?.cost || 0, false) }}</td>
                  <td colspan="2"></td>
                  <td class="px-3 py-2 text-right text-xs font-bold text-theme">{{ formatCurrency(typeTotals[typeName]?.amort || 0, false) }}</td>
                  <td></td>
                  <td class="px-3 py-2 text-right text-xs font-bold text-theme">{{ formatCurrency(typeTotals[typeName]?.bookVal || 0, false) }}</td>
                  <td></td>
                </tr>

              </template>
            </tbody>

            <!-- Grand Total -->
            <tfoot class="bg-surface-muted/50 border-t-2 border-border">
              <tr class="font-bold">
                <td colspan="3" class="px-3 py-3 text-right text-[10px] uppercase font-black tracking-wider text-theme-muted">
                  Total Calculated Amortization
                </td>
                <td class="px-3 py-3 text-right text-xs text-theme">{{ formatCurrency(totalOriginalCost, false) }}</td>
                <td colspan="2"></td>
                <td class="px-3 py-3 text-right text-xs text-theme">{{ formatCurrency(calculatedTotalAmortization, false) }}</td>
                <td></td>
                <td class="px-3 py-3 text-right text-xs text-theme">{{ formatCurrency(totalBookValueEnd, false) }}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </SectionCard>
    </div>

    <!-- Amortization Items List (Manual & Transactions) -->
    <SectionCard
      class="mb-6"
      contentClass="overflow-hidden"
      bodyClass="p-0"
    >
      <template #header>
        <div>
          <h3 class="section-card__title">Manual & Transaction Adjustments</h3>
          <p class="mt-1 text-xs section-card__subtitle">
            Manual and transactional adjustments. Total:
            {{ formatCurrency(manualTotalAmortization) }}
            <span v-if="manualItems.length > 0" class="text-theme">
              ({{ manualItems.length }} entries)
            </span>
          </p>
        </div>
      </template>
      <template #actions>
        <div class="flex items-center gap-3">
          <div class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
            Manual/Tx
          </div>
          <Button
            icon="bi bi-plus-lg"
            variant="primary"
            size="sm"
            :disabled="!companyId"
            @click="openAddModal"
          >
            Add Entry
          </Button>
          <Button
            icon="bi bi-journal-text"
            variant="secondary"
            size="sm"
            :disabled="!companyId || manualItems.length === 0"
            @click="generateJournalEntries"
          >
            Generate Journals
          </Button>
        </div>
      </template>

      <div class="amortization-workspace__body p-0">
        <!-- Empty State -->
        <div
          v-if="manualItems.length === 0"
          class="flex flex-col items-center justify-center rounded-2xl px-6 py-12 text-center bg-surface-muted border border-dashed border-border"
        >
          <i class="bi bi-calendar-check text-4xl text-theme-muted opacity-40"></i>
          <p class="mt-3 text-xs font-bold text-theme">No manual amortization entries yet</p>
          <p class="mt-1 text-[10px] text-theme-muted uppercase tracking-wider">Click "Add Entry" to create a new record</p>
        </div>

        <div v-if="manualItems.length > 0" class="overflow-x-auto">
          <table class="table-compact min-w-full">
            <thead>
              <tr>
                <th class="w-[120px]">Tx Date</th>
                <th class="min-w-[200px]">Asset Name</th>
                <th class="min-w-[120px]">Group / Deductible</th>
                <th class="w-[110px] text-right">Original Cost</th>
                <th class="w-[110px] text-right">Accum. Depr (Prev)</th>
                <th class="w-[60px] text-center">Mult.</th>
                <th class="w-[110px] text-right">Amortization (Curr)</th>
                <th class="w-[110px] text-right">Total Accum. Depr</th>
                <th class="w-[110px] text-right">Book Value (End)</th>
                <th class="w-[80px] text-center">Actions</th>
              </tr>
            </thead>
            <tbody class="amortization-table-body divide-y">
              <tr
                v-for="item in manualItems"
                :key="item.id"
                class="amortization-row"
                :class="{ 'opacity-80 amortization-row--muted': !item.is_manual }"
              >
                <td class="px-3 py-2 text-xs text-muted font-mono">
                  {{
                    formatDate(
                      item.amortization_date ||
                        item.acquisition_date ||
                        item.txn_date ||
                        item.created_at,
                    )
                  }}
                </td>
                <td class="px-3 py-2">
                  <div class="flex flex-col gap-0.5 max-w-[250px]">
                    <div
                      v-if="item.notes"
                      class="text-xs font-bold text-theme break-words leading-tight"
                    >
                      {{ item.notes }}
                    </div>
                    <div
                      class="text-xs text-muted italic break-words leading-tight"
                      :class="{
                        'font-semibold text-theme not-italic text-xs':
                          !item.notes,
                      }"
                    >
                      {{ item.description }}
                      <span
                        v-if="!item.is_manual"
                        class="ml-1 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-primary/10 text-primary border border-primary/20"
                      >Transaction</span>
                    </div>
                  </div>
                </td>
                <td class="px-3 py-2">
                  <div class="flex flex-col">
                    <template v-if="item.asset_group_id">
                      <span class="text-xs font-medium text-theme">{{
                        getGroupName(item.asset_group_id)
                      }}</span>
                      <span class="text-[10px] text-muted">{{
                        getDeductibleLabel(item)
                      }}</span>
                    </template>
                    <template v-else>
                      <span class="text-xs font-medium text-theme">{{
                        item.coa_code
                      }}</span>
                      <span
                        class="text-[10px] text-muted truncate max-w-[120px]"
                        >{{ item.coa_name }}</span
                      >
                    </template>
                  </div>
                </td>
                <td
                  class="px-3 py-2 text-xs text-right text-muted"
                >
                  {{ formatCurrency(item.amount, false) }}
                </td>
                <td class="px-3 py-2 text-xs text-right text-muted">
                  {{
                    item.asset_group_id
                      ? formatCurrency(
                          item.accumulated_depreciation_prev_year || 0,
                          false,
                        )
                      : "-"
                  }}
                </td>
                <td class="px-3 py-2 text-center">
                  <span
                    v-if="
                      item.multiplier !== null && item.multiplier !== undefined
                    "
                    class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
                  >
                    {{ item.multiplier }}
                  </span>
                  <span v-else class="text-muted">-</span>
                </td>
                <td
                  class="px-3 py-2 text-xs text-right font-bold text-theme"
                >
                  {{
                    formatCurrency(
                      item.annual_amortization ?? item.amount,
                      false,
                    )
                  }}
                </td>
                <td
                  class="px-3 py-2 text-xs text-right text-muted"
                >
                  {{
                    formatCurrency(
                      item.total_accumulated_depreciation || item.amount,
                      false,
                    )
                  }}
                </td>
                <td class="px-3 py-2 text-xs text-right text-muted">
                  {{
                    item.book_value_end_year !== undefined
                      ? formatCurrency(item.book_value_end_year, false)
                      : item.asset_group_id
                        ? "0"
                        : "-"
                  }}
                </td>
                <td class="px-3 py-2 text-xs text-center">
                  <div class="flex items-center justify-center gap-2">
                    <template v-if="item.is_manual">
                      <button
                        @click="editItem(item)"
                        class="text-muted hover:text-theme transition-colors"
                        title="Edit"
                      >
                        <i class="bi bi-pencil-square"></i>
                      </button>
                      <button
                        @click="confirmDelete(item)"
                        class="text-muted hover:text-danger transition-colors"
                        title="Delete"
                      >
                        <i class="bi bi-trash"></i>
                      </button>
                    </template>
                    <template v-else>
                      <button
                        @click="openTransactionDetail(item)"
                        class="text-muted hover:text-theme transition-colors"
                        title="View Details"
                      >
                        <i class="bi bi-eye"></i>
                      </button>
                    </template>
                  </div>
                </td>
              </tr>
            </tbody>
            <tfoot class="bg-surface-muted/50 border-t border-border">
              <tr class="font-bold">
                <td
                  colspan="3"
                  class="px-3 py-3 text-[10px] uppercase font-bold tracking-wider text-right text-theme-muted"
                >
                  Total Manual Adjustments
                </td>
                <td class="px-3 py-3 text-right text-xs text-theme">
                  {{ formatCurrency(manualTotalCalculated, false) }}
                </td>
                <td class="px-3 py-3 text-right text-xs text-theme">
                  {{ formatCurrency(manualTotalAccumPrev, false) }}
                </td>
                <td class="px-3 py-3 text-center text-theme">-</td>
                <td class="px-3 py-3 text-right text-xs text-theme">
                  {{ formatCurrency(manualTotalAmortization, false) }}
                </td>
                <td class="px-3 py-3 text-right text-xs text-theme">
                  {{ formatCurrency(manualTotalAccumTotal, false) }}
                </td>
                <td class="px-3 py-3 text-right text-xs text-theme">
                  {{ formatCurrency(manualTotalBookValue, false) }}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </SectionCard>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
      <StatCard
        label="Total Amortization (Curr)"
        :value="formatCurrency(grandTotalAmortization)"
        variant="primary"
      />
      <StatCard
        label="Total Book Value (End)"
        :value="formatCurrency(grandTotalBookValue)"
        variant="default"
      />
    </div>

    <!-- Add/Edit Modal -->
    <BaseModal :isOpen="showModal" @close="closeModal" size="lg">
      <template #title>
        {{ editingItem ? "Edit" : "Add" }} Amortization Entry
      </template>

      <div class="p-6 space-y-4">
        <!-- Asset Mark Selection -->
        <FormField label="Asset Mark *" labelClass="text-[11px] font-bold uppercase tracking-wider text-theme-muted">
          <SelectInput
            v-model="form.mark_id"
            :options="[
              { value: '', label: 'Select Asset Mark' },
              ...availableMarks.map(mark => ({
                value: mark.id,
                label: `${mark.personal_use}${mark.asset_type ? ` (${mark.asset_type})` : ''}`
              }))
            ]"
          />
        </FormField>

        <!-- Date -->
        <FormField label="Amortization Date" labelClass="text-[11px] font-bold uppercase tracking-wider text-theme-muted">
          <TextInput
            v-model="form.amortization_date"
            type="date"
          />
        </FormField>

        <div class="grid grid-cols-2 gap-4">
          <FormField label="Asset Group" labelClass="text-[11px] font-bold uppercase tracking-wider text-theme-muted">
            <SelectInput
              v-model="form.asset_group_id"
              :options="[
                { value: '', label: 'None (One-time adjustment)' },
                ...Object.entries(groupedAssetGroups).flatMap(([type, groups]) => [
                  { label: getAssetTypeLabel(type), isGroupLabel: true },
                  ...groups.map(group => ({
                    value: group.id,
                    label: `${group.group_name} (${group.tarif_rate}%)`
                  }))
                ])
              ]"
            />
          </FormField>

          <FormField label="Deductible Level" labelClass="text-[11px] font-bold uppercase tracking-wider text-theme-muted">
            <SelectInput
              v-model="form.use_half_rate"
              :options="[
                { value: false, label: '100% Deductible' },
                { value: true, label: '50% Deductible' }
              ]"
            />
          </FormField>
        </div>
        <div
          v-if="!form.asset_group_id && form.amount > 0"
          class="rounded-2xl px-4 py-3 flex items-start gap-3 bg-amber-500/10 border border-amber-500/20"
        >
          <i class="bi bi-info-circle-fill mt-0.5 text-amber-600 dark:text-amber-400"></i>
          <p class="text-[11px] leading-tight text-theme font-medium">
            <strong>Calculation Note:</strong> No Asset Group selected. This
            will be treated as a direct amortization expense. Select a group
            to enable automatic annual depreciation.
          </p>
        </div>

        <!-- Description -->
        <FormField label="Description *" labelClass="text-[11px] font-bold uppercase tracking-wider text-theme-muted">
          <TextInput
            v-model="form.description"
            placeholder="e.g., Amortization of intangible assets..."
          />
        </FormField>

        <!-- Amount -->
        <FormField label="Original Cost / Amount (Rp) *" labelClass="text-[11px] font-bold uppercase tracking-wider text-theme-muted">
          <TextInput
            v-model="amountDisplay"
            inputmode="decimal"
            placeholder="0"
          >
            <template #leading>
              <span class="text-theme-muted text-[10px] font-bold pr-2 border-r border-border mr-2">RP</span>
            </template>
          </TextInput>
        </FormField>

        <!-- Notes -->
        <FormField label="Notes" labelClass="text-[11px] font-bold uppercase tracking-wider text-theme-muted">
          <textarea
            v-model="form.notes"
            rows="3"
            class="input-base w-full text-xs"
            placeholder="Additional information about this amortization..."
          ></textarea>
        </FormField>
      </div>

      <template #footer>
        <Button variant="secondary" @click="closeModal">Cancel</Button>
        <Button
          variant="primary"
          icon="bi bi-check-lg"
          :disabled="!isFormValid || isSaving"
          :loading="isSaving"
          @click="saveItem"
        >
          {{ editingItem ? "Update" : "Save" }}
        </Button>
      </template>
    </BaseModal>

    <!-- Delete Confirmation Modal -->
    <ConfirmModal
      :isOpen="showDeleteModal"
      title="Delete Entry?"
      :message="
        itemToDelete
          ? `Are you sure you want to delete the amortization entry for ${itemToDelete.description || 'this entry'} (${formatCurrency(itemToDelete.amount)})? This action cannot be undone.`
          : 'Are you sure you want to delete this amortization entry? This action cannot be undone.'
      "
      confirmText="Delete"
      variant="danger"
      :loading="isDeleting"
      @close="showDeleteModal = false"
      @confirm="deleteItem"
    />

    <!-- Transaction Detail Modal -->
    <BaseModal
      :isOpen="showTransactionDetailModal"
      @close="closeTransactionDetailModal"
      size="lg"
    >
      <template #title>Transaction Details</template>

      <div v-if="selectedTransaction" class="p-6 space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-muted mb-1"
                >Transaction Date</label
              >
              <p class="text-xs text-theme">
                {{ selectedTransaction.txn_date }}
              </p>
            </div>
            <div>
              <label class="block text-xs font-semibold text-muted mb-1"
                >Amount</label
              >
              <p class="text-xs font-bold text-theme">
                {{ formatCurrency(selectedTransaction.amount) }}
              </p>
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-muted mb-1"
              >Description</label
            >
            <p class="text-xs text-theme">
              {{ selectedTransaction.description }}
            </p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-muted mb-1"
              >Asset Mark</label
            >
            <p class="text-xs text-theme">
              {{
                selectedTransaction.mark_name ||
                selectedTransaction.coa_name ||
                "-"
              }}
            </p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-muted mb-1"
              >Notes</label
            >
            <p class="text-xs text-theme italic">
              {{
                selectedTransaction.notes ||
                selectedTransaction.amortization_notes ||
                "-"
              }}
            </p>
          </div>

          <div class="border-t border-border pt-4">
            <h4 class="text-xs font-semibold text-theme mb-3">
              Amortization Settings
            </h4>

            <div class="space-y-3">
              <div class="grid grid-cols-2 gap-4">
                <FormField label="Asset Group" labelClass="text-[11px] font-bold uppercase tracking-wider text-theme-muted">
                  <SelectInput
                    v-model="selectedTransaction.asset_group_id"
                    :options="[
                      { value: '', label: 'Select Group...' },
                      ...Object.entries(groupedAssetGroups).flatMap(([type, groups]) => [
                        { label: getAssetTypeLabel(type), isGroupLabel: true },
                        ...groups.map(group => ({
                          value: group.id,
                          label: `${group.group_name} (${group.tarif_rate}%)`
                        }))
                      ])
                    ]"
                  />
                </FormField>
                <FormField label="Deductible Level" labelClass="text-[11px] font-bold uppercase tracking-wider text-theme-muted">
                  <SelectInput
                    v-model="selectedTransaction.use_half_rate"
                    :options="[
                      { value: false, label: '100% Deductible' },
                      { value: true, label: '50% Deductible' }
                    ]"
                  />
                </FormField>
              </div>

              <FormField label="Amortization Start Date" labelClass="text-[11px] font-bold uppercase tracking-wider text-theme-muted">
                <TextInput
                  v-model="selectedTransaction.amortization_start_date"
                  type="date"
                />
              </FormField>

              <FormField label="Notes" labelClass="text-[11px] font-bold uppercase tracking-wider text-theme-muted">
                <textarea
                  v-model="selectedTransaction.notes"
                  rows="2"
                  class="input-base w-full text-xs"
                  placeholder="Additional notes about amortization..."
                ></textarea>
              </FormField>
            </div>
          </div>
        </div>

      <template #footer>
        <Button variant="secondary" @click="closeTransactionDetailModal">
          Cancel
        </Button>
        <Button variant="primary" @click="saveSelectedTransactionGroup">
          Save Changes
        </Button>
      </template>
    </BaseModal>

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
import { useAmortizationStore } from "../../stores/amortization";
import api, { reportsApi, historyApi } from "../../api/index";
import Alert from "../ui/Alert.vue";
import BaseModal from "../ui/BaseModal.vue";
import Button from "../ui/Button.vue";
import ConfirmModal from "../ui/ConfirmModal.vue";
import FormField from "../ui/FormField.vue";
import SectionCard from "../ui/SectionCard.vue";
import StatCard from "../ui/StatCard.vue";
import TextInput from "../ui/TextInput.vue";
import SelectInput from "../ui/SelectInput.vue"; // Added SelectInput import
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

// Grouped structure: { Tangible: { 'Group 1': [...], ... }, Intangible: {...}, Building: {...} }
const groupedCalculatedItems = computed(() => {
  const TYPE_ORDER = ['Tangible', 'Building', 'Intangible'];
  const result = {};

  calculatedItems.value.forEach(item => {
    const type = item.asset_type || 'Tangible';
    const groupKey = item.group_name || item.mark_name || '-';
    if (!result[type]) result[type] = {};
    if (!result[type][groupKey]) result[type][groupKey] = [];
    result[type][groupKey].push(item);
  });

  // Sort types by preferred order, then groups alphabetically
  const sorted = {};
  TYPE_ORDER.forEach(type => {
    if (result[type]) {
      sorted[type] = {};
      Object.keys(result[type])
        .sort()
        .forEach(group => {
          sorted[type][group] = result[type][group];
        });
    }
  });
  // Add any unexpected types at the end
  Object.keys(result).forEach(type => {
    if (!sorted[type]) sorted[type] = result[type];
  });

  return sorted;
});

// Subtotals per type
const typeTotals = computed(() => {
  const totals = {};
  Object.entries(groupedCalculatedItems.value).forEach(([type, groups]) => {
    let cost = 0, amort = 0, bookVal = 0;
    Object.values(groups).forEach(items => {
      items.forEach(item => {
        cost += item.acquisition_cost || 0;
        amort += item.annual_amortization || 0;
        bookVal += item.book_value_end_year || 0;
      });
    });
    totals[type] = { cost, amort, bookVal };
  });
  return totals;
});

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

const amountDisplay = computed({
  get: () => formatDisplayNumber(form.value.amount),
  set: (value) => {
    form.value.amount = parseFormattedNumber(value);
  },
});

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
/* Table Row Hovers */
.table-compact tbody tr {
  @apply transition-colors duration-150;
}

.table-compact tbody tr:hover {
  background-color: var(--color-surface-muted);
}

.amortization-row--muted {
  @apply bg-surface-muted;
  opacity: 0.8;
}

/* ─── Grouped Table Separators ─── */
.amort-type-header {
  background: var(--color-surface-muted);
  border-top: 2px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

.amort-type-header:first-child {
  border-top: none;
}

.amort-group-header {
  background: var(--color-surface-raised);
  border-top: 1px dashed var(--color-border);
  border-bottom: 1px dashed var(--color-border);
}

.amort-type-subtotal {
  background: var(--color-surface-muted);
  border-top: 1px solid var(--color-border);
  border-bottom: 2px solid var(--color-border-strong);
}

.amort-type-header td,
.amort-group-header td,
.amort-type-subtotal td {
  /* prevent hover color from overriding these rows */
  background: inherit !important;
}
</style>
