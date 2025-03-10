<template>
  <FileUploader
    supportedFileText="Supports Mandiri bank statement PDF files"
    :showSupportWidget="true"
    :supportImage="saweria"
    supportImageAlt="Support us on Saweria"
    supportText="Support Us"
    convertEndpoint="/convert_pdf"
    @file-selected="onFileSelected"
    @conversion-start="onConversionStart"
    @conversion-success="onConversionSuccess"
    @conversion-error="onConversionError"
  />
</template>

<script setup>
import FileUploader from '../components/FileUploader.vue'
import saweria from '../assets/saweria.png'

const onFileSelected = (file) => {
  console.log('File selected:', file.name)
}

const onConversionStart = () => {
  console.log('Starting conversion...')
}

const onConversionSuccess = () => {
  console.log('Conversion completed successfully')
}

const onConversionError = (error) => {
  console.error('Conversion failed:', error)
}
</script>