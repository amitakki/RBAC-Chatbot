import { useEffect, useRef } from 'react'
import { useChat } from '@/hooks/useChat'
import { useAuth } from '@/hooks/useAuth'
import { RoleBadge } from '@/components/auth/RoleBadge'
import { MessageBubble } from './MessageBubble'
import { InputBar } from './InputBar'
import { CitationPanel } from './CitationPanel'
import { ErrorBanner } from './ErrorBanner'

export function ChatWindow() {
  const { user, logout } = useAuth()
  const { messages, error, isLoading, sendQuestion, resetSession, latestSources } = useChat()
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  return (
    <div className="flex h-screen overflow-hidden bg-white">
      {/* Sidebar */}
      <aside className="flex w-64 flex-shrink-0 flex-col bg-finsolve-dark px-5 py-6 text-white">
        <h1 className="mb-1 text-lg font-bold tracking-wide">FinSolve</h1>
        <p className="mb-6 text-xs text-blue-300">AI Knowledge Assistant</p>

        <div className="mb-6 flex flex-col gap-2">
          <p className="text-xs font-medium uppercase tracking-widest text-blue-300">
            Signed in as
          </p>
          <p className="truncate text-sm font-semibold">{user?.user_id}</p>
          {user?.role && <RoleBadge role={user.role} />}
        </div>

        <div className="mt-auto flex flex-col gap-3">
          <button
            onClick={resetSession}
            aria-label="Start a new conversation"
            className="w-full rounded-lg border border-blue-400/40 px-3 py-2 text-sm font-medium text-blue-200 transition-colors hover:bg-white/10"
          >
            New Conversation
          </button>
          <button
            onClick={logout}
            aria-label="Log out"
            className="w-full rounded-lg px-3 py-2 text-sm font-medium text-blue-300 transition-colors hover:text-white"
          >
            Log out
          </button>
        </div>
      </aside>

      {/* Main chat area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Error banner */}
        {error && <ErrorBanner error={error} />}

        {/* Message list */}
        <main className="flex-1 overflow-y-auto px-6 py-6" aria-label="Chat messages">
          {messages.length === 0 && (
            <div className="flex h-full items-center justify-center text-center text-gray-400">
              <div>
                <p className="text-lg font-medium">Ask me anything</p>
                <p className="mt-1 text-sm">
                  I have access to FinSolve internal documents based on your role.
                </p>
              </div>
            </div>
          )}
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          {isLoading && (
            <div className="flex justify-start mb-4">
              <div className="max-w-[75%] rounded-2xl bg-gray-100 px-4 py-3 text-sm text-gray-500">
                <span className="flex items-center gap-1.5">
                  <span className="animate-bounce delay-0">●</span>
                  <span className="animate-bounce delay-100">●</span>
                  <span className="animate-bounce delay-200">●</span>
                </span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </main>

        {/* Input bar */}
        <InputBar onSend={sendQuestion} disabled={isLoading} />
      </div>

      {/* Citation panel */}
      {latestSources.length > 0 && <CitationPanel sources={latestSources} />}
    </div>
  )
}
