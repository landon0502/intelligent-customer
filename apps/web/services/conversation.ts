import { fetchClient } from "@/lib/fetch"

// ========== 类型定义 ==========

export interface Conversation {
  id: number
  title: string
  status: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: number
  role: "user" | "assistant" | "system"
  content: string
  sources: Record<string, unknown> | null
  created_at: string
}

// ========== 会话接口 ==========

export async function getConversationsApi() {
  return fetchClient.get<Conversation[]>("/conversations")
}

export async function createConversationApi(title?: string) {
  return fetchClient.post<{ id: number; title: string; status: string }>("/conversations", {
    title: title || undefined,
  })
}

export async function getConversationMessagesApi(conversationId: number) {
  return fetchClient.get<Message[]>(`/conversations/${conversationId}/messages`)
}

export async function deleteConversationApi(conversationId: number) {
  return fetchClient.delete<{ success: boolean }>(`/conversations/${conversationId}`)
}
