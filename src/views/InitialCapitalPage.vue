<template>
  <div class="container-fluid py-4">
    <div class="row">
      <div class="col-12">
        <div class="d-flex justify-content-between align-items-center mb-4">
          <h2>
            <i class="fas fa-coins me-2"></i>
            Pengaturan Modal Awal
          </h2>
          <button class="btn btn-outline-secondary" @click="goBack">
            <i class="fas fa-arrow-left me-2"></i>
            Kembali
          </button>
        </div>
        
        <div class="alert alert-warning" v-if="!companyId">
          <i class="fas fa-exclamation-triangle me-2"></i>
          <strong>Peringatan:</strong> Company ID tidak ditemukan. Silakan pilih company terlebih dahulu.
        </div>
        
        <initial-capital-settings
          v-if="companyId"
          :company-id="companyId"
        />
        
        <div class="mt-4">
          <div class="card bg-light">
            <div class="card-body">
              <h5 class="card-title">
                <i class="fas fa-info-circle me-2"></i>
                Tentang Modal Setor di Awal
              </h5>
              <p class="card-text">
                Modal Setor di Awal adalah jumlah modal yang disetorkan oleh pendiri atau pemegang saham 
                ketika perusahaan pertama kali berdiri. Modal ini akan muncul di bagian Equity di Balance Sheet.
              </p>
              <h6>Penggunaan:</h6>
              <ul>
                <li>
                  <strong>Jumlah Modal Awal:</strong> Masukkan total modal yang disetorkan saat perusahaan berdiri.
                </li>
                <li>
                  <strong>Tahun Mulai:</strong> Tahun ketika modal mulai disetorkan. Ini akan mempengaruhi 
                  perhitungan Laba Ditahan Tahun Sebelumnya di Balance Sheet.
                </li>
                <li>
                  <strong>Deskripsi:</strong> Keterangan opsional untuk modal tersebut.
                </li>
              </ul>
              <div class="alert alert-info mb-0">
                <i class="fas fa-lightbulb me-2"></i>
                <strong>Tips:</strong> Pastikan jumlah Modal Awal disesuaikan dengan dokumen pendirian perusahaan 
                atau laporan keuangan sebelumnya agar Balance Sheet balance.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import InitialCapitalSettings from '../components/settings/InitialCapitalSettings.vue'

export default {
  name: 'InitialCapitalPage',
  components: {
    InitialCapitalSettings
  },
  data() {
    return {
      companyId: null
    }
  },
  mounted() {
    this.companyId = this.$route.params.companyId || 
                     localStorage.getItem('selectedCompanyId') ||
                     this.getCompanyIdFromUrl()
  },
  methods: {
    getCompanyIdFromUrl() {
      const params = new URLSearchParams(window.location.search)
      return params.get('company_id')
    },
    goBack() {
      if (window.history.length > 1) {
        window.history.back()
      } else {
        if (this.$router) {
          this.$router.push({ name: 'Settings' })
        } else {
          window.location.href = '/settings'
        }
      }
    }
  }
}
</script>

<style scoped>
.container-fluid {
  max-width: 1200px;
}

h2 {
  color: #495057;
  font-weight: 600;
}

.card {
  border: none;
  box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
}

.card-title {
  font-weight: 600;
  color: #495057;
}
</style>
