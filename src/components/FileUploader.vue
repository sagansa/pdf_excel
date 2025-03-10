<template>
  <div class="file-uploader h-full flex flex-col">
    <div class="drop-zone flex-grow flex flex-col items-center justify-center p-8 cursor-pointer relative" 
         @dragover.prevent 
         @drop.prevent="handleDrop"
         @click="triggerFileInput"
         :class="{ 'drop-zone--active': isDragging }">
      <div v-if="showSupportWidget" class="absolute top-4 right-4 text-center">
        <img :src="supportImage" :alt="supportImageAlt" class="w-32 h-32 object-contain" />
        <p class="text-sm font-medium text-gray-600 mt-2">{{ supportText }}</p>
      </div>
      <input
        type="file"
        class="file-input"
        @change="handleFileSelect"
        accept=".pdf"
        ref="fileInput"
      />
      
      <i :class="[uploadIcon, 'upload-icon mb-4']"></i>
      
      <div class="drop-zone__prompt text-center">
        <p class="mb-2">{{ dropzoneText }}</p>
      </div>
      
      <p class="drop-zone__hint mt-2">{{ supportedFileText }}</p>
      
      <div v-if="selectedFile" class="file-info">
        <p class="font-medium">{{ selectedFile.name }}</p>
        <p class="text-sm text-gray-500">{{ formatFileSize(selectedFile.size) }}</p>
      </div>
    </div>
    
    <div class="mt-4 flex justify-center">
      <slot name="convert-button" 
            :disabled="!selectedFile || isConverting"
            :is-converting="isConverting"
            :on-convert="handleConvert">
        <BaseButton
          @click="handleConvert"
          :disabled="!selectedFile || isConverting"
        >
          {{ isConverting ? 'Converting...' : 'Convert to Excel' }}
        </BaseButton>
      </slot>
    </div>
    
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>
    
    <div v-if="successMessage" class="success-message">
      {{ successMessage }}
    </div>
    
    <div v-if="isConverting" class="loading-indicator">
      <div class="spinner"></div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import BaseButton from './BaseButton.vue'

const props = defineProps({
  uploadIcon: {
    type: String,
    default: 'fas fa-file-pdf'
  },
  dropzoneText: {
    type: String,
      default: 'Drag and drop here or click to browse'
  },
  supportedFileText: {
    type: String,
    default: 'Supports PDF files'
  },
  showSupportWidget: {
    type: Boolean,
    default: false
  },
  supportImage: {
    type: String,
    default: ''
  },
  supportImageAlt: {
    type: String,
    default: 'Support us'
  },
  supportText: {
    type: String,
    default: 'Support Us'
  },
  convertEndpoint: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['file-selected', 'conversion-start', 'conversion-success', 'conversion-error'])

const fileInput = ref(null)
const selectedFile = ref(null)
const isDragging = ref(false)
const isConverting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const handleDrop = (e) => {
  isDragging.value = false
  const file = e.dataTransfer.files[0]
  if (file && file.type === 'application/pdf') {
    selectedFile.value = file
    errorMessage.value = ''
    emit('file-selected', file)
  } else {
    errorMessage.value = 'Please upload a PDF file'
  }
}

const handleFileSelect = (e) => {
  const file = e.target.files[0]
  if (file && file.type === 'application/pdf') {
    selectedFile.value = file
    errorMessage.value = ''
    emit('file-selected', file)
  } else {
    errorMessage.value = 'Please upload a PDF file'
  }
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const handleConvert = async () => {
  if (!selectedFile.value) return
  
  isConverting.value = true
  errorMessage.value = ''
  successMessage.value = ''
  emit('conversion-start')
  
  const formData = new FormData()
  formData.append('pdf_file', selectedFile.value)
  
  try {
    const response = await fetch(props.convertEndpoint, {
      method: 'POST',
      body: formData
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Failed to convert PDF')
    }
    
    // Trigger file download
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = selectedFile.value.name.replace('.pdf', '.xlsx')
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
    
    successMessage.value = 'PDF successfully converted to Excel!'
    selectedFile.value = null
    fileInput.value.value = ''
    emit('conversion-success')
  } catch (error) {
    errorMessage.value = error.message
    emit('conversion-error', error)
  } finally {
    isConverting.value = false
  }
}

const triggerFileInput = () => {
  fileInput.value.click()
}
</script>

<style scoped>
.file-uploader {
  width: 100%;
  background: white;
  border-radius: 8px;
}

.drop-zone {
  border: 2px dashed #dee2e6;
  border-radius: 8px;
  background: #f8f9fa;
}

.drop-zone:hover,
.drop-zone--active {
  border-color: #0d6efd;
  background: #f8f9fa;
}

.file-input {
  display: none;
}

.upload-icon {
  font-size: clamp(2rem, 5vw, 3rem);
  color: #6c757d;
}

.drop-zone__prompt {
  margin: 1rem 0;
  font-size: clamp(0.875rem, 2vw, 1rem);
}

.drop-zone__hint {
  color: #6c757d;
  font-size: clamp(0.75rem, 1.5vw, 0.875rem);
}

.file-info {
  margin-top: 1.5rem;
  text-align: center;
}

.error-message {
  color: #dc3545;
  margin-top: 1rem;
  text-align: center;
  font-size: clamp(0.875rem, 2vw, 1rem);
}

.success-message {
  color: #198754;
  margin-top: 1rem;
  text-align: center;
  font-size: clamp(0.875rem, 2vw, 1rem);
}

.loading-indicator {
  text-align: center;
  margin-top: 1rem;
}

.spinner {
  border: 3px solid #f3f3f3;
  border-top: 3px solid #0d6efd;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@media (max-width: 480px) {
  .file-uploader {
    padding: 0.5rem;
  }
  
  .drop-zone {
    padding: 1.5rem 1rem;
  }
}
</style>