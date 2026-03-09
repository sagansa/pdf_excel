<template>
  <div 
    class="file-dropzone group relative cursor-pointer overflow-hidden rounded-2xl border-2 border-dashed p-10 transition-all duration-300"
    :class="{ 'file-dropzone--dragging': isDragging }"
    @dragover.prevent="onDragOver"
    @dragleave.prevent="onDragLeave"
    @drop.prevent="onDrop"
    @click="triggerFileInput"
  >
    <div
      class="file-dropzone__overlay absolute inset-0 opacity-0 transition-opacity group-hover:opacity-100"
    ></div>
    <div class="relative text-center">
      <div
        class="file-dropzone__icon mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border shadow-sm transition-transform group-hover:scale-110"
      >
        <i class="bi bi-file-earmark-arrow-up text-3xl"></i>
      </div>
      <p class="text-sm font-semibold text-theme">Drag & drop your PDF or CSV here</p>
      <p class="mt-1 text-xs text-muted">or click to browse from your computer</p>
      
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

<style scoped>
.file-dropzone {
  border-color: var(--color-border);
  background: var(--color-surface-raised);
}

.file-dropzone:hover {
  border-color: var(--color-primary);
  background: var(--color-surface);
}

.file-dropzone--dragging {
  border-color: var(--color-primary);
  background: rgba(15, 118, 110, 0.08);
}

.file-dropzone__overlay {
  background: linear-gradient(180deg, rgba(15, 118, 110, 0.08), transparent);
}

.file-dropzone__icon {
  background: var(--color-surface);
  border-color: var(--color-border);
  color: var(--color-primary);
}
</style>
