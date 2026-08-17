# user-management Specification

## Purpose
用户管理的后端与前端能力：管理员可查看用户列表、创建新用户（可选角色）并删除用户（受保护规则约束），前端用户管理页接入真实接口，不再使用模拟数据。
## Requirements
### Requirement: 用户列表接口
系统 SHALL 提供 `GET /api/users` 接口，仅管理员可获取全部用户列表；返回每个用户的 id、用户名、角色与创建时间。

#### Scenario: 管理员获取用户列表
- **WHEN** 管理员请求 `GET /api/users`
- **THEN** 系统返回全部用户（id、username、role、created_at）

#### Scenario: 非管理员访问列表
- **WHEN** 普通用户请求 `GET /api/users`
- **THEN** 系统返回无权限错误

### Requirement: 创建用户接口
系统 SHALL 提供 `POST /api/users` 接口，仅管理员可创建用户；请求体含用户名、密码、角色（user/admin，可选，默认 user）。

#### Scenario: 管理员创建用户
- **WHEN** 管理员提交不重复的用户名、有效密码与角色
- **THEN** 系统创建用户并返回新用户信息

#### Scenario: 用户名已存在
- **WHEN** 管理员提交已存在的用户名
- **THEN** 系统返回用户名已存在的错误

#### Scenario: 密码过短
- **WHEN** 管理员提交少于 6 位的密码
- **THEN** 系统返回密码不合法错误

### Requirement: 删除用户接口
系统 SHALL 提供 `DELETE /api/users/{id}` 接口，仅管理员可删除用户；删除受保护规则约束：不能删除当前登录用户自己，不能删除 admin 角色用户。

#### Scenario: 管理员删除普通用户
- **WHEN** 管理员删除一个非自身的普通用户
- **THEN** 系统删除该用户并返回成功

#### Scenario: 删除当前登录用户自己被拒
- **WHEN** 管理员尝试删除当前登录用户自己
- **THEN** 系统返回不能删除当前登录用户的错误

#### Scenario: 删除 admin 角色用户被拒
- **WHEN** 管理员尝试删除 admin 角色用户
- **THEN** 系统返回不能删除管理员用户的错误

#### Scenario: 删除不存在的用户
- **WHEN** 管理员尝试删除不存在的用户 id
- **THEN** 系统返回用户不存在的错误

### Requirement: 前端用户管理页接入真实接口
系统 SHALL 在 Web 端用户管理页（`/users`）接入真实用户管理接口，不再使用模拟数据；展示真实用户列表，支持按用户名搜索（前端过滤）、新增用户（用户名/密码/角色）与删除用户（admin 行删除按钮置灰）。

#### Scenario: 用户列表真实渲染
- **WHEN** 管理员进入 `/users`
- **THEN** 页面展示真实用户列表（含 admin 与已注册用户）

#### Scenario: 新增用户
- **WHEN** 管理员在新增对话框填写用户名、密码并选择角色
- **THEN** 页面调用创建接口，成功后列表刷新并出现新用户

#### Scenario: 删除用户
- **WHEN** 管理员点击非 admin 用户的删除按钮
- **THEN** 页面调用删除接口，成功后列表移除该用户

#### Scenario: admin 行删除按钮置灰
- **WHEN** 管理员查看用户列表中的 admin 角色行
- **THEN** 该行删除按钮置灰不可用

