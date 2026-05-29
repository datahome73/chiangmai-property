<template>
  <div class="settings-page">
    <van-nav-bar title="设置" left-arrow @click-left="$router.back()" />

    <van-cell-group>
      <van-cell title="语言" is-link :value="currentLangLabel" @click="showLangSheet = true" />
      <van-cell title="版本" value="v0.1.0" />
    </van-cell-group>

    <van-action-sheet
      v-model:show="showLangSheet"
      :actions="langOptions"
      @select="onLangSelect"
      cancel-text="取消"
      close-on-click-action
    />

    <van-button
      type="danger"
      block
      style="margin: 24px 16px; width: calc(100% - 32px);"
      @click="handleLogout"
    >
      退出登录
    </van-button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const localeMap = {
  zh: '中文',
  en: 'English',
  th: 'ภาษาไทย',
}

const showLangSheet = ref(false)
const currentLang = ref(localStorage.getItem('locale') || 'zh')

const currentLangLabel = computed(() => localeMap[currentLang.value] || '中文')

const langOptions = [
  { name: '中文', value: 'zh' },
  { name: 'English', value: 'en' },
  { name: 'ภาษาไทย', value: 'th' },
]

function onLangSelect(option) {
  currentLang.value = option.value
  localStorage.setItem('locale', option.value)
  showToast('语言已切换')
}

function handleLogout() {
  userStore.logout()
  showToast('已退出登录')
  router.push('/')
}
</script>
