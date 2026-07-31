import { tokenManager } from "@/lib/fetch/token-manager"

// ========== 聊天 SSE 流式接口 ==========

export interface ChatSendParams {
  conversation_id: number
  message: string
}

export interface ToolCallEvent {
  name: string
  args: Record<string, unknown>
  id: string
}

export interface ToolResultEvent {
  name: string
  content: string
  tool_call_id: string
}

/**
 * 发送聊天消息并返回 SSE 流式响应。
 * 使用 fetch + EventSource 模式，逐块读取 SSE 事件。
 *
 * @param params - 包含 conversation_id 和 message
 * @param onMessage - 每收到一个 message 事件时调用
 * @param onDone - 流结束时调用
 * @param onError - 发生错误时调用
 * @param onToolCall - LLM 决定调用工具时调用
 * @param onToolResult - 工具执行完成时调用
 */
export async function sendChatStream(
  params: ChatSendParams,
  onMessage: (text: string) => void,
  onDone: () => void,
  onError: (error: Error) => void,
  onToolCall?: (toolCall: ToolCallEvent) => void,
  onToolResult?: (result: ToolResultEvent) => void,
): Promise<void> {
  const token = tokenManager.getToken()
  const baseUrl = process.env.NEXT_PUBLIC_API_URL! + process.env.NEXT_PUBLIC_API_BASE_URL!

  try {
    const response = await fetch(`${baseUrl}/chat/send`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(params),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error("No response body")
    }

    const decoder = new TextDecoder()
    let buffer = ""

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // 解析 SSE 事件
      const lines = buffer.split("\n")
      buffer = lines.pop() || "" // 保留未完成的行

      let currentEvent = ""
      for (const line of lines) {
        if (line.startsWith("event:")) {
          currentEvent = line.slice(6).trim()
        } else if (line.startsWith("data:")) {
          const data = line.slice(5).trim()
          if (currentEvent === "message" || currentEvent === "") {
            onMessage(data)
          } else if (currentEvent === "done") {
            onDone()
            return
          } else if (currentEvent === "error") {
            onError(new Error(data))
            return
          } else if (currentEvent === "tool_call") {
            try {
              const toolCall = JSON.parse(data) as ToolCallEvent
              onToolCall?.(toolCall)
            } catch {
              // 忽略解析失败的 tool_call 事件
            }
          } else if (currentEvent === "tool_result") {
            try {
              const result = JSON.parse(data) as ToolResultEvent
              onToolResult?.(result)
            } catch {
              // 忽略解析失败的 tool_result 事件
            }
          }
        }
      }
    }

    // 流正常结束
    onDone()
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)))
  }
}
