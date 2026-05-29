<template>
  <div class="search-page">
    <!-- 顶部搜索框 -->
    <van-search
      v-model="keyword"
      shape="round"
      placeholder="输入城市、区域或房产名称"
      @search="onSearch"
      @clear="onClear"
      @focus="onFocus"
    />

    <!-- 快捷筛选行 -->
    <div class="quick-filters">
      <van-tabs
        v-model:active="priceTab"
        @change="onPriceTabChange"
        class="price-tabs"
        :ellipsis="false"
      >
        <van-tab title="全部" name="" />
        <van-tab title="出租" name="rent" />
        <van-tab title="出售" name="sale" />
      </van-tabs>
      <div class="bedroom-chips">
        <van-tag
          v-for="item in bedroomOptions"
          :key="item.value"
          :type="selectedBedrooms === item.value ? 'danger' : 'default'"
          size="medium"
          plain
          round
          class="chip"
          @click="onBedroomClick(item.value)"
        >
          {{ item.label }}
        </van-tag>
      </div>
    </div>

    <!-- 结果状态栏 -->
    <div class="result-bar">
      <span class="result-count">找到 {{ totalCount }} 套房源</span>
      <van-button size="small" round plain @click="showFilterSheet = true" class="filter-btn">
        <van-icon name="filter-o" size="14" /> 筛选
      </van-button>
    </div>

    <!-- 房源列表 -->
    <van-pull-refresh v-model="refreshing" @refresh="onRefresh" class="list-wrapper">
      <van-list
        v-model:loading="listLoading"
        :finished="listFinished"
        finished-text="没有更多了"
        @load="onLoad"
      >
        <div v-if="displayList.length > 0" class="property-list">
          <PropertyCard v-for="item in displayList" :key="item.id" :property="item" />
        </div>
        <van-empty v-else-if="!listLoading" description="未找到匹配房源" />
      </van-list>
    </van-pull-refresh>

    <!-- 底部筛选面板 -->
    <van-action-sheet
      v-model:show="showFilterSheet"
      title="筛选条件"
      closeable
      close-icon="close"
    >
      <div class="filter-content">
        <!-- 区域选择 -->
        <div class="filter-group">
          <div class="filter-label">选择区域</div>
          <div class="filter-tags">
            <van-tag
              :type="filterDistrict === '' ? 'danger' : 'default'"
              size="medium"
              plain
              round
              class="filter-tag"
              @click="onFilterDistrict('')"
            >不限</van-tag>
            <van-tag
              v-for="d in store.districts"
              :key="d.name"
              :type="filterDistrict === d.name ? 'danger' : 'default'"
              size="medium"
              plain
              round
              class="filter-tag"
              @click="onFilterDistrict(d.name)"
            >{{ d.name }}</van-tag>
          </div>
        </div>

        <!-- 价格范围 -->
        <div class="filter-group">
          <div class="filter-label">价格范围（泰铢 THB）</div>
          <div class="price-range">
            <van-field
              v-model="filterMinPrice"
              type="number"
              placeholder="最低价"
              input-align="center"
              clearable
            />
            <span class="range-sep">—</span>
            <van-field
              v-model="filterMaxPrice"
              type="number"
              placeholder="最高价"
              input-align="center"
              clearable
            />
          </div>
        </div>

        <!-- 排序方式 -->
        <div class="filter-group">
          <div class="filter-label">排序方式</div>
          <van-radio-group v-model="filterSort" class="sort-options">
            <van-radio name="default">默认排序</van-radio>
            <van-radio name="price_asc">价格从低到高</van-radio>
            <van-radio name="price_desc">价格从高到低</van-radio>
            <van-radio name="newest">最新发布</van-radio>
          </van-radio-group>
        </div>

        <!-- 底部按钮 -->
        <div class="filter-actions">
          <van-button block round plain @click="resetAllFilters" class="reset-btn">
            重置筛选
          </van-button>
          <van-button block round type="danger" @click="showFilterSheet = false">
            完成
          </van-button>
        </div>
      </div>
    </van-action-sheet>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePropertyStore } from '@/stores/property'
import PropertyCard from '@/components/PropertyCard.vue'

const route = useRoute()
const router = useRouter()
const store = usePropertyStore()

// ─── 搜索关键词 ───
const keyword = ref('')

// ─── 快捷筛选 ───
const priceTab = ref('')
const selectedBedrooms = ref(null)

const bedroomOptions = [
  { label: '不限', value: null },
  { label: '1卧', value: 1 },
  { label: '2卧', value: 2 },
  { label: '3卧', value: 3 },
  { label: '4卧+', value: 4 },
]

function onSearch(val) {
  store.updateFilters({ keyword: val })
  router.replace({ query: { ...route.query, q: val || undefined } })
}

function onClear() {
  keyword.value = ''
  store.updateFilters({ keyword: '' })
  router.replace({ query: { ...route.query, q: undefined } })
}

function onFocus() {
  // no-op, kept for future analytics
}

function onPriceTabChange(name) {
  store.updateFilters({ priceType: name })
}

function onBedroomClick(val) {
  selectedBedrooms.value = selectedBedrooms.value === val ? null : val
  store.updateFilters({ bedrooms: selectedBedrooms.value })
}

// ─── 结果列表 & 分页 ───
const pageSize = 10
const page = ref(1)
const listLoading = ref(false)
const listFinished = ref(false)
const refreshing = ref(false)

const allItems = computed(() => store.filteredProperties)
const totalCount = computed(() => allItems.value.length)
const displayList = computed(() => allItems.value.slice(0, page.value * pageSize))

function onLoad() {
  if (listFinished.value) return

  // 模拟异步加载延迟
  setTimeout(() => {
    page.value++
    listLoading.value = false

    // 判断是否还有更多
    if (displayList.value.length >= allItems.value.length) {
      listFinished.value = true
    }
  }, 300)
}

function onRefresh() {
  page.value = 1
  listFinished.value = false
  listLoading.value = false
  refreshing.value = false
}

// 筛选项变化时重置分页
watch(
  () => [store.searchFilters, store.sortBy],
  () => {
    page.value = 1
    listFinished.value = false
    nextTick(() => {
      listLoading.value = false
    })
  },
  { deep: true }
)

// ─── 底部筛选面板 ───
const showFilterSheet = ref(false)
const filterDistrict = ref('')
const filterMinPrice = ref(null)
const filterMaxPrice = ref(null)
const filterSort = ref('default')

// 打开面板时同步当前筛选值
watch(showFilterSheet, (val) => {
  if (val) {
    filterDistrict.value = store.searchFilters.district || ''
    filterMinPrice.value = store.searchFilters.minPrice
    filterMaxPrice.value = store.searchFilters.maxPrice
    filterSort.value = store.sortBy
  }
})

function onFilterDistrict(name) {
  filterDistrict.value = name
  store.updateFilters({ district: name || '' })
}

// 面板内价格变化即时更新
watch(filterMinPrice, (val) => {
  store.updateFilters({ minPrice: val ? Number(val) : null })
})
watch(filterMaxPrice, (val) => {
  store.updateFilters({ maxPrice: val ? Number(val) : null })
})
watch(filterSort, (val) => {
  store.sortBy = val
})

function resetAllFilters() {
  store.resetFilters()
  store.sortBy = 'default'
  keyword.value = ''
  selectedBedrooms.value = null
  priceTab.value = ''
  filterDistrict.value = ''
  filterMinPrice.value = null
  filterMaxPrice.value = null
  filterSort.value = 'default'
  router.replace({ query: {} })
}

// ─── 初始化 ───
onMounted(() => {
  store.loadProperties()

  // 处理从其他页面带入的查询参数
  const q = route.query
  if (q.q) {
    keyword.value = q.q
    store.updateFilters({ keyword: q.q })
  }
  if (q.district) {
    store.updateFilters({ district: q.district })
    filterDistrict.value = q.district
  }

  // 同步现有筛选状态
  if (store.searchFilters.priceType) {
    priceTab.value = store.searchFilters.priceType
  }
  if (store.searchFilters.bedrooms) {
    selectedBedrooms.value = store.searchFilters.bedrooms
  }
})
</script>

<style scoped>
.search-page {
  min-height: 100vh;
  background: #f7f8fa;
  padding-bottom: 60px;
}

/* 快捷筛选行 */
.quick-filters {
  background: #fff;
  padding-bottom: 4px;
}

.price-tabs {
  --van-tabs-bottom-bar-height: 0;
  --van-tab-font-size: 14px;
}

.price-tabs :deep(.van-tab) {
  padding: 0 12px;
  font-size: 14px;
}

.bedroom-chips {
  display: flex;
  gap: 8px;
  padding: 6px 12px 10px;
  overflow-x: auto;
  white-space: nowrap;
  -webkit-overflow-scrolling: touch;
}

.bedroom-chips::-webkit-scrollbar {
  display: none;
}

.chip {
  flex-shrink: 0;
  font-size: 13px;
  padding: 6px 14px;
}

/* 结果状态栏 */
.result-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: #f7f8fa;
}

.result-count {
  font-size: 13px;
  color: #666;
}

.filter-btn {
  font-size: 12px;
  padding: 0 10px;
}

/* 列表区域 */
.list-wrapper {
  height: calc(100vh - 200px);
  overflow-y: auto;
}

.property-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0 12px 12px;
}

/* 底部筛选面板 */
.filter-content {
  padding: 16px 20px 30px;
  max-height: 60vh;
  overflow-y: auto;
}

.filter-group {
  margin-bottom: 20px;
}

.filter-label {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
}

.filter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-tag {
  flex-shrink: 0;
  font-size: 13px;
  padding: 6px 14px;
}

.price-range {
  display: flex;
  align-items: center;
  gap: 8px;
}

.price-range .van-field {
  flex: 1;
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 4px 0;
}

.range-sep {
  color: #ccc;
  font-size: 14px;
  flex-shrink: 0;
}

.sort-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sort-options :deep(.van-radio__label) {
  font-size: 14px;
}

.filter-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.filter-actions .van-button {
  flex: 1;
}

.reset-btn {
  color: #666;
  border-color: #ddd;
}
</style>
