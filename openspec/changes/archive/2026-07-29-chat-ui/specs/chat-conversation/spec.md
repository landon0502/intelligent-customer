## ADDED Requirements

### Requirement: 聊天页面布局
首页 `/` SHALL 展示聊天界面，采用三栏布局：左侧会话列表（260px）+ 右侧聊天主区（消息区 + 输入区）。聊天界面 SHALL 在 AppLayout 内渲染。

#### Scenario: 已认证用户访问首页
- **WHEN** 已认证用户访问 `/`
- **THEN** 页面展示会话列表侧栏和聊天主区

### Requirement: 会话列表管理
会话列表侧栏 SHALL 展示所有会话项，每项包含会话标题和时间。SHALL 提供"新建会话"按钮。点击会话项切换当前对话。hover 会话项时显示删除按钮。当前活跃会话 SHALL 有高亮样式。

#### Scenario: 查看会话列表
- **WHEN** 用户查看聊天界面
- **THEN** 左侧展示会话列表，包含预设的假数据会话

#### Scenario: 新建会话
- **WHEN** 用户点击"新建会话"按钮
- **THEN** 创建一个新的空会话，自动切换到该会话

#### Scenario: 切换会话
- **WHEN** 用户点击另一个会话项
- **THEN** 右侧消息区切换为该会话的消息内容

#### Scenario: 删除会话
- **WHEN** 用户 hover 会话项并点击删除按钮
- **THEN** 该会话从列表中移除

### Requirement: 消息展示
消息区 SHALL 展示当前会话的所有消息。用户消息右对齐、蓝色气泡；助手消息左对齐、白色气泡带边框。助手消息内容 SHALL 通过 Markdown 渲染。

#### Scenario: 查看消息
- **WHEN** 用户选择一个有消息的会话
- **THEN** 消息区展示该会话的所有消息，用户和助手消息样式区分

#### Scenario: Markdown 渲染
- **WHEN** 助手消息包含 Markdown 格式（加粗、表格、列表、引用等）
- **THEN** 消息内容按 Markdown 格式渲染

### Requirement: 工具调用状态展示
当助手消息关联工具调用时，SHALL 在消息气泡上方展示工具调用状态。调用中显示 spinner + 描述文字；完成后显示 ✓ + 摘要。

#### Scenario: 工具调用中
- **WHEN** AI 正在调用工具（如知识库检索）
- **THEN** 消息区显示 spinner 和"正在调用工具..."描述

#### Scenario: 工具调用完成
- **WHEN** 工具调用完成
- **THEN** spinner 替换为 ✓ 和工具调用摘要

### Requirement: 流式模拟响应
用户发送消息后，SHALL 模拟 AI 流式响应，逐字打字效果展示助手回复。

#### Scenario: 流式响应
- **WHEN** 用户发送消息
- **THEN** 助手消息以逐字打字效果逐步展示

### Requirement: 输入框交互
输入区 SHALL 包含 textarea 和发送按钮。Enter 发送消息，Shift+Enter 换行。textarea 自适应高度（40px-120px）。空消息不可发送。

#### Scenario: Enter 发送消息
- **WHEN** 用户在输入框中输入内容后按 Enter
- **THEN** 消息发送，输入框清空

#### Scenario: Shift+Enter 换行
- **WHEN** 用户按 Shift+Enter
- **THEN** 输入框内换行，不发送消息

#### Scenario: 空消息不可发送
- **WHEN** 输入框为空或仅含空白字符
- **THEN** 发送按钮禁用，点击无效果

### Requirement: 假数据模拟
SHALL 使用假数据提供预设会话和模拟 AI 响应。不实现后端 API 接口。

#### Scenario: 预设会话数据
- **WHEN** 用户首次进入聊天界面
- **THEN** 展示 3 个预设会话（退货政策咨询、订单查询、商品咨询），每个会话包含历史消息

#### Scenario: 模拟 AI 响应
- **WHEN** 用户发送消息
- **THEN** 根据消息内容关键词匹配返回模拟响应（问候、退货/售后→知识库检索、订单→订单查询、商品→商品信息）
