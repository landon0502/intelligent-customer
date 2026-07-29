## Why

当前首页 `/` 仅展示应用名称和欢迎信息，缺乏核心功能。根据 `docs/原型.html` 的产品设计，智能对话是系统的核心能力入口。需要先实现聊天界面的 UI 框架和数据结构，为后续接入真实 AI 接口奠定基础。本次先用假数据完成界面交互，让产品形态可感知、可演示。

## What Changes

- 新增 chat 聊天页面组件，替换首页当前欢迎内容
- 实现会话列表侧栏（260px）：新建会话、会话切换、会话删除、活跃会话高亮
- 实现消息展示区：用户消息（右对齐）和助手消息（左对齐），气泡样式区分
- 集成 Markdown 渲染（支持加粗、斜体、代码、引用块、表格、列表）
- 实现工具调用状态展示（spinner 加载中 → 完成结果）
- 实现流式模拟响应（逐字打字效果）
- 实现输入框交互：textarea 自适应高度，Enter 发送，Shift+Enter 换行
- 使用假数据（mock sessions、mock AI 响应），不实现后端接口

## Capabilities

### New Capabilities

- `chat-conversation`: 智能对话聊天界面，包含会话管理、消息展示、Markdown 渲染、工具调用状态、流式模拟响应和输入交互

### Modified Capabilities

（无修改的 capability；chat 为全新功能，不修改现有 spec）

## Impact

- **代码文件**：新增 `apps/web/app/page.tsx`（改造为 chat 容器）、`apps/web/components/chat/` 目录下的聊天组件、`apps/web/config/mock-chat.ts`（假数据）
- **依赖**：新增 `react-markdown`（Markdown 渲染）、`remark-gfm`（GFM 表格支持）
- **路由**：首页 `/` 改为聊天界面（仍在 AppLayout 内）
- **i18n**：补充 chat 相关翻译键（会话列表、新建会话、输入占位符等）
- **UI 组件库**：复用现有组件（如需要），不修改 UI 包
