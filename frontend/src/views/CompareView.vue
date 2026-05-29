<template>
  <div class="compare-view">
    <!-- 顶部导航 -->
    <van-nav-bar
      title="房产对比"
      fixed
      placeholder
      z-index="100"
    />

    <!-- 顶部提示 -->
    <div class="compare-header">
      <div class="header-info">
        <van-icon name="info-o" color="#1989fa" size="16" />
        <span>已选择 {{ compareStore.count }}/4 个房源</span>
      </div>
      <div class="header-actions">
        <van-button
          v-if="compareStore.count > 0"
          size="small"
          plain
          hairline
          icon="plus"
          round
          @click="showPicker = true"
        >
          添加房源
        </van-button>
      </div>
    </div>

    <!-- 空状态 -->
    <van-empty
      v-if="compareStore.count === 0"
      image="search"
      description="暂无对比项"
    >
      <template #extra>
        <div class="empty-content">
          <p>点击下方按钮添加房源进行对比</p>
          <van-button
            type="primary"
            icon="plus"
            round
            @click="showPicker = true"
            style="margin-top:12px"
          >
            添加房源
          </van-button>
        </div>
      </template>
    </van-empty>

    <!-- 对比表格 -->
    <div v-else class="compare-table-wrap">
      <div class="compare-table">
        <!-- 表头：图片列 -->
        <div class="table-row row-header">
          <div class="cell cell-label">图片</div>
          <div
            v-for="(item, idx) in compareStore.items"
            :key="item.id"
            class="cell cell-value"
            :class="priceClass(item)"
          >
            <div class="cell-img-wrap">
              <van-image
                :src="item.images?.[0] || 'https://via.placeholder.com/160x120/667eea/ffffff?text=CM'"
                fit="cover"
                class="cell-img"
              />
              <van-tag
                round
                closeable
                size="small"
                color="#999"
                class="remove-tag"
                @close="removeItem(item.id)"
              >
                移除
              </van-tag>
            </div>
          </div>
        </div>

        <!-- 标题行 -->
        <div class="table-row">
          <div class="cell cell-label">标题</div>
          <div
            v-for="item in compareStore.items"
            :key="item.id"
            class="cell cell-value"
            :class="priceClass(item)"
          >
            <div class="cell-title van-multi-ellipsis--l2">{{ item.title }}</div>
          </div>
        </div>

        <!-- 价格行 -->
        <div class="table-row">
          <div class="cell cell-label">价格</div>
          <div
            v-for="item in compareStore.items"
            :key="item.id"
            class="cell cell-value"
            :class="priceClass(item)"
          >
            <span class="price-cell" :class="priceClass(item)">
              ฿{{ formatPrice(item) }}
            </span>
            <span class="price-unit-label">{{ item.price_type === 'rent' ? '/月' : '' }}</span>
            <div class="price-badge" v-if="priceClass(item) === 'price-low'">
              <van-tag color="#07c160" size="small">最低</van-tag>
            </div>
            <div class="price-badge" v-else-if="priceClass(item) === 'price-high'">
              <van-tag color="#ee0a24" size="small">最高</van-tag>
            </div>
          </div>
        </div>

        <!-- 户型行 -->
        <div class="table-row">
          <div class="cell cell-label">户型</div>
          <div
            v-for="item in compareStore.items"
            :key="item.id"
            class="cell cell-value"
            :class="priceClass(item)"
          >
            {{ item.bedrooms || '-' }}室{{ item.bathrooms || '-' }}卫
          </div>
        </div>

        <!-- 面积行 -->
        <div class="table-row">
          <div class="cell cell-label">面积</div>
          <div
            v-for="item in compareStore.items"
            :key="item.id"
            class="cell cell-value"
            :class="priceClass(item)"
          >
            {{ item.area_sqm || '-' }} m²
          </div>
        </div>

        <!-- 每平米单价行 -->
        <div class="table-row">
          <div class="cell cell-label">每平米单价</div>
          <div
            v-for="item in compareStore.items"
            :key="item.id"
            class="cell cell-value"
            :class="priceClass(item)"
          >
            ฿{{ pricePerSqm(item) }}
          </div>
        </div>

        <!-- 区域行 -->
        <div class="table-row">
          <div class="cell cell-label">区域</div>
          <div
            v-for="item in compareStore.items"
            :key="item.id"
            class="cell cell-value"
            :class="priceClass(item)"
          >
            {{ item.district || '-' }}
          </div>
        </div>

        <!-- 来源行 -->
        <div class="table-row">
          <div class="cell cell-label">来源</div>
          <div
            v-for="item in compareStore.items"
            :key="item.id"
            class="cell cell-value"
            :class="priceClass(item)"
          >
            <van-tag plain size="small">{{ item.source_label || item.source || '-' }}</van-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部操作栏 -->
    <div class="bottom-bar" v-if="compareStore.count > 0">
      <van-button
        plain
        hairline
        icon="delete-o"
        round
        class="bottom-action"
        @click="clearAll"
      >
        清除全部
      </van-button>
      <van-button
        type="primary"
        icon="share-o"
        round
        class="bottom-action"
        @click="shareCompare"
      >
        分享比价
      </van-button>
    </div>

    <!-- 添加房源弹窗 -->
    <van-popup
      v-model:show="showPicker"
      position="bottom"
      round
      safe-area-inset-bottom
      :style="{ height: '60vh' }"
    >
      <div class="picker-header">
        <span class="picker-title">选择要对比的房源</span>
        <van-icon name="cross" size="18" @click="showPicker = false" />
      </div>
      <div class="picker-list">
        <div
          v-for="p in availableProperties"
          :key="p.id"
          class="picker-item"
          :class="{ selected: compareStore.hasItem(p.id) }"
          @click="selectProperty(p)"
        >
          <van-image
            :src="p.images?.[0] || 'https://via.placeholder.com/60x45/667eea/ffffff?text=CM'"
            fit="cover"
            width="60"
            height="45"
            round
          />
          <div class="picker-info">
            <div class="picker-name van-ellipsis">{{ p.title }}</div>
            <div class="picker-meta">
              ฿{{ formatPrice(p) }}{{ p.price_type === 'rent' ? '/月' : '' }}
              · {{ p.district }}
            </div>
          </div>
          <div class="picker-check">
            <van-icon
              :name="compareStore.hasItem(p.id) ? 'success' : 'circle'"
              :color="compareStore.hasItem(p.id) ? '#07c160' : '#ccc'"
              size="22"
            />
          </div>
        </div>
        <div v-if="availableProperties.length === 0" class="picker-empty">
          没有更多可添加的房源
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useCompareStore } from '@/stores/compare'
import { usePropertyStore } from '@/stores/property'
import { showToast } from 'vant'

const compareStore = useCompareStore()
const propertyStore = usePropertyStore()

const showPicker = ref(false)

// 从 store 获取所有房产供选择
const availableProperties = computed(() => {
  return propertyStore.filteredProperties
})

// 计算价格高低
const priceExtremes = computed(() => {
  const items = compareStore.items
  if (items.length < 2) return { low: null, high: null }
  let low = Infinity
  let high = -Infinity
  let lowItem = null
  let highItem = null
  items.forEach(item => {
    const p = propertyStore.getPriceValue(item) || 0
    if (p < low) { low = p; lowItem = item.id }
    if (p > high) { high = p; highItem = item.id }
  })
  return { low: lowItem, high: highItem }
})

function priceClass(item) {
  if (!priceExtremes.value.low) return ''
  if (item.id === priceExtremes.value.low) return 'price-low'
  if (item.id === priceExtremes.value.high) return 'price-high'
  return ''
}

function formatPrice(item) {
  const p = propertyStore.getPriceValue(item)
  if (!p) return '0'
  if (p >= 10000) return (p / 10000).toFixed(1) + '万'
  return p.toLocaleString()
}

function pricePerSqm(item) {
  const price = propertyStore.getPriceValue(item)
  const area = item.area_sqm
  if (!price || !area) return '-'
  return Math.round(price / area).toLocaleString()
}

function removeItem(id) {
  compareStore.removeItem(id)
  showToast('已移除')
}

function clearAll() {
  compareStore.clearAll()
  showToast('已清除全部')
}

function selectProperty(p) {
  if (compareStore.hasItem(p.id)) {
    compareStore.removeItem(p.id)
  } else {
    if (compareStore.count >= 4) {
      showToast('最多选择4个房源进行对比')
      return
    }
    compareStore.addItem({ ...p })
    showToast('已添加')
  }
}

async function shareCompare() {
  const items = compareStore.items
  if (items.length === 0) return

  let text = '【清迈房产对比】\n'
  items.forEach((item, idx) => {
    const price = `฿${formatPrice(item)}${item.price_type === 'rent' ? '/月' : ''}`
    text += `\n${idx + 1}. ${item.title}\n`
    text += `   价格: ${price} | ${item.bedrooms}室${item.bathrooms}卫 | ${item.area_sqm}m²\n`
    text += `   区域: ${item.district} | 来源: ${item.source_label || item.source}\n`
  })

  // 先尝试原生分享
  if (navigator.share) {
    try {
      await navigator.share({
        title: '清迈房产对比',
        text,
      })
      return
    } catch (e) {
      if (e.name !== 'AbortError') {
        // fallback to clipboard
      }
    }
  }

  // 降级：复制到剪贴板
  try {
    await navigator.clipboard.writeText(text)
    showToast('对比信息已复制到剪贴板')
  } catch {
    // 最后降级：显示对话框
    showToast('分享失败，请手动复制')
  }
}

onMounted(() => {
  if (propertyStore.properties.length === 0) {
    propertyStore.loadProperties()
  }
})
</script>

<style scoped>
.compare-view {
  background: #f7f8fa;
  min-height: 100vh;
  padding-bottom: 70px;
}

/* 顶部提示 */
.compare-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
}
.header-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #333;
}

/* 空状态 */
.empty-content {
  text-align: center;
}
.empty-content p {
  font-size: 14px;
  color: #999;
  margin: 0;
}

/* 对比表格 */
.compare-table-wrap {
  padding: 12px;
}
.compare-table {
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.table-row {
  display: flex;
  border-bottom: 1px solid #f5f5f5;
}
.table-row:last-child {
  border-bottom: none;
}
.row-header {
  background: #fafafa;
}
.cell {
  flex: 1;
  min-width: 0;
  padding: 10px 8px;
  text-align: center;
  font-size: 13px;
  color: #333;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.cell-label {
  flex: 0 0 80px;
  font-weight: 600;
  color: #646566;
  background: #f7f8fa;
  font-size: 12px;
  padding: 10px 6px;
  border-right: 1px solid #f0f0f0;
}
.cell-value {
  min-width: 100px;
}

/* 图片 */
.cell-img-wrap {
  position: relative;
  width: 80px;
  height: 60px;
}
.cell-img {
  width: 80px;
  height: 60px;
  border-radius: 6px;
}
.remove-tag {
  position: absolute;
  top: -6px;
  right: -6px;
}

/* 标题 */
.cell-title {
  font-size: 12px;
  line-height: 1.4;
  color: #333;
  max-width: 100%;
}

/* 价格 */
.price-cell {
  font-weight: 600;
  font-size: 15px;
}
.price-unit-label {
  font-size: 11px;
  color: #999;
}
.price-badge {
  margin-top: 3px;
}

/* 价格高低高亮 */
.price-low .price-cell {
  color: #07c160;
}
.price-high .price-cell {
  color: #ee0a24;
}
.price-low {
  background: #f0fff4;
}
.price-high {
  background: #fff5f5;
}

/* 底部操作栏 */
.bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: #fff;
  padding: 8px 16px;
  padding-bottom: calc(8px + env(safe-area-inset-bottom, 0px));
  display: flex;
  gap: 12px;
  box-shadow: 0 -2px 10px rgba(0,0,0,0.06);
  z-index: 99;
}
.bottom-action {
  flex: 1;
  font-size: 14px;
}

/* 添加房源弹窗 */
.picker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 16px 12px;
  border-bottom: 1px solid #f0f0f0;
}
.picker-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}
.picker-list {
  height: calc(60vh - 56px);
  overflow-y: auto;
  padding: 0 16px;
}
.picker-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  transition: background 0.15s;
}
.picker-item:active {
  background: #f7f8fa;
}
.picker-item.selected {
  background: #f0fff4;
  margin: 0 -16px;
  padding: 12px 16px;
}
.picker-info {
  flex: 1;
  min-width: 0;
}
.picker-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 4px;
}
.picker-meta {
  font-size: 12px;
  color: #999;
}
.picker-check {
  flex-shrink: 0;
}
.picker-empty {
  text-align: center;
  color: #999;
  padding: 40px 0;
  font-size: 14px;
}
</style>
