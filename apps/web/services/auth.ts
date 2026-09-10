import { fetchClient } from "@/lib/fetch"

export interface User {
  id: number
  username: string
  role: string
}

export interface AuthResponse {
  token: string
  user: User
}

export interface LoginParams {
  username: string
  password: string
}

export interface RegisterParams {
  username: string
  password: string
}

export async function loginApi(username: string, password: string) {
  return fetchClient.post<AuthResponse, LoginParams>("/auth/login", {
    username,
    password,
  })
}

export async function registerApi(username: string, password: string) {
  return fetchClient.post<AuthResponse, RegisterParams>("/auth/register", {
    username,
    password,
  })
}

export async function getMeApi() {
  return fetchClient.get<User>("/auth/me")
}
