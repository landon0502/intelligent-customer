## Purpose

对 chat-conversation 的增量需求：会话 `updated_at` 随消息更新，支撑会话列表按更新时间倒序。

## ADDED Requirements

### Requirement: 会话更新时间随消息更新
系统 SHALL 在会话中创建新消息时同步更新会话的 `updated_at` 字段，使会话列表可依据最新消息时间倒序展示。

#### Scenario: 发消息后会话时间更新
- **WHEN** 用户在会话中发送一条消息
- **THEN** 该会话的 `updated_at` 更新为最新消息时间

#### Scenario: 会话列表按更新时间倒序
- **WHEN** 用户查看会话列表
- **THEN** 会话按 `updated_at` 倒序排列，最近有消息的会话置顶
