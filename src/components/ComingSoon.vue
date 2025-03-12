<template>
  <div class="coming-soon h-full flex flex-col items-center justify-center p-8 text-center">
    <div class="development-icon mb-6">
      <i class="fas fa-tools text-5xl text-gray-600"></i>
    </div>
    
    <h2 class="text-2xl font-bold text-gray-800 mb-4">Coming Soon!</h2>
    
    <div class="message-container max-w-md">
      <p class="text-gray-600 mb-4">
        We're currently working hard to bring you support for this bank statement.
        Stay tuned for updates!
      </p>
      
      <div class="progress-indicator">
        <div class="spinner"></div>
        <p class="text-sm text-gray-500 mt-3">Under Development</p>
      </div>
    </div>
  </div>
</template>

<script setup>
// No props or logic needed for this placeholder component
</script>

<style scoped>
.coming-soon {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.development-icon {
  animation: bounce 2s infinite;
}

.progress-indicator {
  margin-top: 2rem;
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

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

@media (max-width: 480px) {
  .coming-soon {
    padding: 1.5rem 1rem;
  }
  
  h2 {
    font-size: 1.5rem;
  }
}
</style>