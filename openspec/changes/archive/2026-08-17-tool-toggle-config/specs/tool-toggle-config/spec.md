## Purpose

工具启停配置能力：管理员可查看全部 Agent 工具及其启用状态、启停任意非兜底工具，Agent 仅绑定启用状态的工具（禁用工具的提示词描述同步移除），切换即时生效。`transfer_human`、`clarify` 为兜底工具，不允许禁用。

## ADDED Requirements

### Requirement: 工具启停配置存储
系统 SHALL 在 `system_configs` 表中按 `tools` 分类存储每个 Agent 工具的启停状态（键为工具名，值为 `enabled`/`disabled`），默认全部启用，并随系统配置统一读写。

#### Scenario: 默认全部启用
- **WHEN** 系统初始化 `tools` 分类配置
- **THEN** 全部 6 个工具均为 `enabled`

#### Scenario: 修改启停状态持久化
- **WHEN** 管理员将某工具切换为 `disabled` 或恢复为 `enabled`
- **THEN** 系统将该工具的启停状态持久化到 `tools` 分类配置

### Requirement: Agent 动态绑定启用工具
系统 SHALL 在创建 Agent 时按 `tools` 分类配置过滤工具集，仅绑定启用状态的工具；禁用某工具时，Agent 系统提示词中的对应工具描述同步移除，避免 Agent 调用未绑定工具。

#### Scenario: 仅绑定启用工具
- **WHEN** 某工具被禁用后创建 Agent
- **THEN** Agent 仅绑定其余启用状态的工具，不再绑定被禁用工具

#### Scenario: 禁用工具后提示词同步
- **WHEN** 某工具被禁用
- **THEN** Agent 系统提示词中不包含该工具的描述与调用引导

#### Scenario: 启停切换即时生效
- **WHEN** 管理员切换某工具启停状态
- **THEN** 现有 Agent 实例通过热更新即时重新绑定，无需重启服务

### Requirement: 工具列表接口
系统 SHALL 提供 `GET /api/tools` 接口，仅管理员可获取全部 Agent 工具及其启用状态。

#### Scenario: 管理员获取工具列表
- **WHEN** 管理员请求 `GET /api/tools`
- **THEN** 系统返回全部工具（名称、描述、启用状态）

#### Scenario: 非管理员访问列表
- **WHEN** 非管理员请求 `GET /api/tools`
- **THEN** 系统返回无权限错误

### Requirement: 工具启停接口
系统 SHALL 提供 `PATCH /api/tools/{name}` 接口，仅管理员可切换工具启停状态；`transfer_human`、`clarify` 为兜底工具，不允许禁用。

#### Scenario: 管理员启停工具
- **WHEN** 管理员对非兜底工具提交 `enabled`/`disabled` 状态
- **THEN** 系统更新该工具启停状态并即时生效，返回更新后的状态

#### Scenario: 禁用兜底工具被拒
- **WHEN** 管理员尝试禁用 `transfer_human` 或 `clarify`
- **THEN** 系统返回兜底工具不可禁用的错误，状态不变

#### Scenario: 未知工具名
- **WHEN** 管理员对不存在的工具名提交启停操作
- **THEN** 系统返回工具不存在的错误

### Requirement: 前端工具管理页对接
系统 SHALL 在 Web 端工具管理页（`/tools`）对接工具列表与启停接口，不再使用模拟数据；展示真实工具列表与启用状态，开关切换调用接口并刷新，兜底工具开关置灰不可操作。

#### Scenario: 工具列表真实渲染
- **WHEN** 管理员进入 `/tools`
- **THEN** 页面展示真实工具列表（含名称、触发场景与启用状态）

#### Scenario: 切换启停
- **WHEN** 管理员切换非兜底工具的开关
- **THEN** 页面调用启停接口，成功后刷新列表并反映新状态

#### Scenario: 兜底工具开关置灰
- **WHEN** 管理员查看 `transfer_human` 或 `clarify` 行
- **THEN** 该行开关置灰不可操作
