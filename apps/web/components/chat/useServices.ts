import { useRequest } from "ahooks";
import { useMemo } from "react";
import {
  getConversationsApi,
  createConversationApi,
  deleteConversationApi,
  getConversationMessagesApi,
  type Conversation,
  type Message,
} from "@/services/conversation";
import { sendChatStream, type ToolCallEvent, type ToolResultEvent } from "@/services/chat";
import type { ToolCall } from "./tool-call-status";

// ========== 展示类型 ==========

export interface DisplayMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  time: string;
  toolCalls?: ToolCall[];
}

export interface DisplaySession {
  id: number;
  title: string;
  time: string;
  messages: DisplayMessage[];
}

// ========== 工具函数 ==========

function formatTime(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return dateStr;
  }
}

function formatDateTime(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

let nextMsgId = 100;
function genMsgId() {
  return `msg-${nextMsgId++}`;
}

/** 将后端 Conversation 转换为 DisplaySession */
function toDisplaySession(c: Conversation): DisplaySession {
  return {
    id: c.id,
    title: c.title,
    time: formatDateTime(c.updated_at),
    messages: [],
  };
}

/** 将后端 Message 转换为 DisplayMessage */
function toDisplayMessage(m: Message): DisplayMessage {
  return {
    id: `db-${m.id}`,
    role: m.role as "user" | "assistant",
    content: m.content,
    time: formatTime(m.created_at),
  };
}

// ========== useServices ==========

export default function useChatServices() {
  // 获取会话列表
  const conversationsControl = useRequest(getConversationsApi, { manual: true });
  const { data: convData } = conversationsControl;
  const sessions = useMemo(() => (convData?.data ?? []).map(toDisplaySession), [convData]);

  // 获取会话消息
  const messagesControl = useRequest(getConversationMessagesApi, { manual: true });
  const { data: msgData } = messagesControl;
  const messages = useMemo(() => (msgData?.data ?? []).map(toDisplayMessage), [msgData]);

  // 创建会话
  const createControl = useRequest(createConversationApi, { manual: true });

  // 删除会话
  const deleteControl = useRequest(deleteConversationApi, { manual: true });

  /** 创建新会话并返回 DisplaySession */
  async function createSession(title: string): Promise<DisplaySession | null> {
    try {
      const res = await createControl.runAsync(title);
      const newConv = res.data;
      return {
        id: newConv.id,
        title: newConv.title,
        time: formatDateTime(new Date().toISOString()),
        messages: [],
      };
    } catch {
      return null;
    }
  }

  /** 删除会话 */
  async function removeSession(conversationId: number): Promise<boolean> {
    try {
      await deleteControl.runAsync(conversationId);
      return true;
    } catch {
      return false;
    }
  }

  /** 加载会话消息 */
  async function loadMessages(conversationId: number): Promise<DisplayMessage[]> {
    try {
      const res = await messagesControl.runAsync(conversationId);
      return res.data.map(toDisplayMessage);
    } catch {
      return [];
    }
  }

  /** 发送聊天消息（SSE 流式） */
  function sendChat(
    params: { conversation_id: number; message: string },
    onMessage: (chunk: string) => void,
    onDone: () => void,
    onError: (error: Error) => void,
    onToolCall?: (toolCall: ToolCallEvent) => void,
    onToolResult?: (result: ToolResultEvent) => void,
  ) {
    sendChatStream(params, onMessage, onDone, onError, onToolCall, onToolResult);
  }

  /** 创建一条本地展示用的用户消息 */
  function createLocalUserMessage(content: string): DisplayMessage {
    return {
      id: genMsgId(),
      role: "user",
      content,
      time: formatTime(new Date().toISOString()),
    };
  }

  /** 创建一条本地展示用的空助手消息 */
  function createLocalAssistantMessage(): DisplayMessage {
    return {
      id: genMsgId(),
      role: "assistant",
      content: "",
      time: formatTime(new Date().toISOString()),
    };
  }

  return {
    // 会话列表
    conversationsControl,
    sessions,
    // 消息
    messagesControl,
    messages,
    loadMessages,
    // 创建
    createControl,
    createSession,
    // 删除
    deleteControl,
    removeSession,
    // 聊天
    sendChat,
    createLocalUserMessage,
    createLocalAssistantMessage,
  };
}
