import { create } from 'zustand'
import api from '../api'

const useUserStore = create((set, get) => ({
  user: null,
  token: localStorage.getItem('token') || '',
  loading: false,

  isLoggedIn: () => !!get().token,

  setUser: (userData) => set({ user: userData }),

  setToken: (newToken) => {
    localStorage.setItem('token', newToken)
    set({ token: newToken })
  },

  logout: () => {
    localStorage.removeItem('token')
    set({ user: null, token: '' })
  },

  fetchProfile: async () => {
    const { token } = get()
    if (!token) return null
    try {
      const res = await api.get('/auth/me')
      if (res.data) {
        set({ user: res.data })
      }
      return res.data
    } catch {
      return null
    }
  },
}))

export default useUserStore
