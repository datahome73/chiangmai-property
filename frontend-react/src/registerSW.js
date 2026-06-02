/**
 * Service Worker 注册模块
 *
 * 在支持 SW 的浏览器中注册 sw.js，
 * 提供生命周期钩子和自动更新提示。
 */

const SW_PATH = '/sw.js'

export function registerSW() {
  if (!('serviceWorker' in navigator)) {
    console.log('[PWA] Service Worker 不被此浏览器支持')
    return
  }

  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register(SW_PATH)
      .then((registration) => {
        console.log('[PWA] Service Worker 注册成功:', registration.scope)

        // 检测新版本可用
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing
          if (!newWorker) return

          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // 新版本已下载，提示用户刷新
              console.log('[PWA] 新版本可用，请刷新页面')
              // 可在此触发 UI 提示（如 Toast 提示刷新）
            }
          })
        })
      })
      .catch((error) => {
        console.error('[PWA] Service Worker 注册失败:', error)
      })

    // 当新的 SW 接管页面时，提示用户
    let refreshing = false
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (refreshing) return
      refreshing = true
      window.location.reload()
    })
  })
}

/**
 * 检查是否有等待激活的新 SW，并主动触发更新
 */
export function skipWaitingAndReload() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready.then((registration) => {
      if (registration.waiting) {
        registration.waiting.postMessage({ type: 'SKIP_WAITING' })
      }
    })
  }
}
