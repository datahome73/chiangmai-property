<template>
  <div class="property-card" @click="$router.push(`/detail/${property.id}`)">
    <!-- 图片 -->
    <div class="card-image">
      <van-image
        :src="property.images?.[0] || 'https://via.placeholder.com/400x250/667eea/ffffff?text=CM'"
        fit="cover"
        height="200"
        loading="lazy"
      />
      <div class="card-badges">
        <van-tag :color="property.price_type === 'rent' ? '#ee0a24' : '#07c160'" size="medium">
          {{ property.price_type === 'rent' ? '出租' : '出售' }}
        </van-tag>
        <van-tag color="#1989fa" size="medium" v-if="property.furnished">精装修</van-tag>
      </div>
    </div>

    <!-- 内容 -->
    <div class="card-body">
      <div class="card-price">
        <span class="price-amount">฿{{ formattedPrice }}</span>
        <span class="price-unit">{{ property.price_type === 'rent' ? '/月' : '' }}</span>
      </div>
      <div class="card-title van-multi-ellipsis--l2">{{ property.title }}</div>
      <div class="card-info">
        <span>{{ property.bedrooms }}卧{{ property.bathrooms }}卫</span>
        <span class="dot">·</span>
        <span>{{ property.area_sqm }}m²</span>
        <span class="dot">·</span>
        <span>{{ property.district }}</span>
      </div>
      <div class="card-footer">
        <span class="card-source">{{ property.source_label || property.source }}</span>
        <div class="card-actions">
          <van-icon
            :name="isFav ? 'star' : 'star-o'"
            :color="isFav ? '#ee0a24' : '#999'"
            size="18"
            @click.stop="toggleFav"
          />
          <van-icon
            :name="inCompare ? 'smile-o' : 'smile-comment-o'"
            color="#999"
            size="18"
            style="margin-left:12px"
            @click.stop="toggleCompare"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePropertyStore } from '@/stores/property'
import { useCompareStore } from '@/stores/compare'

const props = defineProps({
  property: { type: Object, required: true }
})

const router = useRouter()
const store = usePropertyStore()
const compareStore = useCompareStore()

const formattedPrice = computed(() => {
  const p = store.getPriceValue(props.property)
  if (!p) return '0'
  if (p >= 10000) return (p / 10000).toFixed(1) + '万'
  return p.toLocaleString()
})

const isFav = computed(() => store.isFavorite(props.property.id))
const inCompare = computed(() => compareStore.hasItem(props.property.id))

function toggleFav() {
  store.toggleFavorite(props.property)
}

function toggleCompare() {
  if (inCompare.value) {
    compareStore.removeItem(props.property.id)
  } else {
    compareStore.addItem(structuredClone(props.property))
  }
}
</script>

<style scoped>
.property-card {
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  transition: transform 0.2s;
}
.property-card:active {
  transform: scale(0.98);
}
.card-image {
  position: relative;
}
.card-badges {
  position: absolute;
  top: 10px;
  left: 10px;
  display: flex;
  gap: 6px;
}
.card-body {
  padding: 12px 14px 14px;
}
.card-price {
  margin-bottom: 6px;
}
.price-amount {
  font-size: 20px;
  font-weight: 700;
  color: #ee0a24;
}
.price-unit {
  font-size: 13px;
  color: #999;
}
.card-title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  line-height: 1.4;
  margin-bottom: 6px;
}
.card-info {
  font-size: 13px;
  color: #888;
  margin-bottom: 10px;
}
.dot {
  margin: 0 4px;
  color: #ccc;
}
.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid #f5f5f5;
}
.card-source {
  font-size: 12px;
  color: #aaa;
}
.card-actions {
  display: flex;
  align-items: center;
}
</style>
