## Context

当前 web chat 模块的前端采用手写 SSE 流式处理：`sendChatStream` 通过 `fetch` + `ReadableStream` 逐 chunk 读取后端 SSE 事件，然后在 `chat-page.tsx` 中通过 `m.content + chunk` 逐块拼接字符串，最终传给 `ReactMarkdown` 渲染。后端使用 LangChain `agent.astream(stream_mode="messages")` + `sse-starlette` 输出自定义 SSE 事件（`event: message`、`event: tool_call`、`event: tool_result`）。

核心痛点：流式拼接的中间态 Markdown 文本包含不完整的语法结构，`ReactMarkdown` 无法正确解析，导致加粗、代码块、表格等格式在流式过程中显示异常，只有刷新后（加载完整消息）才能正常渲染。

项目已安装 `@ai-sdk/react@4.0.40` 和 `ai@7.0.37`，可直接使用 `useChat` hook。

## Goals / Non-Goals

**Goals:**
- 用 AI SDK `useChat` hook 替换手写 SSE 流式处理，从根本上解决流式 Markdown 渲染问题
- 后端输出 AI SDK UIMessageStream 协议格式，前端使用 `DefaultChatTransport` 零适配
- 利用 `UIMessage.parts` 结构化渲染，消除"不完整 Markdown"问题
- 利用 `ToolUIPart` 内置工具调用状态管理，简化前端代码
- 保留现有会话列表 CRUD 管理（`useChatServices` + `ahooks`）
- 鉴权通过 `DefaultChatTransport` 的 `headers` 配置传入 Bearer token

**Non-Goals:**
- 不替换 LangChain agent 本身（保留 `create_agent` + 工具集）
- 不替换会话列表 CRUD API
- 不引入 AI SDK Python 的 `Agent` 类
- 不实现消息持久化的前端缓存/离线支持
- 不实现多轮对话的流式恢复（resumeStream）

## Decisions

### 决策 1：后端协议转换方式 — 参考 vercel-ai-sdk 协议手写转换层

**选择**：在 `chat.py` 中参考 `vercel-ai-sdk` Python 包的 `to_ui_message_stream` 协议格式，手写 LangChain agent stream → UIMessageStream 的转换层。

**否决方案**：
- ❌ 使用 `vercel-ai-sdk` Python 包的 `ai_sdk_ui` adapter — 该 adapter 是为其自有 `Agent` 类设计的，不兼容 LangChain 的 `agent.astream()` 输出格式
- ❌ 使用 `sse-starlette` 的 `EventSourceResponse` — AI SDK `DefaultChatTransport` 期望的是标准 `data: ...\n\n` 格式的 SSE（不带 `event:` 前缀），`sse-starlette` 默认会添加 `event:` 前缀，需要自定义

**理由**：`vercel-ai-sdk` Python 包版本为 `0.0.1.dev10`，API 不稳定且与 LangChain 不兼容。直接参考其协议格式手写转换更可控，且只需处理我们实际使用的几种事件类型。

### 决策 2：前端 Transport — DefaultChatTransport + headers 鉴权

**选择**：使用 `DefaultChatTransport`，通过 `headers` 配置动态传入 Bearer token。

**实现方式**：
```typescript
const chat = useChat({
  id: `chat-${conversationId}`,
  transport: new DefaultChatTransport({
    api: `${baseUrl}/chat/send`,
    headers: () => ({
      Authorization: `Bearer ${tokenManager.getToken()}`,
    }),
    body: { conversation_id: conversationId },
  }),
})
```

**理由**：后端将输出标准 UIMessageStream 格式，无需自定义 Transport。`headers` 支持函数形式，可动态获取 token。

### 决策 3：会话切换 — key 强制重挂载

**选择**：通过 React `key` 属性强制 `useChat` 组件重挂载来切换会话。

**理由**：React hooks 不能条件调用，`useChat` 的 `id` 参数在 hook 创建后不可变。切换会话时需要清空消息和状态，用 `key={conversationId}` 强制重挂载是最简洁可靠的方式。

### 决策 4：历史消息加载 — setMessages 注入

**选择**：会话切换时，从 API 加载历史消息并转换为 `UIMessage` 格式，通过 `useChat` 返回的 `setMessages` 注入。

**实现方式**：将后端 `Message` 转换为 `UIMessage`，文本内容放入 `parts: [{ type: 'text', text: content }]`。

### 决策 5：消息渲染 — 基于 UIMessage.parts 结构化渲染

**选择**：遍历 `UIMessage.parts`，按 part type 分别渲染：`TextUIPart` 用 `ReactMarkdown`、`ToolUIPart` 用 `ToolCallStatus`。

**理由**：AI SDK 的流式更新是结构化的——`TextUIPart.text` 在流式过程中是完整的已解析文本，不存在"不完整 Markdown"问题。每个 part 独立渲染，互不干扰。

### 决策 6：后端 SSE 格式 — 使用 StreamingResponse 手写

**选择**：使用 FastAPI 的 `StreamingResponse` 替换 `sse-starlette` 的 `EventSourceResponse`，手动输出 `data: {json}\n\n` 格式。

**理由**：AI SDK `DefaultChatTransport` 期望标准 SSE 格式（`data: ...\n\n`），不带 `event:` 前缀。`sse-starlette` 会自动添加 `event:` 前缀，与 AI SDK 不兼容。

## Risks / Trade-offs

- **[后端 API 破坏性变更]** → `/api/chat/send` 的 SSE 格式变更，旧版前端将无法解析。Mitigation：前后端同步部署。
- **[vercel-ai-sdk Python 包不稳定]** → 版本 `0.0.1.dev10`，未来 API 可能变更。Mitigation：我们只参考其协议格式，不直接依赖其 adapter 代码。
- **[LangChain agent.astream chunk 与 UIMessageStream 映射不完整]** → 特别是工具调用的增量参数（`tool-input-delta`）可能无法从 LangChain chunk 中获取。Mitigation：如果无法获取增量参数，则使用 `tool-input-available` 直接发送完整参数，跳过 `tool-input-delta`。
- **[useChat key 重挂载开销]** → 每次切换会话都重新创建 hook 实例，可能有短暂闪烁。Mitigation：历史消息通过 `initialMessages` 传入，减少加载延迟。

## Open Questions

1. LangChain `agent.astream(stream_mode="messages")` 在工具调用时是否提供增量参数（`args_delta`）？如果不提供，需要跳过 `tool-input-delta` 事件，直接使用 `tool-input-available` 发送完整参数。
2. `DefaultChatTransport` 的 `body` 参数是否支持在每次 `sendMessage` 时动态更新 `conversation_id`？如果不行，可能需要自定义 Transport 或在 `prepareSendMessagesRequest` 中注入。
