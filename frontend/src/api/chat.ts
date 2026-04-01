import type { ChatRequest, ChatResponse } from '@/types/chat'
import apiClient from './client'

export async function sendMessage(
  question: string,
  session_id?: string,
): Promise<ChatResponse> {
  const payload: ChatRequest = { question, session_id }
  const { data } = await apiClient.post<ChatResponse>('/api/chat', payload)
  return data
}
