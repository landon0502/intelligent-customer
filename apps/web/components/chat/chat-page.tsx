"use client"

import { useState, useEffect, useCallback, useMemo } from "react"
import { useTranslations } from "next-intl"
import useChatServices from "./useServices"
import { SessionList } from "./session-list"
import { ChatContainer } from "./chat-container"

export function ChatPage() {
  const t = useTranslations("chat")
  const { conversationsControl, sessions, createSession, removeSession } =
    useChatServices()

  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null)

  // 自动选中：当 currentSessionId 无效时回退到第一个会话
  const activeSessionId = useMemo(() => {
    if (currentSessionId && sessions.some((s) => s.id === currentSessionId)) {
      return currentSessionId
    }
    return sessions.length > 0 ? sessions[0]!.id : null
  }, [currentSessionId, sessions])

  // 页面加载时获取会话列表
  useEffect(() => {
    conversationsControl.run()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- conversationsControl.run 是稳定引用，仅需挂载时执行一次
  }, [])

  const handleSelectSession = useCallback((id: number) => {
    setCurrentSessionId(id)
  }, [])

  const handleNewSession = useCallback(async () => {
    const newSession = await createSession(t("newSession"))
    if (!newSession) return
    await conversationsControl.runAsync()
    setCurrentSessionId(newSession.id)
  }, [t, createSession, conversationsControl])

  const handleDeleteSession = useCallback(
    async (id: number) => {
      const ok = await removeSession(id)
      if (!ok) return
      await conversationsControl.runAsync()
      setCurrentSessionId((prev) => {
        // 找到下一个会话
        const idx = sessions.findIndex((s) => s.id === id)
        const remaining = sessions.filter((s) => s.id !== id)
        if (prev === id) {
          return remaining[Math.min(idx, remaining.length - 1)]?.id ?? null
        }
        return prev
      })
    },
    [sessions, removeSession, conversationsControl]
  )

  if (conversationsControl.loading) {
    return (
      <div
        className="flex h-full items-center justify-center"
        style={{ height: "calc(100% + 3rem)" }}
      >
        <p className="text-muted-foreground">{t("loading")}</p>
      </div>
    )
  }

  return (
    <div className="-m-6 flex h-full" style={{ height: "calc(100% + 3rem)" }}>
      <SessionList
        sessions={sessions}
        currentSessionId={activeSessionId}
        onSelect={handleSelectSession}
        onNew={handleNewSession}
        onDelete={handleDeleteSession}
      />
      <div className="flex flex-1 flex-col">
        {activeSessionId ? (
          <ChatContainer
            key={activeSessionId}
            conversationId={activeSessionId}
          />
        ) : (
          <div className="flex flex-1 items-center justify-center">
            <p className="text-muted-foreground">{t("selectSession")}</p>
          </div>
        )}
      </div>
    </div>
  )
}
