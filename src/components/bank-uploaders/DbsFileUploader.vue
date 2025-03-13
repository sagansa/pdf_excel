<template>
  <div class="bank-file-uploader">
    <FileUploader
      :supportedFileText="'Supports DBS bank statement PDF files'"
      :showSupportWidget="true"
      :supportImage="saweria"
      supportImageAlt="Support us on Saweria"
      supportText="Support Us"
      convertEndpoint="/convert_pdf"
      :requirePassword="true"
      :formData="{ bank_type: 'dbs' }"
      @file-selected="onFileSelected"
      @conversion-start="onConversionStart"
      @conversion-success="onConversionSuccess"
      @conversion-error="onConversionError"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import FileUploader from '../FileUploader.vue'
import saweria from '../../assets/saweria.png'

const emit = defineEmits(['file-selected', 'conversion-start', 'conversion-success', 'conversion-error'])

const onFileSelected = (file) => {
  emit('file-selected', file)
}

const onConversionStart = () => {
  emit('conversion-start')
}

const onConversionSuccess = () => {
  emit('conversion-success')
}

const onConversionError = (error) => {
  emit('conversion-error', error)
}
</script>

<style scoped>
.bank-file-uploader {
  width: 100%;
}
</style>