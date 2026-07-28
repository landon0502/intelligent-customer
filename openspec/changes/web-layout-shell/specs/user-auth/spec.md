## MODIFIED Requirements

### Requirement: 退出登录
系统 SHALL 提供退出登录功能，清除客户端 token。退出登录入口 SHALL 位于 Sidebar 底部用户信息区域。

#### Scenario: 退出登录
- **WHEN** 用户在 Sidebar 底部点击"退出登录"
- **THEN** 前端清除 Cookie 中的 token 和用户状态，跳转到登录页

## ADDED Requirements

### Requirement: Layout 读取用户信息用于菜单和展示
App Shell Layout SHALL 从 auth store 读取当前用户的 `username` 和 `role`，用于 Sidebar 用户信息展示和菜单角色过滤。

#### Scenario: Sidebar 展示用户名和角色
- **WHEN** 已认证用户查看 Sidebar 底部
- **THEN** 显示 `user.username` 和 `user.role`（管理员/普通用户）

#### Scenario: 菜单根据角色过滤
- **WHEN** auth store 中 `user.role` 为 `admin`
- **THEN** Sidebar 渲染所有菜单项（含管理分组）

#### Scenario: 普通用户菜单过滤
- **WHEN** auth store 中 `user.role` 为 `user`
- **THEN** Sidebar 仅渲染无 `roles` 限制或 `roles` 包含 `user` 的菜单项
