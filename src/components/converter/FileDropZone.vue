<template>
  <div 
    class="relative group border-2 border-dashed border-gray-200 hover:border-indigo-400 rounded-2xl p-10 transition-all duration-300 bg-gray-50/50 hover:bg-white cursor-pointer overflow-hidden"
    @dragover.prevent="onDragOver"
    @dragleave.prevent="onDragLeave"
    @drop.prevent="onDrop"
    @click="triggerFileInput"
    :class="{ 'border-indigo-400 bg-indigo-50': isDragging }"
  >
    <div class="absolute inset-0 bg-gradient-to-b from-indigo-50/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
    <div class="relative text-center">
      <div class="w-16 h-16 bg-white rounded-2xl shadow-sm border border-gray-100 flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform">
        <i class="bi bi-file-earmark-arrow-up text-3xl text-indigo-500"></i>
      </div>
      <p class="text-sm font-semibold text-gray-700">Drag & drop your PDF or CSV here</p>
      <p class="text-xs text-gray-500 mt-1">or click to browse from your computer</p>
      
      <div v-if="selectedFileName" class="text-center font-bold text-indigo-600 text-sm py-2">
        {{ selectedFileName }}
      </div>

      <input
        type="file"
        ref="fileInputRef"
        class="hidden"
        accept="application/pdf,.csv"
        @change="onFileSelected"
      />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const emit = defineEmits(['file-selected']);
const fileInputRef = ref(null);
const isDragging = ref(false);
const selectedFileName = ref('');

const triggerFileInput = () => {
    fileInputRef.value.click();
};

const handleFile = (file) => {
    if (file) {
        selectedFileName.value = file.name;
        emit('file-selected', file);
    }
};

const onFileSelected = (event) => {
    const file = event.target.files[0];
    handleFile(file);
};

const onDragOver = () => { isDragging.value = true; };
const onDragLeave = () => { isDragging.value = false; };
const onDrop = (event) => {
    isDragging.value = false;
    const file = event.dataTransfer.files[0];
    handleFile(file);
};
</script>
