import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auth helpers
export function updateAuthHeader(token) {
  api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  localStorage.setItem('token', token)
}

export function clearAuthHeader() {
  delete api.defaults.headers.common['Authorization']
  localStorage.removeItem('token')
}

// Properties
export function fetchProperties(params = {}) {
  return api.get('/properties', { params })
}

export function fetchPropertyDetail(id) {
  return api.get(`/properties/${id}`)
}

export function fetchPriceHistory(id, limit = 20) {
  return api.get(`/properties/${id}/price-history`, { params: { limit } })
}

export function fetchPropertyCompare(ids) {
  return api.get('/properties/compare', { params: { ids: ids.join(',') } })
}

export function fetchMarkers(bounds) {
  return api.get('/markers', { params: bounds || {} })
}

export function fetchDistricts() {
  return api.get('/districts')
}

// Favorites
export function fetchFavorites() {
  return api.get('/favorites')
}
export function addFavorite(propertyId) {
  return api.post('/favorites', { property_id: propertyId })
}
export function removeFavorite(propertyId) {
  return api.delete(`/favorites/${propertyId}`)
}

// Comparisons
export function fetchComparisons() {
  return api.get('/comparisons')
}
export function saveComparison(data) {
  return api.post('/comparisons', data)
}

// Auth
export function login(data) {
  return api.post('/auth/login', data)
}
export function register(data) {
  return api.post('/auth/register', data)
}

// AI Analysis
export function fetchAIAnalysis(propertyId) {
  return api.get(`/properties/${propertyId}/ai-analysis`)
}

export function fetchAICompare(ids) {
  return api.get('/properties/ai/compare', { params: { ids: ids.join(',') } })
}

export function fetchSmartSearch(query, page = 1, pageSize = 20) {
  return api.get('/properties/ai/smart-search', { params: { q: query, page, page_size: pageSize } })
}

export default api
