<template>
  <div class="space-y-8">
    <!-- Welcome Header -->
    <div class="bg-gradient-to-r from-indigo-600 to-indigo-800 rounded-3xl p-8 text-white shadow-xl shadow-indigo-200 relative overflow-hidden">
      <div class="relative z-10">
        <h1 class="text-3xl font-bold mb-2">Welcome Back, Admin!</h1>
        <p class="text-indigo-100 max-w-xl">
          StatementX is ready. Manage your bank statements, track expense history, and organize your financial data all in one place.
        </p>
      </div>
      <!-- Decorative circle -->
      <div class="absolute -right-10 -bottom-20 w-64 h-64 bg-white opacity-10 rounded-full blur-3xl"></div>
    </div>

    <!-- Quick Actions Grid -->
    <h3 class="text-lg font-bold text-gray-800 px-1">Quick Access</h3>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      
      <!-- Converter Card -->
      <router-link to="/converter" class="group bg-white p-6 rounded-2xl shadow-sm border border-gray-200 hover:shadow-md hover:border-indigo-200 transition-all duration-300">
        <div class="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
           <i class="bi bi-file-earmark-medical text-2xl"></i>
        </div>
        <h3 class="font-bold text-lg text-gray-900 group-hover:text-indigo-600 transition-colors">Converter</h3>
        <p class="text-xs text-gray-500 mt-2 leading-relaxed">
          Upload PDF/CSV statements and extract transactions automatically.
        </p>
      </router-link>

      <!-- History Card -->
      <router-link to="/history" class="group bg-white p-6 rounded-2xl shadow-sm border border-gray-200 hover:shadow-md hover:border-green-200 transition-all duration-300">
        <div class="w-12 h-12 bg-green-50 text-green-600 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
           <i class="bi bi-database-fill text-2xl"></i>
        </div>
        <h3 class="font-bold text-lg text-gray-900 group-hover:text-green-600 transition-colors">History & DB</h3>
        <p class="text-xs text-gray-500 mt-2 leading-relaxed">
          Search, filter, and manage your full transaction history.
        </p>
      </router-link>

      <!-- Companies Card -->
      <router-link to="/companies" class="group bg-white p-6 rounded-2xl shadow-sm border border-gray-200 hover:shadow-md hover:border-blue-200 transition-all duration-300">
        <div class="w-12 h-12 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
           <i class="bi bi-building text-2xl"></i>
        </div>
        <h3 class="font-bold text-lg text-gray-900 group-hover:text-blue-600 transition-colors">Companies</h3>
        <p class="text-xs text-gray-500 mt-2 leading-relaxed">
          Add or edit company entities and mapping rules.
        </p>
      </router-link>

      <!-- Marks Card -->
      <router-link to="/marks" class="group bg-white p-6 rounded-2xl shadow-sm border border-gray-200 hover:shadow-md hover:border-purple-200 transition-all duration-300">
        <div class="w-12 h-12 bg-purple-50 text-purple-600 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
           <i class="bi bi-tags-fill text-2xl"></i>
        </div>
        <h3 class="font-bold text-lg text-gray-900 group-hover:text-purple-600 transition-colors">Marks</h3>
        <p class="text-xs text-gray-500 mt-2 leading-relaxed">
          Manage reporting categories for transaction tagging.
        </p>
      </router-link>

    </div>
  </div>
</template>

<script setup>
</script>
