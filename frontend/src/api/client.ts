import axios from 'axios'
import type { ApiError } from '@/types/chat'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '',
  headers: { 'Content-Type': 'application/json' },
})

// Attach Bearer token from authStore on every request
apiClient.interceptors.request.use((config) => {
  // Dynamic import to avoid circular dependency with authStore
  const raw = (window as Window & { __authToken?: string }).__authToken
  if (raw) {
    config.headers.Authorization = `Bearer ${raw}`
  }
  return config
})

// Normalise error shape into ApiError
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status: number = error.response?.status ?? 0
    const detail = error.response?.data?.detail

    let code = 'unknown'
    let message = 'An unexpected error occurred. Please try again.'
    let retryAfter: number | undefined

    if (status === 401) {
      code = 'auth'
      message = 'Session expired. Please log in again.'
    } else if (status === 429) {
      code = 'rate_limit'
      retryAfter = parseInt(error.response?.headers?.['retry-after'] ?? '3600', 10)
      message = `Rate limit reached. Try again in ${retryAfter}s.`
    } else if (status === 400 && detail?.message) {
      code = 'guardrail'
      message = `Your query was blocked: ${detail.message}`
    } else if (status === 403) {
      code = 'forbidden'
      message = 'You do not have access to this resource.'
    } else if (status >= 500) {
      code = 'server'
      message = 'Server error — please try again shortly.'
    }

    const apiError: ApiError = { status, code, message, retryAfter }
    return Promise.reject(apiError)
  },
)

export default apiClient
