import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const usePropertyStore = defineStore('property', () => {
  // ─── State ──────────────────────────────────
  const properties = ref([])
  const favorites = ref(JSON.parse(localStorage.getItem('favorites') || '[]'))
  const currentProperty = ref(null)
  const loading = ref(false)
  const districts = ref([])
  const searchFilters = ref({
    keyword: '',
    priceType: '',       // 'rent' | 'sale' | ''
    propertyType: '',    // 'condo' | 'house' | ''
    district: '',
    minPrice: null,
    maxPrice: null,
    bedrooms: null,
  })
  const sortBy = ref('default') // 'default' | 'price_asc' | 'price_desc' | 'newest'

  // ─── Computed ───────────────────────────────
  const favoriteIds = computed(() => new Set(favorites.value.map(f => f.id)))

  // 筛选后的房产列表
  const filteredProperties = computed(() => {
    let list = [...properties.value]
    const f = searchFilters.value

    if (f.keyword) {
      const kw = f.keyword.toLowerCase()
      list = list.filter(p =>
        p.title.toLowerCase().includes(kw) ||
        p.district.toLowerCase().includes(kw) ||
        p.description?.toLowerCase().includes(kw)
      )
    }
    if (f.priceType) {
      list = list.filter(p => p.price_type === f.priceType)
    }
    if (f.propertyType) {
      list = list.filter(p => p.property_type === f.propertyType)
    }
    if (f.district) {
      list = list.filter(p => p.district === f.district)
    }
    if (f.bedrooms) {
      list = list.filter(p => p.bedrooms >= f.bedrooms)
    }
    if (f.minPrice) {
      list = list.filter(p => {
        const price = p.price_type === 'rent' ? p.price_rent : p.price_sale
        return price >= f.minPrice
      })
    }
    if (f.maxPrice) {
      list = list.filter(p => {
        const price = p.price_type === 'rent' ? p.price_rent : p.price_sale
        return price <= f.maxPrice
      })
    }

    // 排序
    if (sortBy.value === 'price_asc') {
      list.sort((a, b) => (a.price_rent || a.price_sale) - (b.price_rent || b.price_sale))
    } else if (sortBy.value === 'price_desc') {
      list.sort((a, b) => (b.price_rent || b.price_sale) - (a.price_rent || a.price_sale))
    } else if (sortBy.value === 'newest') {
      list.sort((a, b) => new Date(b.posted_date) - new Date(a.posted_date))
    }

    return list
  })

  // ─── Actions ────────────────────────────────
  async function loadProperties() {
    loading.value = true
    try {
      const res = await api.get('/properties', {
        params: { page: 1, page_size: 50 }
      })
      if (res.data?.items) {
        properties.value = res.data.items
      }
    } catch (e) {
      console.error('Failed to load properties:', e)
    }
    loading.value = false
  }

  async function loadDistricts() {
    try {
      const res = await api.get('/districts')
      if (res.data && Array.isArray(res.data)) {
        districts.value = res.data
      }
    } catch (e) {
      console.error('Failed to load districts:', e)
    }
  }

  async function loadPropertyDetail(id) {
    try {
      const res = await api.get('/properties/' + id)
      if (res.data) {
        currentProperty.value = res.data
        return res.data
      }
    } catch (e) {
      console.error('Failed to load property detail:', e)
    }
    currentProperty.value = null
    return null
  }

  async function toggleFavorite(property) {
    const idx = favorites.value.findIndex(f => f.id === property.id)
    if (idx === -1) {
      try {
        await api.post('/favorites', { property_id: property.id })
      } catch {
        // Silently continue even if API fails
      }
      favorites.value.push(property)
    } else {
      try {
        await api.delete('/favorites/' + property.id)
      } catch {
        // Silently continue
      }
      favorites.value.splice(idx, 1)
    }
    localStorage.setItem('favorites', JSON.stringify(favorites.value))
  }

  async function loadFavorites() {
    try {
      const res = await api.get('/favorites')
      if (res.data && Array.isArray(res.data)) {
        return res.data
      }
    } catch {
      // Fallback to local
    }
    return favorites.value
  }

  function updateFilters(partial) {
    Object.assign(searchFilters.value, partial)
  }

  function resetFilters() {
    searchFilters.value = {
      keyword: '',
      priceType: '',
      propertyType: '',
      district: '',
      minPrice: null,
      maxPrice: null,
      bedrooms: null,
    }
  }

  function isFavorite(id) {
    return favoriteIds.value.has(id)
  }

  function getPriceLabel(p) {
    if (p.price_type === 'rent') return `฿${p.price_rent?.toLocaleString()}/月`
    return `฿${p.price_sale?.toLocaleString()}`
  }

  function getPriceValue(p) {
    return p.price_type === 'rent' ? p.price_rent : p.price_sale
  }

  return {
    properties, favorites, currentProperty, loading, searchFilters, sortBy,
    favoriteIds, districts, filteredProperties,
    loadProperties, loadPropertyDetail, updateFilters, resetFilters,
    toggleFavorite, isFavorite, getPriceLabel, getPriceValue,
    loadFavorites, loadDistricts,
  }
})
