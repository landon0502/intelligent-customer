"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import type { Session, Message, ToolCall } from "@/config/mock-chat";
import { mockSessions, mockGetAIResponse } from "@/config/mock-chat";
import { SessionList } from "./session-list";
import { MessageArea } from "./message-area";
import { ChatInput } from "./chat-input";

let nextId = 100;
function genId() {
  return `id-${nextId++}`;
}

export function ChatPage() {
  const t = useTranslations("chat");
  const [sessions, setSessions] = useState<Session[]>(mockSessions);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(
    mockSessions[0]?.id ?? null
  );
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    },
    []
  );

  const currentSession = sessions.find((s) => s.id === currentSessionId) ?? null;

  const handleSelectSession = useCallback((id: string) => {
    setCurrentSessionId(id);
  }, []);

  const handleNewSession = useCallback(() => {
    const newSession: Session = {
      id: genId(),
      title: t("newSession"),
      time: new Date().toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }),
      messages: [],
    };
    setSessions((prev) => [newSession, ...prev]);
    setCurrentSessionId(newSession.id);
  }, [t]);

  const handleDeleteSession = useCallback(
    (id: string) => {
      setSessions((prev) => {
        const next = prev.filter((s) => s.id !== id);
        if (id === currentSessionId) {
          setCurrentSessionId(next[0]?.id ?? null);
        }
        return next;
      });
    },
    [currentSessionId]
  );

  const handleSendMessage = useCallback(
    (text: string) => {
      if (!currentSessionId) return;

      const userMsg: Message = {
        id: genId(),
        role: "user",
        content: text,
        time: new Date().toLocaleTimeString("zh-CN", {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };

      const response = mockGetAIResponse(text);
      const assistantId = genId();

      // Step 1: add user message + assistant message (with toolCalls in calling state if any)
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id !== currentSessionId) return s;
          const toolCalls: ToolCall[] | undefined = response.toolCalls
            ? response.toolCalls.map((tc) => ({ ...tc, status: "calling" as const }))
            : undefined;
          const assistantMsg: Message = {
            id: assistantId,
            role: "assistant",
            content: "",
            time: new Date().toLocaleTimeString("zh-CN", {
              hour: "2-digit",
              minute: "2-digit",
            }),
            toolCalls,
          };
          return { ...s, messages: [...s.messages, userMsg, assistantMsg] };
        })
      );

      // Step 2: if toolCalls, show spinner for 1.2s then mark done
      if (response.toolCalls) {
        timerRef.current = setTimeout(() => {
          setSessions((prev) =>
            prev.map((s) => {
              if (s.id !== currentSessionId) return s;
              return {
                ...s,
                messages: s.messages.map((m) => {
                  if (m.id !== assistantId) return m;
                  return {
                    ...m,
                    toolCalls: response.toolCalls!.map((tc) => ({
                      ...tc,
                      status: "done" as const,
                    })),
                  };
                }),
              };
            })
          );

          // Step 3: after 0.4s, start streaming text
          timerRef.current = setTimeout(() => {
            streamResponse(response.content);
          }, 400);
        }, 1200);
      } else {
        streamResponse(response.content);
      }

      function streamResponse(fullText: string) {
        let charIdx = 0;
        function typeChar() {
          if (charIdx < fullText.length) {
            const chunk = Math.min(2, fullText.length - charIdx);
            const nextContent = fullText.slice(0, charIdx + chunk);
            charIdx += chunk;
            setSessions((prev) =>
              prev.map((s) => {
                if (s.id !== currentSessionId) return s;
                return {
                  ...s,
                  messages: s.messages.map((m) => {
                    if (m.id !== assistantId) return m;
                    return { ...m, content: nextContent };
                  }),
                };
              })
            );
            timerRef.current = setTimeout(typeChar, 30);
          }
        }
        typeChar();
      }
    },
    [currentSessionId]
  );

  return (
    <div className="flex h-full -m-6" style={{ height: "calc(100% + 3rem)" }}>
      <SessionList
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelect={handleSelectSession}
        onNew={handleNewSession}
        onDelete={handleDeleteSession}
      />
      <div className="flex-1 flex flex-col">
        {currentSession ? (
          <>
            <MessageArea messages={currentSession.messages} />
            <ChatInput onSend={handleSendMessage} />
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
