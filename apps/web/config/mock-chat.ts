/**
 * 旧版 mock 数据已移除。
 * 聊天功能现已对接后端 SSE 流式接口（services/chat.ts），
 * 会话管理对接 services/conversation.ts，
 * 知识库管理对接 services/knowledge.ts。
 *
 * 此文件保留仅为向后兼容任何可能的外部引用，
 * 新代码请勿引用此文件。
 */

export interface ToolCall {
  name: string;
  display: string;
  status: "calling" | "done";
  summary: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  time: string;
  toolCalls?: ToolCall[];
}

export interface Session {
  id: string;
  title: string;
  time: string;
  messages: Message[];
}
