import client from './client'
import type { LoginRequest, TokenResponse, User } from '@/types'

export const authApi = {
  login: (credentials: LoginRequest) =>
    client.post<any, TokenResponse>('/auth/login', credentials),

  getMe: () => client.get<any, User>('/auth/me'),
}
