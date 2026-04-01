import { useState } from 'react'
import type { ApiError } from '@/types/chat'

interface ErrorBannerProps {
  error: ApiError
}

const BANNER_STYLES: Record<string, string> = {
  rate_limit: 'bg-amber-50 border-amber-300 text-amber-800',
  guardrail: 'bg-yellow-50 border-yellow-300 text-yellow-800',
  forbidden: 'bg-orange-50 border-orange-300 text-orange-800',
  server: 'bg-red-50 border-red-300 text-red-700',
  unknown: 'bg-red-50 border-red-300 text-red-700',
}

export function ErrorBanner({ error }: ErrorBannerProps) {
  const [dismissed, setDismissed] = useState(false)
  if (dismissed) return null

  const styles = BANNER_STYLES[error.code] ?? BANNER_STYLES.unknown

  return (
    <div
      role="alert"
      className={`flex items-start gap-3 border-b px-5 py-3 text-sm ${styles}`}
    >
      <span className="flex-1">{error.message}</span>
      <button
        onClick={() => setDismissed(true)}
        aria-label="Dismiss error"
        className="flex-shrink-0 font-semibold opacity-70 hover:opacity-100"
      >
        ✕
      </button>
    </div>
  )
}
