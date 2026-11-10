// frontend/src/api/client.ts
// Axios instance with JWT auth and automatic token refresh.

import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/store/authStore'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Request interceptor: attach Bearer token ──────────────────────────────────
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor: auto-refresh on 401 ────────────────────────────────
let _refreshing = false
let _waiters: Array<(token: string | null) => void> = []

apiClient.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true

      if (_refreshing) {
        // Queue this request until refresh completes
        return new Promise((resolve, reject) => {
          _waiters.push((newToken) => {
            if (newToken) {
              original.headers.Authorization = `Bearer ${newToken}`
              resolve(apiClient(original))
            } else {
              reject(error)
            }
          })
        })
      }

      _refreshing = true
      const store = useAuthStore.getState()

      try {
        const refreshToken = store.refreshToken
        if (!refreshToken) throw new Error('No refresh token')

        const { data } = await axios.post(`${BASE_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        })
        const newToken: string = data.access_token
        store.setAccessToken(newToken)
        _waiters.forEach((cb) => cb(newToken))
        _waiters = []
        original.headers.Authorization = `Bearer ${newToken}`
        return apiClient(original)
      } catch {
        _waiters.forEach((cb) => cb(null))
        _waiters = []
        store.logout()
        return Promise.reject(error)
      } finally {
        _refreshing = false
      }
    }

    return Promise.reject(error)
  },
)
