<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200">
    <!-- Header -->
    <div class="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-6 text-white">
      <div class="flex items-center gap-4">
        <div class="flex-shrink-0 w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
          <i class="bi bi-coins text-xl"></i>
        </div>
        <div>
          <h2 class="text-xl font-semibold">Initial Capital</h2>
          <p class="text-white/80 text-sm">Configure company initial capital settings</p>
        </div>
      </div>
    </div>
    
    <div class="p-6">
        <!-- Company Selector -->
        <div class="mb-6">
          <label for="companySelect" class="block text-sm font-medium text-gray-700 mb-2">
            <i class="bi bi-building text-indigo-600 mr-2"></i>
            Select Company
          </label>
          <select 
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors" 
            id="companySelect"
            v-model="$data.selectedCompany"
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
          <div v-if="loadingCompanies" class="mt-2 text-sm text-gray-500">
            <div class="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-600 mr-2"></div>
            Loading companies...
          </div>
          <div v-else-if="!$data.selectedCompany" class="mt-2 text-sm text-amber-600">
            <i class="bi bi-exclamation-triangle mr-1"></i>
            Please select a company first
          </div>
        </div>
        
        <div class="border-t border-gray-200 my-6"></div>
        
        <div v-if="loading" class="text-center py-8">
          <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          <p class="mt-3 text-gray-600">Loading initial capital data...</p>
        </div>
        
        <div v-else>
          <!-- Info Alert -->
          <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6" v-if="!hasData">
            <div class="flex">
              <div class="flex-shrink-0">
                <i class="bi bi-info-circle-fill text-blue-600 text-lg"></i>
              </div>
              <div class="ml-3">
                <h3 class="text-sm font-medium text-blue-800">No Initial Capital Data</h3>
                <p class="mt-1 text-sm text-blue-700">
                  Please enter the initial capital amount contributed when the company was established. 
                  This data will be used to calculate Equity in the Balance Sheet.
                </p>
              </div>
            </div>
          </div>
          
          <!-- Form -->
          <form @submit.prevent="saveData">
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div class="lg:col-span-2 space-y-6">
                <div>
                  <label for="amount" class="block text-sm font-medium text-gray-700 mb-2">
                    <i class="bi bi-cash-stack text-indigo-600 mr-2"></i>
                    Initial Capital Amount
                  </label>
                  <div class="relative rounded-md shadow-sm">
                    <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <span class="text-gray-500 sm:text-sm">Rp</span>
                    </div>
                    <input 
                      type="number" 
                      class="block w-full pl-8 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors" 
                      id="amount" 
                      v-model="formData.amount"
                      placeholder="0"
                      step="0.01"
                      required
                    >
                  </div>
                  <p class="mt-2 text-sm text-gray-500">
                    <i class="bi bi-lightbulb mr-1"></i>
                    Enter the capital amount according to company establishment documents
                  </p>
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label for="startYear" class="block text-sm font-medium text-gray-700 mb-2">
                      <i class="bi bi-calendar text-indigo-600 mr-2"></i>
                      Start Year
                    </label>
                    <input 
                      type="number" 
                      class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors" 
                      id="startYear" 
                      v-model="formData.startYear"
                      :min="2000"
                      :max="new Date().getFullYear()"
                      required
                    >
                  </div>
                  
                  <div>
                    <label for="description" class="block text-sm font-medium text-gray-700 mb-2">
                      <i class="bi bi-tag text-indigo-600 mr-2"></i>
                      Description
                    </label>
                    <input 
                      type="text" 
                      class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors" 
                      id="description" 
                      v-model="formData.description"
                      placeholder="e.g., Founder's capital"
                    >
                  </div>
                </div>
                
                <!-- Action Buttons -->
                <div class="flex flex-wrap gap-3 pt-4">
                  <button 
                    type="submit" 
                    class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    :disabled="saving || !isFormValid"
                  >
                    <i class="bi bi-check-lg" v-if="!saving"></i>
                    <div v-if="saving" class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    {{ saving ? 'Saving...' : 'Save Data' }}
                  </button>
                  
                  <button 
                    type="button" 
                    class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors flex items-center gap-2"
                    @click="resetForm"
                    v-if="hasData"
                    :disabled="saving"
                  >
                    <i class="bi bi-arrow-counterclockwise"></i>
                    Reset
                  </button>
                  
                  <button 
                    type="button" 
                    class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
                    @click="deleteData"
                    v-if="hasData"
                    :disabled="saving || deleting"
                  >
                    <i class="bi bi-trash" v-if="!deleting"></i>
                    <div v-if="deleting" class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    {{ deleting ? 'Deleting...' : 'Delete' }}
                  </button>
                </div>
              </div>
              
              <!-- Current Data Card -->
              <div class="lg:col-span-1">
                <div class="bg-gray-50 rounded-lg p-6" v-if="hasData">
                  <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    <i class="bi bi-database text-indigo-600"></i>
                    Current Data
                  </h3>
                  
                  <div class="space-y-4">
                    <div class="border-b border-gray-200 pb-3">
                      <div class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Capital Amount</div>
                      <div class="text-lg font-semibold text-indigo-600">
                        Rp {{ formatNumber(currentData.amount) }}
                      </div>
                    </div>
                    
                    <div class="border-b border-gray-200 pb-3">
                      <div class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Start Year</div>
                      <div class="text-lg font-semibold text-gray-900">
                        {{ currentData.startYear }}
                      </div>
                    </div>
                    
                    <div class="border-b border-gray-200 pb-3" v-if="currentData.description">
                      <div class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Description</div>
                      <div class="text-gray-900">
                        {{ currentData.description }}
                      </div>
                    </div>
                    
                    <div>
                      <div class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Last Updated</div>
                      <div class="text-sm text-gray-500 flex items-center gap-1">
                        <i class="bi bi-clock"></i>
                        {{ formatDate(currentData.updatedAt) }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
</template>

<script>
export default {
  name: 'InitialCapitalSettings',
  props: {
    companyId: {
      type: String,
      required: false,
      default: ''
    }
  },
  data() {
    return {
      loading: false,
      saving: false,
      deleting: false,
      loadingCompanies: false,
      hasData: false,
      errors: {},
      companies: [],
      formData: {
        amount: 0,
        startYear: new Date().getFullYear(),
        description: ''
      },
      currentData: {
        amount: 0,
        startYear: 0,
        description: '',
        updatedAt: ''
      }
    }
  },
  computed: {
    isFormValid() {
      return this.selectedCompanyId && 
             this.formData.amount > 0 && 
             this.formData.startYear >= 2000 && 
             this.formData.startYear <= new Date().getFullYear()
    },
    selectedCompanyId() {
      return this.companyId || this.$data.selectedCompany || ''
    }
  },
  mounted() {
    console.log('InitialCapitalSettings mounted with companyId:', this.companyId)
    this.loadCompanies()
  },
  methods: {
    async loadCompanies() {
      this.loadingCompanies = true
      try {
        const response = await fetch('/api/companies')
        const data = await response.json()
        this.companies = data.companies || data || []
        console.log('Loaded companies:', this.companies)
        
        // Auto-select company if prop is provided or only one company exists
        if (this.companyId) {
          this.$data.selectedCompany = this.companyId
        } else if (this.companies.length === 1) {
          this.$data.selectedCompany = this.companies[0].id
        } else {
          this.$data.selectedCompany = ''
        }
        
        if (this.selectedCompanyId) {
          this.loadData()
        }
      } catch (error) {
        console.error('Error loading companies:', error)
        this.errors.general = 'Failed to load companies list'
      } finally {
        this.loadingCompanies = false
      }
    },
    async loadData() {
      const companyIdToUse = this.selectedCompanyId
      console.log('Loading initial capital for companyId:', companyIdToUse)
      
      if (!companyIdToUse) {
        this.hasData = false
        this.formData = {
          amount: 0,
          startYear: new Date().getFullYear(),
          description: ''
        }
        return
      }
      
      this.loading = true
      this.errors = {}
      try {
        const response = await fetch(`/api/initial-capital?company_id=${encodeURIComponent(companyIdToUse)}`)
        console.log('API Response status:', response.status)
        const data = await response.json()
        console.log('API Response data:', data)
        
        if (data.setting) {
          this.hasData = true
          this.currentData = {
            amount: data.setting.amount,
            startYear: data.setting.start_year,
            description: data.setting.description || '',
            updatedAt: data.setting.updated_at
          }
          this.formData = { ...this.currentData }
        } else {
          this.hasData = false
          this.formData = {
            amount: 0,
            startYear: new Date().getFullYear(),
            description: ''
          }
        }
      } catch (error) {
        console.error('Error loading initial capital:', error)
        this.errors.general = 'Failed to load initial capital data'
      } finally {
        this.loading = false
      }
    },
    
    async saveData() {
      if (!this.selectedCompanyId) {
        this.errors.general = 'Please select a company first'
        return
      }
      
      this.saving = true
      this.errors = {}
      
      try {
        const response = await fetch('/api/initial-capital', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            company_id: this.selectedCompanyId,
            amount: parseFloat(this.formData.amount),
            start_year: parseInt(this.formData.startYear),
            description: this.formData.description
          })
        })
        
        const data = await response.json()
        
        if (response.ok) {
          this.hasData = true
          this.loadData()
          this.showSuccess('Initial capital saved successfully!')
        } else {
          this.errors.general = data.error || 'Failed to save data'
        }
      } catch (error) {
        console.error('Error saving initial capital:', error)
        this.errors.general = 'Failed to save initial capital'
      } finally {
        this.saving = false
      }
    },
    
    async deleteData() {
      if (!this.selectedCompanyId) {
        this.errors.general = 'Please select a company first'
        return
      }
      
      if (!confirm('Are you sure you want to delete the initial capital? The Balance Sheet may become unbalanced after this action.')) {
        return
      }
      
      this.deleting = true
      this.errors = {}
      
      try {
        const response = await fetch(`/api/initial-capital?company_id=${this.selectedCompanyId}`, {
          method: 'DELETE'
        })
        
        const data = await response.json()
        
        if (response.ok) {
          this.hasData = false
          this.formData = {
            amount: 0,
            startYear: new Date().getFullYear(),
            description: ''
          }
          this.currentData = {
            amount: 0,
            startYear: 0,
            description: '',
            updatedAt: ''
          }
          this.showSuccess('Initial capital deleted successfully!')
        } else {
          this.errors.general = data.error || 'Failed to delete data'
        }
      } catch (error) {
        console.error('Error deleting initial capital:', error)
        this.errors.general = 'Failed to delete initial capital'
      } finally {
        this.deleting = false
      }
    },
    
    resetForm() {
      this.formData = {
        amount: this.currentData.amount,
        startYear: this.currentData.startYear,
        description: this.currentData.description
      }
      this.errors = {}
    },
    
    formatNumber(num) {
      return new Intl.NumberFormat('id-ID').format(num)
    },
    
    formatDate(dateStr) {
      if (!dateStr) return '-'
      const date = new Date(dateStr)
      return date.toLocaleDateString('id-ID', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    },
    
    showSuccess(message) {
      // You can integrate with a toast notification library here
      alert(message)
    }
  }
}
</script>

<style scoped>
/* Component uses Tailwind CSS classes - additional custom styles if needed */
</style>
