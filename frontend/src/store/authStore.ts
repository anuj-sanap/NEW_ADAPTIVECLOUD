// frontend/src/store/authStore.ts
// Zustand store for JWT auth state.

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  role: string | null
  username: string | null
  setTokens: (access: string, refresh: string) => void
  setAccessToken: (token: string) => void
  setUser: (username: string, role: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      role: null,
      username: null,

      setTokens: (access, refresh) =>
        set({ accessToken: access, refreshToken: refresh }),

      setAccessToken: (token) => set({ accessToken: token }),

      setUser: (username, role) => set({ username, role }),

      logout: () =>
        set({ accessToken: null, refreshToken: null, role: null, username: null }),
    }),
    {
      name: 'auth-storage',
      // Only persist refresh token and user info — access token is short-lived
      partialize: (state) => ({
        refreshToken: state.refreshToken,
        username: state.username,
        role: state.role,
      }),
    },
  ),
)
