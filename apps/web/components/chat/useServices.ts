import { useRequest } from "ahooks"
import { useMemo } from "react"
import {
  getConversationsApi,
  createConversationApi,
  deleteConversationApi,
  getConversationMessagesApi,
  type Conversation,
  type Message,
} from "@/services/conversation"

// ========== 展示类型 ==========

export interface DisplaySession {
  id: number
  title: string
  time: string
}

// ========== 工具函数 ==========

function formatDateTime(dateStr: string): string {
  try {
    const d = new Date(dateStr)
    return d.toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    })
  } catch {
    return dateStr
  }
}

/** 将后端 Conversation 转换为 DisplaySession */
function toDisplaySession(c: Conversation): DisplaySession {
  return {
    id: c.id,
    title: c.title,
    time: formatDateTime(c.updated_at),
  }
}

/** 将后端 Message 转换为 UIMessage 格式 */
export function toUIMessage(msg: Message) {
  return {
    id: `db-${msg.id}`,
    role: msg.role as "user" | "assistant",
    parts: [{ type: "text" as const, text: msg.content }],
  }
}

// ========== useServices ==========

export default function useChatServices() {
  // 获取会话列表
  const conversationsControl = useRequest(getConversationsApi, { manual: true })
  const { data: convData } = conversationsControl
  const sessions = useMemo(
    () => (convData?.data ?? []).map(toDisplaySession),
    [convData]
  )

  // 获取会话消息
  const messagesControl = useRequest(getConversationMessagesApi, {
    manual: true,
  })

  // 创建会话
  const createControl = useRequest(createConversationApi, { manual: true })

  // 删除会话
  const deleteControl = useRequest(deleteConversationApi, { manual: true })

  /** 创建新会话并返回 DisplaySession */
  async function createSession(title: string): Promise<DisplaySession | null> {
    try {
      const res = await createControl.runAsync(title)
      const newConv = res.data
      return {
        id: newConv.id,
        title: newConv.title,
        time: formatDateTime(new Date().toISOString()),
      }
    } catch {
      return null
    }
  }

  /** 删除会话 */
  async function removeSession(conversationId: number): Promise<boolean> {
    try {
      await deleteControl.runAsync(conversationId)
      return true
    } catch {
      return false
    }
  }

  /** 加载会话消息（UIMessage 格式） */
  async function loadMessages(conversationId: number) {
    try {
      const res = await messagesControl.runAsync(conversationId)
      return res.data.map(toUIMessage)
    } catch {
      return []
    }
  }

  return {
    conversationsControl,
    sessions,
    loadMessages,
    createSession,
    removeSession,
  }
}
