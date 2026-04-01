import { useState, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { sendMessage } from '@/api/chat'
import type { Message, ApiError } from '@/types/chat'

function generateId() {
  return Math.random().toString(36).slice(2, 10)
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionId, setSessionId] = useState<string | undefined>(undefined)
  const [error, setError] = useState<ApiError | null>(null)

  const mutation = useMutation({
    mutationFn: ({ question }: { question: string }) =>
      sendMessage(question, sessionId),
    onMutate: ({ question }) => {
      setError(null)
      const userMsg: Message = {
        id: generateId(),
        role: 'user',
        content: question,
        timestamp: Date.now(),
      }
      setMessages((prev) => [...prev, userMsg])
    },
    onSuccess: (data) => {
      setSessionId(data.session_id)
      const aiMsg: Message = {
        id: generateId(),
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        timestamp: Date.now(),
      }
      setMessages((prev) => [...prev, aiMsg])
    },
    onError: (err) => {
      setError(err as unknown as ApiError)
    },
  })

  const sendQuestion = useCallback(
    (question: string) => {
      if (!question.trim()) return
      mutation.mutate({ question: question.trim() })
    },
    [mutation],
  )

  const resetSession = useCallback(() => {
    setMessages([])
    setSessionId(undefined)
    setError(null)
  }, [])

  const latestSources =
    [...messages].reverse().find((m) => m.role === 'assistant' && m.sources?.length)?.sources ?? []

  return {
    messages,
    sessionId,
    error,
    isLoading: mutation.isPending,
    sendQuestion,
    resetSession,
    latestSources,
  }
}
