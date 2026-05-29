<template>
  <div class="detail-view">
    <!-- 顶部导航 -->
    <van-nav-bar
      title="房产详情"
      left-arrow
      @click-left="goBack"
      fixed
      placeholder
      z-index="100"
    />

    <!-- 图片轮播 -->
    <van-swipe
      v-if="property?.images?.length"
      :autoplay="0"
      indicator-color="white"
      class="detail-swipe"
    >
      <van-swipe-item v-for="(img, idx) in property.images" :key="idx">
        <van-image :src="img" fit="cover" class="swipe-img" />
      </van-swipe-item>
    </van-swipe>
    <van-image
      v-else
      src="https://via.placeholder.com/400x280/667eea/ffffff?text=CM"
      fit="cover"
      class="swipe-img"
    />

    <!-- 价格 + 标签 -->
    <div class="price-section">
      <div class="price-row">
        <span class="price-amount">฿{{ formattedPrice }}</span>
        <span class="price-unit">{{ property?.price_type === 'rent' ? '/月' : '（总价）' }}</span>
      </div>
      <div class="tag-row">
        <van-tag
          :color="property?.price_type === 'rent' ? '#ee0a24' : '#07c160'"
          size="medium"
        >
          {{ property?.price_type === 'rent' ? '出租' : '出售' }}
        </van-tag>
        <van-tag color="#1989fa" size="medium" style="margin-left:8px">
          {{ property?.source_label || property?.source || '未知来源' }}
        </van-tag>
        <van-tag
          v-if="property?.furnished"
          color="#ff976a"
          size="medium"
          style="margin-left:8px"
        >
          精装修
        </van-tag>
      </div>
    </div>

    <!-- 房产标题 -->
    <div class="title-section">
      <h2 class="detail-title">{{ property?.title || '房产标题' }}</h2>
      <div class="location-row">
        <van-icon name="location-o" color="#999" size="14" />
        <span>{{ property?.address || property?.district || '未知位置' }}</span>
      </div>
    </div>

    <!-- 基本信息 -->
    <div class="info-section">
      <div class="info-grid">
        <div class="info-item">
          <div class="info-icon"><van-icon name="home-o" size="20" color="#1989fa" /></div>
          <div class="info-label">户型</div>
          <div class="info-value">{{ property?.bedrooms || '-' }}室{{ property?.bathrooms || '-' }}卫</div>
        </div>
        <div class="info-item">
          <div class="info-icon"><van-icon name="eye-o" size="20" color="#07c160" /></div>
          <div class="info-label">面积</div>
          <div class="info-value">{{ property?.area_sqm || '-' }} m²</div>
        </div>
        <div class="info-item">
          <div class="info-icon"><van-icon name="bars" size="20" color="#ee0a24" /></div>
          <div class="info-label">楼层</div>
          <div class="info-value">{{ property?.floor || '-' }}/{{ property?.total_floors || '-' }}层</div>
        </div>
        <div class="info-item">
          <div class="info-icon"><van-icon name="flower-o" size="20" color="#ff976a" /></div>
          <div class="info-label">装修</div>
          <div class="info-value">{{ property?.furnished ? '精装修' : '毛坯' }}</div>
        </div>
        <div class="info-item">
          <div class="info-icon"><van-icon name="clock-o" size="20" color="#7232dd" /></div>
          <div class="info-label">类型</div>
          <div class="info-value">{{ propertyTypeLabel }}</div>
        </div>
      </div>
    </div>

    <!-- 房源描述 -->
    <div class="desc-section">
      <div class="section-title">房源描述</div>
      <p class="desc-text">{{ property?.description || '暂无描述信息' }}</p>
    </div>

    <!-- 位置地图 -->
    <div class="map-section">
      <div class="section-title">
        <van-icon name="map-marked" color="#ee0a24" size="16" />
        位置信息
      </div>
      <div class="location-text" v-if="property?.district">
        <van-icon name="location-o" color="#1989fa" size="14" />
        在 {{ property.district }} 区
      </div>
      <div ref="mapRef" class="detail-map"></div>
    </div>

    <!-- 底部固定按钮栏 -->
    <div class="bottom-bar">
      <van-button
        :icon="isFav ? 'star' : 'star-o'"
        :color="isFav ? '#ee0a24' : '#999'"
        plain
        hairline
        round
        class="bottom-btn fav-btn"
        @click="toggleFav"
      >
        {{ isFav ? '已收藏' : '收藏' }}
      </van-button>
      <van-button
        type="warning"
        :icon="inCompare ? 'success' : 'exchange'"
        round
        class="bottom-btn"
        :disabled="compareDisabled"
        @click="toggleCompare"
      >
        {{ inCompare ? '已加入比价' : '加入比价' }}
      </van-button>
      <van-button
        type="danger"
        icon="phone-o"
        round
        class="bottom-btn contact-btn"
        @click="showContact = true"
      >
        联系中介
      </van-button>
    </div>

    <!-- 联系中介弹窗 -->
    <van-dialog
      v-model:show="showContact"
      title="联系方式"
      show-cancel-button
      confirm-button-text="我知道了"
      @confirm="showContact = false"
    >
      <div class="contact-content">
        <van-icon name="info-o" size="40" color="#1989fa" />
        <p>请联系中介获取更多信息</p>
        <p style="font-size:12px;color:#999;">电话：请向平台客服索取</p>
      </div>
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePropertyStore } from '@/stores/property'
import { useCompareStore } from '@/stores/compare'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const route = useRoute()
const router = useRouter()
const store = usePropertyStore()
const compareStore = useCompareStore()

const property = ref(null)
const showContact = ref(false)
const mapRef = ref(null)
let mapInstance = null

const formattedPrice = computed(() => {
  if (!property.value) return '0'
  const p = store.getPriceValue(property.value)
  if (!p) return '0'
  if (p >= 10000) return (p / 10000).toFixed(1) + '万'
  return p.toLocaleString()
})

const isFav = computed(() => property.value && store.isFavorite(property.value.id))
const inCompare = computed(() => property.value && compareStore.hasItem(property.value.id))
const compareDisabled = computed(() => !inCompare.value && compareStore.count >= 4)

const propertyTypeLabel = computed(() => {
  const map = { condo: '公寓', house: '别墅', townhouse: '联排别墅', apartment: '普通公寓' }
  return map[property.value?.property_type] || property.value?.property_type || '-'
})

function goBack() {
  router.back()
}

function toggleFav() {
  if (property.value) {
    store.toggleFavorite(property.value)
  }
}

function toggleCompare() {
  if (!property.value) return
  if (inCompare.value) {
    compareStore.removeItem(property.value.id)
  } else {
    compareStore.addItem({ ...property.value })
  }
}

function initMap() {
  if (!mapRef.value || !property.value) return
  const { lat, lng, district } = property.value
  if (!lat || !lng) return

  nextTick(() => {
    mapInstance = L.map(mapRef.value, {
      zoomControl: false,
      dragging: true,
      scrollWheelZoom: false,
    }).setView([lat, lng], 14)

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap'
    }).addTo(mapInstance)

    L.marker([lat, lng])
      .addTo(mapInstance)
      .bindPopup(`<b>${district || '清迈'}</b>`)
      .openPopup()
  })
}

function destroyMap() {
  if (mapInstance) {
    mapInstance.remove()
    mapInstance = null
  }
}

onMounted(() => {
  const id = route.params.id
  property.value = store.loadPropertyDetail(id)
  if (property.value) {
    initMap()
  }
})

onBeforeUnmount(() => {
  destroyMap()
})
</script>

<style scoped>
.detail-view {
  padding-bottom: 70px;
  background: #f7f8fa;
  min-height: 100vh;
}

/* 图片轮播 */
.detail-swipe {
  width: 100%;
  height: 280px;
}
.swipe-img {
  width: 100%;
  height: 280px;
  display: block;
}

/* 价格区 */
.price-section {
  background: #fff;
  padding: 16px 16px 12px;
}
.price-row {
  display: flex;
  align-items: baseline;
  margin-bottom: 8px;
}
.price-amount {
  font-size: 28px;
  font-weight: 700;
  color: #ee0a24;
}
.price-unit {
  font-size: 14px;
  color: #999;
  margin-left: 4px;
}
.tag-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

/* 标题区 */
.title-section {
  background: #fff;
  padding: 0 16px 16px;
  border-bottom: 1px solid #f0f0f0;
}
.detail-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin: 0 0 6px;
  line-height: 1.4;
}
.location-row {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #888;
}

/* 基本信息网格 */
.info-section {
  background: #fff;
  margin-top: 10px;
  padding: 16px;
}
.info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px 8px;
}
.info-item {
  text-align: center;
}
.info-icon {
  margin-bottom: 4px;
}
.info-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 2px;
}
.info-value {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

/* 描述区 */
.desc-section {
  background: #fff;
  margin-top: 10px;
  padding: 16px;
}
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.desc-text {
  font-size: 14px;
  color: #555;
  line-height: 1.7;
  margin: 0;
}

/* 地图区 */
.map-section {
  background: #fff;
  margin-top: 10px;
  padding: 16px;
}
.location-text {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.detail-map {
  width: 100%;
  height: 250px;
  border-radius: 8px;
  overflow: hidden;
}

/* 底部固定按钮栏 */
.bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: #fff;
  padding: 8px 16px;
  padding-bottom: calc(8px + env(safe-area-inset-bottom, 0px));
  display: flex;
  gap: 8px;
  box-shadow: 0 -2px 10px rgba(0,0,0,0.06);
  z-index: 99;
  align-items: center;
}
.bottom-btn {
  flex: 1;
  font-size: 13px;
  border: none !important;
}
.fav-btn {
  flex: 0 0 auto;
  min-width: 80px;
}
.contact-btn {
  flex: 1.2;
}

/* 联系弹窗 */
.contact-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 16px 10px;
}
.contact-content p {
  margin: 8px 0 0;
  font-size: 15px;
  color: #333;
}
</style>
