"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import useChatServices, { type DisplaySession, type DisplayMessage } from "./useServices";
import { SessionList } from "./session-list";
import { MessageArea } from "./message-area";
import { ChatInput } from "./chat-input";
import type { ToolCall } from "./tool-call-status";

export function ChatPage() {
  const t = useTranslations("chat");
  const {
    conversationsControl,
    sessions: apiSessions,
    createSession,
    removeSession,
    loadMessages,
    sendChat,
    createLocalUserMessage,
    createLocalAssistantMessage,
  } = useChatServices();

  const [localSessions, setLocalSessions] = useState<DisplaySession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const [sending, setSending] = useState(false);

  // 会话列表加载完成时同步到本地状态
  useEffect(() => {
    if (apiSessions.length > 0) {
      setLocalSessions((prev) => {
        // 合并：API 返回的会话 + 本地新增消息
        return apiSessions.map((apiS) => {
          const local = prev.find((l) => l.id === apiS.id);
          return local ? { ...apiS, messages: local.messages } : apiS;
        });
      });
      // 自动选中第一个
      if (!currentSessionId) {
        const first = apiSessions[0]!;
        setCurrentSessionId(first.id);
        handleLoadMessages(first.id);
      }
    }
  }, [apiSessions]);

  // 页面加载时获取会话列表
  useEffect(() => {
    conversationsControl.run();
  }, []);

  async function handleLoadMessages(conversationId: number) {
    const msgs = await loadMessages(conversationId);
    setLocalSessions((prev) =>
      prev.map((s) =>
        s.id === conversationId ? { ...s, messages: msgs } : s,
      ),
    );
  }

  const currentSession = localSessions.find((s) => s.id === currentSessionId) ?? null;

  const handleSelectSession = useCallback((id: number) => {
    setCurrentSessionId(id);
    handleLoadMessages(id);
  }, []);

  const handleNewSession = useCallback(async () => {
    const newSession = await createSession(t("newSession"));
    if (!newSession) return;
    setLocalSessions((prev) => [newSession, ...prev]);
    setCurrentSessionId(newSession.id);
  }, [t, createSession]);

  const handleDeleteSession = useCallback(
    async (id: number) => {
      const ok = await removeSession(id);
      if (!ok) return;
      setLocalSessions((prev) => {
        const next = prev.filter((s) => s.id !== id);
        if (id === currentSessionId) {
          const newId = next[0]?.id ?? null;
          setCurrentSessionId(newId);
          if (newId) handleLoadMessages(newId);
        }
        return next;
      });
    },
    [currentSessionId, removeSession],
  );

  const handleSendMessage = useCallback(
    (text: string) => {
      if (!currentSessionId || sending) return;

      const userMsg = createLocalUserMessage(text);
      const assistantMsg = createLocalAssistantMessage();
      const assistantId = assistantMsg.id;

      // 添加用户消息和空的助手消息
      setLocalSessions((prev) =>
        prev.map((s) => {
          if (s.id !== currentSessionId) return s;
          return { ...s, messages: [...s.messages, userMsg, assistantMsg] };
        }),
      );

      setSending(true);

      sendChat(
        { conversation_id: currentSessionId, message: text },
        // onMessage
        (chunk: string) => {
          setLocalSessions((prev) =>
            prev.map((s) => {
              if (s.id !== currentSessionId) return s;
              return {
                ...s,
                messages: s.messages.map((m: DisplayMessage) => {
                  if (m.id !== assistantId) return m;
                  return { ...m, content: m.content + chunk };
                }),
              };
            }),
          );
        },
        // onDone
        () => {
          setSending(false);
        },
        // onError
        (error: Error) => {
          setSending(false);
          setLocalSessions((prev) =>
            prev.map((s) => {
              if (s.id !== currentSessionId) return s;
              return {
                ...s,
                messages: s.messages.map((m: DisplayMessage) => {
                  if (m.id !== assistantId) return m;
                  return { ...m, content: m.content || `⚠️ ${error.message}` };
                }),
              };
            }),
          );
        },
        // onToolCall — LLM 决定调用工具，显示"调用中"状态
        (toolCall) => {
          const newToolCall: ToolCall = {
            name: toolCall.name,
            display: `🔧 调用工具：${toolCall.name}(${Object.entries(toolCall.args).map(([k, v]) => `${k}="${v}"`).join(", ")})`,
            status: "calling",
            summary: "",
          };
          setLocalSessions((prev) =>
            prev.map((s) => {
              if (s.id !== currentSessionId) return s;
              return {
                ...s,
                messages: s.messages.map((m: DisplayMessage) => {
                  if (m.id !== assistantId) return m;
                  return { ...m, toolCalls: [...(m.toolCalls ?? []), newToolCall] };
                }),
              };
            }),
          );
        },
        // onToolResult — 工具执行完成，更新为"已完成"状态
        (result) => {
          setLocalSessions((prev) =>
            prev.map((s) => {
              if (s.id !== currentSessionId) return s;
              return {
                ...s,
                messages: s.messages.map((m: DisplayMessage) => {
                  if (m.id !== assistantId) return m;
                  const toolCalls = (m.toolCalls ?? []).map((tc: ToolCall) =>
                    tc.name === result.name && tc.status === "calling"
                      ? { ...tc, status: "done" as const, summary: `✓ ${result.name}: ${result.content.slice(0, 60)}${result.content.length > 60 ? "..." : ""}` }
                      : tc,
                  );
                  return { ...m, toolCalls };
                }),
              };
            }),
          );
        },
      );
    },
    [currentSessionId, sending, sendChat, createLocalUserMessage, createLocalAssistantMessage],
  );

  if (conversationsControl.loading) {
    return (
      <div className="flex h-full items-center justify-center" style={{ height: "calc(100% + 3rem)" }}>
        <p className="text-muted-foreground">{t("loading")}</p>
      </div>
    );
  }

  return (
    <div className="flex h-full -m-6" style={{ height: "calc(100% + 3rem)" }}>
      <SessionList
        sessions={localSessions}
        currentSessionId={currentSessionId}
        onSelect={handleSelectSession}
        onNew={handleNewSession}
        onDelete={handleDeleteSession}
      />
      <div className="flex-1 flex flex-col">
        {currentSession ? (
          <>
            <MessageArea messages={currentSession.messages} />
            <ChatInput onSend={handleSendMessage} disabled={sending} />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-muted-foreground">{t("selectSession")}</p>
          </div>
        )}
      </div>
    </div>
  );
}
