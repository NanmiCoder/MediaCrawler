<!-- 在vitepress右侧的目录导航中插入动态广告组件-->

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const ads = ref([])
const currentAdIndex = ref(0)
let intervalId = null

const fetchAds = async () => {
  return [
    {
      id: 1,
      imageUrl: 'https://github.com/NanmiCoder/MediaCrawler/raw/main/docs/static/images/auto_test.png',
      landingUrl: 'https://item.jd.com/10124939676219.html',
      text: '给好朋友虫师新书站台推荐 - 基于Python的自动化测试框架设计'
    }
  ]
}

const nextAd = () => {
  currentAdIndex.value = (currentAdIndex.value + 1) % ads.value.length
}

onMounted(async () => {
  ads.value = await fetchAds()
  intervalId = setInterval(nextAd, 3000)
})

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId)
})
</script>

<template>
  <div class="vp-ad-carousel">
    <template v-if="ads.length > 0">
      <div class="ad-content">
        <a :href="ads[currentAdIndex].landingUrl" target="_blank" rel="noopener noreferrer">
          <img :src="ads[currentAdIndex].imageUrl" :alt="ads[currentAdIndex].text" class="ad-image">
          <p class="ad-text">{{ ads[currentAdIndex].text }}</p>
        </a>
      </div>
    </template>
    <p v-else class="loading">Loading ads...</p>
  </div>
</template>

<style scoped>
.vp-ad-carousel {
  margin-top: 1rem;
  padding: 1rem;
  background-color: var(--vp-c-bg-soft);
  border-radius: 8px;
  font-size: 0.875rem;
  line-height: 1.5;
}

.ad-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.ad-image {
  max-width: 130px;
  height: auto;
  margin-bottom: 0.5rem;
}

.ad-text {
  text-align: center;
  color: var(--vp-c-text-1);
}

.loading {
  text-align: center;
  color: var(--vp-c-text-2);
}

a {
  text-decoration: none;
  color: inherit;
}
</style>
