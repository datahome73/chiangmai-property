import { create } from 'zustand'

const useCompareStore = create((set, get) => ({
  items: [],

  count: 0,

  addItem: (property) => {
    const { items } = get()
    if (items.length >= 4) return
    if (items.find(i => i.id === property.id)) return
    set({ items: [...items, property], count: items.length + 1 })
  },

  removeItem: (id) => {
    const { items } = get()
    const filtered = items.filter(i => i.id !== id)
    set({ items: filtered, count: filtered.length })
  },

  clearAll: () => {
    set({ items: [], count: 0 })
  },

  hasItem: (id) => {
    return get().items.some(i => i.id === id)
  },
}))

export default useCompareStore
