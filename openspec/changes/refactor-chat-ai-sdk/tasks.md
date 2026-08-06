## 1. 后端 UIMessageStream 协议转换

- [ ] 1.1 研究 LangChain `agent.astream(stream_mode="messages")` 的 chunk 格式，确认工具调用增量参数是否可用
- [ ] 1.2 实现 LangChain chunk → UIMessageStream 事件转换函数（`to_ui_message_stream`）：处理文本 delta、工具调用 start/available、工具结果 available
- [ ] 1.3 重写 `chat.py` 的 `chat_stream` 端点：用 `StreamingResponse` 替换 `EventSourceResponse`，输出标准 SSE 格式（`data: {json}\n\n`），使用转换函数输出 UIMessageStream 事件
- [ ] 1.4 验证后端 SSE 输出格式：确认 `text-delta`、`tool-input-start`、`tool-input-available`、`tool-output-available`、`finish` 事件正确输出

## 2. 前端 useChat hook 集成

- [ ] 2.1 创建 `useChatWithSession` hook：封装 `useChat` + `DefaultChatTransport`，配置 API URL、headers 鉴权、body 参数（conversation_id）
- [ ] 2.2 重构 `chat-page.tsx`：用 `useChatWithSession` 替换手写 SSE 流式处理（`sendChat`/`onMessage`/`onDone`/`onError`），会话切换通过 `key` 重挂载
- [ ] 2.3 实现历史消息转换：将后端 `Message` 转换为 `UIMessage` 格式，通过 `setMessages` 注入

## 3. 消息渲染重构

- [ ] 3.1 重构 `message-bubble.tsx`：基于 `UIMessage.parts` 遍历渲染，`TextUIPart` 用 `ReactMarkdown`，`ToolUIPart` 用 `ToolCallStatus`；移除 `preprocessStreamingMarkdown` 补丁函数
- [ ] 3.2 适配 `tool-call-status.tsx`：接收 `ToolUIPart` 的 `state`/`toolName`/`args`/`result` 替代现有 `ToolCall` 接口

## 4. 清理与整合

- [ ] 4.1 删除或大幅简化 `services/chat.ts`（`sendChatStream` 不再需要）
- [ ] 4.2 简化 `useServices.ts`：移除 `sendChat`、`createLocalAssistantMessage` 等不再需要的函数，保留会话 CRUD
- [ ] 4.3 更新 `chat-input.tsx`：使用 `useChat` 的 `input`/`setInput` 和 `sendMessage` 替代 `onSend` prop

## 5. 端到端验证

- [ ] 5.1 验证流式 Markdown 渲染：发送包含加粗、代码块、表格、列表的消息，确认流式过程中正确渲染
- [ ] 5.2 验证工具调用状态：触发知识库检索等工具，确认调用中和完成状态正确显示
- [ ] 5.3 验证会话切换：切换会话后历史消息正确加载，新消息正常发送和流式接收
- [ ] 5.4 验证鉴权：确认 Bearer token 正确注入请求头
