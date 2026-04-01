import type { LoginRequest, LoginResponse } from '@/types/auth'
import apiClient from './client'

export async function login(username: string, password: string): Promise<LoginResponse> {
  const payload: LoginRequest = { username, password }
  const { data } = await apiClient.post<LoginResponse>('/api/auth/login', payload)
  return data
}
