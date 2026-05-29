import { create } from 'zustand'
import { fetchProperties, fetchPropertyDetail, fetchMarkers, fetchDistricts, fetchFavorites, addFavorite, removeFavorite } from '../api'

const usePropertyStore = create((set, get) => ({
  // State
  properties: [],
  totalCount: 0,
  currentPage: 1,
  pageSize: 20,
  loading: false,
  refreshing: false,
  finished: false,
  filters: {
    keyword: '',
    priceType: '',
    bedrooms: '',
    district: '',
    minPrice: '',
    maxPrice: '',
    source: '',
    sort: '',
  },
  currentProperty: null,
  detailLoading: false,
  markers: [],
  districts: [],
  favorites: [],

  // Getters
  getPriceValue: (p) => p?.price_type === 'RENT' ? p.price_rent : p.price_sale,

  getPriceLabel: (p) => {
    if (!p) return ''
    const val = p.price_type === 'RENT' ? p.price_rent : p.price_sale
    if (!val) return ''
    if (val >= 10000) {
      return `฿${(val / 10000).toFixed(1)}万${p.price_type === 'RENT' ? '/月' : ''}`
    }
    return `฿${val.toLocaleString()}${p.price_type === 'RENT' ? '/月' : ''}`
  },

  // Actions
  loadProperties: async (page = 1, append = false) => {
    const { filters, pageSize } = get()
    set({ loading: true })
    try {
      const params = {
        page,
        page_size: pageSize,
        ...(filters.keyword && { keyword: filters.keyword }),
        ...(filters.priceType && { price_type: filters.priceType.toUpperCase() }),
        ...(filters.bedrooms && { bedrooms: filters.bedrooms }),
        ...(filters.district && { district: filters.district }),
        ...(filters.minPrice && { min_price: filters.minPrice * 36 }),
        ...(filters.maxPrice && { max_price: filters.maxPrice * 36 }),
        ...(filters.source && { source: filters.source }),
        ...(filters.sort && { sort: filters.sort }),
      }
      const res = await fetchProperties(params)
      const data = res.data
      const items = data.items || data.data || []
      const total = data.total || items.length

      set({
        properties: append ? [...get().properties, ...items] : items,
        totalCount: total,
        currentPage: page,
        loading: false,
        finished: items.length < pageSize,
      })
    } catch (e) {
      set({ loading: false })
      console.error('Failed to load properties:', e)
    }
  },

  refreshProperties: async () => {
    set({ refreshing: true })
    await get().loadProperties(1, false)
    set({ refreshing: false })
  },

  loadPropertyDetail: async (id) => {
    set({ detailLoading: true, currentProperty: null })
    try {
      const res = await fetchPropertyDetail(id)
      const prop = res.data
      set({ currentProperty: prop, detailLoading: false })
      return prop
    } catch (e) {
      set({ detailLoading: false })
      console.error('Failed to load detail:', e)
      return null
    }
  },

  setFilters: (newFilters) => {
    set((state) => ({
      filters: { ...state.filters, ...newFilters },
    }))
  },

  fetchDistricts: async () => {
    try {
      const res = await fetchDistricts()
      set({ districts: res.data })
    } catch (e) {
      console.error('Failed to fetch districts:', e)
    }
  },

  fetchMarkers: async (bounds) => {
    try {
      const res = await fetchMarkers(bounds)
      set({ markers: res.data })
    } catch (e) {
      console.error('Failed to fetch markers:', e)
    }
  },

  loadFavorites: async () => {
    try {
      const res = await fetchFavorites()
      set({ favorites: res.data?.favorites || res.data || [] })
    } catch (e) {
      console.error('Failed to load favorites:', e)
    }
  },

  toggleFavorite: async (property) => {
    const { favorites } = get()
    const existing = favorites.find(f => f.id === property.id || f.property_id === property.id)
    if (existing) {
      try {
        await removeFavorite(property.id)
        set({ favorites: favorites.filter(f => f.id !== property.id && f.property_id !== property.id) })
      } catch (e) { console.error(e) }
    } else {
      try {
        await addFavorite(property.id)
        set({ favorites: [...favorites, property] })
      } catch (e) { console.error(e) }
    }
  },

  isFavorite: (id) => {
    return get().favorites.some(f => f.id === id || f.property_id === id)
  },
}))

export default usePropertyStore
