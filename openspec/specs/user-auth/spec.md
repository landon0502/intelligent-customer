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
系统 SHALL 提供用户名+密码注册功能，注册成功后自动登录。

#### Scenario: 注册成功
- **WHEN** 用户提交不重复的用户名和有效密码
- **THEN** 系统创建用户记录（默认角色 user），返回 JWT token，前端自动登录并跳转首页

#### Scenario: 用户名已存在
- **WHEN** 用户提交已存在的用户名
- **THEN** 系统返回错误码 30002（USER_ALREADY_EXISTS），前端显示"用户名已存在"提示

#### Scenario: 密码过短
- **WHEN** 用户提交的密码少于 6 位
- **THEN** 前端显示"密码至少 6 位"校验提示，不发送请求

#### Scenario: 两次密码不一致
- **WHEN** 用户在注册表单中两次输入的密码不一致
- **THEN** 前端显示"两次密码不一致"校验提示，不发送请求

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
系统 SHALL 通过 Next.js middleware 保护需要认证的页面路由。

#### Scenario: 未登录访问受保护页面
- **WHEN** 未登录用户访问非 `/login` 页面
- **THEN** middleware 重定向到 `/login`

#### Scenario: 已登录访问登录页
- **WHEN** 已登录用户访问 `/login`
- **THEN** middleware 重定向到首页 `/`

#### Scenario: 已登录访问受保护页面
- **WHEN** 已登录用户访问受保护页面
- **THEN** 正常显示页面内容

### Requirement: 退出登录
系统 SHALL 提供退出登录功能，清除客户端 token。

#### Scenario: 退出登录
- **WHEN** 用户点击退出登录
- **THEN** 前端清除 Cookie 中的 token 和用户状态，跳转到登录页

