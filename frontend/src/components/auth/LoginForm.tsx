import { FormEvent, useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import type { ApiError } from '@/types/chat'

const ROLE_CREDENTIALS = {
  finance: { username: 'alice_finance', password: 'finance123' },
  hr: { username: 'bob_hr', password: 'hr123' },
  marketing: { username: 'charlie_marketing', password: 'marketing123' },
  engineering: { username: 'diana_engineering', password: 'engineering123' },
  executive: { username: 'eve_executive', password: 'executive123' },
} as const

type Role = keyof typeof ROLE_CREDENTIALS

export function LoginForm() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [role, setRole] = useState<Role>('finance')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const displayName = username.trim()
      const credentials = ROLE_CREDENTIALS[role]
      await login(displayName, credentials.username, credentials.password)
    } catch (err) {
      const apiErr = err as ApiError
      if (apiErr.status === 401) {
        setError('Invalid username or password.')
      } else {
        setError(apiErr.message ?? 'Login failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-finsolve-light">
      <div className="w-full max-w-sm rounded-2xl bg-white p-8 shadow-lg">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-finsolve-dark">FinSolve</h1>
          <p className="mt-1 text-sm text-gray-500">Sign in to your account</p>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          <div className="mb-4">
            <label htmlFor="username" className="mb-1.5 block text-sm font-medium text-gray-700">
              Username
            </label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-finsolve-blue focus:ring-2 focus:ring-finsolve-blue/20"
              placeholder="e.g. amita"
            />
          </div>

          <div className="mb-6">
            <label htmlFor="role" className="mb-1.5 block text-sm font-medium text-gray-700">
              Role
            </label>
            <select
              id="role"
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-finsolve-blue focus:ring-2 focus:ring-finsolve-blue/20"
            >
              <option value="finance">Finance</option>
              <option value="hr">HR</option>
              <option value="marketing">Marketing</option>
              <option value="engineering">Engineering</option>
              <option value="executive">Executive</option>
            </select>
            <p className="mt-2 text-xs text-gray-500">
              The selected role determines which mock backend account is used.
            </p>
          </div>

          {error && (
            <div
              role="alert"
              className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !username.trim()}
            className="w-full rounded-lg bg-finsolve-blue px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}
