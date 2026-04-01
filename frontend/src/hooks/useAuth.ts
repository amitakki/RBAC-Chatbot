import { useCallback, useRef } from 'react'
import { login as apiLogin } from '@/api/auth'
import { useAuthStore } from '@/store/authStore'

export function useAuth() {
  const { user, setUser, clearUser } = useAuthStore()
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const logout = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    clearUser()
  }, [clearUser])

  const login = useCallback(
    async (displayUsername: string, authUsername: string, authPassword: string) => {
      const response = await apiLogin(authUsername, authPassword)
      const expiresAt = Date.now() + response.expires_in * 1000
      setUser({
        user_id: displayUsername,
        role: response.role,
        token: response.access_token,
        expires_at: expiresAt,
      })
      timerRef.current = setTimeout(logout, response.expires_in * 1000)
    },
    [setUser, logout],
  )

  return { user, login, logout }
}
