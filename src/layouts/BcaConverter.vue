<template>
  <BcaFileUploader
    @file-selected="onFileSelected"
    @conversion-start="onConversionStart"
    @conversion-success="onConversionSuccess"
    @conversion-error="onConversionError"
  />
</template>

<script setup>
import BcaFileUploader from '../components/bank-uploaders/BcaFileUploader.vue'

const onFileSelected = (file) => {
  console.log('File selected:', file.name)
}

const onConversionStart = () => {
  console.log('Starting BCA statement conversion...')
}

const onConversionSuccess = () => {
  console.log('BCA statement conversion completed successfully')
}

const onConversionError = (error) => {
  console.error('BCA statement conversion failed:', error)
}
</script>