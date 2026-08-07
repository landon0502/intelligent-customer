## MODIFIED Requirements

### Requirement: 消息展示
消息区 SHALL 展示当前会话的所有消息。用户消息右对齐、蓝色气泡；助手消息左对齐、白色气泡带边框。助手消息内容 SHALL 基于 `UIMessage.parts` 结构化渲染：`TextUIPart` 通过 `ReactMarkdown` 渲染，`ToolUIPart` 通过 `ToolCallStatus` 组件渲染。流式过程中 Markdown 格式 SHALL 正确渲染，不存在不完整语法导致的显示异常。

#### Scenario: 查看消息
- **WHEN** 用户选择一个有消息的会话
- **THEN** 消息区展示该会话的所有消息，用户和助手消息样式区分

#### Scenario: Markdown 流式渲染
- **WHEN** 助手消息正在流式输出且包含 Markdown 格式（加粗、代码块、表格、列表、引用等）
- **THEN** 消息内容按 Markdown 格式正确渲染，不会因语法不完整而显示异常

#### Scenario: Markdown 完整渲染
- **WHEN** 助手消息流式输出完成且包含 Markdown 格式
- **THEN** 消息内容按 Markdown 格式正确渲染

### Requirement: 工具调用状态展示
当助手消息关联工具调用时，SHALL 基于 `UIMessage.parts` 中的 `ToolUIPart` 渲染工具调用状态。`ToolUIPart.state` 为 `"call"` 时显示 spinner + 描述文字；`state` 为 `"result"` 时显示 ✓ + 摘要。

#### Scenario: 工具调用中
- **WHEN** AI 正在调用工具（如知识库检索），`ToolUIPart.state` 为 `"call"`
- **THEN** 消息区显示 spinner 和工具调用描述

#### Scenario: 工具调用完成
- **WHEN** 工具调用完成，`ToolUIPart.state` 为 `"result"`
- **THEN** spinner 替换为 ✓ 和工具调用结果摘要

### Requirement: 流式模拟响应
用户发送消息后，SHALL 通过 AI SDK `useChat` hook 的流式机制实时展示助手回复。SHALL 支持 `stop()` 中断流式响应，已接收内容保留。

#### Scenario: 流式响应
- **WHEN** 用户发送消息
- **THEN** 助手消息通过 `useChat` 的流式机制实时逐步展示

#### Scenario: 中断流式响应
- **WHEN** 用户在流式响应过程中点击停止按钮
- **THEN** 流式响应中断，已接收的内容保留显示

## REMOVED Requirements

### Requirement: 假数据模拟
**Reason**: 假数据模拟已在之前的迭代中移除，chat 模块已接入真实后端 API
**Migration**: 使用真实后端 API 接口
