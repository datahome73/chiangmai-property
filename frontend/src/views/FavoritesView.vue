<template>
  <div class="favorites-page">
    <van-nav-bar title="我的收藏" />

    <div class="favorites-content">
      <!-- Empty state -->
      <van-empty v-if="favorites.length === 0" description="还没有收藏的房源" />

      <!-- Favorites grid -->
      <template v-else>
        <van-grid :column-num="2" :gutter="8" class="fav-grid" :border="false">
          <van-grid-item v-for="item in favorites" :key="item.id" class="fav-grid-item">
            <van-swipe-cell :right-width="80" :stop-propagation="true">
              <PropertyCard :property="item" />
              <template #right>
                <div class="swipe-right-action">
                  <van-button
                    square
                    type="danger"
                    text="取消收藏"
                    class="swipe-delete-btn"
                    @click="removeFavorite(item.id)"
                  />
                </div>
              </template>
            </van-swipe-cell>
          </van-grid-item>
        </van-grid>
      </template>
    </div>

    <!-- Footer count -->
    <div v-if="favorites.length > 0" class="favorites-footer">
      共 {{ favorites.length }} 个收藏
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { usePropertyStore } from '@/stores/property'
import PropertyCard from '@/components/PropertyCard.vue'

const store = usePropertyStore()
const favorites = computed(() => store.favorites)

function removeFavorite(id) {
  const item = favorites.value.find(f => f.id === id)
  if (item) {
    store.toggleFavorite(item)
  }
}
</script>

<style scoped>
.favorites-page {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  background: #f7f8fa;
}

.favorites-content {
  flex: 1;
  padding: 12px 8px;
}

.fav-grid {
  width: 100%;
}

.fav-grid-item {
  height: auto !important;
}

.swipe-right-action {
  display: flex;
  align-items: center;
  height: 100%;
}

.swipe-delete-btn {
  height: 100% !important;
  border-radius: 0 !important;
  min-width: 80px;
}

.favorites-footer {
  text-align: center;
  padding: 12px 16px;
  padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px));
  font-size: 13px;
  color: #999;
  border-top: 1px solid #ebedf0;
  background: #fff;
}
</style>
