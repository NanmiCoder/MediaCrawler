<!--.vitepress/theme/MyLayout.vue-->
<script setup>
import DefaultTheme from 'vitepress/theme'
import DynamicAds from './DynamicAds.vue'
const { Layout } = DefaultTheme
</script>

<template>
  <Layout>
    <template #aside-bottom>
      <DynamicAds />
    </template>
  </Layout>
</template>