import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useCompareStore = defineStore('compare', () => {
  const items = ref([])

  const count = computed(() => items.value.length)

  function addItem(property) {
    if (items.value.length >= 4) {
      return false // max 4 items
    }
    const exists = items.value.some(item => item.id === property.id)
    if (!exists) {
      items.value.push(property)
      return true
    }
    return false
  }

  function removeItem(id) {
    const index = items.value.findIndex(item => item.id === id)
    if (index !== -1) {
      items.value.splice(index, 1)
    }
  }

  function clearAll() {
    items.value = []
  }

  function hasItem(id) {
    return items.value.some(item => item.id === id)
  }

  return {
    items,
    count,
    addItem,
    removeItem,
    clearAll,
    hasItem
  }
})
