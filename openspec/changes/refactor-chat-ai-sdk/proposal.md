## Why

当前 web chat 模块使用手写的 SSE 流式处理逻辑（`sendChatStream` + 逐 chunk 拼接字符串），导致流式 Markdown 渲染异常——不完整的 Markdown 语法结构（未闭合的代码围栏、加粗/斜体标记等）无法被 `ReactMarkdown` 正确解析，只有刷新后才能正常显示。引入 Vercel AI SDK 的 `useChat` hook 可以从根本上解决此问题：AI SDK 的 `UIMessage.parts` 是结构化的消息部件，不存在"不完整 Markdown"解析问题，同时内置了工具调用状态管理、流式状态追踪和停止/重试能力。

## What Changes

- **BREAKING** 后端 `/api/chat/send` SSE 输出格式从自定义事件（`event: message`/`event: tool_call`/`event: tool_result`）改为 AI SDK UIMessageStream 协议（`data: {type: "text-delta", ...}` 等）
- 前端用 `@ai-sdk/react` 的 `useChat` hook 替换手写 SSE 流式处理逻辑（`sendChatStream`）
- 前端用 `UIMessage.parts` 结构化渲染替换 `ReactMarkdown` 直接解析原始拼接字符串
- 前端工具调用状态展示改用 `ToolUIPart` 的 `state` 字段（`call`/`partial-call`/`result`）
- 前端移除 `preprocessStreamingMarkdown` 补丁函数（不再需要）
- 后端添加 `vercel-ai-sdk` Python 包依赖，参考其协议格式手写 LangChain → UIMessageStream 转换层
- 前端鉴权通过 `DefaultChatTransport` 的 `headers` 配置传入 Bearer token

## Capabilities

### New Capabilities
- `chat-ai-sdk-streaming`: AI SDK UIMessageStream 协议的流式聊天能力，包括后端协议转换层和前端 useChat hook 集成

### Modified Capabilities
- `chat-conversation`: 流式响应方式从手写 SSE 逐 chunk 拼接改为 AI SDK UIMessageStream 协议；工具调用状态管理从手写 ToolCall 数组改为 ToolUIPart；消息渲染从 ReactMarkdown 直接解析原始字符串改为基于 UIMessage.parts 结构化渲染

## Impact

- **后端**：`apps/service/api/chat.py` — 重写 SSE 输出格式；新增 `vercel-ai-sdk` Python 依赖
- **前端**：`apps/web/components/chat/` — chat-page.tsx、message-bubble.tsx、useServices.ts 重构；删除 `apps/web/services/chat.ts`（或大幅简化）
- **前端**：`apps/web/components/chat/tool-call-status.tsx` — 适配 ToolUIPart 状态
- **依赖**：后端新增 `vercel-ai-sdk` Python 包；前端已有 `@ai-sdk/react@4.0.40` 和 `ai@7.0.37`
- **API 兼容性**：`/api/chat/send` 的 SSE 格式变更，旧版前端将无法解析新格式
