<template>
  <MainLayout v-if="!route.meta.public" />
  <router-view v-else />
  <ToastViewport />
</template>

<script setup>
import { useRoute } from 'vue-router';
import MainLayout from './layouts/MainLayout.vue';
import ToastViewport from './components/ui/ToastViewport.vue';

const route = useRoute();
</script>
