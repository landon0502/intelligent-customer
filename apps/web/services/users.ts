import { fetchClient } from "@/lib/fetch"

// ========== 类型定义 ==========

export interface User {
  id: number
  username: string
  role: "user" | "admin"
  created_at: string
}

// ========== 用户管理接口 ==========

export async function getUsersApi() {
  return fetchClient.get<User[]>("/users")
}

export async function createUserApi(
  username: string,
  password: string,
  role: string
) {
  return fetchClient.post<User>("/users", { username, password, role })
}

export async function deleteUserApi(id: number) {
  return fetchClient.delete<{ success: boolean }>(`/users/${id}`)
}
