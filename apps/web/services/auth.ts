import { fetchClient } from "@/lib/fetch"
import type { ApiResponse } from "@intelligent-customer/fetch-client"

export interface User {
  id: number
  username: string
  role: string
}

export interface AuthResponse {
  token: string
  user: User
}

export async function loginApi(username: string, password: string) {
  return fetchClient.post<AuthResponse>("/auth/login", {
    username,
    password,
  })
}

export async function registerApi(username: string, password: string) {
  return fetchClient.post<AuthResponse>("/auth/register", {
    username,
    password,
  })
}

export async function getMeApi() {
  return fetchClient.get<User>("/auth/me")
}
