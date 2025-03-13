<template>
  <div class="flex flex-col h-full file-uploader">
    <div class="flex relative flex-col flex-grow justify-center items-center p-8 cursor-pointer drop-zone" 
         @dragover.prevent 
         @drop.prevent="handleDrop"
         @click="triggerFileInput"
         :class="{ 'drop-zone--active': isDragging }">
      <div v-if="showSupportWidget" class="absolute top-4 right-4 text-center">
        <img :src="supportImage" :alt="supportImageAlt" class="object-contain w-32 h-32" />
        <p class="mt-2 text-sm font-medium text-gray-600">{{ supportText }}</p>
      </div>
      <input
        type="file"
        class="file-input"
        @change="handleFileSelect"
        accept=".pdf"
        ref="fileInput"
      />
      
      <i :class="[uploadIcon, 'upload-icon mb-4']"></i>
      
      <div class="text-center drop-zone__prompt">
        <p class="mb-2">{{ dropzoneText }}</p>
      </div>
      
      <p class="mt-2 drop-zone__hint">{{ supportedFileText }}</p>
      
      <div v-if="selectedFile" class="file-info">
        <p class="font-medium">{{ selectedFile.name }}</p>
        <p class="text-sm text-gray-500">{{ formatFileSize(selectedFile.size) }}</p>
      </div>
    </div>
    
    <div v-if="selectedFile && requirePassword" class="mt-4">
      <div class="relative w-full">
        <input
          type="password"
          v-model="password"
          placeholder="Enter PDF password"
          class="px-4 py-2 w-full bg-white rounded-md border border-gray-300 focus:outline-none"
        />
      </div>
    </div>
    
    <div class="flex justify-center mt-4">
      <slot name="convert-button" 
            :disabled="!selectedFile || isConverting || (requirePassword && !password)"
            :is-converting="isConverting"
            :on-convert="handleConvert">
        <BaseButton
          @click="handleConvert"
          :disabled="!selectedFile || isConverting || (requirePassword && !password)"
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
  },
  requirePassword: {
    type: Boolean,
    default: false
  },
  formData: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['file-selected', 'conversion-start', 'conversion-success', 'conversion-error'])

const fileInput = ref(null)
const selectedFile = ref(null)
const isDragging = ref(false)
const isConverting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const password = ref('')

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
  if (!selectedFile.value || (props.requirePassword && !password.value)) return
  
  isConverting.value = true
  errorMessage.value = ''
  successMessage.value = ''
  emit('conversion-start')
  
  const formData = new FormData()
  formData.append('pdf_file', selectedFile.value)
  if (props.requirePassword && password.value) {
    formData.append('password', password.value)
  }
  
  // Append additional form data from props
  Object.entries(props.formData).forEach(([key, value]) => {
    formData.append(key, value)
  })
  
  try {
    const response = await fetch(props.convertEndpoint, {
      method: 'POST',
      body: formData
    })
    
    const contentType = response.headers.get('content-type')
    if (!response.ok) {
      let errorText = 'Failed to convert PDF'
      try {
        if (contentType && contentType.includes('application/json')) {
          const error = await response.json()
          if (error.error && typeof error.error === 'string') {
            const errorMessage = error.error.toLowerCase()
            if (errorMessage.includes('password required') || errorMessage.includes('need password')) {
              errorText = 'This PDF is password protected. Please enter the password.'
            } else if (errorMessage.includes('incorrect password') || errorMessage.includes('wrong password')) {
              errorText = 'Incorrect password. Please try again.'
            } else if (errorMessage.includes('invalid bank statement') || errorMessage.includes('no transaction data')) {
              errorText = 'Invalid bank statement format. Please ensure you are uploading the correct bank statement type.'
            } else if (errorMessage.includes('module') && errorMessage.includes('has no attribute')) {
              errorText = 'Server error: Unable to process PDF. Please try again or contact support.'
            } else {
              errorText = error.error
            }
          }
        }
      } catch (e) {
        console.error('Error parsing error response:', e)
      }
      errorMessage.value = errorText
      emit('conversion-error', errorText)
      return
    }
    
    // Handle successful response
    if (contentType && contentType.includes('application/json')) {
      const data = await response.json()
      if (data.error) {
        errorMessage.value = data.error
        emit('conversion-error', errorMessage.value)
        return
      }
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
    password.value = ''
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