<template>
  <div id="app-container">
    <router-view />
    <van-tabbar v-if="showTab" route>
      <van-tabbar-item icon="home-o" to="/">首页</van-tabbar-item>
      <van-tabbar-item icon="search" to="/search">搜索</van-tabbar-item>
      <van-tabbar-item icon="map-marked" to="/map">地图</van-tabbar-item>
      <van-tabbar-item icon="star-o" to="/favorites">收藏</van-tabbar-item>
      <van-tabbar-item icon="contact" to="/profile">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const showTab = computed(() => route.meta?.showTab === true)
</script>

<style>
/* ── Global Reset & Base ── */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-size: 14px;
  color: #323233;
  background-color: #f7f8fa;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  height: 100%;
}

#app-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* ── Router View ── */
#app-container > .router-view {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

/* ── Safe area for iPhone notch ── */
:root {
  --safe-area-bottom: env(safe-area-inset-bottom, 0px);
  --tabbar-height: 50px;
}

/* ── Scrollbar ── */
::-webkit-scrollbar {
  width: 4px;
}
::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 4px;
}

/* ── A tag ── */
a {
  color: #1989fa;
  text-decoration: none;
}
</style>
