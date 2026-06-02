<template>
  <div class="home-page">
    <!-- 顶部搜索栏 -->
    <div class="header-section">
      <van-search
        v-model="searchKeyword"
        shape="round"
        placeholder="搜索区域、房产名称..."
        readonly
        @click="goSearch"
        @touchstart.prevent="goSearch"
      />
    </div>

    <!-- 快捷切换标签 -->
    <div class="tabs-section">
      <van-tabs v-model:active="activeTab" @change="onTabChange" sticky :offset-top="0">
        <van-tab title="全部" name="all" />
        <van-tab title="出租" name="rent" />
        <van-tab title="出售" name="sale" />
      </van-tabs>
    </div>

    <!-- 区域快捷入口 -->
    <div class="section">
      <div class="section-header">
        <span class="section-title">🏘️ 热门区域</span>
        <span class="section-more" @click="goSearch">全部区域 &gt;</span>
      </div>
      <van-grid :column-num="5" :border="false" :gutter="4" class="district-grid">
        <van-grid-item
          v-for="d in store.districts"
          :key="d.id"
          :to="{ name: 'search', query: { district: d.name } }"
          class="district-item"
        >
          <div class="district-card">
            <div class="district-name">{{ d.name }}</div>
            <div class="district-count">{{ d.count }}套</div>
            <div class="district-en">{{ d.nameEn }}</div>
          </div>
        </van-grid-item>
      </van-grid>
    </div>

    <!-- 比价入口 -->
    <div class="section">
      <div class="compare-entry" @click="$router.push('/compare')">
        <div class="compare-icon">
          <van-icon name="balance-list-o" size="24" color="#fff" />
        </div>
        <div class="compare-text">
          <div class="compare-title">创建比价</div>
          <div class="compare-desc">最多可同时对比 4 套房源</div>
        </div>
        <van-icon name="arrow" color="rgba(255,255,255,0.6)" size="16" />
      </div>
    </div>

    <!-- 推荐房源 -->
    <div class="section">
      <div class="section-header">
        <span class="section-title">🏠 推荐房源</span>
        <span class="section-more" @click="goSearch">查看更多 &gt;</span>
      </div>

      <van-loading v-if="store.loading" class="loading-center" size="24px">
        加载中...
      </van-loading>

      <van-empty v-else-if="displayList.length === 0" description="暂无房源" />

      <div v-else class="property-list">
        <PropertyCard v-for="item in displayList" :key="item.id" :property="item" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePropertyStore } from '@/stores/property'
import PropertyCard from '@/components/PropertyCard.vue'

const router = useRouter()
const store = usePropertyStore()

const searchKeyword = ref('')
const activeTab = ref('all')

// 展示前 6 条
const displayList = computed(() => store.filteredProperties.slice(0, 6))

onMounted(() => {
  store.loadProperties()
  store.loadDistricts()
})

function goSearch() {
  router.push({ name: 'search' })
}

function onTabChange(name) {
  if (name === 'all') {
    store.updateFilters({ priceType: '' })
  } else {
    store.updateFilters({ priceType: name })
  }
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: #f7f8fa;
  padding-bottom: 60px;
}

/* 搜索栏 */
.header-section {
  padding: 0 12px 0;
  background: #fff;
}

/* Tab 区域 - 覆盖默认 sticky 带来的偏移 */
.tabs-section {
  background: #fff;
  position: sticky;
  top: 0;
  z-index: 9;
}

/* 通用区块 */
.section {
  margin-top: 10px;
  padding: 0 12px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0 10px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.section-more {
  font-size: 13px;
  color: #999;
}

/* 区域网格 */
.district-grid {
  background: transparent;
}

.district-item {
  --van-grid-item-content-background: transparent;
}

.district-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 10px;
  padding: 8px 0;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.04);
  width: 100%;
}

.district-name {
  font-size: 13px;
  font-weight: 600;
  color: #333;
  line-height: 1.4;
}

.district-count {
  font-size: 11px;
  color: #ee0a24;
  font-weight: 500;
  margin: 2px 0;
}

.district-en {
  font-size: 10px;
  color: #bbb;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  padding: 0 2px;
}

/* 比价入口 */
.compare-entry {
  display: flex;
  align-items: center;
  background: linear-gradient(135deg, #ee0a24 0%, #c5001a 100%);
  border-radius: 12px;
  padding: 14px 16px;
  color: #fff;
  cursor: pointer;
}

.compare-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  flex-shrink: 0;
}

.compare-text {
  flex: 1;
  min-width: 0;
}

.compare-title {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.4;
}

.compare-desc {
  font-size: 12px;
  opacity: 0.8;
  margin-top: 2px;
}

/* 房产列表 */
.property-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.loading-center {
  display: flex;
  justify-content: center;
  padding: 40px 0;
}
</style>
