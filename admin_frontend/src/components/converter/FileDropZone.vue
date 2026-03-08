<template>
  <div 
    class="relative group border-2 border-dashed rounded-2xl p-10 transition-all duration-300 cursor-pointer overflow-hidden"
    :class="[
      isDark
        ? 'border-slate-600 hover:border-indigo-400 bg-slate-800/50 hover:bg-slate-800'
        : 'border-gray-200 hover:border-indigo-400 bg-gray-50/50 hover:bg-white',
      isDragging
        ? (isDark ? 'border-indigo-400 bg-indigo-500/10' : 'border-indigo-400 bg-indigo-50')
        : ''
    ]"
    @dragover.prevent="onDragOver"
    @dragleave.prevent="onDragLeave"
    @drop.prevent="onDrop"
    @click="triggerFileInput"
  >
    <div
      class="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity"
      :class="isDark ? 'bg-gradient-to-b from-indigo-500/10 to-transparent' : 'bg-gradient-to-b from-indigo-50/20 to-transparent'"
    ></div>
    <div class="relative text-center">
      <div
        class="w-16 h-16 rounded-2xl shadow-sm border flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform"
        :class="isDark ? 'bg-slate-900 border-slate-700' : 'bg-white border-gray-100'"
      >
        <i class="bi bi-file-earmark-arrow-up text-3xl text-indigo-500"></i>
      </div>
      <p class="text-sm font-semibold" :class="isDark ? 'text-slate-200' : 'text-gray-700'">Drag & drop your PDF or CSV here</p>
      <p class="text-xs mt-1" :class="isDark ? 'text-slate-400' : 'text-gray-500'">or click to browse from your computer</p>
      
      <div v-if="selectedFileName" class="text-center font-bold text-indigo-500 text-sm py-2">
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

defineProps({
  isDark: {
    type: Boolean,
    default: false
  }
});

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
