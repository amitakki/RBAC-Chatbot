export interface ChatRequest {
  question: string
  session_id?: string
}

export interface ChatResponse {
  answer: string
  sources: string[]
  session_id: string
  run_id: string
}

export type MessageRole = 'user' | 'assistant'

export interface Message {
  id: string
  role: MessageRole
  content: string
  sources?: string[]
  timestamp: number
}

export interface ApiError {
  status: number
  code: string
  message: string
  retryAfter?: number
}
