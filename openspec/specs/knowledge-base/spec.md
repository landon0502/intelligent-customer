# knowledge-base Specification

## Purpose
知识库文档管理与检索的行为规范：上传强化（大小上限与内容校验）、检索接口权限一致化。
## Requirements
### Requirement: 知识库上传大小与内容校验
系统 SHALL 在上传知识库文档时校验文件大小与内容有效性：超过 20MB 的文件拒绝上传；无法解析或内容为空的文档拒绝入库；正常文档成功入库并可检索。

#### Scenario: 超过大小上限拒绝
- **WHEN** 管理员上传超过 20MB 的文档
- **THEN** 系统拒绝上传并返回大小超限错误，不写入知识库

#### Scenario: 无效内容拒绝
- **WHEN** 管理员上传无法解析（损坏）或内容为空的文档
- **THEN** 系统拒绝上传并返回内容无效错误，不写入知识库

#### Scenario: 正常文档上传成功
- **WHEN** 管理员上传合法且可解析的企业文档
- **THEN** 系统成功入库，文档状态为可检索

### Requirement: 知识库检索接口 admin 权限
系统 SHALL 要求知识库检索测试接口 `POST /api/knowledge/query` 仅管理员可访问，与知识库上传、列表、删除接口的权限一致。

#### Scenario: 管理员检索知识库
- **WHEN** 管理员请求 `POST /api/knowledge/query`
- **THEN** 系统执行检索并返回命中结果

#### Scenario: 非管理员检索被拒
- **WHEN** 非管理员请求 `POST /api/knowledge/query`
- **THEN** 系统返回无权限错误（40003），不执行检索

