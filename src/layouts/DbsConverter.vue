<template>
  <DbsFileUploader
    @file-selected="onFileSelected"
    @conversion-start="onConversionStart"
    @conversion-success="onConversionSuccess"
    @conversion-error="onConversionError"
  />
</template>

<script setup>
import DbsFileUploader from '../components/bank-uploaders/DbsFileUploader.vue'

const onFileSelected = (file) => {
  console.log('File selected:', file.name)
}

const onConversionStart = () => {
  console.log('Starting DBS statement conversion...')
}

const onConversionSuccess = () => {
  console.log('DBS statement conversion completed successfully')
}

const onConversionError = (error) => {
  console.error('DBS statement conversion failed:', error)
}
</script>