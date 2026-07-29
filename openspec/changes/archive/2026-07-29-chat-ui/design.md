## Context

当前首页仅展示欢迎信息。根据 `docs/原型.html`，聊天界面是系统的核心交互入口，需要实现包含会话列表、消息展示、输入交互的完整 UI。本次使用假数据，不接入真实 AI 后端。

## Goals / Non-Goals

**Goals:**
- 实现 chat 聊天界面完整 UI（会话列表 + 消息区 + 输入框）
- 消息支持 Markdown 渲染（加粗、斜体、代码、引用、表格、列表）
- 工具调用状态展示（spinner → 完成结果）
- 流式模拟响应（逐字打字效果）
- 会话管理（新建、切换、删除）
- 输入框自适应高度，Enter 发送 / Shift+Enter 换行

**Non-Goals:**
- 不实现后端 API 接口
- 不实现真实 AI 对话能力
- 不实现会话持久化（刷新后数据丢失可接受）
- 不实现文件上传或图片消息

## Decisions

1. **页面结构**：首页 `/` 替换为聊天界面，在 AppLayout 内渲染。聊天界面采用三栏布局：会话列表（260px）+ 聊天主区（消息区 + 输入区）。这与原型一致。

2. **组件拆分**：
   - `ChatPage` — 页面容器，管理会话状态
   - `SessionList` — 会话列表侧栏
   - `MessageArea` — 消息展示区
   - `MessageBubble` — 单条消息气泡（用户/助手样式区分）
   - `ChatInput` — 输入框 + 发送按钮
   - `ToolCallStatus` — 工具调用状态展示
   所有组件放在 `apps/web/components/chat/` 目录下

3. **状态管理**：使用 React useState 管理当前会话 ID 和消息列表。假数据定义在 `apps/web/config/mock-chat.ts`，包含 3 个预设会话和模拟 AI 响应函数。后续接入真实 API 时替换为 zustand store 或 API 调用。

4. **Markdown 渲染**：使用 `react-markdown` + `remark-gfm` 插件。助手消息内容通过 Markdown 渲染，用户消息保持纯文本（仅换行转 `<br>`）。这与原型行为一致。

5. **流式模拟**：使用 `setTimeout` + `requestAnimationFrame` 实现逐字打字效果，每 30ms 输出 2 个字符。模拟工具调用时先展示 spinner（1.2s），完成后展示结果标签，然后开始流式输出 AI 回复。

6. **数据结构**：
   - Session: `{ id, title, time, messages[] }`
   - Message: `{ role: 'user' | 'assistant', content, time, toolCalls?: ToolCall[] }`
   - ToolCall: `{ name, display, status: 'calling' | 'done', summary }`

7. **输入交互**：textarea 使用 `onKeyDown` 检测 Enter（无 Shift 则发送）和 Shift+Enter（换行）。textarea 设置 `minHeight: 40px, maxHeight: 120px`，通过 `scrollHeight` 动态调整高度。

## Risks / Trade-offs

- [react-markdown 包体积较大 (~40KB)] → 仅在助手消息渲染时使用，用户消息保持纯文本
- [假数据与真实数据结构可能不一致] → 后续接入 API 时需要调整 mock 函数，但 UI 组件和数据结构可复用
- [流式模拟与真实流式响应机制不同] → 后续需替换为 SSE/WebSocket，但 UI 逐字渲染逻辑可复用
