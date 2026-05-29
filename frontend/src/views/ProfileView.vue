<template>
  <div class="profile-page">
    <!-- 未登录状态 -->
    <template v-if="!userStore.isLoggedIn">
      <div class="login-card">
        <div class="login-avatar">
          <van-icon name="contact" size="48" color="#c8c9cc" />
        </div>
        <h3 class="login-title">欢迎使用清迈房产比价</h3>
        <p class="login-desc">登录后可收藏房源、比价和查看更多信息</p>
        <van-button
          type="danger"
          round
          block
          class="login-btn"
          @click="router.push('/login')"
        >
          登录 / 注册
        </van-button>
      </div>
    </template>

    <!-- 已登录状态 -->
    <template v-else>
      <!-- 顶部用户信息区域 -->
      <div class="user-header">
        <div class="user-bg"></div>
        <div class="user-info">
          <div class="user-avatar">
            <span class="avatar-text">{{ avatarChar }}</span>
          </div>
          <div class="user-meta">
            <h3 class="user-name">{{ userStore.user?.nickname || '用户' }}</h3>
            <p class="user-phone">{{ userStore.user?.phone || '' }}</p>
          </div>
        </div>
      </div>

      <!-- 统计卡片 -->
      <div class="stat-cards">
        <div class="stat-item" @click="router.push('/favorites')">
          <span class="stat-num">{{ favCount }}</span>
          <span class="stat-label">收藏</span>
        </div>
        <div class="stat-item" @click="showComparisonSheet = true">
          <span class="stat-num">{{ compareCount }}</span>
          <span class="stat-label">比价</span>
        </div>
        <div class="stat-item" @click="router.push('/history')">
          <span class="stat-num">0</span>
          <span class="stat-label">浏览</span>
        </div>
      </div>

      <!-- 功能列表 -->
      <van-cell-group class="menu-group" :border="false">
        <van-cell
          title="我的收藏"
          icon="star-o"
          is-link
          to="/favorites"
        />
        <van-cell
          title="我的比价"
          icon="smile-comment-o"
          is-link
          @click="openComparisons"
        />
        <van-cell
          title="设置"
          icon="setting-o"
          is-link
          to="/settings"
        />
      </van-cell-group>

      <!-- 退出登录 -->
      <div class="logout-wrapper">
        <van-button
          type="danger"
          block
          round
          class="logout-btn"
          @click="handleLogout"
        >
          退出登录
        </van-button>
      </div>
    </template>

    <!-- 比价列表 ActionSheet -->
    <van-action-sheet
      v-model:show="showComparisonSheet"
      title="我的比价"
      :close-on-click-action="true"
    >
      <div class="comparison-list">
        <van-cell
          v-for="item in comparisonList"
          :key="item.id"
          :title="item.label || `比价集 #${item.id}`"
          :label="`${item.property_ids?.length || 0} 个房源`"
          is-link
          @click="goToComparison(item)"
        />
        <van-empty v-if="comparisonList.length === 0" description="暂无比价记录" />
      </div>
    </van-action-sheet>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { usePropertyStore } from '@/stores/property'
import api from '@/services/api'
import { showConfirmDialog, showToast } from 'vant'

const router = useRouter()
const userStore = useUserStore()
const propertyStore = usePropertyStore()

const favCount = ref(0)
const compareCount = ref(0)
const showComparisonSheet = ref(false)
const comparisonList = ref([])

const avatarChar = computed(() => {
  const name = userStore.user?.nickname || userStore.user?.phone || 'U'
  return name.charAt(0).toUpperCase()
})

onMounted(async () => {
  if (userStore.isLoggedIn) {
    await userStore.fetchProfile()
    await loadStats()
  }
})

async function loadStats() {
  try {
    const res = await api.get('/favorites')
    favCount.value = Array.isArray(res.data) ? res.data.length : res.data?.items?.length || 0
  } catch {
    favCount.value = propertyStore.favorites.length
  }
  try {
    const res = await api.get('/comparisons')
    compareCount.value = Array.isArray(res.data) ? res.data.length : 0
  } catch {
    compareCount.value = 0
  }
}

async function openComparisons() {
  try {
    const res = await api.get('/comparisons')
    comparisonList.value = Array.isArray(res.data) ? res.data : []
  } catch {
    comparisonList.value = []
  }
  showComparisonSheet.value = true
}

function goToComparison(item) {
  showComparisonSheet.value = false
  if (item.property_ids?.length) {
    const ids = item.property_ids.join(',')
    router.push(`/compare?ids=${ids}`)
  }
}

async function handleLogout() {
  try {
    await showConfirmDialog({
      title: '退出登录',
      message: '确定要退出登录吗？',
    })
    userStore.logout()
    router.replace('/')
    showToast('已退出登录')
  } catch {
    // cancelled
  }
}
</script>

<style scoped>
.profile-page {
  min-height: 100%;
  background: #f7f8fa;
  padding-bottom: 20px;
}

/* ─── 未登录卡片 ─── */
.login-card {
  margin: 60px 24px 0;
  padding: 40px 24px 32px;
  background: #fff;
  border-radius: 16px;
  text-align: center;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.login-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: #f2f3f5;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.login-title {
  font-size: 18px;
  font-weight: 600;
  color: #323233;
  margin: 0 0 8px;
}

.login-desc {
  font-size: 13px;
  color: #969799;
  margin: 0 0 24px;
  line-height: 1.5;
}

.login-btn {
  width: 80%;
  margin: 0 auto;
}

/* ─── 已登录头部 ─── */
.user-header {
  position: relative;
  padding: 0 16px 0;
}

.user-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 160px;
  background: linear-gradient(135deg, #ee0a24 0%, #ff6b35 100%);
  border-radius: 0 0 24px 24px;
}

.user-info {
  position: relative;
  display: flex;
  align-items: center;
  padding: 40px 0 24px;
  gap: 16px;
}

.user-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: rgba(255,255,255,0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgba(255,255,255,0.6);
}

.avatar-text {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
}

.user-name {
  font-size: 20px;
  font-weight: 600;
  color: #fff;
  margin: 0 0 4px;
}

.user-phone {
  font-size: 13px;
  color: rgba(255,255,255,0.8);
  margin: 0;
}

/* ─── 统计卡片 ─── */
.stat-cards {
  display: flex;
  gap: 10px;
  margin: -8px 16px 16px;
  position: relative;
  z-index: 1;
}

.stat-item {
  flex: 1;
  background: #fff;
  border-radius: 12px;
  padding: 16px 8px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  cursor: pointer;
}

.stat-num {
  display: block;
  font-size: 22px;
  font-weight: 700;
  color: #ee0a24;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: #969799;
}

/* ─── 功能列表 ─── */
.menu-group {
  margin: 0 16px;
  border-radius: 12px;
  overflow: hidden;
}

/* ─── 退出登录 ─── */
.logout-wrapper {
  margin: 24px 16px 0;
}

.logout-btn {
  height: 44px;
  font-size: 15px;
}

/* ─── 比价列表 ─── */
.comparison-list {
  max-height: 60vh;
  overflow-y: auto;
  padding: 0 0 16px;
}
</style>
