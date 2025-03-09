<template>
  <div class="pdf-converter">
    <div class="converter-container">
      <h1 class="title">BCA Statement PDF to Excel Converter</h1>
      
      <div
        class="drop-zone"
        @dragover.prevent
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
        :class="{ 'drop-zone--active': isDragging }"
        @dragenter.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
      >
        <input
          type="file"
          ref="fileInput"
          @change="handleFileSelect"
          accept=".pdf"
          class="file-input"
        >
        <div class="drop-zone__content">
          <i class="bi bi-cloud-arrow-up upload-icon"></i>
          <p class="drop-zone__prompt">
            {{ file ? file.name : 'Drop your PDF file here or click to browse' }}
          </p>
          <p v-if="!file" class="drop-zone__hint">Supports BCA Bank Statement PDF files</p>
        </div>
      </div>

      <div v-if="file" class="file-info">
        <p><strong>Selected file:</strong> {{ file.name }}</p>
        <button 
          class="convert-button"
          @click="convertFile"
          :disabled="isConverting"
        >
          <i class="bi bi-file-earmark-excel me-2"></i>
          {{ isConverting ? 'Converting...' : 'Convert to Excel' }}
        </button>
      </div>

      <div v-if="error" class="error-message">
        <i class="bi bi-exclamation-circle me-2"></i>
        {{ error }}
      </div>

      <div v-if="isConverting" class="loading-indicator">
        <div class="spinner"></div>
        <p>Converting your PDF file...</p>
      </div>

      <div v-if="showSuccess" class="success-message">
        <i class="bi bi-check-circle me-2"></i> Conversion successful!
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const fileInput = ref(null)
const file = ref(null)
const error = ref(null)
const isConverting = ref(false)
const isDragging = ref(false)
const showSuccess = ref(false)

const triggerFileInput = () => {
  fileInput.value.click()
}

const handleFileSelect = (event) => {
  const selectedFile = event.target.files[0]
  if (selectedFile && selectedFile.type === 'application/pdf') {
    file.value = selectedFile
    error.value = null
  } else {
    error.value = 'Please select a valid PDF file'
  }
}

const handleDrop = (event) => {
  isDragging.value = false
  const droppedFile = event.dataTransfer.files[0]
  if (droppedFile && droppedFile.type === 'application/pdf') {
    file.value = droppedFile
    error.value = null
  } else {
    error.value = 'Please drop a valid PDF file'
  }
}

const convertFile = async () => {
  if (!file.value) return

  const formData = new FormData()
  formData.append('pdf_file', file.value)
  
  isConverting.value = true
  error.value = null
  showSuccess.value = false

  try {
    const response = await fetch('/convert_pdf', {
      method: 'POST',
      body: formData
    })
    
    const contentType = response.headers.get('Content-Type')
    
    if (!response.ok) {
      // Only try to parse JSON if the content type is application/json
      if (contentType && contentType.includes('application/json')) {
        try {
          const errorData = await response.json()
          throw new Error(errorData.error || 'Error converting file')
        } catch (jsonError) {
          // If JSON parsing fails, use the status text
          throw new Error(`Error (${response.status}): ${response.statusText}`)
        }
      } else {
        // For non-JSON errors
        throw new Error(`Error (${response.status}): ${response.statusText}`)
      }
    }
    
    // For successful responses, check if it's JSON or binary
    if (contentType && contentType.includes('application/json')) {
      try {
        const jsonResponse = await response.json()
        if (jsonResponse.error) {
          throw new Error(jsonResponse.error)
        }
      } catch (jsonError) {
        throw new Error('Invalid response format from server')
      }
    } else if (contentType && contentType.includes('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')) {
      // Handle Excel file download
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${file.value.name.replace('.pdf', '.xlsx')}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      
      showSuccess.value = true
      setTimeout(() => {
        showSuccess.value = false
      }, 3000)
      
      // Reset form
      file.value = null
      fileInput.value.value = null
    } else {
      // Unknown content type
      throw new Error('Unexpected response format from server')
    }
  } catch (err) {
    console.error('Conversion error:', err)
    error.value = err.message || 'Error converting file. Please try again.'
  } finally {
    isConverting.value = false
  }
}
</script>

<style scoped>
.pdf-converter {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f8f9fa;
  padding: 2rem;
}

.converter-container {
  max-width: 800px;
  width: 100%;
  background: white;
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.title {
  text-align: center;
  color: #2c3e50;
  margin-bottom: 2rem;
  font-size: 2rem;
}

.drop-zone {
  border: 2px dashed #dee2e6;
  border-radius: 8px;
  padding: 3rem 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
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
  font-size: 3rem;
  color: #6c757d;
  margin-bottom: 1rem;
}

.drop-zone__prompt {
  font-size: 1.2rem;
  color: #495057;
  margin-bottom: 0.5rem;
}

.drop-zone__hint {
  color: #6c757d;
  font-size: 0.9rem;
}

.file-info {
  margin-top: 1.5rem;
  text-align: center;
}

.convert-button {
  background-color: #0d6efd;
  color: white;
  border: none;
  padding: 0.8rem 2rem;
  border-radius: 4px;
  font-size: 1.1rem;
  cursor: pointer;
  transition: background-color 0.3s ease;
  margin-top: 1rem;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.convert-button:hover {
  background-color: #0b5ed7;
}

.convert-button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.error-message {
  color: #dc3545;
  margin-top: 1rem;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.loading-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 1rem;
}

.spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #0d6efd;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.success-message {
  color: #198754;
  text-align: center;
  margin-top: 1rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}
</style>