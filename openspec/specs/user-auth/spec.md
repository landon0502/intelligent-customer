# user-auth Specification

## Purpose
TBD - created by archiving change login-auth-flow. Update Purpose after archive.
## Requirements
### Requirement: 用户登录
系统 SHALL 提供用户名+密码登录功能，验证通过后返回 JWT access token。

#### Scenario: 登录成功
- **WHEN** 用户提交有效的用户名和密码
- **THEN** 系统返回 JWT token，前端将 token 存入 Cookie，跳转到首页

#### Scenario: 密码错误
- **WHEN** 用户提交有效用户名但密码错误
- **THEN** 系统返回错误码 30001（INVALID_CREDENTIALS），前端显示"用户名或密码错误"提示

#### Scenario: 用户不存在
- **WHEN** 用户提交不存在的用户名
- **THEN** 系统返回错误码 30003（USER_NOT_FOUND），前端显示"用户名或密码错误"提示（不暴露用户是否存在）

#### Scenario: 表单校验失败
- **WHEN** 用户提交空用户名或空密码
- **THEN** 前端显示表单校验错误，不发送请求

### Requirement: 用户注册
系统 SHALL 提供独立的注册页面 `/register`，用户通过用户名+密码注册，注册成功后自动登录。

#### Scenario: 注册成功
- **WHEN** 用户在 `/register` 页面提交不重复的用户名和有效密码
- **THEN** 系统创建用户记录（默认角色 user），返回 JWT token，前端自动登录并跳转首页

#### Scenario: 用户名已存在
- **WHEN** 用户在 `/register` 页面提交已存在的用户名
- **THEN** 系统返回错误码 30002（USER_ALREADY_EXISTS），前端显示"用户名已存在"提示

#### Scenario: 密码过短
- **WHEN** 用户提交的密码少于 6 位
- **THEN** 前端显示"密码至少 6 位"校验提示，不发送请求

#### Scenario: 两次密码不一致
- **WHEN** 用户在注册表单中两次输入的密码不一致
- **THEN** 前端显示"两次密码不一致"校验提示，不发送请求

#### Scenario: 跳转到登录页
- **WHEN** 用户在注册页面点击"已有账户？登录"链接
- **THEN** 页面跳转到 `/login`

### Requirement: 获取当前用户信息
系统 SHALL 提供接口返回当前登录用户的信息。

#### Scenario: 已登录用户获取信息
- **WHEN** 已登录用户请求 `/api/auth/me`
- **THEN** 系统返回用户信息（id、username、role）

#### Scenario: Token 无效或过期
- **WHEN** 请求携带无效或过期的 token
- **THEN** 系统返回 401 状态码，前端清除 token 并跳转登录页

### Requirement: JWT Token 校验
系统 SHALL 使用 JWT 对受保护接口进行身份验证。

#### Scenario: 有效 Token 请求
- **WHEN** 请求携带有效的 JWT token
- **THEN** 系统解析 token 获取用户信息，正常处理请求

#### Scenario: Token 过期
- **WHEN** 请求携带过期的 JWT token
- **THEN** 系统返回 401 状态码，前端清除 token 并跳转登录页

#### Scenario: 无 Token 请求受保护接口
- **WHEN** 请求未携带 token 访问受保护接口
- **THEN** 系统返回 401 状态码

### Requirement: 前端路由守卫
系统 SHALL 通过 Next.js middleware 保护需要认证的页面路由，并放行 `/login` 和 `/register` 页面。

#### Scenario: 未登录访问受保护页面
- **WHEN** 未登录用户访问非 `/login` 和 `/register` 页面
- **THEN** middleware 重定向到 `/login`

#### Scenario: 已登录访问登录页
- **WHEN** 已登录用户访问 `/login`
- **THEN** middleware 重定向到首页 `/`

#### Scenario: 已登录访问注册页
- **WHEN** 已登录用户访问 `/register`
- **THEN** middleware 重定向到首页 `/`

#### Scenario: 未登录访问注册页
- **WHEN** 未登录用户访问 `/register`
- **THEN** 正常显示注册页面

#### Scenario: 已登录访问受保护页面
- **WHEN** 已登录用户访问受保护页面
- **THEN** 正常显示页面内容

### Requirement: 退出登录
系统 SHALL 提供退出登录功能，清除客户端 token。退出登录入口 SHALL 位于 Sidebar 底部用户信息区域。

#### Scenario: 退出登录
- **WHEN** 用户在 Sidebar 底部点击"退出登录"
- **THEN** 前端清除 Cookie 中的 token 和用户状态，跳转到登录页

### Requirement: 登录页跳转注册
登录页 SHALL 提供跳转到注册页的链接。

#### Scenario: 从登录页跳转注册
- **WHEN** 用户在登录页面点击"没有账户？注册"链接
- **THEN** 页面跳转到 `/register`

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

