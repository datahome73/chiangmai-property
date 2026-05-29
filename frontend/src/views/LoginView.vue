<template>
  <div class="login-page">
    <van-nav-bar title="登录" left-arrow @click-left="$router.back()" />

    <!-- Tab 切换：登录 / 注册 -->
    <van-tabs v-model:active="tabActive" sticky>
      <van-tab title="登录">
        <div class="form-wrap">
          <van-field
            v-model="phone"
            label="手机号"
            placeholder="请输入手机号"
            type="tel"
            maxlength="11"
            clearable
          />
          <van-field
            v-model="password"
            label="密码"
            placeholder="请输入密码"
            type="password"
            clearable
          />
          <van-button
            type="danger"
            block
            :loading="userStore.loading"
            style="margin-top: 24px;"
            @click="handleLogin"
          >
            登录
          </van-button>
        </div>
      </van-tab>

      <van-tab title="注册">
        <div class="form-wrap">
          <van-field
            v-model="phone"
            label="手机号"
            placeholder="请输入手机号"
            type="tel"
            maxlength="11"
            clearable
          />
          <van-field
            v-model="nickname"
            label="昵称"
            placeholder="请输入昵称"
            clearable
          />
          <van-field
            v-model="password"
            label="密码"
            placeholder="请输入密码"
            type="password"
            clearable
          />
          <van-button
            type="danger"
            block
            :loading="userStore.loading"
            style="margin-top: 24px;"
            @click="handleRegister"
          >
            注册
          </van-button>
        </div>
      </van-tab>
    </van-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const tabActive = ref(0)
const phone = ref('')
const password = ref('')
const nickname = ref('')

async function handleLogin() {
  if (!phone.value || !password.value) {
    showToast('请填写手机号和密码')
    return
  }
  try {
    await userStore.login(phone.value, password.value)
    showToast('登录成功')
    router.push('/profile')
  } catch (e) {
    showToast(e.message)
  }
}

async function handleRegister() {
  if (!phone.value || !password.value || !nickname.value) {
    showToast('请填写完整信息')
    return
  }
  try {
    await userStore.register(phone.value, password.value, nickname.value)
    showToast('注册成功')
    router.push('/profile')
  } catch (e) {
    showToast(e.message)
  }
}
</script>

<style scoped>
.form-wrap {
  padding: 24px 16px;
}
</style>
