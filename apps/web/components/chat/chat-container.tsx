"use client";

import { useState, useEffect, useMemo } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import type { UIMessage } from "ai";
import useChatServices from "./useServices";
import { MessageArea } from "./message-area";
import { ChatInput } from "./chat-input";
import { tokenManager } from "@/lib/fetch/token-manager";
import type { DisplayMessage } from "./session-list";

// ========== UIMessage -> DisplayMessage 临时桥接 ==========
// Task 5 将重写 MessageBubble 以原生支持 UIMessage，届时移除此桥接

function uiMessageToDisplayMessage(msg: UIMessage): DisplayMessage {
  // 从 parts 中提取文本内容
  const textParts = msg.parts.filter((p): p is Extract<typeof p, { type: "text" }> => p.type === "text");
  const content = textParts.map((p) => p.text).join("");

  return {
    id: msg.id,
    role: msg.role as "user" | "assistant",
    content,
    time: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }),
  };
}

// ========== ChatContainer ==========

interface ChatContainerProps {
  conversationId: number;
}

export function ChatContainer({ conversationId }: ChatContainerProps) {
  const { loadMessages } = useChatServices();
  const [initialMessages, setInitialMessages] = useState<UIMessage[] | null>(null);

  // 首次加载历史消息
  useEffect(() => {
    let cancelled = false;
    loadMessages(conversationId).then((msgs) => {
      if (!cancelled) {
        setInitialMessages(msgs.length > 0 ? msgs : []);
      }
    });
    return () => { cancelled = true; };
  }, [conversationId]);

  if (initialMessages === null) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-muted-foreground">加载中...</p>
      </div>
    );
  }

  return <ChatInner conversationId={conversationId} initialMessages={initialMessages} />;
}

// ========== ChatInner ==========

function ChatInner({
  conversationId,
  initialMessages,
}: {
  conversationId: number;
  initialMessages: UIMessage[];
}) {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL! + process.env.NEXT_PUBLIC_API_BASE_URL!;

  // 创建 transport，注入鉴权头和 conversation_id
  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: `${baseUrl}/chat/send`,
        headers: (): Record<string, string> => {
          const token = tokenManager.getToken();
          return token ? { Authorization: `Bearer ${token}` } : {};
        },
        body: { conversation_id: conversationId },
      }),
    [baseUrl, conversationId],
  );

  const chat = useChat({
    id: `chat-${conversationId}`,
    transport,
    messages: initialMessages,
  });

  // UIMessage[] -> DisplayMessage[] 临时桥接
  const displayMessages = useMemo(
    () => chat.messages.map(uiMessageToDisplayMessage),
    [chat.messages],
  );

  const isStreaming = chat.status === "streaming" || chat.status === "submitted";

  const handleSend = (text: string) => {
    chat.sendMessage({ text });
  };

  return (
    <>
      <MessageArea messages={displayMessages} />
      <ChatInput onSend={handleSend} disabled={isStreaming} />
    </>
  );
}
