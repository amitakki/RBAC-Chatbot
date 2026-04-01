import { create } from 'zustand'
import type { UserContext } from '@/types/auth'

interface AuthState {
  user: UserContext | null
  setUser: (user: UserContext) => void
  clearUser: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  setUser: (user) => {
    // Expose token on window for the Axios interceptor (avoids circular import)
    ;(window as Window & { __authToken?: string }).__authToken = user.token
    set({ user })
  },
  clearUser: () => {
    ;(window as Window & { __authToken?: string }).__authToken = undefined
    set({ user: null })
  },
}))
