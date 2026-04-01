import { useState, useRef, KeyboardEvent, ChangeEvent } from 'react'

const MAX_CHARS = 1000

interface InputBarProps {
  onSend: (question: string) => void
  disabled: boolean
}

export function InputBar({ onSend, disabled }: InputBarProps) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  function handleChange(e: ChangeEvent<HTMLTextAreaElement>) {
    if (e.target.value.length <= MAX_CHARS) {
      setText(e.target.value)
    }
  }

  function submit() {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
    textareaRef.current?.focus()
  }

  const remaining = MAX_CHARS - text.length
  const nearLimit = remaining <= 100

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3">
      <div className="flex items-end gap-3">
        <div className="relative flex-1">
          <textarea
            ref={textareaRef}
            rows={1}
            value={text}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="Ask a question… (Enter to send, Shift+Enter for new line)"
            aria-label="Message input"
            className="w-full resize-none rounded-xl border border-gray-300 px-4 py-2.5 pr-16 text-sm outline-none focus:border-finsolve-blue focus:ring-2 focus:ring-finsolve-blue/20 disabled:cursor-not-allowed disabled:bg-gray-50"
            style={{ maxHeight: '160px', overflowY: 'auto' }}
          />
          <span
            className={`absolute bottom-2.5 right-3 text-[11px] ${
              nearLimit ? 'text-red-500 font-semibold' : 'text-gray-400'
            }`}
            aria-live="polite"
            aria-label={`${remaining} characters remaining`}
          >
            {remaining}
          </span>
        </div>

        <button
          onClick={submit}
          disabled={!text.trim() || disabled}
          aria-label="Send message"
          className="flex-shrink-0 rounded-xl bg-finsolve-blue px-4 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {disabled ? (
            <span className="flex items-center gap-1.5">
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Sending
            </span>
          ) : (
            'Send'
          )}
        </button>
      </div>
    </div>
  )
}
