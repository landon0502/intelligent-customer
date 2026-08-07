## ADDED Requirements

### Requirement: 后端 UIMessageStream 协议输出
后端 `/api/chat/send` 端点 SHALL 输出符合 AI SDK UIMessageStream 协议的 SSE 流。SSE 事件 SHALL 使用标准 `data: {json}\n\n` 格式（不使用 `event:` 前缀）。SHALL 支持以下事件类型：`start`、`start-step`、`text-start`、`text-delta`、`text-end`、`tool-input-start`、`tool-input-available`、`tool-output-available`、`finish-step`、`finish`。

#### Scenario: 文本流式输出
- **WHEN** LangChain agent 产生文本内容 chunk
- **THEN** 后端输出 `text-delta` 事件，包含 `id` 和 `delta` 字段

#### Scenario: 工具调用输出
- **WHEN** LangChain agent 发起工具调用
- **THEN** 后端先输出 `tool-input-start` 事件（包含 `toolCallId` 和 `toolName`），再输出 `tool-input-available` 事件（包含完整 `input` 参数）

#### Scenario: 工具结果输出
- **WHEN** 工具执行完成返回结果
- **THEN** 后端输出 `tool-output-available` 事件（包含 `toolCallId` 和 `output`）

#### Scenario: 流结束
- **WHEN** agent 流式输出完成
- **THEN** 后端输出 `finish` 事件，`finishReason` 为 `"stop"`

### Requirement: 前端 useChat hook 集成
前端 SHALL 使用 `@ai-sdk/react` 的 `useChat` hook 管理聊天消息流和流式状态。SHALL 使用 `DefaultChatTransport` 连接后端。SHALL 通过 `headers` 配置动态传入 Bearer token 进行鉴权。

#### Scenario: 发送消息
- **WHEN** 用户输入消息并提交
- **THEN** `useChat` 的 `sendMessage` 方法发送请求，后端响应通过 `DefaultChatTransport` 解析为 `UIMessage` 更新

#### Scenario: 流式状态追踪
- **WHEN** 消息正在流式响应
- **THEN** `useChat` 的 `status` 字段为 `"streaming"`

#### Scenario: 流式完成
- **WHEN** 流式响应结束
- **THEN** `useChat` 的 `status` 字段变为 `"ready"`

#### Scenario: 鉴权 token 注入
- **WHEN** `useChat` 发送请求
- **THEN** 请求头包含 `Authorization: Bearer <token>`，token 从 `tokenManager` 动态获取

### Requirement: 基于 UIMessage.parts 结构化渲染
助手消息 SHALL 基于 `UIMessage.parts` 结构化渲染，遍历 parts 数组按类型分别渲染。`TextUIPart` SHALL 使用 `ReactMarkdown` 渲染。`ToolUIPart` SHALL 使用 `ToolCallStatus` 组件渲染。

#### Scenario: 文本 part 渲染
- **WHEN** `UIMessage.parts` 包含 `TextUIPart`
- **THEN** 该 part 的 `text` 内容通过 `ReactMarkdown` 渲染为格式化 HTML

#### Scenario: 工具调用 part 渲染
- **WHEN** `UIMessage.parts` 包含 `ToolUIPart` 且 `state` 为 `"call"`
- **THEN** 显示 spinner 和工具调用描述

#### Scenario: 工具结果 part 渲染
- **WHEN** `UIMessage.parts` 包含 `ToolUIPart` 且 `state` 为 `"result"`
- **THEN** 显示 ✓ 和工具调用结果摘要

### Requirement: 会话切换 key 重挂载
切换会话时 SHALL 通过 React `key` 属性强制 `useChat` 组件重挂载。切换后的 `useChat` 实例 SHALL 通过 `setMessages` 注入从 API 加载的历史消息（转换为 `UIMessage` 格式）。

#### Scenario: 切换会话
- **WHEN** 用户点击另一个会话项
- **THEN** `useChat` 组件因 `key` 变化而重挂载，新实例加载并显示目标会话的历史消息

#### Scenario: 历史消息格式转换
- **WHEN** 从 API 加载历史消息
- **THEN** 后端 `Message` 对象转换为 `UIMessage`，`content` 映射为 `parts: [{ type: 'text', text: content }]`
