---
comet_change: refactor-chat-ai-sdk
role: technical-design
canonical_spec: openspec
---

# refactor-chat-ai-sdk 深度技术设计

## 架构概览

全量替换方案：后端重写 `/api/chat/send` 端点输出 AI SDK UIMessageStream 协议，前端用 `useChat` hook 替换手写 SSE 流式处理。

```
┌──────────────┐    POST /api/chat/send     ┌──────────────┐
│  useChat     │ ──────────────────────────▶ │  FastAPI     │
│  (前端)      │    UIMessage[] + conv_id    │  chat_stream │
│              │ ◀────────────────────────── │              │
│              │    SSE: UIMessageStream     │  LangChain   │
└──────────────┘                             │  agent       │
                                             └──────────────┘
```

## 1. 后端协议转换层

### 1.1 请求格式

AI SDK `DefaultChatTransport` 发送 POST 请求体：

```json
{
  "id": "chat-123",
  "messages": [
    { "id": "msg-1", "role": "user", "parts": [{ "type": "text", "text": "退货政策是什么" }] }
  ],
  "conversation_id": 123,
  "trigger": "submit-message"
}
```

后端需要：
1. 从请求体提取 `conversation_id`（来自 body）和 `messages`（UIMessage 格式）
2. 将 UIMessage[] 转换为 LangChain HistoryMessage
3. 验证会话归属（保留现有逻辑）
4. 持久化用户消息

### 1.2 UIMessage → LangChain HistoryMessage 转换

```python
def ui_messages_to_langchain(ui_messages: list[dict]) -> list:
    """将 AI SDK UIMessage[] 转换为 LangChain Message 列表"""
    result = []
    for msg in ui_messages:
        if msg["role"] == "user":
            text = "".join(
                p["text"] for p in msg.get("parts", [])
                if p["type"] == "text"
            )
            if text:
                result.append(HumanMessage(content=text))
        elif msg["role"] == "assistant":
            text_parts = []
            tool_calls = []
            tool_results = []
            for p in msg.get("parts", []):
                if p["type"] == "text":
                    text_parts.append(p["text"])
                elif p["type"] == "tool-invocation":
                    # Legacy format
                    tool_calls.append(p)
                    if p.get("state") in ("result", "output-available"):
                        tool_results.append(p)
                elif p["type"].startswith("tool-"):
                    # Dynamic tool-{toolName} format
                    tool_calls.append(p)
                    if p.get("state") in ("result", "output-available"):
                        tool_results.append(p)

            # 创建 AIMessage（含文本和工具调用）
            if text_parts or tool_calls:
                tc_list = [
                    {"name": tc.get("toolName", tc.get("name")),
                     "args": tc.get("args", tc.get("input", {})),
                     "id": tc.get("toolCallId", tc.get("tool_invocation_id")),
                     "type": "tool_call"}
                    for tc in tool_calls
                ]
                result.append(AIMessage(
                    content=" ".join(text_parts) if text_parts else "",
                    tool_calls=tc_list if tc_list else None,
                ))

            # 创建 ToolMessage（工具结果）
            for tr in tool_results:
                result.append(ToolMessage(
                    content=str(tr.get("result", tr.get("output", ""))),
                    tool_call_id=tr.get("toolCallId", tr.get("tool_invocation_id")),
                    name=tr.get("toolName", tr.get("name")),
                ))
    return result
```

### 1.3 LangChain → UIMessageStream 转换函数

`to_ui_message_stream` 函数处理以下 chunk 类型：

| LangChain Chunk 类型 | chunk 字段 | 输出 UIMessageStream 事件 |
|---------------------|-----------|--------------------------|
| `AIMessageChunk` (文本) | `chunk.content` | `text-start` → `text-delta` → `text-end` |
| `AIMessageChunk` (增量工具调用) | `chunk.tool_call_chunks` | `tool-input-start` → `tool-input-delta` |
| `AIMessageChunk` (完整工具调用) | `chunk.tool_calls` | `tool-input-start` → `tool-input-available` |
| `ToolMessage` (工具结果) | `chunk.content`, `chunk.tool_call_id` | `tool-output-available` |
| 流结束 | — | `finish-step` → `finish` |

状态管理：
- `text_id`: 当前打开的文本块 ID，遇到工具调用或流结束时关闭
- `started_tool_calls: set`: 已发送 `tool-input-start` 的工具调用 ID，避免重复
- `message_id`: 消息 ID，由 `start` 事件发送

关键边界条件：
- 文本 delta 和工具调用可能出现在同一个 chunk（先关闭文本块再发工具事件）
- `tool_call_chunks` 可能为 `None`（不是空列表），需要检查
- `AIMessageChunk.content` 可能是空字符串，不应发送 `text-delta`
- 工具结果后通常有新的文本输出，需要新的 `start-step`

### 1.4 chat.py 端点重写

```python
@router.post("/send")
async def chat_stream(req: ChatSendRequest, ...):
    # 1. 验证会话归属
    conv = await get_conversation_by_id(db, req.conversation_id, current_user.id)

    # 2. 从请求体提取 UIMessage[] 并转换为 LangChain 历史
    ui_messages = req.messages  # 新增: 从请求体获取
    history = ui_messages_to_langchain(ui_messages)

    # 3. 持久化用户消息（取最后一条 user 消息的文本）
    user_text = history[-1].content if history else ""
    await create_message(db, req.conversation_id, "user", user_text)

    # 4. 流式生成
    full_response = []

    async def event_generator():
        try:
            async for chunk, metadata in agent.astream(
                {"messages": history},
                stream_mode="messages",
            ):
                full_response.append(...)
                async for event in to_ui_message_stream_chunk(chunk, state):
                    yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            error_event = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"
        finally:
            # 持久化助手回复
            if full_response:
                await create_message(db, req.conversation_id, "assistant", ...)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

### 1.5 请求模型更新

```python
class ChatSendRequest(BaseModel):
    conversation_id: int
    messages: list[dict] = []     # 新增: AI SDK UIMessage[]
    id: str | None = None         # AI SDK chat ID
    trigger: str | None = None    # 'submit-message' | 'regenerate-message'
```

## 2. 前端重构

### 2.1 ChatContainer 组件

新组件封装 `useChat` hook，通过 `key` 重挂载实现会话切换：

```typescript
// components/chat/chat-container.tsx
interface ChatContainerProps {
  conversationId: number
}

export function ChatContainer({ conversationId }: ChatContainerProps) {
  const { loadMessages } = useChatServices()
  const [initialMessages, setInitialMessages] = useState<UIMessage[] | null>(null)
  const [loaded, setLoaded] = useState(false)

  // 首次加载历史消息
  useEffect(() => {
    loadMessages(conversationId).then(msgs => {
      setInitialMessages(msgs.length > 0 ? msgs.map(toUIMessage) : [])
      setLoaded(true)
    })
  }, [conversationId])

  if (!loaded) return <LoadingPlaceholder />

  return <ChatInner conversationId={conversationId} initialMessages={initialMessages} />
}

function ChatInner({ conversationId, initialMessages }: {
  conversationId: number
  initialMessages: UIMessage[]
}) {
  const chat = useChat({
    id: `chat-${conversationId}`,
    initialMessages,
    transport: new DefaultChatTransport({
      api: `${process.env.NEXT_PUBLIC_API_URL!}${process.env.NEXT_PUBLIC_API_BASE_URL!}/chat/send`,
      headers: () => {
        const token = tokenManager.getToken()
        return token ? { Authorization: `Bearer ${token}` } : {}
      },
      body: { conversation_id: conversationId },
    }),
  })

  return (
    <>
      <MessageArea messages={chat.messages} />
      <ChatInput
        input={chat.input}
        setInput={chat.setInput}
        sendMessage={chat.sendMessage}
        status={chat.status}
        stop={chat.stop}
      />
    </>
  )
}
```

### 2.2 MessageBubble 基于 UIMessage.parts 渲染

```typescript
// components/chat/message-bubble.tsx (重写)
import type { UIMessage } from "ai"

export function MessageBubble({ message }: { message: UIMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[70%] rounded-xl rounded-br-sm bg-primary px-3.5 py-2.5 text-primary-foreground">
          {message.parts
            .filter((p): p is TextUIPart => p.type === "text")
            .map((p, i) => (
              <p key={i}>{p.text}</p>
            ))}
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[70%] rounded-xl rounded-bl-sm border bg-background px-3.5 py-2.5">
        {message.parts.map((part, i) => {
          if (part.type === "text") {
            return (
              <ReactMarkdown key={i} remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {part.text}
              </ReactMarkdown>
            )
          }
          if (isToolUIPart(part)) {
            return <ToolCallStatus key={i} toolPart={part} />
          }
          return null
        })}
      </div>
    </div>
  )
}
```

### 2.3 ToolCallStatus 适配

```typescript
// components/chat/tool-call-status.tsx (适配)
import type { ToolUIPart } from "ai"

interface ToolCallStatusProps {
  toolPart: ToolUIPart
}

export function ToolCallStatus({ toolPart }: ToolCallStatusProps) {
  const isCalling = toolPart.state === "call" || toolPart.state === "partial-call"
  const isDone = toolPart.state === "result"

  return (
    <div className="mt-2 space-y-1.5">
      {isCalling && (
        <div className="flex items-center gap-2 rounded-lg border border-yellow-200 bg-yellow-50 px-3.5 py-2 text-sm">
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-yellow-400 border-t-transparent" />
          <span className="text-black">🔧 调用工具：{toolPart.toolName}(...)</span>
        </div>
      )}
      {isDone && (
        <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-3.5 py-2 text-sm">
          <span className="text-green-600">✓</span>
          <span className="text-black">{formatToolResult(toolPart)}</span>
        </div>
      )}
    </div>
  )
}
```

### 2.4 ChatInput 适配

```typescript
// components/chat/chat-input.tsx (适配)
interface ChatInputProps {
  input: string
  setInput: (value: string) => void
  sendMessage: (message: string) => void
  status: string
  stop: () => void
}

export function ChatInput({ input, setInput, sendMessage, status, stop }: ChatInputProps) {
  const isStreaming = status === "streaming" || status === "submitted"

  const handleSend = useCallback(() => {
    const trimmed = input.trim()
    if (!trimmed || isStreaming) return
    sendMessage(trimmed)
  }, [input, isStreaming, sendMessage])

  // ...其余逻辑类似，使用 input/setInput 替代本地 state
  // 流式过程中显示停止按钮
}
```

### 2.5 历史消息转换

```typescript
// 将后端 Message 转换为 UIMessage
function toUIMessage(msg: DisplayMessage): UIMessage {
  return {
    id: msg.id,
    role: msg.role as "user" | "assistant",
    parts: [{ type: "text" as const, text: msg.content }],
  }
}
```

## 3. 删除/简化的文件

| 文件 | 操作 | 理由 |
|------|------|------|
| `services/chat.ts` | 删除 | `sendChatStream` 由 AI SDK Transport 替代 |
| `useServices.ts` | 简化 | 移除 `sendChat`、`createLocalUserMessage`、`createLocalAssistantMessage`，保留会话 CRUD |
| `message-bubble.tsx` | 重写 | 移除 `preprocessStreamingMarkdown`，基于 `UIMessage.parts` |
| `tool-call-status.tsx` | 适配 | 接收 `ToolUIPart` 替代 `ToolCall` 接口 |
| `chat-input.tsx` | 适配 | 使用 `useChat` 的 `input`/`setInput` |
| `chat-page.tsx` | 重构 | 用 `ChatContainer` + `key` 替代手写 SSE |

## 4. 测试策略

### 后端测试

1. **单元测试**：`to_ui_message_stream` 转换函数
   - 输入：模拟的 AIMessageChunk（文本、工具调用、工具调用增量）
   - 验证：输出事件序列和字段值
   - 边界：空内容 chunk、文本+工具调用同 chunk、工具结果后新文本

2. **集成测试**：向 `/api/chat/send` 发送请求，验证 SSE 输出格式

### 前端验证

1. **流式 Markdown 渲染**：发送包含加粗、代码块、表格、列表的消息
2. **工具调用状态**：触发知识库检索等工具
3. **会话切换**：切换会话后历史消息加载
4. **鉴权**：Bearer token 正确注入
5. **停止功能**：流式过程中停止
