export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  role: string
}

export interface UserContext {
  user_id: string
  role: string
  token: string
  expires_at: number // epoch ms
}
