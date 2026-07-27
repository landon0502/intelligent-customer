## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: 登录页跳转注册
登录页 SHALL 提供跳转到注册页的链接。

#### Scenario: 从登录页跳转注册
- **WHEN** 用户在登录页面点击"没有账户？注册"链接
- **THEN** 页面跳转到 `/register`
