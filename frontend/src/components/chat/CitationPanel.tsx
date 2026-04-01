import { useState } from 'react'

interface CitationPanelProps {
  sources: string[]
}

export function CitationPanel({ sources }: CitationPanelProps) {
  const [collapsed, setCollapsed] = useState(false)

  if (sources.length === 0) return null

  return (
    <aside
      className={`flex-shrink-0 border-l border-gray-200 bg-finsolve-light transition-all duration-200 ${
        collapsed ? 'w-10' : 'w-64'
      }`}
      aria-label="Source citations"
    >
      {/* Toggle button */}
      <button
        onClick={() => setCollapsed((c) => !c)}
        aria-label={collapsed ? 'Expand citations panel' : 'Collapse citations panel'}
        className="flex w-full items-center justify-between px-3 py-3 text-xs font-semibold uppercase tracking-widest text-gray-500 hover:bg-gray-100"
      >
        {!collapsed && <span>Sources</span>}
        <svg
          className={`h-4 w-4 flex-shrink-0 transition-transform ${collapsed ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </button>

      {!collapsed && (
        <ul className="divide-y divide-gray-200 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 60px)' }}>
          {sources.map((src, i) => (
            <li key={i} className="px-4 py-3">
              <p className="text-xs font-medium text-gray-700 break-words">{src}</p>
            </li>
          ))}
        </ul>
      )}
    </aside>
  )
}
